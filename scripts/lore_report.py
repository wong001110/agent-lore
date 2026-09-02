"""Human-readable Markdown observability reports for Agent Lore."""

import html

from lore_common import *  # noqa: F401,F403


NOT_COLLECTED = "-"
NOT_APPLICABLE = "N/A"
PENDING_ACCEPTANCE = "Pending"
ROLLING_LIMITS = {
    "benchmarks": 50,
    "task_groups": 30,
    "agents": 200,
    "telemetry": 200,
    "recent_runs": 30,
}


def pct(value: float | None, missing: str = NOT_COLLECTED) -> str:
    return missing if value is None else f"{value * 100:.1f}%"


def num(value: float | int | None, digits: int = 2, missing: str = NOT_COLLECTED) -> str:
    if value is None:
        return missing
    if isinstance(value, int):
        return str(value)
    return f"{value:.{digits}f}"


def cell(value: Any, missing: str = NOT_COLLECTED) -> str:
    if value is None or value == "":
        return missing
    return str(value).replace("|", "\\|").replace("\n", " ")


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


def limit_clause(limit: int | None) -> str:
    return "" if limit is None else f" LIMIT {limit}"


def model_rows(
    conn: sqlite3.Connection,
    clauses: list[str],
    params: list[Any],
    limit: int | None,
) -> list[sqlite3.Row]:
    return conn.execute(
        f"""
        SELECT
            COALESCE(source_project, 'Unspecified') AS project,
            COALESCE(module, 'Unspecified') AS module,
            COALESCE(task_type, 'Unspecified') AS task_type,
            COALESCE(task_subtype, 'Unspecified') AS task_subtype,
            COALESCE(model, '-') AS model,
            COALESCE(harness, '-') AS harness,
            COALESCE(agent_role, '-') AS agent_role,
            COUNT(*) AS runs,
            AVG(CASE WHEN outcome='success' THEN 1.0 ELSE 0.0 END) AS execution_success_rate,
            SUM(CASE WHEN verification_status IN ('passed','not-required') THEN 1 ELSE 0 END) AS verified,
            SUM(CASE WHEN acceptance_status IN ('accepted','not-required') THEN 1 ELSE 0 END) AS accepted,
            SUM(CASE WHEN acceptance_status IN ('accepted','not-required','rework','rejected','invalidated') THEN 1 ELSE 0 END) AS acceptance_observed,
            SUM(CASE
                WHEN acceptance_status IN ('accepted','not-required') AND attempt_index=1
                THEN 1 ELSE 0 END) AS first_pass_accepted,
            SUM(CASE
                WHEN acceptance_status IN ('accepted','not-required','rework','rejected','invalidated')
                 AND attempt_index=1
                THEN 1 ELSE 0 END) AS first_pass_observed,
            SUM(CASE WHEN acceptance_status='rework' THEN 1 ELSE 0 END) AS reworks,
            AVG(quality_score) AS avg_quality,
            AVG(cost_usd) AS avg_cost,
            AVG(COALESCE(wall_time_ms, latency_ms)) AS avg_wall_time,
            AVG(compute_time_ms) AS avg_compute_time,
            AVG(verification_time_ms) AS avg_verification_time,
            AVG(review_time_ms) AS avg_review_time,
            AVG(coordination_time_ms) AS avg_coordination_time,
            AVG(retry_count) AS avg_retries,
            MAX(created_at) AS latest_run_at
        FROM runs
        WHERE {' AND '.join(clauses)}
        GROUP BY source_project, module, task_type, task_subtype, model, harness, agent_role
        ORDER BY latest_run_at DESC, runs DESC
        {limit_clause(limit)}
        """,
        params,
    ).fetchall()


