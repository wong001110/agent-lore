"""Multi-agent topology and selective challenge routing."""

from lore_common import *  # noqa: F401,F403
from lore_memory import *  # noqa: F401,F403
from lore_registry import *  # noqa: F401,F403


def topology_history(conn: sqlite3.Connection, args: argparse.Namespace) -> dict[str, dict[str, Any]]:
    clauses = ["topology IS NOT NULL"]
    params: list[Any] = []
    for column, value in (
        ("source_project", getattr(args, "project", None)),
        ("module", getattr(args, "module", None)),
        ("task_type", args.type),
        ("task_subtype", getattr(args, "subtype", None)),
        ("language", args.language),
        ("framework", args.framework),
    ):
        if value:
            clauses.append(f"COALESCE({column}, '') = ?")
            params.append(value)
    rows = conn.execute(
        f"""
        SELECT topology,
               COUNT(*) AS runs,
               AVG(CASE WHEN outcome='success' THEN 1.0 ELSE 0.0 END) AS execution_success_rate,
               SUM(CASE WHEN acceptance_status IN ('accepted','not-required') THEN 1 ELSE 0 END) AS accepted,
               SUM(CASE WHEN acceptance_status IN ('accepted','not-required','rework','rejected','invalidated') THEN 1 ELSE 0 END) AS acceptance_observed,
               AVG(COALESCE(quality_score, CASE WHEN outcome='success' THEN 1.0 ELSE 0.0 END)) AS avg_quality,
               AVG(cost_usd) AS avg_cost,
               AVG(COALESCE(wall_time_ms, latency_ms)) AS avg_wall_time,
               AVG(retry_count) AS avg_retries,
               AVG(COALESCE(merge_conflicts, 0)) AS avg_conflicts,
               AVG(COALESCE(agent_count, 1)) AS avg_agents
        FROM runs
        WHERE {' AND '.join(clauses)}
        GROUP BY topology
        """,
        params,
    ).fetchall()
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        observed = int(row["acceptance_observed"] or 0)
        accepted = int(row["accepted"] or 0)
        acceptance_rate = accepted / observed if observed else None
        execution_rate = float(row["execution_success_rate"] or 0.0)
        acceptance_confidence = min(1.0, observed / 8.0)
        effective_success = (
            acceptance_confidence * acceptance_rate + (1.0 - acceptance_confidence) * execution_rate
            if acceptance_rate is not None
            else execution_rate
        )
        result[row["topology"]] = {
            "runs": int(row["runs"]),
            "execution_success_rate": execution_rate,
            "acceptance_observed": observed,
            "acceptance_rate": acceptance_rate,
            "effective_success": effective_success,
            "avg_quality": float(row["avg_quality"] or 0.0),
            "avg_cost": float(row["avg_cost"]) if row["avg_cost"] is not None else None,
            "avg_wall_time": float(row["avg_wall_time"]) if row["avg_wall_time"] is not None else None,
            "avg_retries": float(row["avg_retries"] or 0.0),
            "avg_conflicts": float(row["avg_conflicts"] or 0.0),
            "avg_agents": float(row["avg_agents"] or 1.0),
        }
    return result


def allowed_topologies(args: argparse.Namespace, current_policy: dict[str, Any]) -> list[str]:
    allowed = ["single", "sequential"]
    if args.parallelizable == "yes" and args.estimated_subtasks >= 2 and current_policy["max_agents"] >= 2:
        allowed.append("flat-parallel")
    if (
        args.complexity in ("medium", "high")
        and args.cross_domain
        and current_policy["max_depth"] >= 2
        and current_policy["max_agents"] >= 3
    ):
        allowed.append("lead-worker")
    return list(dict.fromkeys(allowed))


