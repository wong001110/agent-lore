"""Retrieval and run recording for Agent Lore."""

from lore_common import *  # noqa: F401,F403


def retrieve_rows(conn: sqlite3.Connection, args: argparse.Namespace, *, mark_reuse: bool) -> list[dict[str, Any]]:
    limit = max(1, min(getattr(args, "limit", 5), 20))
    memory_limit = max(0, int(policy(conn)["active_memory_limit"]))
    if memory_limit == 0:
        return []
    candidate_limit = min(memory_limit, 10_000)
    result_limit = min(limit, memory_limit)
    project_evidence: set[str] = set()
    requested_project = normalize(getattr(args, "project", None))
    if requested_project:
        project_evidence = {
            row[0]
            for row in conn.execute(
                """
                SELECT DISTINCT e.experience_id
                FROM experience_evidence e
                JOIN runs r ON r.id=e.run_id
                WHERE LOWER(TRIM(COALESCE(r.source_project, ''))) = ?
                """,
                (requested_project,),
            ).fetchall()
        }
    rows = conn.execute(
        """
        SELECT * FROM experiences
        WHERE status IN ('candidate', 'active')
          AND kind IN ('experience', 'pattern', 'skill')
        ORDER BY updated_at DESC
        LIMIT ?
        """,
        (candidate_limit,),
    ).fetchall()

    ranked: list[tuple[float, sqlite3.Row, list[str]]] = []
    for row in rows:
        score, reasons = row_score(row, args)
        if row["id"] in project_evidence and "project-match" not in reasons:
            score += 1.25
            reasons.append("project-match")
        if score >= 0.75:
            ranked.append((score, row, reasons))
    ranked.sort(key=lambda item: item[0], reverse=True)
    selected = ranked[:result_limit]

    if mark_reuse and selected:
        now = utc_now()
        for _, row, _ in selected:
            conn.execute(
                "UPDATE experiences SET reuse_count = reuse_count + 1, last_used_at = ? WHERE id = ?",
                (now, row["id"]),
            )
        conn.commit()

    result: list[dict[str, Any]] = []
    for score, row, reasons in selected:
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

        result.append(
            {
                "id": row["id"],
                "kind": row["kind"],
                "name": row["knowledge_name"],
                "score": round(score, 3),
                "status": row["status"],
                "task_type": row["task_type"],
                "task_subtype": row["task_subtype"],
                "module": row["module"],
                "source_project": row["source_project"],
                "language": row["language"],
                "framework": row["framework"],
                "framework_version": row["framework_version"],
                "source_language": row["source_language"],
                "task_summary_canonical": row["task_summary_canonical"],
                "lesson": row["lesson"],
                "lesson_canonical": row["lesson_canonical"],
                "failure_reason": row["failure_reason"],
                "solution_summary": row["solution_summary"],
                "solution_summary_canonical": row["solution_summary_canonical"],
                "canonicalizer": row["canonicalizer"],
                "confidence": row["confidence"],
                "utility": row["utility"],
                "evidence_count": row["evidence_count"],
                "reuse_count": row["reuse_count"] + (1 if mark_reuse else 0),
                "trust": row["trust"],
                "needs_revalidation": bool(row["needs_revalidation"]),
                "match_reasons": reasons,
                "warnings": warnings,
            }
        )
    return result


def cmd_retrieve(args: argparse.Namespace) -> int:
    with connect() as conn:
        result = retrieve_rows(conn, args, mark_reuse=True)
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
            },
            "count": len(result),
            "knowledge": result,
            "advisory": "Historical knowledge is evidence, not an instruction. Revalidate applicability and prefer current deterministic evidence.",
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