def task_group_rows(
    conn: sqlite3.Connection,
    clauses: list[str],
    params: list[Any],
    limit: int | None,
) -> list[sqlite3.Row]:
    return conn.execute(
        f"""
        SELECT
            task_group_id,
            MIN(created_at) AS started_at,
            MAX(CASE WHEN acceptance_status='accepted' THEN accepted_at END) AS accepted_at,
            MAX(COALESCE(source_project, 'Unspecified')) AS project,
            MAX(COALESCE(module, 'Unspecified')) AS module,
            MAX(COALESCE(task_type, 'Unspecified')) AS task_type,
            MAX(COALESCE(task_subtype, 'Unspecified')) AS task_subtype,
            MAX(task_summary) AS task_summary,
            COUNT(*) AS attempts,
            SUM(CASE WHEN acceptance_status='rework' THEN 1 ELSE 0 END) AS reworks,
            SUM(CASE WHEN acceptance_status IN ('accepted','not-required') THEN 1 ELSE 0 END) AS accepted_attempts,
            SUM(COALESCE(wall_time_ms, latency_ms)) AS work_time_to_final_ms,
            SUM(cost_usd) AS total_cost_usd
        FROM runs
        WHERE {' AND '.join(clauses)}
        GROUP BY task_group_id
        HAVING COUNT(*) > 1 OR SUM(CASE WHEN acceptance_status IN ('accepted','rework','rejected','invalidated') THEN 1 ELSE 0 END) > 0
        ORDER BY MIN(created_at) DESC
        {limit_clause(limit)}
        """,
        params,
    ).fetchall()


def agent_rows(
    conn: sqlite3.Connection,
    clauses: list[str],
    params: list[Any],
    limit: int | None,
) -> list[sqlite3.Row]:
    return conn.execute(
        f"""
        SELECT
            r.id AS run_id,
            r.created_at,
            r.task_summary AS run_task,
            COALESCE(r.execution_capture_status, 'not-collected') AS capture_status,
            r.execution_capture_source,
            r.agent_count,
            a.agent_id,
            a.parent_agent_id,
            a.display_name,
            a.role,
            a.specialization,
            a.model,
            a.harness,
            a.status AS agent_status,
            a.task_summary AS agent_task,
            a.depth,
            a.wall_time_ms,
            a.compute_time_ms,
            a.cost_usd
        FROM runs r
        LEFT JOIN run_agents a ON a.run_id = r.id
        WHERE r.id IN (
            SELECT id FROM runs WHERE {' AND '.join(clauses)}
        )
        ORDER BY r.created_at DESC, COALESCE(a.depth, 999), a.created_at, a.agent_id
        {limit_clause(limit)}
        """,
        params,
    ).fetchall()


def telemetry_rows(
    conn: sqlite3.Connection,
    clauses: list[str],
    params: list[Any],
    limit: int | None,
) -> list[sqlite3.Row]:
    return conn.execute(
        f"""
        SELECT
            r.id AS run_id,
            COALESCE(r.execution_capture_status, 'not-collected') AS capture_status,
            COUNT(a.agent_id) AS agents,
            SUM(CASE WHEN a.specialization IS NOT NULL THEN 1 ELSE 0 END) AS specialization,
            SUM(CASE WHEN a.model IS NOT NULL THEN 1 ELSE 0 END) AS model,
            SUM(CASE WHEN a.harness IS NOT NULL THEN 1 ELSE 0 END) AS harness
        FROM runs r
        LEFT JOIN run_agents a ON a.run_id = r.id
        WHERE {' AND '.join(clauses)}
        GROUP BY r.id, r.execution_capture_status, r.created_at
        ORDER BY r.created_at DESC
        {limit_clause(limit)}
        """,
        params,
    ).fetchall()