def heuristic_topology(args: argparse.Namespace, current_policy: dict[str, Any]) -> tuple[str, float, list[str]]:
    reasons: list[str] = []
    if args.dependency_level == "high":
        return "sequential", 0.85, ["strong task dependencies favor ordered execution"]
    if (
        args.complexity == "high"
        and args.cross_domain
        and current_policy["max_depth"] >= 2
        and current_policy["max_agents"] >= 3
    ):
        return "lead-worker", 0.75, ["large cross-domain task favors scoped lead/worker hierarchy"]
    if args.parallelizable == "yes" and args.estimated_subtasks >= 2 and current_policy["max_agents"] >= 2:
        return "flat-parallel", 0.75, ["independent subtasks can run in parallel"]
    if args.complexity == "low" and args.estimated_subtasks <= 1:
        return "single", 0.90, ["small task does not justify coordination overhead"]
    reasons.append("no strong decomposition signal; prefer minimal topology")
    return "single", 0.65, reasons


def choose_topology(conn: sqlite3.Connection, args: argparse.Namespace, current_policy: dict[str, Any]) -> dict[str, Any]:
    baseline, baseline_conf, reasons = heuristic_topology(args, current_policy)
    allowed = allowed_topologies(args, current_policy)
    history = topology_history(conn, args)

    ranked_history: list[tuple[float, str, dict[str, Any]]] = []
    observed_costs = [v["avg_cost"] for k, v in history.items() if k in allowed and v["avg_cost"] is not None]
    observed_times = [v["avg_wall_time"] for k, v in history.items() if k in allowed and v["avg_wall_time"] is not None]
    for topology, stats in history.items():
        if topology not in allowed or stats["runs"] < 3:
            continue
        cost_score = minmax_inverse(stats["avg_cost"], observed_costs)
        time_score = minmax_inverse(stats["avg_wall_time"], observed_times)
        retry_score = 1.0 / (1.0 + stats["avg_retries"])
        conflict_score = 1.0 / (1.0 + stats["avg_conflicts"])
        agent_efficiency = 1.0 / max(1.0, stats["avg_agents"] / 2.0)
        utility = (
            0.42 * stats["effective_success"]
            + 0.20 * stats["avg_quality"]
            + 0.10 * cost_score
            + 0.10 * time_score
            + 0.07 * retry_score
            + 0.06 * conflict_score
            + 0.05 * agent_efficiency
        )
        ranked_history.append((utility, topology, stats))
    ranked_history.sort(reverse=True, key=lambda item: item[0])

    if ranked_history:
        utility, learned, stats = ranked_history[0]
        accepted_samples = stats["acceptance_observed"]
        learned_conf = min(0.95, 0.40 + stats["runs"] / 25.0 + accepted_samples / 30.0)
        if learned != baseline and utility >= 0.70 and learned_conf >= 0.60:
            reasons.append(f"historical accepted outcomes favor {learned} over heuristic baseline")
            return {
                "topology": learned,
                "confidence": round(learned_conf, 4),
                "source": "learned",
                "reasons": reasons,
                "allowed": allowed,
                "history": history,
            }
    return {
        "topology": baseline,
        "confidence": round(baseline_conf, 4),
        "source": "heuristic",
        "reasons": reasons,
        "allowed": allowed,
        "history": history,
    }


COORDINATIONS = ("single", "manager-worker", "hierarchical")
SCHEDULES = ("serial", "parallel", "hybrid")
VERIFICATION_TIERS = ("V0", "V1", "V2", "V3", "V4")
SECURITY_DEPTHS = ("none", "smoke", "focused", "deep", "adversarial")


def load_json_object(raw: str | None, label: str) -> dict[str, Any] | None:
    """Accept an inline JSON object or an @path containing one."""
    if raw is None:
        return None
    source = raw
    if raw.startswith("@"):
        path_text = raw[1:].strip()
        if not path_text:
            raise ValueError(f"{label} @path is empty")
        source = Path(path_text).expanduser().read_text(encoding="utf-8")
    try:
        value = json.loads(source)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{label} must be valid JSON: {exc.msg}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object")
    return value


