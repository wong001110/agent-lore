#!/usr/bin/env python3
"""Shared schema and utilities for Agent Lore.

Integrated Alpha (Phase 1-4) plus human acceptance/observability:
- local persistence and portability
- evidence lifecycle and learned knowledge
- task-conditioned agent/model capability observations
- model, topology, and challenge recommendations
- verification, acceptance, rework lineage, and module/task timing

The CLI intentionally uses only the Python standard library.
"""

from __future__ import annotations

import argparse
import hashlib
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

APP_VERSION = "0.5.0-alpha"
SCHEMA_VERSION = "5"
TOKEN_RE = re.compile(r"[a-zA-Z0-9_+.#-]{2,}")
SKILL_NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

DEFAULT_POLICY: dict[str, str] = {
    "policy.mode": "observe",
    "policy.exploration_rate": "0.10",
    "policy.max_depth": "2",
    "policy.max_agents": "6",
    "policy.max_challenge_level": "3",
    "policy.min_model_confidence": "0.35",
    "policy.active_memory_limit": "2000",
}

TOPOLOGIES = ("single", "flat-parallel", "lead-worker", "sequential")
CHALLENGE_LEVELS = ("none", "self-check", "cheap-challenger", "strong-challenger")
VERIFICATION_STATUSES = ("pending", "passed", "failed", "not-required")
ACCEPTANCE_STATUSES = ("pending", "accepted", "rework", "rejected", "invalidated", "not-required")
FEEDBACK_VERDICTS = ("accept", "rework", "reject", "invalidate")
FEEDBACK_SOURCES = ("human", "reviewer", "auto")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def days_since(value: str | None) -> float:
    parsed = parse_iso(value)
    if parsed is None:
        return 10_000.0
    return max(0.0, (datetime.now(timezone.utc) - parsed).total_seconds() / 86400.0)


def lore_home() -> Path:
    override = os.environ.get("AGENT_LORE_HOME")
    return Path(override).expanduser().resolve() if override else Path.home() / ".agent-lore"


def paths() -> dict[str, Path]:
    home = lore_home()
    return {
        "home": home,
        "db": home / "agent-lore.db",
        "knowledge": home / "knowledge",
        "skills": home / "knowledge" / "skills",
        "traces": home / "traces",
        "archive": home / "archive",
        "exports": home / "exports",
        "reports": home / "reports",
    }


def ensure_dirs() -> dict[str, Path]:
    p = paths()
    for key in ("home", "knowledge", "skills", "traces", "archive", "exports", "reports"):
        p[key].mkdir(parents=True, exist_ok=True)
    return p


def emit(payload: Any) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=False))


def normalize(value: str | None) -> str:
    return " ".join((value or "").strip().lower().split())


def parse_tags(raw: str | None) -> list[str]:
    if not raw:
        return []
    return sorted({normalize(item) for item in raw.split(",") if normalize(item)})


def bool_int(value: bool | None) -> int | None:
    if value is None:
        return None
    return 1 if value else 0


def infer_project_name(start: Path | None = None) -> str:
    current = (start or Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".git").exists():
            return candidate.name
    return current.name


def stable_id(prefix: str = "") -> str:
    value = str(uuid.uuid4())
    return f"{prefix}{value}" if prefix else value


