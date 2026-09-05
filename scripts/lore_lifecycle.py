"""Knowledge lifecycle for scoped evidence and reusable patterns."""

from lore_common import *  # noqa: F401,F403
from lore_memory import *  # noqa: F401,F403


def accepted_evidence_metrics(conn: sqlite3.Connection, experience_id: str) -> dict[str, Any]:
    row = conn.execute(
        """
        SELECT
            COUNT(*) AS linked_runs,
            SUM(CASE WHEN r.verification_status IN ('passed','not-required') THEN 1 ELSE 0 END) AS verified_runs,
            SUM(CASE WHEN r.acceptance_status IN ('accepted','not-required') THEN 1 ELSE 0 END) AS accepted_runs,
            SUM(CASE
                WHEN r.acceptance_status IN ('accepted','not-required')
                 AND r.verification_status IN ('passed','not-required')
                 AND r.outcome='success'
                THEN 1 ELSE 0 END) AS accepted_verified_runs,
            SUM(CASE WHEN r.acceptance_status='rework' THEN 1 ELSE 0 END) AS rework_runs,
            SUM(CASE WHEN r.acceptance_status IN ('rejected','invalidated') THEN 1 ELSE 0 END) AS rejected_runs,
            COUNT(DISTINCT CASE
                WHEN r.acceptance_status IN ('accepted','not-required')
                 AND r.verification_status IN ('passed','not-required')
                 AND r.outcome='success'
                THEN COALESCE(r.source_project, '') END) AS accepted_projects
        FROM experience_evidence e
        JOIN runs r ON r.id=e.run_id
        WHERE e.experience_id=?
        """,
        (experience_id,),
    ).fetchone()
    accepted = int(row["accepted_runs"] or 0)
    accepted_verified = int(row["accepted_verified_runs"] or 0)
    rework = int(row["rework_runs"] or 0)
    rejected = int(row["rejected_runs"] or 0)
    decided = accepted + rework + rejected
    return {
        "linked_runs": int(row["linked_runs"] or 0),
        "verified_runs": int(row["verified_runs"] or 0),
        "accepted_runs": accepted,
        "accepted_verified_runs": accepted_verified,
        "rework_runs": rework,
        "rejected_runs": rejected,
        "accepted_projects": int(row["accepted_projects"] or 0),
        "acceptance_decisions": decided,
        "acceptance_ratio": (accepted / decided) if decided else 0.5,
    }


def independent_projects(conn: sqlite3.Connection, experience_id: str, fallback: str | None) -> int:
    metrics = accepted_evidence_metrics(conn, experience_id)
    return int(metrics["accepted_projects"])


def lifecycle_metrics(conn: sqlite3.Connection, row: sqlite3.Row) -> dict[str, Any]:
    evidence_metrics = accepted_evidence_metrics(conn, row["id"])
    projects = int(evidence_metrics["accepted_projects"])
    freshness = freshness_value(row["last_verified_at"] or row["updated_at"])
    accepted_evidence = min(1.0, evidence_metrics["accepted_verified_runs"] / 5.0)
    project_diversity = min(1.0, projects / 3.0)
    reuse = min(1.0, int(row["reuse_count"]) / 5.0)
    verification_ratio = (
        evidence_metrics["accepted_verified_runs"] / evidence_metrics["accepted_runs"]
        if evidence_metrics["accepted_runs"]
        else 0.5
    )
    utility = (
        0.32 * evidence_metrics["acceptance_ratio"]
        + 0.18 * verification_ratio
        + 0.18 * accepted_evidence
        + 0.15 * project_diversity
        + 0.09 * reuse
        + 0.08 * freshness
    )
    if int(row["needs_revalidation"] or 0):
        utility *= 0.65
    return {
        "acceptance_ratio": round(evidence_metrics["acceptance_ratio"], 4),
        "accepted_runs": evidence_metrics["accepted_runs"],
        "accepted_verified_runs": evidence_metrics["accepted_verified_runs"],
        "rework_runs": evidence_metrics["rework_runs"],
        "rejected_runs": evidence_metrics["rejected_runs"],
        "verified_runs": evidence_metrics["verified_runs"],
        "independent_projects": projects,
        "freshness": round(freshness, 4),
        "needs_revalidation": bool(row["needs_revalidation"]),
        "utility": round(max(0.0, min(1.0, utility)), 4),
    }


