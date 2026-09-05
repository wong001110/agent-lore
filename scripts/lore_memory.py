"""Pull-based historical evidence retrieval and run recording for Agent Lore."""

from lore_common import *  # noqa: F401,F403


def _memory_mode(conn: sqlite3.Connection, args: argparse.Namespace) -> str:
    requested = getattr(args, "memory_mode", None)
    mode = requested or policy(conn)["memory_mode"]
    if mode not in MEMORY_MODES:
        raise ValueError(f"memory mode must be one of {', '.join(MEMORY_MODES)}")
    return mode


def _scope_applicable(row: sqlite3.Row, args: argparse.Namespace) -> bool:
    """Keep project-local evidence from leaking into unrelated repositories."""
    scope = row["knowledge_scope"] or "project"
    requested_project = normalize(getattr(args, "project", None))
    source_project = normalize(row["source_project"])
    requested_module = normalize(getattr(args, "module", None))
    source_module = normalize(row["module"])

    if scope == "global":
        return True
    if scope == "stack":
        language_ok = bool(getattr(args, "language", None)) and normalize(args.language) == normalize(row["language"])
        framework_ok = bool(getattr(args, "framework", None)) and normalize(args.framework) == normalize(row["framework"])
        return language_ok or framework_ok
    if not requested_project or requested_project != source_project:
        return False
    if scope == "project":
        return True
    if scope == "module":
        return bool(requested_module and source_module and requested_module == source_module)
    if scope == "task":
        type_ok = bool(getattr(args, "type", None)) and normalize(args.type) == normalize(row["task_type"])
        subtype = normalize(getattr(args, "subtype", None))
        subtype_ok = not normalize(row["task_subtype"]) or (bool(subtype) and subtype == normalize(row["task_subtype"]))
        return type_ok and subtype_ok
    return False


def _parse_json_list(value: str | None) -> list[str]:
    if not value:
        return []
    try:
        parsed = json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return []
    return [str(item) for item in parsed] if isinstance(parsed, list) else []


def _memory_card(row: sqlite3.Row, mode: str) -> dict[str, Any]:
    card: dict[str, Any] = {
        "id": row["id"],
        "kind": row["kind"],
        "scope": row["knowledge_scope"],
        "scope_ref": row["scope_ref"],
        "family": row["experience_family"],
        "observation": row["observation"] or row["failure_reason"] or row["lesson"],
        "invariant": row["invariant"],
        "root_cause": row["root_cause"] if row["root_cause_status"] in ("established", "disputed") else None,
        "root_cause_status": row["root_cause_status"],
        "applies_when": _parse_json_list(row["applies_when"]),
        "not_proven": _parse_json_list(row["not_proven"]),
        "status": row["status"],
        "trust": row["trust"],
        "last_verified_at": row["last_verified_at"],
    }
    if mode in ("rescue", "proactive"):
        card.update(
            {
                "historical_lesson": row["lesson"],
                "historical_solution": row["solution_summary"],
                "solution_status": row["solution_status"],
                "failure_reason": row["failure_reason"],
            }
        )
    return card