def recent_run_rows(
    conn: sqlite3.Connection,
    clauses: list[str],
    params: list[Any],
    limit: int | None,
) -> list[sqlite3.Row]:
    return conn.execute(
        f"""
        SELECT id, created_at, source_project, module, task_type, task_subtype,
               task_summary, outcome, verification_status, acceptance_status,
               model, harness, agent_role
        FROM runs
        WHERE {' AND '.join(clauses)}
        ORDER BY created_at DESC
        {limit_clause(limit)}
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
    limits = {key: None for key in ROLLING_LIMITS} if args.full else ROLLING_LIMITS
    with connect() as conn:
        overview = conn.execute(
            f"""
            SELECT COUNT(*) AS runs,
                   COUNT(DISTINCT source_project) AS projects,
                   COUNT(DISTINCT CASE WHEN module IS NOT NULL THEN source_project || ':' || module END) AS modules,
                   SUM(CASE WHEN acceptance_status='pending' THEN 1 ELSE 0 END) AS awaiting_acceptance,
                   SUM(CASE WHEN execution_capture_status='complete' THEN 1 ELSE 0 END) AS complete_agent_capture,
                   SUM(CASE WHEN execution_capture_status='partial' THEN 1 ELSE 0 END) AS partial_agent_capture,
                   SUM(CASE WHEN execution_capture_status='not-collected' OR execution_capture_status IS NULL THEN 1 ELSE 0 END) AS missing_agent_capture
            FROM runs WHERE {' AND '.join(clauses)}
            """,
            params,
        ).fetchone()
        models = model_rows(conn, clauses, params, limits["benchmarks"])
        task_groups = task_group_rows(conn, clauses, params, limits["task_groups"])
        agents = agent_rows(conn, clauses, params, limits["agents"])
        telemetry = telemetry_rows(conn, clauses, params, limits["telemetry"])
        health = knowledge_health(conn)

    incomplete_complete_captures = sum(
        1
        for row in telemetry
        if row["capture_status"] == "complete"
        and int(row["agents"] or 0) > 0
        and any(
            int(row[field] or 0) < int(row["agents"] or 0)
            for field in ("specialization", "model", "harness")
        )
    )

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
        f"- Detail window: {'full history' if args.full else 'rolling summary'}",
        "",
        "## Overview",
        "",
        f"- Runs: {int(overview['runs'] or 0)}",
        f"- Projects: {int(overview['projects'] or 0)}",
        f"- Project/module pairs: {int(overview['modules'] or 0)}",
        f"- Awaiting acceptance: {int(overview['awaiting_acceptance'] or 0)}",
        f"- Complete agent capture: {int(overview['complete_agent_capture'] or 0)}",
        f"- Partial agent capture: {int(overview['partial_agent_capture'] or 0)}",
        f"- Agent capture not collected: {int(overview['missing_agent_capture'] or 0)}",
        f"- Complete captures with optional agent metadata omitted: {incomplete_complete_captures}",
        "",
        "Value legend: **-** = not collected; **Pending** = execution evidence exists but acceptance is undecided; **N/A** = the metric does not apply to the row.",
        "",
        "## Project / Module / Task Benchmark",
        "",
        "| Project | Module | Task | Subtype | Model | Role | Runs | Exec success | Acceptance | First-pass | Quality | Avg wall ms | Avg cost | Reworks |",
        "|---|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    if not models:
        lines.append("| - | N/A | N/A | N/A | - | - | 0 | N/A | N/A | N/A | - | - | - | 0 |")
    for row in models:
        observed = int(row["acceptance_observed"] or 0)
        accepted = int(row["accepted"] or 0)
        first_pass_observed = int(row["first_pass_observed"] or 0)
        acceptance = accepted / observed if observed else None
        first_pass = (
            int(row["first_pass_accepted"] or 0) / first_pass_observed
            if first_pass_observed
            else None
        )
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
                    pct(acceptance, PENDING_ACCEPTANCE),
                    pct(first_pass, PENDING_ACCEPTANCE),
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
    if not models:
        lines.append("| - | N/A | N/A | - | - | - | - | - | - |")

    lines.extend(
        [
            "",
            "## Actual Agent Execution",
            "",
            "This ledger is optional, host-supplied telemetry recorded after execution. It observes the harness; it does not prescribe spawning, delegation, models, tools, or testing methods. " + ("All rows in scope are shown." if args.full else "The latest 200 run/agent rows in scope are shown."),
            "",
            "| Run | Run task | Capture | Agent | Parent | Depth | Role | Specialization | Model | Harness | Status | Agent task | Wall ms | Compute ms | Cost |",
            "|---|---|---|---|---|---:|---|---|---|---|---|---|---:|---:|---:|",
        ]
    )
    if not agents:
        lines.append("| N/A | N/A | N/A | - | N/A | N/A | - | - | - | - | - | N/A | - | - | - |")
    for row in agents:
        has_agent = row["agent_id"] is not None
        capture = {
            "complete": "Complete",
            "partial": "Partial",
            "not-collected": NOT_COLLECTED,
        }.get(row["capture_status"], cell(row["capture_status"]))
        lines.append(
            "| " + " | ".join(
                [
                    cell(row["run_id"]),
                    cell(row["run_task"]),
                    capture,
                    cell(row["display_name"] or row["agent_id"]),
                    cell(row["parent_agent_id"], NOT_APPLICABLE),
                    num(int(row["depth"]) if row["depth"] is not None else None, missing=NOT_APPLICABLE if not has_agent else NOT_COLLECTED),
                    cell(row["role"]),
                    cell(row["specialization"]),
                    cell(row["model"]),
                    cell(row["harness"]),
                    cell(row["agent_status"]),
                    cell(row["agent_task"], NOT_APPLICABLE if not has_agent else NOT_COLLECTED),
                    num(int(row["wall_time_ms"]) if row["wall_time_ms"] is not None else None, 0),
                    num(int(row["compute_time_ms"]) if row["compute_time_ms"] is not None else None, 0),
                    num(float(row["cost_usd"]) if row["cost_usd"] is not None else None, 4),
                ]
            ) + " |"
        )

    lines.extend(
        [
            "",
            "## Execution Telemetry Coverage",
            "",
            "This is an observability quality signal, not an execution or routing gate. Run-level model and harness values are inherited into agent rows when the host supplied them; specialization is never inferred.",
            "",
            "| Run | Capture | Agents | Specialization | Model | Harness |",
            "|---|---|---:|---:|---:|---:|",
        ]
    )
    if not telemetry:
        lines.append("| N/A | N/A | 0 | - | - | - |")
    for row in telemetry:
        agents_count = int(row["agents"] or 0)
        capture = {"complete": "Complete", "partial": "Partial", "not-collected": NOT_COLLECTED}.get(
            row["capture_status"], cell(row["capture_status"])
        )
        coverage = lambda field: f"{int(row[field] or 0)}/{agents_count}" if agents_count else NOT_COLLECTED
        lines.append(
            "| " + " | ".join(
                [
                    cell(row["run_id"]),
                    capture,
                    str(agents_count),
                    coverage("specialization"),
                    coverage("model"),
                    coverage("harness"),
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
        lines.append("| N/A | N/A | N/A | No rework or decided-acceptance history | 0 | 0 | 0 | N/A | N/A |")
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
                    num(int(row["work_time_to_final_ms"]) if row["work_time_to_final_ms"] is not None else None, 0),
                    num(float(row["total_cost_usd"]) if row["total_cost_usd"] is not None else None, 4),
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


def html_text(value: Any, missing: str = NOT_COLLECTED) -> str:
    return html.escape(cell(value, missing))


def html_table(headers: list[str], rows: list[list[str]]) -> str:
    head = "".join(f"<th>{html.escape(header)}</th>" for header in headers)
    body = "".join(
        "<tr>" + "".join(f"<td>{value}</td>" for value in row) + "</tr>"
        for row in rows
    ) or f"<tr><td colspan=\"{len(headers)}\">No rows in scope.</td></tr>"
    return f"<div class=\"table-wrap\"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>"


def make_html_report(args: argparse.Namespace) -> str:
    clauses, params = report_filters(args)
    limits = {key: None for key in ROLLING_LIMITS} if args.full else ROLLING_LIMITS
    with connect() as conn:
        overview = conn.execute(
            f"""
            SELECT COUNT(*) AS runs,
                   COUNT(DISTINCT source_project) AS projects,
                   SUM(CASE WHEN acceptance_status='pending' THEN 1 ELSE 0 END) AS awaiting_acceptance,
                   SUM(CASE WHEN execution_capture_status='complete' THEN 1 ELSE 0 END) AS complete_agent_capture
            FROM runs WHERE {' AND '.join(clauses)}
            """,
            params,
        ).fetchone()
        models = model_rows(conn, clauses, params, limits["benchmarks"])
        recent_runs = recent_run_rows(conn, clauses, params, limits["recent_runs"])
        telemetry = telemetry_rows(conn, clauses, params, limits["telemetry"])
        health = knowledge_health(conn)

    benchmark_rows = []
    for row in models:
        observed = int(row["acceptance_observed"] or 0)
        accepted = int(row["accepted"] or 0)
        benchmark_rows.append(
            [
                html_text(row["project"]),
                html_text(row["module"]),
                html_text(row["task_type"]),
                html_text(row["task_subtype"]),
                html_text(row["model"]),
                html_text(row["agent_role"]),
                str(int(row["runs"] or 0)),
                html.escape(pct(float(row["execution_success_rate"] or 0.0))),
                html.escape(pct(accepted / observed if observed else None, PENDING_ACCEPTANCE)),
            ]
        )
    recent_rows = [
        [
            html_text(row["created_at"]),
            html_text(row["source_project"]),
            html_text(row["module"]),
            html_text(row["task_type"]),
            html_text(row["task_summary"]),
            html_text(row["outcome"]),
            html_text(row["verification_status"]),
            html_text(row["acceptance_status"]),
        ]
        for row in recent_runs
    ]
    telemetry_rows_html = []
    for row in telemetry:
        agents_count = int(row["agents"] or 0)
        coverage = lambda field: f"{int(row[field] or 0)}/{agents_count}" if agents_count else NOT_COLLECTED
        telemetry_rows_html.append(
            [
                html_text(row["run_id"]),
                html_text(row["capture_status"]),
                str(agents_count),
                html.escape(coverage("specialization")),
                html.escape(coverage("model")),
                html.escape(coverage("harness")),
            ]
        )

    scope = " / ".join(filter(None, [args.project, args.module, args.type, args.subtype])) or "all data"
    window = "Full historical detail" if args.full else "Rolling summary: 50 benchmarks, 30 recent runs, 200 agent/telemetry rows"
    cards = [
        ("Runs", int(overview["runs"] or 0)),
        ("Projects", int(overview["projects"] or 0)),
        ("Awaiting acceptance", int(overview["awaiting_acceptance"] or 0)),
        ("Complete agent capture", int(overview["complete_agent_capture"] or 0)),
        ("Knowledge", health["total"]),
    ]
    card_html = "".join(
        f"<article class=\"card\"><span>{html.escape(label)}</span><strong>{value}</strong></article>"
        for label, value in cards
    )
    return f"""<!doctype html>
<html lang=\"en\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
<title>Agent Lore Dashboard</title><style>
:root{{color-scheme:dark;font-family:ui-sans-serif,system-ui,sans-serif;background:#10131a;color:#edf2f7}}body{{margin:0 auto;max-width:1440px;padding:28px}}h1{{margin-bottom:4px}}.muted{{color:#aab5c4}}.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin:24px 0}}.card{{background:#1a202b;border:1px solid #303a49;border-radius:10px;padding:16px}}.card span{{display:block;color:#aab5c4;font-size:.85rem}}.card strong{{display:block;font-size:1.8rem;margin-top:6px}}input{{width:min(420px,100%);background:#161c26;color:#edf2f7;border:1px solid #475569;border-radius:7px;padding:10px}}section{{margin-top:32px}}.table-wrap{{overflow:auto;border:1px solid #303a49;border-radius:10px}}table{{width:100%;border-collapse:collapse;font-size:.9rem}}th,td{{padding:10px;text-align:left;border-bottom:1px solid #303a49;vertical-align:top}}th{{background:#1a202b;position:sticky;top:0}}tr:last-child td{{border-bottom:0}}footer{{margin-top:32px;color:#aab5c4;font-size:.85rem}}</style></head>
<body><header><h1>Agent Lore Dashboard</h1><p class=\"muted\">Generated {html.escape(utc_now())} · Scope: {html.escape(scope)} · {html.escape(window)}</p></header>
<div class=\"cards\">{card_html}</div><label>Filter visible tables <input id=\"filter\" placeholder=\"Type to filter rows\"></label>
<section><h2>Project / Module / Task Benchmark</h2>{html_table(["Project", "Module", "Task", "Subtype", "Model", "Role", "Runs", "Success", "Acceptance"], benchmark_rows)}</section>
<section><h2>Recent Runs</h2>{html_table(["Created", "Project", "Module", "Task", "Summary", "Outcome", "Verification", "Acceptance"], recent_rows)}</section>
<section><h2>Execution Telemetry Coverage</h2><p class=\"muted\">Coverage is observational only. It never controls routing, delegation, or verification.</p>{html_table(["Run", "Capture", "Agents", "Specialization", "Model", "Harness"], telemetry_rows_html)}</section>
<footer>Values marked - were not collected; Pending means acceptance is undecided; N/A means not applicable. The SQLite store remains the source of complete history.</footer>
<script>document.querySelector('#filter').addEventListener('input', event => {{const query=event.target.value.toLowerCase();document.querySelectorAll('tbody tr').forEach(row => row.hidden=!row.textContent.toLowerCase().includes(query));}});</script></body></html>"""


def cmd_report(args: argparse.Namespace) -> int:
    p = ensure_dirs()
    content = make_html_report(args) if args.format == "html" else make_report(args)
    extension = "html" if args.format == "html" else "md"
    if args.output:
        output = Path(args.output).expanduser().resolve()
    else:
        output = p["reports"] / f"latest.{extension}"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(content, encoding="utf-8")

    if not args.output:
        timestamped = p["reports"] / f"report-{datetime.now().strftime('%Y%m%d-%H%M%S')}.{extension}"
        timestamped.write_text(content, encoding="utf-8")
    emit({"status": "reported", "path": str(output), "format": args.format, "full": args.full})
    return 0