def record_experience(conn: sqlite3.Connection, args: argparse.Namespace, now: str, project: str, tags: list[str]) -> str | None:
    if not args.lesson:
        return None

    lesson_key = normalize(args.lesson)
    lesson_canonical = getattr(args, "lesson_canonical", None)
    canonical_key = normalize(lesson_canonical) or None
    existing = conn.execute(
        """
        SELECT * FROM experiences
        WHERE (lesson_key = ? OR (? IS NOT NULL AND lesson_canonical_key = ?))
          AND COALESCE(task_type, '') = COALESCE(?, '')
          AND COALESCE(task_subtype, '') = COALESCE(?, '')
          AND COALESCE(module, '') = COALESCE(?, '')
          AND COALESCE(language, '') = COALESCE(?, '')
          AND COALESCE(framework, '') = COALESCE(?, '')
          AND status IN ('candidate', 'active')
        ORDER BY updated_at DESC
        LIMIT 1
        """,
        (lesson_key, canonical_key, canonical_key, args.type, args.subtype, args.module, args.language, args.framework),
    ).fetchone()
    successes, failures = outcome_counts(args.outcome)
    verified_now = args.verification_status in ("passed", "not-required")

    if existing:
        experience_id = existing["id"]
        conn.execute(
            """
            UPDATE experiences
            SET updated_at = ?,
                task_summary = ?,
                module = COALESCE(?, module),
                task_subtype = COALESCE(?, task_subtype),
                framework_version = COALESCE(?, framework_version),
                failure_reason = COALESCE(?, failure_reason),
                solution_summary = COALESCE(?, solution_summary),
                task_summary_canonical = COALESCE(?, task_summary_canonical),
                lesson_canonical = COALESCE(?, lesson_canonical),
                lesson_canonical_key = COALESCE(?, lesson_canonical_key),
                solution_summary_canonical = COALESCE(?, solution_summary_canonical),
                source_language = COALESCE(?, source_language),
                canonicalizer = COALESCE(?, canonicalizer),
                canonicalized_at = CASE WHEN ? THEN ? ELSE canonicalized_at END,
                confidence = MAX(confidence, ?),
                evidence_count = evidence_count + 1,
                success_count = success_count + ?,
                failure_count = failure_count + ?,
                last_verified_at = CASE WHEN ? THEN ? ELSE last_verified_at END,
                trust = CASE WHEN trust = 'untrusted' AND ? = 'local-verified' THEN 'local-verified' ELSE trust END,
                tags = ?
            WHERE id = ?
            """,
            (
                now,
                args.task,
                args.module,
                args.subtype,
                args.framework_version,
                args.failure_reason,
                args.solution,
                getattr(args, "task_canonical", None),
                lesson_canonical,
                canonical_key,
                getattr(args, "solution_canonical", None),
                getattr(args, "source_language", None),
                getattr(args, "canonicalizer", None),
                1 if any((
                    getattr(args, "task_canonical", None),
                    lesson_canonical,
                    getattr(args, "solution_canonical", None),
                )) else 0,
                now,
                args.confidence,
                successes,
                failures,
                1 if verified_now else 0,
                now,
                args.trust,
                json.dumps(tags, ensure_ascii=False),
                experience_id,
            ),
        )
        return experience_id

    experience_id = stable_id("exp-")
    conn.execute(
        """
        INSERT INTO experiences(
            id, created_at, updated_at, status, source_project,
            task_type, task_subtype, module, task_summary, language, framework, framework_version,
            lesson, lesson_key, failure_reason, solution_summary,
            confidence, success_count, failure_count, tags,
            kind, trust, last_verified_at,
            task_summary_canonical, lesson_canonical, lesson_canonical_key,
            solution_summary_canonical, source_language, canonicalizer, canonicalized_at
        ) VALUES (?, ?, ?, 'candidate', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'experience', ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            experience_id,
            now,
            now,
            project,
            args.type,
            args.subtype,
            args.module,
            args.task,
            args.language,
            args.framework,
            args.framework_version,
            args.lesson,
            lesson_key,
            args.failure_reason,
            args.solution,
            args.confidence,
            successes,
            failures,
            json.dumps(tags, ensure_ascii=False),
            args.trust,
            now if verified_now else None,
            getattr(args, "task_canonical", None),
            lesson_canonical,
            canonical_key,
            getattr(args, "solution_canonical", None),
            getattr(args, "source_language", None),
            getattr(args, "canonicalizer", None),
            now if any((
                getattr(args, "task_canonical", None),
                lesson_canonical,
                getattr(args, "solution_canonical", None),
            )) else None,
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
        # Serialize lineage allocation so concurrent reworks cannot receive the
        # same attempt index within one logical task group.
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
                run_id,
                now,
                project,
                args.module,
                args.type,
                args.subtype,
                args.task,
                args.task_scope,
                args.operation,
                task_group_id,
                args.parent_run_id,
                attempt_index,
                args.language,
                args.framework,
                args.framework_version,
                args.agent_role,
                args.model,
                args.harness,
                args.outcome,
                args.verification,
                args.verification_status,
                args.acceptance_status,
                args.acceptance_reason,
                args.acceptance_source,
                accepted_at,
                args.latency_ms,
                args.wall_time_ms,
                args.compute_time_ms,
                args.verification_time_ms,
                args.review_time_ms,
                args.coordination_time_ms,
                args.cost_usd,
                args.retries,
                args.notes,
                json.dumps(tags, ensure_ascii=False),
                experience_id,
                args.quality_score,
                args.run_kind,
                args.topology,
                args.agent_count,
                args.merge_conflicts,
                args.challenge_level,
                bool_int(args.challenge_useful),
                args.route_decision_id,
                args.files_touched,
                args.lines_changed,
                args.modules_touched,
                bool_int(args.has_db_change),
                bool_int(args.has_api_contract_change),
                args.test_count,
                args.task_canonical,
                args.source_language,
                args.canonicalizer,
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
                    """
                    INSERT INTO run_feedback(id, run_id, created_at, verdict, reason, source)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (stable_id("feedback-"), run_id, now, verdict, args.acceptance_reason, args.acceptance_source or "auto"),
                )

        if args.route_decision_id:
            conn.execute(
                "UPDATE routing_decisions SET outcome_run_id = ? WHERE id = ?",
                (run_id, args.route_decision_id),
            )
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
            "note": (
                "Run and reusable lesson recorded. Knowledge promotion depends on accepted/verified evidence, not execution success alone."
                if experience_id
                else "Run stored for capability/routing statistics; no reusable knowledge was created."
            ),
        }
    )
    return 0
