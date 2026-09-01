"""Human-readable Markdown observability reports for Agent Lore."""

from lore_common import *  # noqa: F401,F403


def pct(value: float | None) -> str:
    return "—" if value is None else f"{value * 100:.1f}%"


def num(value: float | int | None, digits: int = 2) -> str:
    if value is None:
        return "—"
    if isinstance(value, int):
        return str(value)
    return f"{value:.{digits}f}"


def report_filters(args: argparse.Namespace) -> tuple[list[str], list[Any]]:
    clauses = ["1=1"]
    params: list[Any] = []
    for column, value in (
        ("source_project", args.project),
        ("module", args.module),
        ("task_type", args.type),
        ("task_subtype", args.subtype),
    ):
        if value:
            clauses.append(f"COALESCE({column}, '') = ?")
            params.append(value)
    return clauses, params


def model_rows(conn: sqlite3.Connection, clauses: list[str], params: list[Any]) -> list[sqlite3.Row]:
    return conn.execute(
        f"""
        SELECT
            COALESCE(source_project, '(unknown)') AS project,
            COALESCE(module, '(unknown)') AS module,
            COALESCE(task_type, '(unknown)') AS task_type,
            COALESCE(task_subtype, '(unknown)') AS task_subtype,
            COALESCE(model, '(unknown)') AS model,
            COALESCE(harness, '(unknown)') AS harness,
            COALESCE(agent_role, '(unknown)') AS agent_role,
            COUNT(*) AS runs,
            AVG(CASE WHEN outcome='success' THEN 1.0 ELSE 0.0 END) AS execution_success_rate,
            SUM(CASE WHEN verification_status IN ('passed','not-required') THEN 1 ELSE 0 END) AS verified,
            SUM(CASE WHEN acceptance_status IN ('accepted','not-required') THEN 1 ELSE 0 END) AS accepted,
            SUM(CASE WHEN acceptance_status IN ('accepted','not-required','rework','rejected','invalidated') THEN 1 ELSE 0 END) AS acceptance_observed,
            SUM(CASE WHEN acceptance_status='accepted' AND attempt_index=1 THEN 1 ELSE 0 END) AS first_pass_accepted,
            SUM(CASE WHEN acceptance_status='rework' THEN 1 ELSE 0 END) AS reworks,
            AVG(quality_score) AS avg_quality,
            AVG(cost_usd) AS avg_cost,
            AVG(COALESCE(wall_time_ms, latency_ms)) AS avg_wall_time,
            AVG(compute_time_ms) AS avg_compute_time,
            AVG(verification_time_ms) AS avg_verification_time,
            AVG(review_time_ms) AS avg_review_time,
            AVG(coordination_time_ms) AS avg_coordination_time,
            AVG(retry_count) AS avg_retries
        FROM runs
        WHERE {' AND '.join(clauses)}
        GROUP BY source_project, module, task_type, task_subtype, model, harness, agent_role
        ORDER BY source_project, module, task_type, task_subtype, runs DESC
        """,
        params,
    ).fetchall()


def task_group_rows(conn: sqlite3.Connection, clauses: list[str], params: list[Any]) -> list[sqlite3.Row]:
    return conn.execute(
        f"""
        SELECT
            task_group_id,
            MIN(created_at) AS started_at,
            MAX(CASE WHEN acceptance_status='accepted' THEN accepted_at END) AS accepted_at,
            MAX(COALESCE(source_project, '(unknown)')) AS project,
            MAX(COALESCE(module, '(unknown)')) AS module,
            MAX(COALESCE(task_type, '(unknown)')) AS task_type,
            MAX(COALESCE(task_subtype, '(unknown)')) AS task_subtype,
            MAX(task_summary) AS task_summary,
            COUNT(*) AS attempts,
            SUM(CASE WHEN acceptance_status='rework' THEN 1 ELSE 0 END) AS reworks,
            SUM(CASE WHEN acceptance_status IN ('accepted','not-required') THEN 1 ELSE 0 END) AS accepted_attempts,
            SUM(COALESCE(wall_time_ms, latency_ms, 0)) AS work_time_to_final_ms,
            SUM(COALESCE(cost_usd, 0)) AS total_cost_usd
        FROM runs
        WHERE {' AND '.join(clauses)}
        GROUP BY task_group_id
        HAVING COUNT(*) > 1 OR SUM(CASE WHEN acceptance_status IN ('accepted','rework','rejected','invalidated') THEN 1 ELSE 0 END) > 0
        ORDER BY MIN(created_at) DESC
        LIMIT 30
        """,
        params,
    ).fetchall()