def ensure_column(conn: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    columns = {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    if column not in columns:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def set_meta(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute(
        "INSERT INTO meta(key, value) VALUES(?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, value),
    )


def get_meta(conn: sqlite3.Connection, key: str, default: str | None = None) -> str | None:
    row = conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
    return row[0] if row else default


def init_schema(conn: sqlite3.Connection) -> None:
    # Base v0.1-compatible tables first, so existing databases can be upgraded in place.
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
            status TEXT NOT NULL DEFAULT 'candidate',
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
            outcome TEXT NOT NULL,
            verification TEXT,
            latency_ms INTEGER,
            cost_usd REAL,
            retry_count INTEGER NOT NULL DEFAULT 0,
            notes TEXT,
            tags TEXT NOT NULL DEFAULT '[]',
            experience_id TEXT,
            FOREIGN KEY(experience_id) REFERENCES experiences(id)
        );
        """
    )

    # Phase 2 lifecycle / lineage columns.
    ensure_column(conn, "experiences", "kind", "TEXT NOT NULL DEFAULT 'experience'")
    ensure_column(conn, "experiences", "knowledge_name", "TEXT")
    ensure_column(conn, "experiences", "trust", "TEXT NOT NULL DEFAULT 'local-verified'")
    ensure_column(conn, "experiences", "last_verified_at", "TEXT")
    ensure_column(conn, "experiences", "status_reason", "TEXT")
    ensure_column(conn, "experiences", "superseded_by", "TEXT")
    ensure_column(conn, "experiences", "module", "TEXT")
    ensure_column(conn, "experiences", "task_subtype", "TEXT")
    ensure_column(conn, "experiences", "needs_revalidation", "INTEGER NOT NULL DEFAULT 0")

    # Phase 3/4 run context.
    ensure_column(conn, "runs", "quality_score", "REAL")
    ensure_column(conn, "runs", "run_kind", "TEXT NOT NULL DEFAULT 'primary'")
    ensure_column(conn, "runs", "topology", "TEXT")
    ensure_column(conn, "runs", "agent_count", "INTEGER")
    ensure_column(conn, "runs", "merge_conflicts", "INTEGER")
    ensure_column(conn, "runs", "challenge_level", "TEXT")
    ensure_column(conn, "runs", "challenge_useful", "INTEGER")
    ensure_column(conn, "runs", "route_decision_id", "TEXT")

    # Human-observable task context and acceptance lifecycle.
    ensure_column(conn, "runs", "module", "TEXT")
    ensure_column(conn, "runs", "task_subtype", "TEXT")
    ensure_column(conn, "runs", "task_scope", "TEXT")
    ensure_column(conn, "runs", "operation", "TEXT")
    ensure_column(conn, "runs", "task_group_id", "TEXT")
    ensure_column(conn, "runs", "parent_run_id", "TEXT")
    ensure_column(conn, "runs", "attempt_index", "INTEGER NOT NULL DEFAULT 1")
    ensure_column(conn, "runs", "verification_status", "TEXT NOT NULL DEFAULT 'pending'")
    ensure_column(conn, "runs", "acceptance_status", "TEXT NOT NULL DEFAULT 'pending'")
    ensure_column(conn, "runs", "acceptance_reason", "TEXT")
    ensure_column(conn, "runs", "acceptance_source", "TEXT")
    ensure_column(conn, "runs", "accepted_at", "TEXT")
    ensure_column(conn, "runs", "wall_time_ms", "INTEGER")
    ensure_column(conn, "runs", "compute_time_ms", "INTEGER")
    ensure_column(conn, "runs", "verification_time_ms", "INTEGER")
    ensure_column(conn, "runs", "review_time_ms", "INTEGER")
    ensure_column(conn, "runs", "coordination_time_ms", "INTEGER")
    ensure_column(conn, "runs", "files_touched", "INTEGER")
    ensure_column(conn, "runs", "lines_changed", "INTEGER")
    ensure_column(conn, "runs", "modules_touched", "INTEGER")
    ensure_column(conn, "runs", "has_db_change", "INTEGER")
    ensure_column(conn, "runs", "has_api_contract_change", "INTEGER")
    ensure_column(conn, "runs", "test_count", "INTEGER")

    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS experience_evidence (
            experience_id TEXT NOT NULL,
            run_id TEXT NOT NULL,
            relation TEXT NOT NULL DEFAULT 'related',
            created_at TEXT NOT NULL,
            PRIMARY KEY(experience_id, run_id),
            FOREIGN KEY(experience_id) REFERENCES experiences(id),
            FOREIGN KEY(run_id) REFERENCES runs(id)
        );

        CREATE TABLE IF NOT EXISTS run_feedback (
            id TEXT PRIMARY KEY,
            run_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            verdict TEXT NOT NULL,
            reason TEXT,
            source TEXT NOT NULL DEFAULT 'human',
            related_run_id TEXT,
            FOREIGN KEY(run_id) REFERENCES runs(id)
        );

        CREATE TABLE IF NOT EXISTS agent_configs (
            id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            name TEXT NOT NULL UNIQUE,
            model TEXT NOT NULL,
            harness TEXT,
            agent_role TEXT,
            enabled INTEGER NOT NULL DEFAULT 1,
            can_delegate INTEGER NOT NULL DEFAULT 0,
            max_depth INTEGER NOT NULL DEFAULT 0,
            quality_tier INTEGER NOT NULL DEFAULT 3,
            cost_tier INTEGER NOT NULL DEFAULT 3,
            priority INTEGER NOT NULL DEFAULT 50,
            notes TEXT
        );

        CREATE TABLE IF NOT EXISTS routing_decisions (
            id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            mode TEXT NOT NULL,
            task_type TEXT,
            task_summary TEXT NOT NULL,
            language TEXT,
            framework TEXT,
            framework_version TEXT,
            agent_role TEXT,
            complexity TEXT,
            risk TEXT,
            parallelizable TEXT,
            dependency_level TEXT,
            cross_domain INTEGER NOT NULL DEFAULT 0,
            estimated_subtasks INTEGER NOT NULL DEFAULT 1,
            uncertainty REAL NOT NULL DEFAULT 0.5,
            memory_conflict INTEGER NOT NULL DEFAULT 0,
            stale_memory INTEGER NOT NULL DEFAULT 0,
            deterministic_evidence TEXT NOT NULL DEFAULT 'none',
            cost_of_failure TEXT NOT NULL DEFAULT 'medium',
            recommended_topology TEXT,
            recommended_config_id TEXT,
            recommended_model TEXT,
            recommended_harness TEXT,
            model_score REAL,
            model_confidence REAL,
            topology_confidence REAL,
            challenge_level TEXT,
            challenge_score REAL,
            reasons_json TEXT NOT NULL DEFAULT '[]',
            applied INTEGER NOT NULL DEFAULT 0,
            outcome_run_id TEXT
        );
        """
    )

    ensure_column(conn, "routing_decisions", "source_project", "TEXT")
    ensure_column(conn, "routing_decisions", "module", "TEXT")
    ensure_column(conn, "routing_decisions", "task_subtype", "TEXT")

    conn.executescript(
        """
        CREATE INDEX IF NOT EXISTS idx_experiences_status ON experiences(status);
        CREATE INDEX IF NOT EXISTS idx_experiences_kind ON experiences(kind);
        CREATE INDEX IF NOT EXISTS idx_experiences_task_type ON experiences(task_type);
        CREATE INDEX IF NOT EXISTS idx_experiences_stack ON experiences(language, framework);
        CREATE INDEX IF NOT EXISTS idx_runs_task_type ON runs(task_type);
        CREATE INDEX IF NOT EXISTS idx_runs_model ON runs(model, harness, agent_role);
        CREATE INDEX IF NOT EXISTS idx_runs_topology ON runs(topology, task_type);
        CREATE INDEX IF NOT EXISTS idx_runs_route_decision ON runs(route_decision_id);
        CREATE INDEX IF NOT EXISTS idx_runs_project_module ON runs(source_project, module, task_type, task_subtype);
        CREATE INDEX IF NOT EXISTS idx_runs_task_group ON runs(task_group_id, attempt_index);
        CREATE INDEX IF NOT EXISTS idx_runs_acceptance ON runs(acceptance_status, verification_status);
        CREATE INDEX IF NOT EXISTS idx_run_feedback_run ON run_feedback(run_id, created_at);
        CREATE INDEX IF NOT EXISTS idx_agent_configs_role ON agent_configs(agent_role, enabled);
        CREATE INDEX IF NOT EXISTS idx_routing_task_type ON routing_decisions(task_type, created_at);
        """
    )

    # Existing v0.4 runs become explicit single-attempt task groups without inventing acceptance.
    conn.execute("UPDATE runs SET task_group_id = id WHERE task_group_id IS NULL OR task_group_id = ''")

    set_meta(conn, "schema_version", SCHEMA_VERSION)
    set_meta(conn, "app_version", APP_VERSION)
    for key, value in DEFAULT_POLICY.items():
        conn.execute("INSERT OR IGNORE INTO meta(key, value) VALUES(?, ?)", (key, value))
    conn.commit()


def connect() -> sqlite3.Connection:
    p = ensure_dirs()
    conn = sqlite3.connect(p["db"])
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    init_schema(conn)
    return conn


def policy(conn: sqlite3.Connection) -> dict[str, Any]:
    return {
        "mode": get_meta(conn, "policy.mode", "observe"),
        "exploration_rate": float(get_meta(conn, "policy.exploration_rate", "0.10") or 0.10),
        "max_depth": int(get_meta(conn, "policy.max_depth", "2") or 2),
        "max_agents": int(get_meta(conn, "policy.max_agents", "6") or 6),
        "max_challenge_level": int(get_meta(conn, "policy.max_challenge_level", "3") or 3),
        "min_model_confidence": float(get_meta(conn, "policy.min_model_confidence", "0.35") or 0.35),
        "active_memory_limit": int(get_meta(conn, "policy.active_memory_limit", "2000") or 2000),
    }


def cmd_init(_: argparse.Namespace) -> int:
    p = ensure_dirs()
    with connect() as conn:
        integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
        current_policy = policy(conn)
    emit(
        {
            "status": "ok",
            "home": str(p["home"]),
            "database": str(p["db"]),
            "app_version": APP_VERSION,
            "schema_version": SCHEMA_VERSION,
            "integrity": integrity,
            "policy": current_policy,
        }
    )
    return 0


def tokenize(*values: str | None) -> set[str]:
    result: set[str] = set()
    for value in values:
        if value:
            result.update(token.lower() for token in TOKEN_RE.findall(value))
    return result


def freshness_value(updated_at: str | None) -> float:
    days = days_since(updated_at)
    if days <= 90:
        return 1.0
    if days <= 365:
        return 0.8
    if days <= 730:
        return 0.5
    return 0.2


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

    if normalize(getattr(args, "type", None)) and normalize(args.type) == normalize(row["task_type"]):
        score += 3.0
        reasons.append("task-type-match")
    if normalize(getattr(args, "subtype", None)) and normalize(args.subtype) == normalize(row["task_subtype"]):
        score += 1.5
        reasons.append("task-subtype-match")
    if normalize(getattr(args, "module", None)) and normalize(args.module) == normalize(row["module"]):
        score += 1.5
        reasons.append("module-match")
    if normalize(getattr(args, "language", None)) and normalize(args.language) == normalize(row["language"]):
        score += 2.0
        reasons.append("language-match")
    if normalize(getattr(args, "framework", None)) and normalize(args.framework) == normalize(row["framework"]):
        score += 2.5
        reasons.append("framework-match")
    if normalize(getattr(args, "framework_version", None)) and normalize(row["framework_version"]):
        if normalize(args.framework_version) == normalize(row["framework_version"]):
            score += 1.5
            reasons.append("version-match")
        else:
            score -= 1.0
            reasons.append("version-mismatch")

    score += 0.8 if row["status"] == "active" else 0.15
    if row["kind"] == "pattern":
        score += 0.25
    elif row["kind"] == "skill":
        score += 0.35
    score += max(0.0, min(1.0, float(row["confidence"])))
    score += min(1.5, math.log2(max(1, int(row["evidence_count"]))) * 0.4)
    score += freshness_value(row["last_verified_at"] or row["updated_at"]) * 0.5

    if row["trust"] not in ("local-verified", "independent-verified"):
        score -= 0.75
        reasons.append("low-trust-provenance")
    if int(row["needs_revalidation"] or 0):
        score -= 1.0
        reasons.append("needs-revalidation")
    if overlap > 0:
        reasons.append("semantic-token-overlap")
    return score, reasons