def cmd_consolidate(args: argparse.Namespace) -> int:
    actions: list[dict[str, Any]] = []
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM experiences WHERE status IN ('candidate', 'active') AND kind IN ('experience','pattern') ORDER BY updated_at DESC"
        ).fetchall()
        for row in rows:
            metrics = lifecycle_metrics(conn, row)
            action = "keep"
            reason = "insufficient accepted/verified evidence for lifecycle change"
            proposed_kind = row["kind"]
            proposed_status = row["status"]

            # Project/module evidence may become active locally without proving
            # cross-project transfer. Broader scopes require broader evidence.
            scope = row["knowledge_scope"] or "project"
            required_projects = 1 if scope in ("task", "module", "project") else 2
            if (
                row["status"] == "candidate"
                and metrics["accepted_verified_runs"] >= 2
                and metrics["independent_projects"] >= required_projects
                and metrics["acceptance_ratio"] >= 0.75
                and metrics["freshness"] >= 0.5
                and not metrics["needs_revalidation"]
                and row["trust"] in ("local-verified", "independent-verified")
            ):
                action = "promote-active"
                proposed_status = "active"
                reason = "accepted and verified evidence supports use within its declared scope"

            if (
                proposed_status == "active"
                and row["kind"] == "experience"
                and metrics["accepted_verified_runs"] >= 4
                and metrics["independent_projects"] >= (3 if scope in ("stack", "global") else 1)
                and metrics["acceptance_ratio"] >= 0.80
                and not metrics["needs_revalidation"]
            ):
                action = "generalize-pattern"
                proposed_kind = "pattern"
                reason = "repeated accepted evidence supports a reusable pattern inside the declared scope"

            if (
                row["status"] == "candidate"
                and int(row["evidence_count"]) <= 1
                and int(row["reuse_count"]) == 0
                and days_since(row["updated_at"]) > 730
            ):
                action = "archive"
                proposed_status = "archived"
                reason = "single-use stale candidate with no reuse"

            needs_revalidation = bool(row["needs_revalidation"]) or days_since(row["last_verified_at"] or row["updated_at"]) > 365

            if args.apply:
                conn.execute(
                    """
                    UPDATE experiences
                    SET utility=?, status=?, kind=?, status_reason=?, updated_at=?
                    WHERE id=?
                    """,
                    (
                        metrics["utility"], proposed_status, proposed_kind,
                        reason if action != "keep" else row["status_reason"],
                        utc_now() if action != "keep" else row["updated_at"], row["id"],
                    ),
                )
            else:
                conn.execute("UPDATE experiences SET utility=? WHERE id=?", (metrics["utility"], row["id"]))

            actions.append(
                {
                    "id": row["id"],
                    "kind": row["kind"],
                    "scope": scope,
                    "status": row["status"],
                    "proposed_kind": proposed_kind,
                    "proposed_status": proposed_status,
                    "action": action,
                    "reason": reason,
                    "metrics": metrics,
                    "needs_revalidation": needs_revalidation,
                }
            )
        conn.commit()

    emit(
        {
            "status": "applied" if args.apply else "preview",
            "count": len(actions),
            "changes": [item for item in actions if item["action"] != "keep" or item["needs_revalidation"]],
            "note": (
                "Execution success alone cannot promote knowledge. Agent Lore stops at scoped experiences/patterns; "
                "learned procedures are not materialized into Agent Skills."
            ),
        }
    )
    return 0


