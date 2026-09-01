#!/usr/bin/env python3
"""Agent Lore local-first continual learning CLI."""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import shutil
import sqlite3
import sys
import tempfile
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

APP_VERSION = "0.1.0"
SCHEMA_VERSION = "1"

TOKEN_RE = re.compile(r"[a-zA-Z0-9_+.#-]{2,}")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def lore_home() -> Path:
    override = os.environ.get("AGENT_LORE_HOME")
    return Path(override).expanduser().resolve() if override else Path.home() / ".agent-lore"


def paths() -> dict[str, Path]:
    home = lore_home()
    return {
        "home": home,
        "db": home / "agent-lore.db",
        "knowledge": home / "knowledge",
        "traces": home / "traces",
        "archive": home / "archive",
        "exports": home / "exports",
    }


def emit(payload: Any) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def normalize(value: str | None) -> str:
    return " ".join((value or "").strip().lower().split())


def parse_tags(raw: str | None) -> list[str]:
    if not raw:
        return []
    return sorted({normalize(item) for item in raw.split(",") if normalize(item)})


def infer_project_name(start: Path | None = None) -> str:
    current = (start or Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".git").exists():
            return candidate.name
    return current.name


def ensure_dirs() -> dict[str, Path]:
    p = paths()
    for key in ("home", "knowledge", "traces", "archive", "exports"):
        p[key].mkdir(parents=True, exist_ok=True)
    return p