def _text(value: Any, location: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{location} must be a non-empty string")
    return value.strip()


def _strings(value: Any, location: str, required: bool = False) -> list[str]:
    if value is None and not required:
        return []
    if not isinstance(value, list) or (required and not value):
        raise ValueError(f"{location} must be a {'non-empty ' if required else ''}array of strings")
    result = [_text(item, f"{location}[{index}]") for index, item in enumerate(value)]
    return list(dict.fromkeys(result))


def _delegation(value: dict[str, Any]) -> dict[str, Any]:
    raw = value.get("delegation_decision", value.get("delegation"))
    if raw is None:
        return {"explicit": False, "delegate": False, "coordination": "single", "schedule": "serial", "depth": 0}
    decision, coordination, schedule, depth = raw, None, None, None
    if isinstance(raw, dict):
        decision = raw.get("decision", raw.get("delegate", raw.get("recommendation")))
        coordination = raw.get("coordination")
        schedule = raw.get("schedule")
        depth = raw.get("delegation_depth", raw.get("depth"))
    if isinstance(decision, bool):
        delegate = decision
    elif isinstance(decision, str):
        decision = normalize(decision).replace("_", "-")
        if decision in ("single", "no", "false", "none", "do-not-delegate", "no-delegation"):
            delegate = False
        elif decision in ("yes", "true", "delegate", "manager-worker", "hierarchical"):
            delegate = True
            coordination = decision if decision in COORDINATIONS else coordination
        else:
            raise ValueError("TaskShape delegation decision must be single, delegate, manager-worker, or hierarchical")
    elif decision is None and coordination in COORDINATIONS:
        delegate = coordination != "single"
    else:
        raise ValueError("TaskShape delegation decision must explicitly say whether to delegate")
    if coordination is not None and coordination not in COORDINATIONS:
        raise ValueError(f"TaskShape delegation.coordination must be one of {', '.join(COORDINATIONS)}")
    if schedule is not None and schedule not in SCHEDULES:
        raise ValueError(f"TaskShape delegation.schedule must be one of {', '.join(SCHEDULES)}")
    if depth is not None and (isinstance(depth, bool) or not isinstance(depth, int) or depth < 0):
        raise ValueError("TaskShape delegation depth must be a non-negative integer")
    if not delegate:
        if coordination not in (None, "single"):
            raise ValueError("TaskShape cannot decline delegation with non-single coordination")
        return {"explicit": True, "delegate": False, "coordination": "single", "schedule": "serial", "depth": 0}
    depth = 1 if depth is None else depth
    if depth < 1:
        raise ValueError("TaskShape delegated coordination requires depth >= 1")
    coordination = coordination or ("hierarchical" if depth >= 2 else "manager-worker")
    if coordination == "hierarchical" and depth < 2:
        raise ValueError("TaskShape hierarchical coordination requires depth >= 2")
    if coordination == "manager-worker" and depth > 1:
        coordination = "hierarchical"
    return {"explicit": True, "delegate": True, "coordination": coordination, "schedule": schedule, "depth": depth}


def validate_task_shape(value: dict[str, Any]) -> dict[str, Any]:
    objective = _text(value.get("objective"), "TaskShape.objective")
    raw_workstreams = value.get("workstreams")
    if not isinstance(raw_workstreams, list) or not raw_workstreams:
        raise ValueError("TaskShape.workstreams must be a non-empty array")
    workstreams: list[dict[str, Any]] = []
    identifiers: set[str] = set()
    for index, raw in enumerate(raw_workstreams):
        where = f"TaskShape.workstreams[{index}]"
        if not isinstance(raw, dict):
            raise ValueError(f"{where} must be an object")
        identifier = _text(raw.get("id"), f"{where}.id")
        if identifier in identifiers:
            raise ValueError(f"TaskShape workstream id is duplicated: {identifier}")
        identifiers.add(identifier)
        workstreams.append({
            **raw,
            "id": identifier,
            "objective": _text(raw.get("objective", raw.get("name")), f"{where}.objective"),
            "depends_on": _strings(raw.get("depends_on"), f"{where}.depends_on"),
            "read_scope": _strings(raw.get("read_scope"), f"{where}.read_scope"),
            "write_scope": _strings(raw.get("write_scope"), f"{where}.write_scope"),
            "contract_scope": _strings(raw.get("contract_scope"), f"{where}.contract_scope"),
        })
    for item in workstreams:
        unknown = [dep for dep in item["depends_on"] if dep not in identifiers]
        if unknown:
            raise ValueError(f"TaskShape workstream {item['id']} has unknown dependencies: {', '.join(unknown)}")
        if item["id"] in item["depends_on"]:
            raise ValueError(f"TaskShape workstream {item['id']} cannot depend on itself")
    completed: set[str] = set()
    while len(completed) < len(workstreams):
        ready = [item["id"] for item in workstreams if item["id"] not in completed and set(item["depends_on"]) <= completed]
        if not ready:
            unresolved = [item["id"] for item in workstreams if item["id"] not in completed]
            raise ValueError(f"TaskShape dependency graph contains a cycle involving: {', '.join(unresolved)}")
        completed.update(ready)
    normalized = dict(value)
    normalized.update(objective=objective, workstreams=workstreams, delegation_decision=_delegation(value))
    return normalized


def _scope_key(value: str) -> str:
    result = value.strip().replace("\\", "/").rstrip("/").casefold()
    return result[:-2].rstrip("/") if result.endswith("/*") else result


def _scope_conflict(left: dict[str, Any], right: dict[str, Any]) -> bool:
    left_scopes = left["write_scope"] + left["contract_scope"]
    right_scopes = right["write_scope"] + right["contract_scope"]
    for left_raw in left_scopes:
        a = _scope_key(left_raw)
        for right_raw in right_scopes:
            b = _scope_key(right_raw)
            if a == b or a.startswith(f"{b}/") or b.startswith(f"{a}/"):
                return True
    return False


def build_dag_waves(workstreams: list[dict[str, Any]], max_agents: int, force_serial: bool = False) -> tuple[list[list[str]], list[dict[str, str]]]:
    completed: set[str] = set()
    waves: list[list[str]] = []
    conflicts: list[dict[str, str]] = []
    capacity = 1 if force_serial else max(1, max_agents)
    while len(completed) < len(workstreams):
        ready = [item for item in workstreams if item["id"] not in completed and set(item["depends_on"]) <= completed]
        wave: list[dict[str, Any]] = []
        for candidate in ready:
            if len(wave) >= capacity:
                continue
            conflict = next((other for other in wave if _scope_conflict(candidate, other)), None)
            if conflict:
                conflicts.append({"first": conflict["id"], "second": candidate["id"], "reason": "overlapping write_scope or contract_scope"})
                continue
            wave.append(candidate)
        if not wave:
            raise ValueError("TaskShape dependency graph cannot be scheduled")
        wave_ids = [item["id"] for item in wave]
        waves.append(wave_ids)
        completed.update(wave_ids)
    return waves, conflicts


def _actual_schedule(waves: list[list[str]]) -> str:
    if all(len(wave) == 1 for wave in waves):
        return "serial"
    return "parallel" if len(waves) == 1 else "hybrid"


def legacy_topology(coordination: str, schedule: str) -> str:
    if coordination == "single":
        return "single"
    if coordination == "hierarchical":
        return "lead-worker"
    return "sequential" if schedule == "serial" else "flat-parallel"


def execution_plan_from_task_shape(task_shape: dict[str, Any], current_policy: dict[str, Any]) -> dict[str, Any]:
    decision = task_shape["delegation_decision"]
    max_agents = max(1, int(current_policy["max_agents"]))
    max_depth = max(0, int(current_policy["max_depth"]))
    coordination = decision["coordination"]
    depth = min(decision["depth"], max_depth)
    reasons = ["execution plan derived from a validated TaskShape and explicit delegation decision"]
    if decision["depth"] > max_depth:
        reasons.append(f"delegation depth capped by policy.max_depth={max_depth}")
    if coordination != "single" and (max_agents < 2 or depth == 0):
        coordination, depth = "single", 0
        reasons.append("delegation collapsed because policy does not permit another agent or delegation depth")
    elif coordination == "hierarchical" and depth < 2:
        coordination = "manager-worker"
        reasons.append("hierarchical coordination reduced to manager-worker by the depth ceiling")
    requested = decision.get("schedule")
    waves, conflicts = build_dag_waves(task_shape["workstreams"], max_agents, coordination == "single" or requested == "serial")
    schedule = "serial" if coordination == "single" else _actual_schedule(waves)
    if conflicts:
        reasons.append("overlapping write/contract scopes were serialized")
    if requested and requested != schedule:
        reasons.append(f"requested {requested} schedule adjusted to feasible {schedule} schedule")
    return {
        "source": "task-shape", "coordination": coordination, "schedule": schedule,
        "delegation_depth": depth, "waves": waves,
        "dependencies": {item["id"]: item["depends_on"] for item in task_shape["workstreams"]},
        "serialized_scope_conflicts": conflicts, "max_agents": max_agents, "max_depth": max_depth, "reasons": reasons,
    }


def execution_plan_from_legacy(topology: dict[str, Any], args: argparse.Namespace, current_policy: dict[str, Any]) -> dict[str, Any]:
    recommended = topology["topology"]
    if recommended == "flat-parallel":
        coordination, schedule, depth = "manager-worker", "parallel", 1
    elif recommended == "lead-worker":
        coordination, schedule, depth = "hierarchical", "hybrid", min(2, int(current_policy["max_depth"]))
        coordination = coordination if depth >= 2 else "manager-worker" if depth == 1 else "single"
    else:
        coordination, schedule, depth = "single", "serial", 0
    count = max(1, min(args.estimated_subtasks, max(1, int(current_policy["max_agents"]))))
    waves = [[f"workstream-{i + 1}" for i in range(count)]] if schedule == "parallel" else [["task"]]
    return {
        "source": "legacy-heuristic", "coordination": coordination, "schedule": schedule,
        "delegation_depth": depth, "waves": waves, "dependencies": {}, "serialized_scope_conflicts": [],
        "max_agents": max(1, int(current_policy["max_agents"])), "max_depth": max(0, int(current_policy["max_depth"])),
        "reasons": ["no TaskShape supplied; modern execution fields mapped from the legacy heuristic"],
    }


def suggested_evidence_depth(args: argparse.Namespace, task_shape: dict[str, Any] | None) -> tuple[str, str]:
    risk, failure_cost, security_relevant = args.risk, args.cost_of_failure, False
    if task_shape:
        impact = task_shape.get("change_impact") or {}
        if not isinstance(impact, dict):
            raise ValueError("TaskShape.change_impact must be an object")
        risk = impact.get("risk", task_shape.get("risk", risk))
        failure_cost = impact.get("failure_cost", task_shape.get("failure_cost", failure_cost))
        security_relevant = bool(task_shape.get("security_surfaces") or impact.get("security_surfaces") or impact.get("trust_boundary_change") or impact.get("authority_change"))
    levels = ("low", "medium", "high", "critical")
    if risk not in levels or failure_cost not in levels:
        raise ValueError("TaskShape risk and failure_cost must be low, medium, high, or critical")
    summary = f"{args.task} {getattr(args, 'task_canonical', '') or ''} {task_shape['objective'] if task_shape else ''}".casefold()
    security_relevant |= any(word in summary for word in ("auth", "credential", "secret", "tenant", "permission", "security", "payment"))
    severity = max(levels.index(risk), levels.index(failure_cost))
    tier = ("V1", "V2", "V3", "V4")[severity]
    if task_shape and any(item["contract_scope"] for item in task_shape["workstreams"]):
        tier = VERIFICATION_TIERS[max(VERIFICATION_TIERS.index(tier), 2)]
    if security_relevant:
        tier = VERIFICATION_TIERS[max(VERIFICATION_TIERS.index(tier), 3 if severity >= 2 else 2)]
    return tier, ("smoke", "focused", "deep", "adversarial")[severity] if security_relevant else "none"


def make_evidence_plan(args: argparse.Namespace, task_shape: dict[str, Any] | None, supplied: dict[str, Any] | None) -> dict[str, Any]:
    tier, security = suggested_evidence_depth(args, task_shape)
    if supplied is None:
        objective = task_shape["objective"] if task_shape else args.task
        return {
            "source": "generated", "claims": [f"requested behavior is correct: {objective}"],
            "checks": ["run the cheapest targeted deterministic checks that prove the requested behavior"],
            "escalate_if": ["a targeted check fails or leaves material residual uncertainty"],
            "stop_when": "all applicable claims have sufficient deterministic evidence and hard invariants pass",
            "verification_tier": tier, "security_depth": security,
        }
    claims = _strings(supplied.get("claims"), "EvidencePlan.claims", required=True)
    raw_checks = supplied.get("checks")
    if not isinstance(raw_checks, list) or not raw_checks:
        raise ValueError("EvidencePlan.checks must be a non-empty array")
    checks: list[Any] = []
    for index, check in enumerate(raw_checks):
        if isinstance(check, str):
            checks.append(_text(check, f"EvidencePlan.checks[{index}]"))
        elif isinstance(check, dict) and check:
            checks.append(check)
        else:
            raise ValueError(f"EvidencePlan.checks[{index}] must be a non-empty string or object")
    verification_tier = supplied.get("verification_tier", tier)
    security_depth = supplied.get("security_depth", security)
    if verification_tier not in VERIFICATION_TIERS:
        raise ValueError(f"EvidencePlan.verification_tier must be one of {', '.join(VERIFICATION_TIERS)}")
    if security_depth not in SECURITY_DEPTHS:
        raise ValueError(f"EvidencePlan.security_depth must be one of {', '.join(SECURITY_DEPTHS)}")
    stop_when = supplied.get("stop_when", supplied.get("stop"))
    if stop_when is not None:
        stop_when = _text(stop_when, "EvidencePlan.stop_when")
    return {
        **supplied, "source": "provided", "claims": claims, "checks": checks,
        "escalate_if": _strings(supplied.get("escalate_if", supplied.get("escalation")), "EvidencePlan.escalate_if"),
        "stop_when": stop_when, "verification_tier": verification_tier, "security_depth": security_depth,
    }


def risk_value(level: str) -> float:
    return {"low": 0.10, "medium": 0.35, "high": 0.68, "critical": 0.92}[level]


def challenge_policy(
    args: argparse.Namespace,
    current_policy: dict[str, Any],
    task_shape: dict[str, Any] | None = None,
) -> dict[str, Any]:
    impact = (task_shape or {}).get("change_impact") or {}
    risk = impact.get("risk", (task_shape or {}).get("risk", args.risk))
    cost_of_failure = impact.get("failure_cost", (task_shape or {}).get("failure_cost", args.cost_of_failure))
    uncertainty = impact.get("uncertainty", (task_shape or {}).get("uncertainty", args.uncertainty))
    if risk not in ("low", "medium", "high", "critical") or cost_of_failure not in ("low", "medium", "high", "critical"):
        raise ValueError("TaskShape challenge risk and failure_cost must be low, medium, high, or critical")
    if isinstance(uncertainty, bool) or not isinstance(uncertainty, (int, float)) or not 0.0 <= uncertainty <= 1.0:
        raise ValueError("TaskShape uncertainty must be a number between 0 and 1")
    score = (
        0.28 * risk_value(risk)
        + 0.24 * max(0.0, min(1.0, uncertainty))
        + 0.22 * risk_value(cost_of_failure)
    )
    reasons: list[str] = []
    if args.memory_conflict:
        score += 0.18
        reasons.append("current plan conflicts with historical knowledge")
    if args.stale_memory:
        score += 0.08
        reasons.append("relevant historical knowledge is stale")
    if args.deterministic_evidence == "strong":
        score -= 0.25
        reasons.append("strong deterministic evidence reduces need for another model")
    elif args.deterministic_evidence == "weak":
        score -= 0.08
        reasons.append("some deterministic evidence is already available")
    score = max(0.0, min(1.0, score))

    if score < 0.30:
        level_index = 0
    elif score < 0.50:
        level_index = 1
    elif score < 0.72:
        level_index = 2
    else:
        level_index = 3
    level_index = min(level_index, current_policy["max_challenge_level"])
    if args.deterministic_evidence == "strong" and risk != "critical":
        level_index = min(level_index, 1)
    level = CHALLENGE_LEVELS[level_index]
    if not reasons:
        reasons.append("challenge level derived from risk, uncertainty, and failure cost")
    return {"level": level, "score": round(score, 4), "reasons": reasons}


def deterministic_exploration_hint(task: str, candidates: list[dict[str, Any]], exploration_rate: float) -> dict[str, Any] | None:
    if exploration_rate <= 0.0 or len(candidates) < 2:
        return None
    under_sampled = sorted(candidates[1:], key=lambda item: (item["historical_runs"], -item["score"]))
    if not under_sampled:
        return None
    bucket = int(hashlib.sha256(task.encode("utf-8")).hexdigest()[:8], 16) / 0xFFFFFFFF
    if bucket > exploration_rate:
        return None
    challenger = under_sampled[0]
    return {
        "config_id": challenger["config_id"],
        "name": challenger["name"],
        "model": challenger["model"],
        "reason": "deterministic exploration slot for under-sampled configuration",
        "recommended_use": "shadow when possible; do not replace production path for high-risk work without evidence",
    }


def cmd_recommend(args: argparse.Namespace) -> int:
    task_shape_raw = load_json_object(getattr(args, "task_shape_json", None), "TaskShape")
    task_shape = validate_task_shape(task_shape_raw) if task_shape_raw is not None else None
    evidence_raw = load_json_object(getattr(args, "evidence_plan_json", None), "EvidencePlan")
    with connect() as conn:
        current_policy = policy(conn)
        mode = args.mode or current_policy["mode"]
        knowledge = retrieve_rows(conn, args, mark_reuse=False)
        if task_shape is not None:
            execution_plan = execution_plan_from_task_shape(task_shape, current_policy)
            topology = {
                "topology": legacy_topology(execution_plan["coordination"], execution_plan["schedule"]),
                "confidence": 0.9,
                "source": "task-shape",
                "reasons": list(execution_plan["reasons"]),
                "allowed": list(dict.fromkeys(["single", legacy_topology(execution_plan["coordination"], execution_plan["schedule"])])),
                "history": {},
            }
        else:
            topology = choose_topology(conn, args, current_policy)
            execution_plan = execution_plan_from_legacy(topology, args, current_policy)
        verification = make_evidence_plan(args, task_shape, evidence_raw)
        require_delegate = execution_plan["coordination"] != "single"
        configs = rank_configs(conn, args, require_delegate=require_delegate)
        if require_delegate:
            configs = [item for item in configs if int(item.get("max_depth") or 0) >= execution_plan["delegation_depth"]]

        if require_delegate and not configs:
            reason = "no registered configuration supports the recommended delegation depth; falling back to single coordination"
            topology["reasons"].append(reason)
            topology["topology"] = "single"
            topology["confidence"] = min(topology["confidence"], 0.55)
            execution_plan.update(
                coordination="single",
                schedule="serial",
                delegation_depth=0,
                waves=[[item["id"]] for item in task_shape["workstreams"]] if task_shape else [["task"]],
            )
            execution_plan["reasons"].append(reason)
            configs = rank_configs(conn, args, require_delegate=False)

        selected = configs[0] if configs else None
        challenge = challenge_policy(args, current_policy, task_shape)
        exploration = deterministic_exploration_hint(args.task, configs, current_policy["exploration_rate"])

        reasons = list(topology["reasons"])
        if selected:
            if selected["historical_runs"]:
                reasons.append(
                    f"selected {selected['name']} using task-conditioned execution, acceptance, cost, and timing outcomes"
                )
            else:
                reasons.append(f"selected {selected['name']} from cold-start quality/cost/priority priors")
        else:
            reasons.append("no enabled agent configuration is registered; model selection unavailable")
        reasons.extend(challenge["reasons"])

        decision_id = stable_id("route-")
        model_confidence = selected["confidence"] if selected else 0.0
        eligible = mode == "adaptive" and (
            selected is None or model_confidence >= current_policy["min_model_confidence"] or selected["source"] == "bootstrap"
        )
        columns = [
            "id", "created_at", "mode", "source_project", "module", "task_type", "task_subtype", "task_summary",
            "task_summary_canonical", "source_language", "language", "framework", "framework_version", "agent_role",
            "complexity", "risk", "parallelizable", "dependency_level", "cross_domain", "estimated_subtasks",
            "uncertainty", "memory_conflict", "stale_memory", "deterministic_evidence", "cost_of_failure",
            "recommended_topology", "recommended_config_id", "recommended_model", "recommended_harness", "model_score",
            "model_confidence", "topology_confidence", "challenge_level", "challenge_score", "reasons_json", "applied",
            "task_shape_json", "evidence_plan_json", "coordination", "schedule", "delegation_depth",
            "verification_tier", "security_depth",
        ]
        values = [
            decision_id, utc_now(), mode, args.project, args.module, args.type, args.subtype, args.task,
            getattr(args, "task_canonical", None), getattr(args, "source_language", None), args.language, args.framework,
            args.framework_version, args.agent_role, args.complexity, args.risk, args.parallelizable, args.dependency_level,
            1 if args.cross_domain else 0, args.estimated_subtasks, args.uncertainty, 1 if args.memory_conflict else 0,
            1 if args.stale_memory else 0, args.deterministic_evidence, args.cost_of_failure, topology["topology"],
            selected["config_id"] if selected else None, selected["model"] if selected else None,
            selected["harness"] if selected else None, selected["score"] if selected else None, model_confidence,
            topology["confidence"], challenge["level"], challenge["score"], json.dumps(reasons, ensure_ascii=False), 0,
            json.dumps(task_shape, ensure_ascii=False) if task_shape else None, json.dumps(verification, ensure_ascii=False),
            execution_plan["coordination"], execution_plan["schedule"], execution_plan["delegation_depth"],
            verification["verification_tier"], verification["security_depth"],
        ]
        conn.execute(
            f"INSERT INTO routing_decisions({', '.join(columns)}) VALUES ({', '.join('?' for _ in columns)})",
            values,
        )
        conn.commit()

    behavior = {
        "observe": "record this recommendation but do not change execution because of it",
        "assist": "present/surface this recommendation; the parent agent remains the decision maker",
        "adaptive": "eligible for host application within harness capability and budget guardrails; the host still executes it",
    }[mode]

    emit(
        {
            "decision_id": decision_id,
            "mode": mode,
            "behavior": behavior,
            "task": {
                "summary": args.task,
                "canonical_summary": getattr(args, "task_canonical", None),
                "source_language": getattr(args, "source_language", None),
                "project": args.project,
                "module": args.module,
                "type": args.type,
                "subtype": args.subtype,
                "language": args.language,
                "framework": args.framework,
                "framework_version": args.framework_version,
                "agent_role": args.agent_role,
                "complexity": args.complexity,
                "risk": args.risk,
            },
            "knowledge": {
                "count": len(knowledge),
                "items": knowledge,
                "advisory": "Do not let retrieved knowledge override current constraints, deterministic evidence, or newer acceptance feedback.",
            },
            "topology": {
                "recommended": topology["topology"],
                "confidence": topology["confidence"],
                "source": topology["source"],
                "allowed": topology["allowed"],
                "reasons": topology["reasons"],
            },
            "agent_config": selected,
            "alternatives": configs[1:4],
            "exploration": exploration,
            "challenge": challenge,
            "task_shape": task_shape,
            "execution_plan": execution_plan,
            "evidence_plan": verification,
            "verification_tier": verification["verification_tier"],
            "security_depth": verification["security_depth"],
            "eligible_for_host_application": eligible,
            "requires_host_execution": True,
            "applied_by_policy": False,
            "record_outcome_with": f"--route-decision-id {decision_id}",
        }
    )
    return 0
