"""Knowledge lifecycle and learned-skill materialization."""

from lore_common import *  # noqa: F401,F403
from lore_memory import *  # noqa: F401,F403

def independent_projects(conn: sqlite3.Connection, experience_id: str, fallback: str | None) -> int:
    count = conn.execute(
        """
        SELECT COUNT(DISTINCT COALESCE(r.source_project, ''))
        FROM experience_evidence e
        JOIN runs r ON r.id = e.run_id
        WHERE e.experience_id = ? AND COALESCE(r.source_project, '') <> ''
        """,
        (experience_id,),
    ).fetchone()[0]
    if count == 0 and fallback:
        return 1
    return int(count)


def lifecycle_metrics(conn: sqlite3.Connection, row: sqlite3.Row) -> dict[str, Any]:
    support_total = int(row["success_count"]) + int(row["failure_count"])
    success_ratio = int(row["success_count"]) / support_total if support_total else 0.5
    projects = independent_projects(conn, row["id"], row["source_project"])
    freshness = freshness_value(row["last_verified_at"] or row["updated_at"])
    evidence = min(1.0, int(row["evidence_count"]) / 5.0)
    project_diversity = min(1.0, projects / 3.0)
    reuse = min(1.0, int(row["reuse_count"]) / 5.0)
    utility = (
        0.35 * success_ratio
        + 0.20 * evidence
        + 0.20 * project_diversity
        + 0.15 * reuse
        + 0.10 * freshness
    )
    return {
        "success_ratio": round(success_ratio, 4),
        "independent_projects": projects,
        "freshness": round(freshness, 4),
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
            reason = "insufficient evidence for lifecycle change"
            proposed_kind = row["kind"]
            proposed_status = row["status"]

            if (
                row["status"] == "candidate"
                and int(row["evidence_count"]) >= 3
                and metrics["independent_projects"] >= 2
                and metrics["success_ratio"] >= 0.75
                and metrics["freshness"] >= 0.5
                and row["trust"] in ("local-verified", "independent-verified")
            ):
                action = "promote-active"
                proposed_status = "active"
                reason = "repeated successful evidence across projects"

            if (
                proposed_status == "active"
                and row["kind"] == "experience"
                and int(row["evidence_count"]) >= 5
                and metrics["independent_projects"] >= 3
                and metrics["success_ratio"] >= 0.80
            ):
                action = "generalize-pattern"
                proposed_kind = "pattern"
                reason = "broad repeated transfer suggests a reusable pattern"

            if (
                row["status"] == "candidate"
                and int(row["evidence_count"]) <= 1
                and int(row["reuse_count"]) == 0
                and days_since(row["updated_at"]) > 730
            ):
                action = "archive"
                proposed_status = "archived"
                reason = "single-use stale candidate with no reuse"

            needs_revalidation = days_since(row["last_verified_at"] or row["updated_at"]) > 365
            skill_eligible = (
                proposed_status == "active"
                and proposed_kind in ("experience", "pattern")
                and bool(row["solution_summary"])
                and int(row["evidence_count"]) >= 5
                and metrics["independent_projects"] >= 2
                and metrics["success_ratio"] >= 0.80
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
            "note": "Automatic consolidation is conservative. Deprecation and skill promotion remain explicit operations.",
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
    emit({"status": "promoted", "id": args.id, "kind": target_kind, "name": knowledge_name})
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
    emit(
        {
            "count": len(rows),
            "knowledge": [
                {
                    "id": row["id"],
                    "kind": row["kind"],
                    "name": row["knowledge_name"],
                    "status": row["status"],
                    "task_type": row["task_type"],
                    "lesson": row["lesson"],
                    "utility": row["utility"],
                    "evidence_count": row["evidence_count"],
                    "reuse_count": row["reuse_count"],
                    "trust": row["trust"],
                    "status_reason": row["status_reason"],
                }
                for row in rows
            ],
        }
    )
    return 0


def materialize_skill(row: sqlite3.Row, root: Path) -> Path:
    name = validate_skill_name(row["knowledge_name"] or "")
    target = root / name
    target.mkdir(parents=True, exist_ok=True)
    description = row["lesson"].strip().replace("\n", " ")[:900]
    body = f"""---\nname: {name}\ndescription: {json.dumps(description, ensure_ascii=False)}\n---\n\n# {name}\n\nThis is a locally learned Agent Lore skill. Treat it as advisory engineering evidence, not a project constraint.\n\n## Use when\n\n- Task type: {row['task_type'] or 'unspecified'}\n- Language: {row['language'] or 'unspecified'}\n- Framework: {row['framework'] or 'unspecified'}\n- Framework version learned: {row['framework_version'] or 'unspecified'}\n\n## Learned lesson\n\n{row['lesson']}\n\n## Procedure / successful approach\n\n{row['solution_summary'] or 'No explicit procedure was recorded.'}\n\n## Known failure mode\n\n{row['failure_reason'] or 'No specific failure mode was recorded.'}\n\n## Evidence metadata\n\n- Agent Lore knowledge id: `{row['id']}`\n- Evidence count: {row['evidence_count']}\n- Success count: {row['success_count']}\n- Failure count: {row['failure_count']}\n- Utility: {row['utility']}\n- Last verified: {row['last_verified_at'] or 'unknown'}\n\nBefore applying this skill, compare it against the current project constraints, dependency versions, and deterministic verification.\n"""
    (target / "SKILL.md").write_text(body, encoding="utf-8")
    return target / "SKILL.md"


def cmd_materialize(args: argparse.Namespace) -> int:
    p = ensure_dirs()
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM experiences WHERE kind='skill' AND status='active' AND knowledge_name IS NOT NULL ORDER BY updated_at DESC"
        ).fetchall()
    files = [str(materialize_skill(row, p["skills"])) for row in rows]
    emit(
        {
            "status": "materialized",
            "count": len(files),
            "skills_root": str(p["skills"]),
            "files": files,
            "note": "Configure this skills_root as a user/custom skill directory only if your agent supports dynamic local skill directories.",
        }
    )
    return 0
