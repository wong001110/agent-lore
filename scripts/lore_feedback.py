"""Human/reviewer acceptance feedback and rework lineage for Agent Lore."""

from lore_common import *  # noqa: F401,F403


VERDICT_TO_STATUS = {
    "accept": "accepted",
    "rework": "rework",
    "reject": "rejected",
    "invalidate": "invalidated",
}


def update_evidence_after_feedback(
    conn: sqlite3.Connection,
    run: sqlite3.Row,
    acceptance_status: str,
    reason: str | None,
) -> None:
    experience_id = run["experience_id"]
    if not experience_id:
        return

    supportive = (
        acceptance_status in ("accepted", "not-required")
        and run["outcome"] == "success"
        and run["verification_status"] in ("passed", "not-required")
    )
    relation = "supports" if supportive else "contradicts" if acceptance_status in ("rework", "rejected", "invalidated") else "related"
    conn.execute(
        "UPDATE experience_evidence SET relation=? WHERE experience_id=? AND run_id=?",
        (relation, experience_id, run["id"]),
    )

    if acceptance_status in ("rework", "rejected", "invalidated"):
        message = f"needs revalidation after {acceptance_status} feedback on {run['id']}"
        if reason:
            message += f": {reason}"
        conn.execute(
            "UPDATE experiences SET needs_revalidation=1, status_reason=?, updated_at=? WHERE id=?",
            (message, utc_now(), experience_id),
        )


def cmd_feedback(args: argparse.Namespace) -> int:
    now = utc_now()
    status = VERDICT_TO_STATUS[args.verdict]
    with connect() as conn:
        run = conn.execute("SELECT * FROM runs WHERE id=?", (args.run_id,)).fetchone()
        if not run:
            raise ValueError(f"unknown run id: {args.run_id}")

        if args.related_run_id:
            related = conn.execute("SELECT 1 FROM runs WHERE id=?", (args.related_run_id,)).fetchone()
            if not related:
                raise ValueError(f"unknown related run id: {args.related_run_id}")

        conn.execute(
            """
            UPDATE runs
            SET acceptance_status=?, acceptance_reason=?, acceptance_source=?,
                accepted_at=CASE WHEN ?='accepted' THEN ? ELSE NULL END
            WHERE id=?
            """,
            (status, args.reason, args.source, status, now, args.run_id),
        )
        feedback_id = stable_id("feedback-")
        conn.execute(
            """
            INSERT INTO run_feedback(id, run_id, created_at, verdict, reason, source, related_run_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (feedback_id, args.run_id, now, args.verdict, args.reason, args.source, args.related_run_id),
        )

        refreshed = conn.execute("SELECT * FROM runs WHERE id=?", (args.run_id,)).fetchone()
        update_evidence_after_feedback(conn, refreshed, status, args.reason)
        conn.commit()

    response: dict[str, Any] = {
        "status": "feedback-recorded",
        "feedback_id": feedback_id,
        "run_id": args.run_id,
        "acceptance_status": status,
        "source": args.source,
        "reason": args.reason,
        "related_run_id": args.related_run_id,
    }
    if status == "rework":
        response["next_step"] = (
            "Record the corrected attempt with --parent-run-id "
            f"{args.run_id}; Agent Lore will preserve the same task group and increment attempt_index."
        )
    if status in ("rejected", "invalidated") and refreshed["experience_id"]:
        response["knowledge_effect"] = "linked knowledge was flagged needs_revalidation instead of being silently trusted"
    emit(response)
    return 0


def acceptance_summary(conn: sqlite3.Connection, clauses: list[str] | None = None, params: list[Any] | None = None) -> dict[str, Any]:
    where = " AND ".join(clauses or ["1=1"])
    values = params or []
    row = conn.execute(
        f"""
        SELECT
            COUNT(*) AS runs,
            SUM(CASE WHEN outcome='success' THEN 1 ELSE 0 END) AS execution_successes,
            SUM(CASE WHEN verification_status IN ('passed','not-required') THEN 1 ELSE 0 END) AS verified,
            SUM(CASE WHEN acceptance_status IN ('accepted','not-required') THEN 1 ELSE 0 END) AS accepted,
            SUM(CASE
                WHEN acceptance_status IN ('accepted','not-required') AND attempt_index=1
                THEN 1 ELSE 0 END) AS first_pass_accepted,
            SUM(CASE
                WHEN acceptance_status IN ('accepted','not-required','rework','rejected','invalidated')
                 AND attempt_index=1
                THEN 1 ELSE 0 END) AS first_pass_observed,
            SUM(CASE WHEN acceptance_status='rework' THEN 1 ELSE 0 END) AS rework,
            SUM(CASE WHEN acceptance_status IN ('rejected','invalidated') THEN 1 ELSE 0 END) AS rejected,
            SUM(CASE WHEN acceptance_status='pending' THEN 1 ELSE 0 END) AS pending
        FROM runs
        WHERE {where}
        """,
        values,
    ).fetchone()
    decided = int(row["accepted"] or 0) + int(row["rework"] or 0) + int(row["rejected"] or 0)
    first_pass_observed = int(row["first_pass_observed"] or 0)
    return {
        "runs": int(row["runs"] or 0),
        "execution_successes": int(row["execution_successes"] or 0),
        "verified": int(row["verified"] or 0),
        "accepted": int(row["accepted"] or 0),
        "first_pass_accepted": int(row["first_pass_accepted"] or 0),
        "rework": int(row["rework"] or 0),
        "rejected": int(row["rejected"] or 0),
        "pending": int(row["pending"] or 0),
        "acceptance_decisions": decided,
        "acceptance_rate": (int(row["accepted"] or 0) / decided) if decided else None,
        "first_pass_observed": first_pass_observed,
        "first_pass_acceptance_rate": (
            int(row["first_pass_accepted"] or 0) / first_pass_observed
            if first_pass_observed
            else None
        ),
    }
