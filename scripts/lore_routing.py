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


def risk_value(level: str) -> float:
    return {"low": 0.10, "medium": 0.35, "high": 0.68, "critical": 0.92}[level]


def challenge_policy(args: argparse.Namespace, current_policy: dict[str, Any]) -> dict[str, Any]:
    score = (
        0.28 * risk_value(args.risk)
        + 0.24 * max(0.0, min(1.0, args.uncertainty))
        + 0.22 * risk_value(args.cost_of_failure)
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
    if args.deterministic_evidence == "strong" and args.risk != "critical":
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
    with connect() as conn:
        current_policy = policy(conn)
        mode = args.mode or current_policy["mode"]
        knowledge = retrieve_rows(conn, args, mark_reuse=False)
        topology = choose_topology(conn, args, current_policy)
        require_delegate = topology["topology"] == "lead-worker"
        configs = rank_configs(conn, args, require_delegate=require_delegate)

        if require_delegate and not configs:
            topology["reasons"].append("no registered delegation-capable configuration; falling back from lead-worker")
            topology["topology"] = "sequential" if args.dependency_level == "high" else "single"
            topology["confidence"] = min(topology["confidence"], 0.55)
            configs = rank_configs(conn, args, require_delegate=False)

        selected = configs[0] if configs else None
        challenge = challenge_policy(args, current_policy)
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
        applied = mode == "adaptive" and (
            selected is None or model_confidence >= current_policy["min_model_confidence"] or selected["source"] == "bootstrap"
        )
        conn.execute(
            """
            INSERT INTO routing_decisions(
                id, created_at, mode, source_project, module, task_type, task_subtype, task_summary,
                language, framework, framework_version, agent_role, complexity, risk, parallelizable,
                dependency_level, cross_domain, estimated_subtasks, uncertainty, memory_conflict,
                stale_memory, deterministic_evidence, cost_of_failure, recommended_topology,
                recommended_config_id, recommended_model, recommended_harness, model_score,
                model_confidence, topology_confidence, challenge_level, challenge_score,
                reasons_json, applied
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                decision_id,
                utc_now(),
                mode,
                args.project,
                args.module,
                args.type,
                args.subtype,
                args.task,
                args.language,
                args.framework,
                args.framework_version,
                args.agent_role,
                args.complexity,
                args.risk,
                args.parallelizable,
                args.dependency_level,
                1 if args.cross_domain else 0,
                args.estimated_subtasks,
                args.uncertainty,
                1 if args.memory_conflict else 0,
                1 if args.stale_memory else 0,
                args.deterministic_evidence,
                args.cost_of_failure,
                topology["topology"],
                selected["config_id"] if selected else None,
                selected["model"] if selected else None,
                selected["harness"] if selected else None,
                selected["score"] if selected else None,
                model_confidence,
                topology["confidence"],
                challenge["level"],
                challenge["score"],
                json.dumps(reasons, ensure_ascii=False),
                1 if applied else 0,
            ),
        )
        conn.commit()

    behavior = {
        "observe": "record this recommendation but do not change execution because of it",
        "assist": "present/surface this recommendation; the parent agent remains the decision maker",
        "adaptive": "apply within harness capability and budget guardrails; fall back safely if unsupported",
    }[mode]

    emit(
        {
            "decision_id": decision_id,
            "mode": mode,
            "behavior": behavior,
            "task": {
                "summary": args.task,
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
            "applied_by_policy": applied,
            "record_outcome_with": f"--route-decision-id {decision_id}",
        }
    )
    return 0