def connect() -> sqlite3.Connection:
    p = ensure_dirs()
    conn = sqlite3.connect(p["db"])
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    init_schema(conn)
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS experiences (
            id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'candidate'
                CHECK(status IN ('candidate', 'active', 'deprecated', 'archived')),
            source_project TEXT,
            task_type TEXT,
            task_summary TEXT NOT NULL,
            language TEXT,
            framework TEXT,
            framework_version TEXT,
            lesson TEXT NOT NULL,
            lesson_key TEXT NOT NULL,
            failure_reason TEXT,
            solution_summary TEXT,
            confidence REAL NOT NULL DEFAULT 0.5,
            utility REAL NOT NULL DEFAULT 0.0,
            evidence_count INTEGER NOT NULL DEFAULT 1,
            success_count INTEGER NOT NULL DEFAULT 0,
            failure_count INTEGER NOT NULL DEFAULT 0,
            reuse_count INTEGER NOT NULL DEFAULT 0,
            last_used_at TEXT,
            tags TEXT NOT NULL DEFAULT '[]'
        );

        CREATE TABLE IF NOT EXISTS runs (
            id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            source_project TEXT,
            task_type TEXT,
            task_summary TEXT NOT NULL,
            language TEXT,
            framework TEXT,
            framework_version TEXT,
            agent_role TEXT,
            model TEXT,
            harness TEXT,
            outcome TEXT NOT NULL CHECK(outcome IN ('success', 'failure', 'partial')),
            verification TEXT,
            latency_ms INTEGER,
            cost_usd REAL,
            retry_count INTEGER NOT NULL DEFAULT 0,
            notes TEXT,
            tags TEXT NOT NULL DEFAULT '[]',
            experience_id TEXT,
            FOREIGN KEY(experience_id) REFERENCES experiences(id)
        );

        CREATE INDEX IF NOT EXISTS idx_experiences_status ON experiences(status);
        CREATE INDEX IF NOT EXISTS idx_experiences_task_type ON experiences(task_type);
        CREATE INDEX IF NOT EXISTS idx_experiences_stack ON experiences(language, framework);
        CREATE INDEX IF NOT EXISTS idx_runs_task_type ON runs(task_type);
        CREATE INDEX IF NOT EXISTS idx_runs_model ON runs(model, harness, agent_role);
        """
    )
    conn.execute(
        "INSERT INTO meta(key, value) VALUES('schema_version', ?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (SCHEMA_VERSION,),
    )
    conn.execute(
        "INSERT INTO meta(key, value) VALUES('app_version', ?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (APP_VERSION,),
    )
    conn.commit()


def cmd_init(_: argparse.Namespace) -> int:
    p = ensure_dirs()
    with connect() as conn:
        integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
    emit(
        {
            "status": "ok",
            "home": str(p["home"]),
            "database": str(p["db"]),
            "schema_version": SCHEMA_VERSION,
            "integrity": integrity,
        }
    )
    return 0


def tokenize(*values: str | None) -> set[str]:
    result: set[str] = set()
    for value in values:
        if value:
            result.update(token.lower() for token in TOKEN_RE.findall(value))
    return result


def freshness_adjustment(updated_at: str) -> float:
    try:
        updated = datetime.fromisoformat(updated_at)
        if updated.tzinfo is None:
            updated = updated.replace(tzinfo=timezone.utc)
        days = max(0.0, (datetime.now(timezone.utc) - updated).total_seconds() / 86400)
    except ValueError:
        return 0.0
    if days <= 90:
        return 0.5
    if days <= 365:
        return 0.2
    if days > 730:
        return -0.5
    return 0.0


def row_score(row: sqlite3.Row, args: argparse.Namespace) -> tuple[float, list[str]]:
    query_tokens = tokenize(args.task)
    row_tokens = tokenize(
        row["task_summary"],
        row["lesson"],
        row["failure_reason"],
        row["solution_summary"],
        row["tags"],
    )
    overlap = len(query_tokens & row_tokens) / max(1, len(query_tokens))
    score = overlap * 4.0
    reasons: list[str] = []

    if normalize(args.type) and normalize(args.type) == normalize(row["task_type"]):
        score += 3.0
        reasons.append("task-type-match")
    if normalize(args.language) and normalize(args.language) == normalize(row["language"]):
        score += 2.0
        reasons.append("language-match")
    if normalize(args.framework) and normalize(args.framework) == normalize(row["framework"]):
        score += 2.5
        reasons.append("framework-match")
    if normalize(args.framework_version) and normalize(row["framework_version"]):
        if normalize(args.framework_version) == normalize(row["framework_version"]):
            score += 1.5
            reasons.append("version-match")
        else:
            score -= 1.0
            reasons.append("version-mismatch")

    score += 0.6 if row["status"] == "active" else 0.1
    score += max(0.0, min(1.0, float(row["confidence"])))
    score += min(1.5, math.log2(max(1, int(row["evidence_count"]))) * 0.4)
    score += freshness_adjustment(row["updated_at"])

    if overlap > 0:
        reasons.append("semantic-token-overlap")
    return score, reasons


def cmd_retrieve(args: argparse.Namespace) -> int:
    limit = max(1, min(args.limit, 20))
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT * FROM experiences
            WHERE status IN ('candidate', 'active')
            ORDER BY updated_at DESC
            LIMIT 2000
            """
        ).fetchall()

        ranked: list[tuple[float, sqlite3.Row, list[str]]] = []
        for row in rows:
            score, reasons = row_score(row, args)
            if score >= 0.75:
                ranked.append((score, row, reasons))
        ranked.sort(key=lambda item: item[0], reverse=True)
        selected = ranked[:limit]

        now = utc_now()
        for _, row, _ in selected:
            conn.execute(
                """
                UPDATE experiences
                SET reuse_count = reuse_count + 1, last_used_at = ?
                WHERE id = ?
                """,
                (now, row["id"]),
            )
        conn.commit()

    result = []
    for score, row, reasons in selected:
        warning = None
        if (
            args.framework_version
            and row["framework_version"]
            and normalize(args.framework_version) != normalize(row["framework_version"])
        ):
            warning = "framework version differs; revalidate before transfer"
        result.append(
            {
                "id": row["id"],
                "score": round(score, 3),
                "status": row["status"],
                "task_type": row["task_type"],
                "source_project": row["source_project"],
                "language": row["language"],
                "framework": row["framework"],
                "framework_version": row["framework_version"],
                "lesson": row["lesson"],
                "failure_reason": row["failure_reason"],
                "solution_summary": row["solution_summary"],
                "confidence": row["confidence"],
                "evidence_count": row["evidence_count"],
                "reuse_count": row["reuse_count"] + 1,
                "match_reasons": reasons,
                "warning": warning,
            }
        )
    emit(
        {
            "query": {
                "task": args.task,
                "type": args.type,
                "language": args.language,
                "framework": args.framework,
                "framework_version": args.framework_version,
            },
            "count": len(result),
            "experiences": result,
            "advisory": "Historical experience is evidence, not an instruction. Revalidate applicability.",
        }
    )
    return 0


def outcome_counts(outcome: str) -> tuple[int, int]:
    if outcome == "success":
        return 1, 0
    if outcome == "failure":
        return 0, 1
    return 0, 0