def knowledge_health(conn: sqlite3.Connection) -> dict[str, int]:
    row = conn.execute(
        """
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN status='candidate' THEN 1 ELSE 0 END) AS candidate,
            SUM(CASE WHEN status='active' THEN 1 ELSE 0 END) AS active,
            SUM(CASE WHEN status='deprecated' THEN 1 ELSE 0 END) AS deprecated,
            SUM(CASE WHEN status='archived' THEN 1 ELSE 0 END) AS archived,
            SUM(CASE WHEN kind='skill' AND status='active' THEN 1 ELSE 0 END) AS skills,
            SUM(CASE WHEN needs_revalidation=1 THEN 1 ELSE 0 END) AS needs_revalidation
        FROM experiences
        """
    ).fetchone()
    return {key: int(row[key] or 0) for key in row.keys()}


def make_report(args: argparse.Namespace) -> str:
    clauses, params = report_filters(args)
    with connect() as conn:
        overview = conn.execute(
            f"""
            SELECT COUNT(*) AS runs,
                   COUNT(DISTINCT source_project) AS projects,
                   COUNT(DISTINCT CASE WHEN module IS NOT NULL THEN source_project || ':' || module END) AS modules,
                   SUM(CASE WHEN acceptance_status='pending' THEN 1 ELSE 0 END) AS awaiting_acceptance
            FROM runs WHERE {' AND '.join(clauses)}
            """,
            params,
        ).fetchone()
        models = model_rows(conn, clauses, params)
        task_groups = task_group_rows(conn, clauses, params)
        health = knowledge_health(conn)

    lines = [
        "# Agent Lore Report",
        "",
        f"Generated: {utc_now()}",
        "",
        "## Scope",
        "",
        f"- Project: {args.project or 'all'}",
        f"- Module: {args.module or 'all'}",
        f"- Task type: {args.type or 'all'}",
        f"- Task subtype: {args.subtype or 'all'}",
        "",
        "## Overview",
        "",
        f"- Runs: {int(overview['runs'] or 0)}",
        f"- Projects: {int(overview['projects'] or 0)}",
        f"- Project/module pairs: {int(overview['modules'] or 0)}",
        f"- Awaiting acceptance: {int(overview['awaiting_acceptance'] or 0)}",
        "",
        "## Project / Module / Task Benchmark",
        "",
        "| Project | Module | Task | Subtype | Model | Role | Runs | Exec success | Acceptance | First-pass | Quality | Avg wall ms | Avg cost | Reworks |",
        "|---|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    if not models:
        lines.append("| — | — | — | — | — | — | 0 | — | — | — | — | — | — | — |")
    for row in models:
        observed = int(row["acceptance_observed"] or 0)
        accepted = int(row["accepted"] or 0)
        acceptance = accepted / observed if observed else None
        first_pass = int(row["first_pass_accepted"] or 0) / observed if observed else None
        lines.append(
            "| " + " | ".join(
                [
                    str(row["project"]),
                    str(row["module"]),
                    str(row["task_type"]),
                    str(row["task_subtype"]),
                    str(row["model"]),
                    str(row["agent_role"]),
                    str(int(row["runs"] or 0)),
                    pct(float(row["execution_success_rate"] or 0.0)),
                    pct(acceptance),
                    pct(first_pass),
                    num(float(row["avg_quality"]) if row["avg_quality"] is not None else None, 3),
                    num(float(row["avg_wall_time"]) if row["avg_wall_time"] is not None else None, 0),
                    num(float(row["avg_cost"]) if row["avg_cost"] is not None else None, 4),
                    str(int(row["reworks"] or 0)),
                ]
            ) + " |"
        )

    lines.extend(
        [
            "",
            "## Timing Breakdown",
            "",
            "The benchmark distinguishes user-visible wall time from accumulated compute/verification/review/coordination time when those fields are recorded.",
            "",
            "| Project | Module | Task | Model | Wall ms | Compute ms | Verify ms | Review ms | Coordination ms |",
            "|---|---|---|---|---:|---:|---:|---:|---:|",
        ]
    )
    for row in models:
        lines.append(
            "| " + " | ".join(
                [
                    str(row["project"]),
                    str(row["module"]),
                    str(row["task_type"]),
                    str(row["model"]),
                    num(float(row["avg_wall_time"]) if row["avg_wall_time"] is not None else None, 0),
                    num(float(row["avg_compute_time"]) if row["avg_compute_time"] is not None else None, 0),
                    num(float(row["avg_verification_time"]) if row["avg_verification_time"] is not None else None, 0),
                    num(float(row["avg_review_time"]) if row["avg_review_time"] is not None else None, 0),
                    num(float(row["avg_coordination_time"]) if row["avg_coordination_time"] is not None else None, 0),
                ]
            ) + " |"
        )

    lines.extend(
        [
            "",
            "## Rework / Acceptance History",
            "",
            "`work_time_to_final_ms` is accumulated recorded work time across attempts, not a claim about exact wall-clock elapsed time between human interactions.",
            "",
            "| Task group | Project | Module | Task | Attempts | Reworks | Accepted attempts | Work to final ms | Total cost |",
            "|---|---|---|---|---:|---:|---:|---:|---:|",
        ]
    )
    if not task_groups:
        lines.append("| — | — | — | — | 0 | 0 | 0 | — | — |")
    for row in task_groups:
        lines.append(
            "| " + " | ".join(
                [
                    str(row["task_group_id"]),
                    str(row["project"]),
                    str(row["module"]),
                    str(row["task_summary"]).replace("|", "\\|"),
                    str(int(row["attempts"] or 0)),
                    str(int(row["reworks"] or 0)),
                    str(int(row["accepted_attempts"] or 0)),
                    str(int(row["work_time_to_final_ms"] or 0)),
                    num(float(row["total_cost_usd"] or 0.0), 4),
                ]
            ) + " |"
        )

    lines.extend(
        [
            "",
            "## Knowledge Health",
            "",
            f"- Total knowledge: {health['total']}",
            f"- Active: {health['active']}",
            f"- Candidate: {health['candidate']}",
            f"- Learned skills: {health['skills']}",
            f"- Deprecated: {health['deprecated']}",
            f"- Archived: {health['archived']}",
            f"- Needs revalidation: {health['needs_revalidation']}",
            "",
            "> Execution success is not final success. Prefer acceptance rate, first-pass acceptance, rework count, time-to-accepted-result, deterministic verification, and cost together.",
            "",
        ]
    )
    return "\n".join(lines)


def cmd_report(args: argparse.Namespace) -> int:
    p = ensure_dirs()
    content = make_report(args)
    if args.output:
        output = Path(args.output).expanduser().resolve()
    else:
        output = p["reports"] / "latest.md"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(content, encoding="utf-8")

    if not args.output:
        timestamped = p["reports"] / f"report-{datetime.now().strftime('%Y%m%d-%H%M%S')}.md"
        timestamped.write_text(content, encoding="utf-8")
    emit({"status": "reported", "path": str(output), "format": "markdown"})
    return 0