def cmd_promote(args: argparse.Namespace) -> int:
    """Explicitly promote evidence to a pattern/eval; learned Skill output is legacy-only."""
    now = utc_now()
    with connect() as conn:
        row = conn.execute("SELECT * FROM experiences WHERE id=?", (args.id,)).fetchone()
        if not row:
            raise ValueError(f"unknown knowledge id: {args.id}")
        if row["kind"] == "skill":
            raise ValueError("legacy learned skills are read-only; create a scoped experience/pattern instead")
        metrics = lifecycle_metrics(conn, row)
        if row["needs_revalidation"]:
            raise ValueError("knowledge needs revalidation after negative feedback; do not promote it yet")
        if metrics["accepted_verified_runs"] < 1:
            raise ValueError("promotion requires at least one supporting run that is both accepted and verified")

        target_kind = args.kind
        knowledge_name = normalize(args.name).replace(" ", "-") if args.name else row["knowledge_name"]
        conn.execute(
            """
            UPDATE experiences
            SET kind=?, status='active', knowledge_name=?, status_reason=?, updated_at=?
            WHERE id=?
            """,
            (target_kind, knowledge_name, args.reason or f"explicitly promoted to {target_kind}", now, args.id),
        )
        conn.commit()
    emit({"status": "promoted", "id": args.id, "kind": target_kind, "name": knowledge_name, "metrics": metrics})
    return 0


def cmd_deprecate(args: argparse.Namespace) -> int:
    with connect() as conn:
        exists = conn.execute("SELECT 1 FROM experiences WHERE id=?", (args.id,)).fetchone()
        if not exists:
            raise ValueError(f"unknown knowledge id: {args.id}")
        conn.execute(
            "UPDATE experiences SET status='deprecated', status_reason=?, superseded_by=?, updated_at=? WHERE id=?",
            (args.reason, args.superseded_by, utc_now(), args.id),
        )
        conn.commit()
    emit({"status": "deprecated", "id": args.id, "reason": args.reason, "superseded_by": args.superseded_by})
    return 0


def cmd_archive(args: argparse.Namespace) -> int:
    with connect() as conn:
        exists = conn.execute("SELECT 1 FROM experiences WHERE id=?", (args.id,)).fetchone()
        if not exists:
            raise ValueError(f"unknown knowledge id: {args.id}")
        conn.execute(
            "UPDATE experiences SET status='archived', status_reason=?, updated_at=? WHERE id=?",
            (args.reason, utc_now(), args.id),
        )
        conn.commit()
    emit({"status": "archived", "id": args.id, "reason": args.reason})
    return 0


def cmd_knowledge(args: argparse.Namespace) -> int:
    clauses = ["1=1"]
    params: list[Any] = []
    if args.status:
        clauses.append("status = ?")
        params.append(args.status)
    if args.kind:
        clauses.append("kind = ?")
        params.append(args.kind)
    if args.type:
        clauses.append("task_type = ?")
        params.append(args.type)
    if getattr(args, "scope", None):
        clauses.append("knowledge_scope = ?")
        params.append(args.scope)
    with connect() as conn:
        rows = conn.execute(
            f"SELECT * FROM experiences WHERE {' AND '.join(clauses)} ORDER BY updated_at DESC LIMIT ?",
            (*params, max(1, min(args.limit, 500))),
        ).fetchall()
        items = []
        for row in rows:
            metrics = lifecycle_metrics(conn, row)
            items.append(
                {
                    "id": row["id"],
                    "kind": row["kind"],
                    "legacy_read_only": row["kind"] == "skill",
                    "name": row["knowledge_name"],
                    "status": row["status"],
                    "scope": row["knowledge_scope"],
                    "scope_ref": row["scope_ref"],
                    "family": row["experience_family"],
                    "task_type": row["task_type"],
                    "task_subtype": row["task_subtype"],
                    "module": row["module"],
                    "observation": row["observation"] or row["failure_reason"] or row["lesson"],
                    "invariant": row["invariant"],
                    "root_cause": row["root_cause"],
                    "root_cause_status": row["root_cause_status"],
                    "applies_when": _parse_json_list(row["applies_when"]),
                    "not_proven": _parse_json_list(row["not_proven"]),
                    "historical_solution": row["solution_summary"],
                    "solution_status": row["solution_status"],
                    "lesson": row["lesson"],
                    "lesson_canonical": row["lesson_canonical"],
                    "source_language": row["source_language"],
                    "canonicalizer": row["canonicalizer"],
                    "utility": row["utility"],
                    "evidence_count": row["evidence_count"],
                    "reuse_count": row["reuse_count"],
                    "trust": row["trust"],
                    "needs_revalidation": bool(row["needs_revalidation"]),
                    "status_reason": row["status_reason"],
                    "acceptance_metrics": metrics,
                }
            )
    emit({"count": len(items), "knowledge": items})
    return 0