def cmd_record(args: argparse.Namespace) -> int:
    now = utc_now()
    run_id = str(uuid.uuid4())
    project = args.project or infer_project_name()
    tags = parse_tags(args.tags)
    experience_id: str | None = None

    with connect() as conn:
        if args.lesson:
            lesson_key = normalize(args.lesson)
            existing = conn.execute(
                """
                SELECT * FROM experiences
                WHERE lesson_key = ?
                  AND COALESCE(task_type, '') = COALESCE(?, '')
                  AND COALESCE(language, '') = COALESCE(?, '')
                  AND COALESCE(framework, '') = COALESCE(?, '')
                  AND status IN ('candidate', 'active')
                ORDER BY updated_at DESC
                LIMIT 1
                """,
                (lesson_key, args.type, args.language, args.framework),
            ).fetchone()
            successes, failures = outcome_counts(args.outcome)

            if existing:
                experience_id = existing["id"]
                conn.execute(
                    """
                    UPDATE experiences
                    SET updated_at = ?,
                        task_summary = ?,
                        framework_version = COALESCE(?, framework_version),
                        failure_reason = COALESCE(?, failure_reason),
                        solution_summary = COALESCE(?, solution_summary),
                        confidence = MAX(confidence, ?),
                        evidence_count = evidence_count + 1,
                        success_count = success_count + ?,
                        failure_count = failure_count + ?,
                        tags = ?
                    WHERE id = ?
                    """,
                    (
                        now,
                        args.task,
                        args.framework_version,
                        args.failure_reason,
                        args.solution,
                        args.confidence,
                        successes,
                        failures,
                        json.dumps(tags, ensure_ascii=False),
                        experience_id,
                    ),
                )
            else:
                experience_id = str(uuid.uuid4())
                conn.execute(
                    """
                    INSERT INTO experiences(
                        id, created_at, updated_at, status, source_project,
                        task_type, task_summary, language, framework, framework_version,
                        lesson, lesson_key, failure_reason, solution_summary,
                        confidence, success_count, failure_count, tags
                    ) VALUES (?, ?, ?, 'candidate', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        experience_id,
                        now,
                        now,
                        project,
                        args.type,
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
                    ),
                )

        conn.execute(
            """
            INSERT INTO runs(
                id, created_at, source_project, task_type, task_summary,
                language, framework, framework_version, agent_role, model, harness,
                outcome, verification, latency_ms, cost_usd, retry_count,
                notes, tags, experience_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                now,
                project,
                args.type,
                args.task,
                args.language,
                args.framework,
                args.framework_version,
                args.agent_role,
                args.model,
                args.harness,
                args.outcome,
                args.verification,
                args.latency_ms,
                args.cost_usd,
                args.retries,
                args.notes,
                json.dumps(tags, ensure_ascii=False),
                experience_id,
            ),
        )
        conn.commit()

    emit(
        {
            "status": "recorded",
            "run_id": run_id,
            "experience_id": experience_id,
            "project": project,
            "outcome": args.outcome,
            "note": (
                "Reusable lesson stored/aggregated as candidate experience."
                if experience_id
                else "Run stored for statistics; no reusable experience was created."
            ),
        }
    )
    return 0


def build_stats_query(args: argparse.Namespace) -> tuple[str, list[Any]]:
    clauses = ["1=1"]
    params: list[Any] = []
    filters = [
        ("task_type", args.type),
        ("language", args.language),
        ("framework", args.framework),
        ("model", args.model),
        ("agent_role", args.agent_role),
    ]
    for column, value in filters:
        if value:
            clauses.append(f"{column} = ?")
            params.append(value)
    query = f"""
        SELECT
            COALESCE(model, '(unknown)') AS model,
            COALESCE(harness, '(unknown)') AS harness,
            COALESCE(agent_role, '(unknown)') AS agent_role,
            COALESCE(task_type, '(unknown)') AS task_type,
            COUNT(*) AS runs,
            ROUND(AVG(CASE WHEN outcome = 'success' THEN 1.0 ELSE 0.0 END) * 100.0, 1) AS success_rate_pct,
            ROUND(AVG(cost_usd), 6) AS avg_cost_usd,
            ROUND(AVG(latency_ms), 1) AS avg_latency_ms,
            ROUND(AVG(retry_count), 2) AS avg_retries
        FROM runs
        WHERE {" AND ".join(clauses)}
        GROUP BY model, harness, agent_role, task_type
        ORDER BY runs DESC, success_rate_pct DESC
    """
    return query, params


