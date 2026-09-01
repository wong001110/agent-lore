"""Statistics, portability, and health operations."""

from lore_common import *  # noqa: F401,F403


def build_stats_query(args: argparse.Namespace) -> tuple[str, list[Any]]:
    clauses = ["1=1"]
    params: list[Any] = []
    filters = [
        ("source_project", getattr(args, "project", None)),
        ("module", getattr(args, "module", None)),
        ("task_type", args.type),
        ("task_subtype", getattr(args, "subtype", None)),
        ("language", args.language),
        ("framework", args.framework),
        ("model", args.model),
        ("agent_role", args.agent_role),
        ("topology", args.topology),
    ]
    for column, value in filters:
        if value:
            clauses.append(f"{column} = ?")
            params.append(value)
    query = f"""
        SELECT
            COALESCE(source_project, '(unknown)') AS project,
            COALESCE(module, '(unknown)') AS module,
            COALESCE(task_type, '(unknown)') AS task_type,
            COALESCE(task_subtype, '(unknown)') AS task_subtype,
            COALESCE(model, '(unknown)') AS model,
            COALESCE(harness, '(unknown)') AS harness,
            COALESCE(agent_role, '(unknown)') AS agent_role,
            COALESCE(topology, '(unknown)') AS topology,
            COUNT(*) AS runs,
            ROUND(AVG(CASE WHEN outcome = 'success' THEN 1.0 ELSE 0.0 END) * 100.0, 1) AS execution_success_rate_pct,
            ROUND(AVG(CASE WHEN verification_status IN ('passed','not-required') THEN 1.0 ELSE 0.0 END) * 100.0, 1) AS verification_pass_rate_pct,
            SUM(CASE WHEN acceptance_status IN ('accepted','not-required') THEN 1 ELSE 0 END) AS accepted,
            SUM(CASE WHEN acceptance_status IN ('accepted','not-required','rework','rejected','invalidated') THEN 1 ELSE 0 END) AS acceptance_observed,
            SUM(CASE WHEN acceptance_status='accepted' AND attempt_index=1 THEN 1 ELSE 0 END) AS first_pass_accepted,
            SUM(CASE WHEN acceptance_status='rework' THEN 1 ELSE 0 END) AS reworks,
            ROUND(AVG(quality_score), 3) AS avg_quality,
            ROUND(AVG(cost_usd), 6) AS avg_cost_usd,
            ROUND(AVG(COALESCE(wall_time_ms, latency_ms)), 1) AS avg_wall_time_ms,
            ROUND(AVG(compute_time_ms), 1) AS avg_compute_time_ms,
            ROUND(AVG(verification_time_ms), 1) AS avg_verification_time_ms,
            ROUND(AVG(review_time_ms), 1) AS avg_review_time_ms,
            ROUND(AVG(coordination_time_ms), 1) AS avg_coordination_time_ms,
            ROUND(AVG(latency_ms), 1) AS avg_latency_ms,
            ROUND(AVG(retry_count), 2) AS avg_retries,
            ROUND(AVG(COALESCE(merge_conflicts, 0)), 2) AS avg_merge_conflicts,
            ROUND(AVG(COALESCE(agent_count, 1)), 2) AS avg_agent_count
        FROM runs
        WHERE {" AND ".join(clauses)}
        GROUP BY source_project, module, task_type, task_subtype, model, harness, agent_role, topology
        ORDER BY runs DESC, execution_success_rate_pct DESC
    """
    return query, params


def cmd_stats(args: argparse.Namespace) -> int:
    query, params = build_stats_query(args)
    with connect() as conn:
        rows = conn.execute(query, params).fetchall()
        groups: list[dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            observed = int(row["acceptance_observed"] or 0)
            accepted = int(row["accepted"] or 0)
            item["acceptance_rate_pct"] = round(accepted / observed * 100.0, 1) if observed else None
            item["first_pass_acceptance_rate_pct"] = (
                round(int(row["first_pass_accepted"] or 0) / observed * 100.0, 1) if observed else None
            )
            groups.append(item)
        routing = conn.execute(
            """
            SELECT mode, recommended_topology, challenge_level,
                   COUNT(*) AS decisions,
                   SUM(CASE WHEN applied=1 THEN 1 ELSE 0 END) AS applied,
                   SUM(CASE WHEN outcome_run_id IS NOT NULL THEN 1 ELSE 0 END) AS outcomes_recorded
            FROM routing_decisions
            GROUP BY mode, recommended_topology, challenge_level
            ORDER BY decisions DESC
            """
        ).fetchall()
    emit({"groups": groups, "count": len(groups), "routing": [dict(row) for row in routing]})
    return 0


def safe_backup_database(source_path: Path, destination_path: Path) -> None:
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    source = sqlite3.connect(source_path)
    target = sqlite3.connect(destination_path)
    try:
        source.backup(target)
        target.commit()
    finally:
        target.close()
        source.close()


def cmd_export(args: argparse.Namespace) -> int:
    p = ensure_dirs()
    with connect():
        pass
    default_name = f"agent-lore-{datetime.now().strftime('%Y%m%d-%H%M%S')}.zip"
    output = Path(args.output).expanduser().resolve() if args.output else p["exports"] / default_name
    output.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="agent-lore-export-") as tmp:
        tmp_dir = Path(tmp)
        snapshot = tmp_dir / "agent-lore.db"
        safe_backup_database(p["db"], snapshot)
        manifest = {
            "format": "agent-lore-portable",
            "app_version": APP_VERSION,
            "schema_version": SCHEMA_VERSION,
            "exported_at": utc_now(),
            "database": "agent-lore.db",
        }
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.write(snapshot, "agent-lore.db")
            zf.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
            if p["knowledge"].exists():
                for file in p["knowledge"].rglob("*"):
                    if file.is_file():
                        zf.write(file, Path("knowledge") / file.relative_to(p["knowledge"]))
    emit({"status": "exported", "path": str(output)})
    return 0