def _approx_tokens(value: Any) -> int:
    rendered = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return max(1, (len(rendered) + 3) // 4)


def retrieve_rows(conn: sqlite3.Connection, args: argparse.Namespace) -> list[dict[str, Any]]:
    mode = _memory_mode(conn, args)
    if mode == "off":
        return []

    current_policy = policy(conn)
    limit = max(1, min(getattr(args, "limit", 5), 20))
    memory_limit = max(0, int(current_policy["active_memory_limit"]))
    token_budget = max(0, int(getattr(args, "memory_token_budget", None) or current_policy["memory_token_budget"]))
    if memory_limit == 0 or token_budget == 0:
        return []

    candidate_limit = min(memory_limit, 10_000)
    result_limit = min(limit, memory_limit)
    rows = conn.execute(
        """
        SELECT * FROM experiences
        WHERE status IN ('candidate', 'active')
          AND kind IN ('experience', 'pattern')
        ORDER BY updated_at DESC
        LIMIT ?
        """,
        (candidate_limit,),
    ).fetchall()

    ranked: list[tuple[float, sqlite3.Row, list[str]]] = []
    for row in rows:
        if not _scope_applicable(row, args):
            continue
        score, reasons = row_score(row, args)
        if score >= 0.75:
            ranked.append((score, row, reasons))
    ranked.sort(key=lambda item: item[0], reverse=True)

    result: list[dict[str, Any]] = []
    used_tokens = 0
    for score, row, reasons in ranked:
        if len(result) >= result_limit:
            break
        warnings: list[str] = []
        if (
            getattr(args, "framework_version", None)
            and row["framework_version"]
            and normalize(args.framework_version) != normalize(row["framework_version"])
        ):
            warnings.append("framework version differs; revalidate before transfer")
        if days_since(row["last_verified_at"] or row["updated_at"]) > 365:
            warnings.append("historical evidence is aging; consider revalidation")
        if row["status"] == "candidate":
            warnings.append("candidate evidence has not been strongly promoted")
        if row["trust"] not in ("local-verified", "independent-verified"):
            warnings.append("low-trust provenance")
        if int(row["needs_revalidation"] or 0):
            warnings.append("linked feedback indicates this knowledge needs revalidation")

        card = _memory_card(row, mode)
        item = {
            **card,
            "score": round(score, 3),
            "task_type": row["task_type"],
            "task_subtype": row["task_subtype"],
            "module": row["module"],
            "source_project": row["source_project"],
            "language": row["language"],
            "framework": row["framework"],
            "framework_version": row["framework_version"],
            "evidence_count": row["evidence_count"],
            "reuse_count": row["reuse_count"],
            "needs_revalidation": bool(row["needs_revalidation"]),
            "match_reasons": reasons,
            "warnings": warnings,
        }
        item_tokens = _approx_tokens(item)
        if result and used_tokens + item_tokens > token_budget:
            break
        result.append(item)
        used_tokens += item_tokens

    return result


def cmd_retrieve(args: argparse.Namespace) -> int:
    with connect() as conn:
        mode = _memory_mode(conn, args)
        current_policy = policy(conn)
        result = retrieve_rows(conn, args)
    emit(
        {
            "query": {
                "task": args.task,
                "task_canonical": getattr(args, "task_canonical", None),
                "source_language": getattr(args, "source_language", None),
                "project": getattr(args, "project", None),
                "module": getattr(args, "module", None),
                "type": args.type,
                "subtype": getattr(args, "subtype", None),
                "language": args.language,
                "framework": args.framework,
                "framework_version": args.framework_version,
                "memory_mode": mode,
                "memory_token_budget": getattr(args, "memory_token_budget", None) or current_policy["memory_token_budget"],
            },
            "count": len(result),
            "knowledge": result,
            "advisory": (
                "Historical knowledge is optional evidence, not an instruction. Guardrail mode hides historical procedures; "
                "rescue/proactive modes may expose them as alternatives only. Retrieval is read-only and current deterministic "
                "evidence plus project constraints remain authoritative."
            ),
        }
    )
    return 0


def cmd_usage(args: argparse.Namespace) -> int:
    """Audit a host usage decision; only actual application increments reuse."""
    now = utc_now()
    source = (args.source or "").strip()
    if not source:
        raise ValueError("usage source must not be empty")

    with connect() as conn:
        conn.execute("BEGIN IMMEDIATE")
        experience = conn.execute(
            "SELECT id, reuse_count FROM experiences WHERE id=?",
            (args.id,),
        ).fetchone()
        if not experience:
            raise ValueError(f"unknown knowledge id: {args.id}")
        if args.run_id:
            run = conn.execute("SELECT 1 FROM runs WHERE id=?", (args.run_id,)).fetchone()
            if not run:
                raise ValueError(f"unknown run id: {args.run_id}")

        usage_id = stable_id("usage-")
        conn.execute(
            """
            INSERT INTO knowledge_usage(id, experience_id, run_id, created_at, decision, reason, source)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (usage_id, args.id, args.run_id, now, args.decision, args.reason, source),
        )
        if args.decision == "applied":
            conn.execute(
                "UPDATE experiences SET reuse_count=reuse_count+1, last_used_at=? WHERE id=?",
                (now, args.id),
            )
        refreshed = conn.execute(
            "SELECT reuse_count, last_used_at FROM experiences WHERE id=?",
            (args.id,),
        ).fetchone()
        conn.commit()

    emit(
        {
            "status": "usage-recorded",
            "usage_id": usage_id,
            "knowledge_id": args.id,
            "run_id": args.run_id,
            "decision": args.decision,
            "source": source,
            "reason": args.reason,
            "reuse_count": int(refreshed["reuse_count"]),
            "last_used_at": refreshed["last_used_at"],
            "knowledge_effect": (
                "reuse incremented"
                if args.decision == "applied"
                else "ignored decision audited without changing reuse or utility"
            ),
        }
    )
    return 0


def outcome_counts(outcome: str) -> tuple[int, int]:
    if outcome == "success":
        return 1, 0
    if outcome == "failure":
        return 0, 1
    return 0, 0


def evidence_relation(args: argparse.Namespace) -> str:
    if args.acceptance_status in ("accepted", "not-required"):
        if args.outcome == "success" and args.verification_status in ("passed", "not-required"):
            return "supports"
        return "related"
    if args.acceptance_status in ("rework", "rejected", "invalidated"):
        return "contradicts"
    return "related"


def _scope_ref(args: argparse.Namespace, project: str) -> str:
    if getattr(args, "scope_ref", None):
        return args.scope_ref
    scope = getattr(args, "knowledge_scope", None) or "project"
    if scope == "module":
        return f"{project}:{args.module or 'unspecified'}"
    if scope == "task":
        return f"{project}:{args.module or 'unspecified'}:{args.type or 'unspecified'}:{args.subtype or 'unspecified'}"
    if scope == "stack":
        return ":".join(part for part in (args.language, args.framework, args.framework_version) if part) or "unspecified-stack"
    return project if scope == "project" else "global"


def record_experience(conn: sqlite3.Connection, args: argparse.Namespace, now: str, project: str, tags: list[str]) -> str | None:
    explicit_knowledge_id = getattr(args, "knowledge_id", None)
    lesson_canonical = getattr(args, "lesson_canonical", None)
    canonical_key = normalize(lesson_canonical) or None
    lesson_text = args.lesson or getattr(args, "observation", None) or getattr(args, "invariant", None) or args.failure_reason

    if explicit_knowledge_id:
        existing = conn.execute("SELECT * FROM experiences WHERE id=?", (explicit_knowledge_id,)).fetchone()
        if not existing:
            raise ValueError(f"unknown knowledge id: {explicit_knowledge_id}")
        lesson_canonical = None
        canonical_key = None
    else:
        if not lesson_text:
            return None
        lesson_key = normalize(lesson_text)
        existing = conn.execute(
            """
            SELECT * FROM experiences
            WHERE (lesson_key = ? OR (? IS NOT NULL AND lesson_canonical_key = ?))
              AND COALESCE(task_type, '') = COALESCE(?, '')
              AND COALESCE(task_subtype, '') = COALESCE(?, '')
              AND COALESCE(module, '') = COALESCE(?, '')
              AND COALESCE(language, '') = COALESCE(?, '')
              AND COALESCE(framework, '') = COALESCE(?, '')
              AND COALESCE(knowledge_scope, 'project') = COALESCE(?, 'project')
              AND status IN ('candidate', 'active')
              AND kind IN ('experience', 'pattern')
            ORDER BY updated_at DESC
            LIMIT 1
            """,
            (
                lesson_key,
                canonical_key,
                canonical_key,
                args.type,
                args.subtype,
                args.module,
                args.language,
                args.framework,
                args.knowledge_scope,
            ),
        ).fetchone()

    successes, failures = outcome_counts(args.outcome)
    verified_now = args.verification_status in ("passed", "not-required")
    applies_when = json.dumps(parse_string_list(getattr(args, "applies_when", None)), ensure_ascii=False)
    not_proven = json.dumps(parse_string_list(getattr(args, "not_proven", None)), ensure_ascii=False)

    if existing:
        experience_id = existing["id"]
        if explicit_knowledge_id:
            conn.execute(
                "UPDATE experiences SET updated_at=?, evidence_count=evidence_count+1, success_count=success_count+?, "
                "failure_count=failure_count+?, last_verified_at=CASE WHEN ? THEN ? ELSE last_verified_at END WHERE id=?",
                (now, successes, failures, 1 if verified_now else 0, now, experience_id),
            )
            return experience_id
        conn.execute(
            """
            UPDATE experiences
            SET updated_at=?, task_summary=?, module=COALESCE(?, module), task_subtype=COALESCE(?, task_subtype),
                framework_version=COALESCE(?, framework_version), failure_reason=COALESCE(?, failure_reason),
                solution_summary=COALESCE(?, solution_summary), task_summary_canonical=COALESCE(?, task_summary_canonical),
                lesson_canonical=COALESCE(?, lesson_canonical), lesson_canonical_key=COALESCE(?, lesson_canonical_key),
                solution_summary_canonical=COALESCE(?, solution_summary_canonical), source_language=COALESCE(?, source_language),
                canonicalizer=COALESCE(?, canonicalizer), canonicalized_at=CASE WHEN ? THEN ? ELSE canonicalized_at END,
                confidence=MAX(confidence, ?), evidence_count=evidence_count+1, success_count=success_count+?,
                failure_count=failure_count+?, last_verified_at=CASE WHEN ? THEN ? ELSE last_verified_at END,
                trust=CASE WHEN trust='untrusted' AND ?='local-verified' THEN 'local-verified' ELSE trust END, tags=?,
                knowledge_scope=COALESCE(?, knowledge_scope), scope_ref=COALESCE(?, scope_ref),
                experience_family=COALESCE(?, experience_family), observation=COALESCE(?, observation),
                invariant=COALESCE(?, invariant), root_cause=COALESCE(?, root_cause),
                root_cause_status=COALESCE(?, root_cause_status), applies_when=CASE WHEN ?!='[]' THEN ? ELSE applies_when END,
                not_proven=CASE WHEN ?!='[]' THEN ? ELSE not_proven END, solution_status=COALESCE(?, solution_status)
            WHERE id=?
            """,
            (
                now, args.task, args.module, args.subtype, args.framework_version, args.failure_reason, args.solution,
                getattr(args, "task_canonical", None), lesson_canonical, canonical_key,
                getattr(args, "solution_canonical", None), getattr(args, "source_language", None),
                getattr(args, "canonicalizer", None),
                1 if any((getattr(args, "task_canonical", None), lesson_canonical, getattr(args, "solution_canonical", None))) else 0,
                now, args.confidence, successes, failures, 1 if verified_now else 0, now, args.trust,
                json.dumps(tags, ensure_ascii=False), args.knowledge_scope, _scope_ref(args, project),
                getattr(args, "experience_family", None), getattr(args, "observation", None), getattr(args, "invariant", None),
                getattr(args, "root_cause", None), getattr(args, "root_cause_status", None), applies_when, applies_when,
                not_proven, not_proven, getattr(args, "solution_status", None), experience_id,
            ),
        )
        return experience_id

    experience_id = stable_id("exp-")
    conn.execute(
        """
        INSERT INTO experiences(
            id, created_at, updated_at, status, source_project, task_type, task_subtype, module, task_summary,
            language, framework, framework_version, lesson, lesson_key, failure_reason, solution_summary,
            confidence, success_count, failure_count, tags, kind, trust, last_verified_at,
            task_summary_canonical, lesson_canonical, lesson_canonical_key, solution_summary_canonical,
            source_language, canonicalizer, canonicalized_at, knowledge_scope, scope_ref, experience_family,
            observation, invariant, root_cause, root_cause_status, applies_when, not_proven, solution_status
        ) VALUES (?, ?, ?, 'candidate', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'experience', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            experience_id, now, now, project, args.type, args.subtype, args.module, args.task, args.language,
            args.framework, args.framework_version, lesson_text, normalize(lesson_text), args.failure_reason, args.solution,
            args.confidence, successes, failures, json.dumps(tags, ensure_ascii=False), args.trust,
            now if verified_now else None, getattr(args, "task_canonical", None), lesson_canonical, canonical_key,
            getattr(args, "solution_canonical", None), getattr(args, "source_language", None),
            getattr(args, "canonicalizer", None),
            now if any((getattr(args, "task_canonical", None), lesson_canonical, getattr(args, "solution_canonical", None))) else None,
            args.knowledge_scope, _scope_ref(args, project), getattr(args, "experience_family", None),
            getattr(args, "observation", None), getattr(args, "invariant", None), getattr(args, "root_cause", None),
            getattr(args, "root_cause_status", "unknown"), applies_when, not_proven,
            getattr(args, "solution_status", "candidate"),
        ),
    )
    return experience_id


def resolve_task_lineage(conn: sqlite3.Connection, args: argparse.Namespace) -> tuple[str, int, sqlite3.Row | None]:
    parent = None
    if args.parent_run_id:
        parent = conn.execute("SELECT * FROM runs WHERE id=?", (args.parent_run_id,)).fetchone()
        if not parent:
            raise ValueError(f"unknown parent run id: {args.parent_run_id}")
        task_group_id = parent["task_group_id"] or parent["id"]
        latest = conn.execute(
            "SELECT COALESCE(MAX(attempt_index), 0) FROM runs WHERE task_group_id=?",
            (task_group_id,),
        ).fetchone()[0]
        return task_group_id, int(latest) + 1, parent
    return args.task_group_id or stable_id("task-"), 1, None


def cmd_record(args: argparse.Namespace) -> int:
    now = utc_now()
    run_id = stable_id("run-")
    tags = parse_tags(args.tags)

    with connect() as conn:
        conn.execute("BEGIN IMMEDIATE")
        task_group_id, attempt_index, parent = resolve_task_lineage(conn, args)
        project = args.project or (parent["source_project"] if parent else None) or infer_project_name()
        if parent:
            args.module = args.module or parent["module"]
            args.type = args.type or parent["task_type"]
            args.subtype = args.subtype or parent["task_subtype"]
            args.language = args.language or parent["language"]
            args.framework = args.framework or parent["framework"]
            args.framework_version = args.framework_version or parent["framework_version"]
            args.agent_role = args.agent_role or parent["agent_role"]
            args.task_canonical = args.task_canonical or parent["task_summary_canonical"]
            args.source_language = args.source_language or parent["source_language"]
            args.canonicalizer = args.canonicalizer or parent["canonicalizer"]

        experience_id = record_experience(conn, args, now, project, tags)
        accepted_at = now if args.acceptance_status == "accepted" else None

        conn.execute(
            """
            INSERT INTO runs(
                id, created_at, source_project, module, task_type, task_subtype, task_summary,
                task_scope, operation, task_group_id, parent_run_id, attempt_index,
                language, framework, framework_version, agent_role, model, harness,
                outcome, verification, verification_status, acceptance_status, acceptance_reason,
                acceptance_source, accepted_at, latency_ms, wall_time_ms, compute_time_ms,
                verification_time_ms, review_time_ms, coordination_time_ms,
                cost_usd, retry_count, notes, tags, experience_id, quality_score, run_kind, topology,
                agent_count, merge_conflicts, challenge_level, challenge_useful, route_decision_id,
                files_touched, lines_changed, modules_touched, has_db_change,
                has_api_contract_change, test_count, task_summary_canonical,
                source_language, canonicalizer, canonicalized_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id, now, project, args.module, args.type, args.subtype, args.task, args.task_scope, args.operation,
                task_group_id, args.parent_run_id, attempt_index, args.language, args.framework, args.framework_version,
                args.agent_role, args.model, args.harness, args.outcome, args.verification, args.verification_status,
                args.acceptance_status, args.acceptance_reason, args.acceptance_source, accepted_at, args.latency_ms,
                args.wall_time_ms, args.compute_time_ms, args.verification_time_ms, args.review_time_ms,
                args.coordination_time_ms, args.cost_usd, args.retries, args.notes, json.dumps(tags, ensure_ascii=False),
                experience_id, args.quality_score, args.run_kind, args.topology, args.agent_count, args.merge_conflicts,
                args.challenge_level, bool_int(args.challenge_useful), args.route_decision_id, args.files_touched,
                args.lines_changed, args.modules_touched, bool_int(args.has_db_change), bool_int(args.has_api_contract_change),
                args.test_count, args.task_canonical, args.source_language, args.canonicalizer,
                now if args.task_canonical else None,
            ),
        )

        if experience_id:
            conn.execute(
                "INSERT OR IGNORE INTO experience_evidence(experience_id, run_id, relation, created_at) VALUES (?, ?, ?, ?)",
                (experience_id, run_id, evidence_relation(args), now),
            )
            if args.acceptance_status in ("rework", "rejected", "invalidated"):
                conn.execute(
                    "UPDATE experiences SET needs_revalidation=1, status_reason=?, updated_at=? WHERE id=?",
                    (f"negative acceptance feedback recorded on {run_id}", now, experience_id),
                )

        if args.acceptance_status != "pending":
            verdict = {
                "accepted": "accept",
                "rework": "rework",
                "rejected": "reject",
                "invalidated": "invalidate",
                "not-required": "accept",
            }.get(args.acceptance_status)
            if verdict:
                conn.execute(
                    "INSERT INTO run_feedback(id, run_id, created_at, verdict, reason, source) VALUES (?, ?, ?, ?, ?, ?)",
                    (stable_id("feedback-"), run_id, now, verdict, args.acceptance_reason, args.acceptance_source or "auto"),
                )

        if args.route_decision_id:
            conn.execute("UPDATE routing_decisions SET outcome_run_id=? WHERE id=?", (run_id, args.route_decision_id))
        conn.commit()

    emit(
        {
            "status": "recorded",
            "run_id": run_id,
            "task_group_id": task_group_id,
            "attempt_index": attempt_index,
            "parent_run_id": args.parent_run_id,
            "experience_id": experience_id,
            "project": project,
            "module": args.module,
            "outcome": args.outcome,
            "verification_status": args.verification_status,
            "acceptance_status": args.acceptance_status,
            "knowledge_scope": args.knowledge_scope if experience_id else None,
            "knowledge_link": "explicit" if args.knowledge_id else ("evidence-capsule" if experience_id else None),
            "note": (
                "Run explicitly linked to existing knowledge; the historical interpretation was not rewritten."
                if experience_id and args.knowledge_id
                else "Run plus a scoped evidence capsule were recorded. Historical procedures remain advisory and are hidden in guardrail mode."
                if experience_id
                else "Run stored for capability/routing statistics; no reusable historical evidence was created."
            ),
        }
    )
    return 0