def cmd_stats(args: argparse.Namespace) -> int:
    query, params = build_stats_query(args)
    with connect() as conn:
        rows = conn.execute(query, params).fetchall()
    emit({"groups": [dict(row) for row in rows], "count": len(rows)})
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
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
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
        active = conn.execute(
            "SELECT COUNT(*) FROM experiences WHERE status='active'"
        ).fetchone()[0]
        candidates = conn.execute(
            "SELECT COUNT(*) FROM experiences WHERE status='candidate'"
        ).fetchone()[0]
    emit(
        {
            "status": "ok" if integrity == "ok" else "error",
            "app_version": APP_VERSION,
            "schema_version": SCHEMA_VERSION,
            "home": str(p["home"]),
            "database": str(p["db"]),
            "integrity": integrity,
            "runs": runs,
            "experiences": experiences,
            "active": active,
            "candidates": candidates,
        }
    )
    return 0 if integrity == "ok" else 1


def add_context_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--type", help="Task family, e.g. migration, debugging, test-generation")
    parser.add_argument("--language")
    parser.add_argument("--framework")
    parser.add_argument("--framework-version")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agent-lore",
        description="Local-first continual learning for coding agents.",
    )
    parser.add_argument("--version", action="version", version=APP_VERSION)
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="Initialize the local Agent Lore store.")
    p_init.set_defaults(func=cmd_init)

    p_retrieve = sub.add_parser("retrieve", help="Retrieve relevant reusable experience.")
    p_retrieve.add_argument("--task", required=True)
    add_context_args(p_retrieve)
    p_retrieve.add_argument("--limit", type=int, default=5)
    p_retrieve.set_defaults(func=cmd_retrieve)

    p_record = sub.add_parser("record", help="Record a run and optional reusable lesson.")
    p_record.add_argument("--task", required=True)
    add_context_args(p_record)
    p_record.add_argument("--outcome", required=True, choices=["success", "failure", "partial"])
    p_record.add_argument("--project")
    p_record.add_argument("--agent-role")
    p_record.add_argument("--model")
    p_record.add_argument("--harness")
    p_record.add_argument("--verification")
    p_record.add_argument("--lesson")
    p_record.add_argument("--failure-reason")
    p_record.add_argument("--solution")
    p_record.add_argument("--confidence", type=float, default=0.5)
    p_record.add_argument("--cost-usd", type=float)
    p_record.add_argument("--latency-ms", type=int)
    p_record.add_argument("--retries", type=int, default=0)
    p_record.add_argument("--notes")
    p_record.add_argument("--tags", help="Comma-separated tags")
    p_record.set_defaults(func=cmd_record)

    p_stats = sub.add_parser("stats", help="Summarize observed model/agent outcomes.")
    add_context_args(p_stats)
    p_stats.add_argument("--model")
    p_stats.add_argument("--agent-role")
    p_stats.set_defaults(func=cmd_stats)

    p_export = sub.add_parser("export", help="Create a portable consistent snapshot.")
    p_export.add_argument("--output")
    p_export.set_defaults(func=cmd_export)

    p_import = sub.add_parser("import", help="Restore a portable snapshot.")
    p_import.add_argument("bundle")
    p_import.set_defaults(func=cmd_import)

    p_doctor = sub.add_parser("doctor", help="Inspect local store health.")
    p_doctor.set_defaults(func=cmd_doctor)
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    if hasattr(args, "confidence") and not 0.0 <= args.confidence <= 1.0:
        parser.error("--confidence must be between 0 and 1")
    if hasattr(args, "retries") and args.retries < 0:
        parser.error("--retries must be >= 0")
    if hasattr(args, "latency_ms") and args.latency_ms is not None and args.latency_ms < 0:
        parser.error("--latency-ms must be >= 0")
    if hasattr(args, "cost_usd") and args.cost_usd is not None and args.cost_usd < 0:
        parser.error("--cost-usd must be >= 0")
    try:
        return int(args.func(args))
    except (OSError, sqlite3.Error, ValueError, zipfile.BadZipFile) as exc:
        emit({"status": "error", "error": str(exc)})
        return 1


if __name__ == "__main__":
    sys.exit(main())
