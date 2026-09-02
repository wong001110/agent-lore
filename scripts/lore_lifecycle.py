"""Knowledge lifecycle and learned-skill materialization."""

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
            "SELECT * FROM experiences WHERE status IN ('candidate', 'active') ORDER BY updated_at DESC"
        ).fetchall()
        for row in rows:
            metrics = lifecycle_metrics(conn, row)
            action = "keep"
            reason = "insufficient accepted/verified evidence for lifecycle change"
            proposed_kind = row["kind"]
            proposed_status = row["status"]

            if (
                row["status"] == "candidate"
                and metrics["accepted_verified_runs"] >= 2
                and metrics["independent_projects"] >= 2
                and metrics["acceptance_ratio"] >= 0.75
                and metrics["freshness"] >= 0.5
                and not metrics["needs_revalidation"]
                and row["trust"] in ("local-verified", "independent-verified")
            ):
                action = "promote-active"
                proposed_status = "active"
                reason = "accepted and verified evidence transferred across projects"

            if (
                proposed_status == "active"
                and row["kind"] == "experience"
                and metrics["accepted_verified_runs"] >= 4
                and metrics["independent_projects"] >= 3
                and metrics["acceptance_ratio"] >= 0.80
                and not metrics["needs_revalidation"]
            ):
                action = "generalize-pattern"
                proposed_kind = "pattern"
                reason = "broad accepted transfer suggests a reusable pattern"

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
            skill_eligible = (
                proposed_status == "active"
                and proposed_kind in ("experience", "pattern")
                and bool(row["solution_summary"])
                and metrics["accepted_verified_runs"] >= 4
                and metrics["independent_projects"] >= 2
                and metrics["acceptance_ratio"] >= 0.80
                and not needs_revalidation
            )

            if args.apply:
                conn.execute(
                    """
                    UPDATE experiences
                    SET utility = ?, status = ?, kind = ?, status_reason = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        metrics["utility"],
                        proposed_status,
                        proposed_kind,
                        reason if action != "keep" else row["status_reason"],
                        utc_now() if action != "keep" else row["updated_at"],
                        row["id"],
                    ),
                )
            else:
                conn.execute("UPDATE experiences SET utility = ? WHERE id = ?", (metrics["utility"], row["id"]))

            actions.append(
                {
                    "id": row["id"],
                    "kind": row["kind"],
                    "status": row["status"],
                    "proposed_kind": proposed_kind,
                    "proposed_status": proposed_status,
                    "action": action,
                    "reason": reason,
                    "metrics": metrics,
                    "needs_revalidation": needs_revalidation,
                    "skill_eligible": skill_eligible,
                }
            )
        conn.commit()

    emit(
        {
            "status": "applied" if args.apply else "preview",
            "count": len(actions),
            "changes": [item for item in actions if item["action"] != "keep" or item["needs_revalidation"] or item["skill_eligible"]],
            "note": "Execution success alone cannot promote knowledge. Automatic promotion requires accepted and verified evidence on the same supporting runs.",
        }
    )
    return 0


def validate_skill_name(name: str) -> str:
    normalized = normalize(name).replace(" ", "-")
    if len(normalized) > 64 or not SKILL_NAME_RE.fullmatch(normalized):
        raise ValueError("skill name must be kebab-case, <=64 chars, with lowercase letters/numbers/hyphens")
    return normalized


def cmd_promote(args: argparse.Namespace) -> int:
    now = utc_now()
    with connect() as conn:
        row = conn.execute("SELECT * FROM experiences WHERE id = ?", (args.id,)).fetchone()
        if not row:
            raise ValueError(f"unknown knowledge id: {args.id}")
        metrics = lifecycle_metrics(conn, row)
        if row["needs_revalidation"]:
            raise ValueError("knowledge needs revalidation after negative feedback; do not promote it yet")
        if metrics["accepted_verified_runs"] < 1:
            raise ValueError("promotion requires at least one supporting run that is both accepted and verified")

        target_kind = args.kind
        knowledge_name = row["knowledge_name"]
        if target_kind == "skill":
            if not row["solution_summary"]:
                raise ValueError("skill promotion requires a solution/procedure summary")
            if not args.name and not knowledge_name:
                raise ValueError("skill promotion requires --name")
            knowledge_name = validate_skill_name(args.name or knowledge_name)
        elif args.name:
            knowledge_name = normalize(args.name).replace(" ", "-")

        conn.execute(
            """
            UPDATE experiences
            SET kind = ?, status = 'active', knowledge_name = ?, status_reason = ?, updated_at = ?
            WHERE id = ?
            """,
            (target_kind, knowledge_name, args.reason or f"explicitly promoted to {target_kind}", now, args.id),
        )
        conn.commit()
    emit({"status": "promoted", "id": args.id, "kind": target_kind, "name": knowledge_name, "metrics": metrics})
    return 0


def cmd_deprecate(args: argparse.Namespace) -> int:
    with connect() as conn:
        exists = conn.execute("SELECT 1 FROM experiences WHERE id = ?", (args.id,)).fetchone()
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
        exists = conn.execute("SELECT 1 FROM experiences WHERE id = ?", (args.id,)).fetchone()
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
                    "name": row["knowledge_name"],
                    "status": row["status"],
                    "task_type": row["task_type"],
                    "task_subtype": row["task_subtype"],
                    "module": row["module"],
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


def materialize_skill(row: sqlite3.Row, root: Path, metrics: dict[str, Any]) -> Path:
    name = validate_skill_name(row["knowledge_name"] or "")
    target = root / name
    target.mkdir(parents=True, exist_ok=True)
    description = row["lesson"].strip().replace("\n", " ")[:900]
    body = f"""---\nname: {name}\ndescription: {json.dumps(description, ensure_ascii=False)}\n---\n\n# {name}\n\nThis is a locally learned Agent Lore skill. Treat it as advisory engineering evidence, not a project constraint.\n\n## Use when\n\n- Project module learned: {row['module'] or 'unspecified'}\n- Task type: {row['task_type'] or 'unspecified'}\n- Task subtype: {row['task_subtype'] or 'unspecified'}\n- Language: {row['language'] or 'unspecified'}\n- Framework: {row['framework'] or 'unspecified'}\n- Framework version learned: {row['framework_version'] or 'unspecified'}\n\n## Learned lesson\n\n{row['lesson']}\n\n## Procedure / successful approach\n\n{row['solution_summary'] or 'No explicit procedure was recorded.'}\n\n## Known failure mode\n\n{row['failure_reason'] or 'No specific failure mode was recorded.'}\n\n## Evidence metadata\n\n- Agent Lore knowledge id: `{row['id']}`\n- Recorded evidence count: {row['evidence_count']}\n- Accepted runs: {metrics['accepted_runs']}\n- Accepted + verified runs: {metrics['accepted_verified_runs']}\n- Rework runs: {metrics['rework_runs']}\n- Rejected runs: {metrics['rejected_runs']}\n- Accepted projects: {metrics['independent_projects']}\n- Utility: {row['utility']}\n- Last verified: {row['last_verified_at'] or 'unknown'}\n\nBefore applying this skill, compare it against current project constraints, dependency versions, deterministic verification, and recent acceptance feedback.\n"""
    (target / "SKILL.md").write_text(body, encoding="utf-8")
    return target / "SKILL.md"


def cmd_materialize(args: argparse.Namespace) -> int:
    p = ensure_dirs()
    files: list[str] = []
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM experiences WHERE kind='skill' AND status='active' AND knowledge_name IS NOT NULL ORDER BY updated_at DESC"
        ).fetchall()
        for row in rows:
            metrics = lifecycle_metrics(conn, row)
            if row["needs_revalidation"] or metrics["accepted_verified_runs"] < 1:
                continue
            files.append(str(materialize_skill(row, p["skills"], metrics)))
    emit(
        {
            "status": "materialized",
            "count": len(files),
            "skills_root": str(p["skills"]),
            "files": files,
            "note": "Only active learned skills with accepted+verified evidence and no revalidation flag are materialized.",
        }
    )
    return 0