def validate_snapshot(path: Path) -> None:
    conn = sqlite3.connect(path)
    try:
        integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
        if integrity != "ok":
            raise ValueError(f"SQLite integrity check failed: {integrity}")
        required = {"runs", "experiences", "meta"}
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        missing = required - tables
        if missing:
            raise ValueError(f"Snapshot missing required tables: {sorted(missing)}")
    finally:
        conn.close()


def cmd_import(args: argparse.Namespace) -> int:
    p = ensure_dirs()
    bundle = Path(args.bundle).expanduser().resolve()
    if not bundle.exists():
        raise FileNotFoundError(bundle)

    with zipfile.ZipFile(bundle, "r") as zf:
        names = set(zf.namelist())
        if "manifest.json" not in names or "agent-lore.db" not in names:
            raise ValueError("Not a valid Agent Lore portable export.")
        manifest = json.loads(zf.read("manifest.json").decode("utf-8"))
        if manifest.get("format") != "agent-lore-portable":
            raise ValueError("Unsupported export format.")

        with tempfile.TemporaryDirectory(prefix="agent-lore-import-") as tmp:
            snapshot = Path(tmp) / "agent-lore.db"
            snapshot.write_bytes(zf.read("agent-lore.db"))
            validate_snapshot(snapshot)
            safety_backup = None
            if p["db"].exists():
                safety_backup = p["archive"] / f"pre-import-{datetime.now().strftime('%Y%m%d-%H%M%S')}.db"
                safe_backup_database(p["db"], safety_backup)
            shutil.copy2(snapshot, p["db"])
            for name in names:
                if not name.startswith("knowledge/") or name.endswith("/"):
                    continue
                relative = Path(name).relative_to("knowledge")
                if ".." in relative.parts:
                    raise ValueError("Unsafe path in export.")
                target = p["knowledge"] / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(zf.read(name))

    with connect():
        pass
    emit(
        {
            "status": "imported",
            "bundle": str(bundle),
            "database": str(p["db"]),
            "safety_backup": str(safety_backup) if safety_backup else None,
        }
    )
    return 0


def cmd_doctor(_: argparse.Namespace) -> int:
    p = ensure_dirs()
    with connect() as conn:
        integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
        runs = conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
        experiences = conn.execute("SELECT COUNT(*) FROM experiences").fetchone()[0]
        active = conn.execute("SELECT COUNT(*) FROM experiences WHERE status='active'").fetchone()[0]
        candidates = conn.execute("SELECT COUNT(*) FROM experiences WHERE status='candidate'").fetchone()[0]
        patterns = conn.execute("SELECT COUNT(*) FROM experiences WHERE kind='pattern' AND status='active'").fetchone()[0]
        skills = conn.execute("SELECT COUNT(*) FROM experiences WHERE kind='skill' AND status='active'").fetchone()[0]
        revalidation = conn.execute("SELECT COUNT(*) FROM experiences WHERE needs_revalidation=1").fetchone()[0]
        configs = conn.execute("SELECT COUNT(*) FROM agent_configs WHERE enabled=1").fetchone()[0]
        decisions = conn.execute("SELECT COUNT(*) FROM routing_decisions").fetchone()[0]
        pending_acceptance = conn.execute("SELECT COUNT(*) FROM runs WHERE acceptance_status='pending'").fetchone()[0]
        accepted = conn.execute("SELECT COUNT(*) FROM runs WHERE acceptance_status IN ('accepted','not-required')").fetchone()[0]
        reworks = conn.execute("SELECT COUNT(*) FROM runs WHERE acceptance_status='rework'").fetchone()[0]
        current_policy = policy(conn)
    emit(
        {
            "status": "ok" if integrity == "ok" else "error",
            "app_version": APP_VERSION,
            "schema_version": SCHEMA_VERSION,
            "home": str(p["home"]),
            "database": str(p["db"]),
            "integrity": integrity,
            "runs": runs,
            "knowledge": experiences,
            "active": active,
            "candidates": candidates,
            "patterns": patterns,
            "skills": skills,
            "needs_revalidation": revalidation,
            "accepted_runs": accepted,
            "rework_runs": reworks,
            "awaiting_acceptance": pending_acceptance,
            "enabled_agent_configs": configs,
            "routing_decisions": decisions,
            "policy": current_policy,
        }
    )
    return 0 if integrity == "ok" else 1
