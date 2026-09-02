"""Optional host-supplied execution topology and per-agent telemetry."""

from lore_common import *  # noqa: F401,F403


CAPTURE_STATUSES = ("complete", "partial", "not-collected")
AGENT_COLUMNS = (
    "agent_id",
    "parent_agent_id",
    "display_name",
    "role",
    "specialization",
    "model",
    "harness",
    "status",
    "task_summary",
    "depth",
    "started_at",
    "finished_at",
    "wall_time_ms",
    "compute_time_ms",
    "cost_usd",
)
TELEMETRY_FIELDS = ("specialization", "model", "harness")


def load_agent_manifest(raw: str) -> dict[str, Any]:
    """Accept an inline object or @path without requiring a specific harness."""
    source = raw
    if raw.startswith("@"):
        path_text = raw[1:].strip()
        if not path_text:
            raise ValueError("Agent manifest @path is empty")
        source = Path(path_text).expanduser().read_text(encoding="utf-8")
    try:
        value = json.loads(source)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Agent manifest must be valid JSON: {exc.msg}") from exc
    if not isinstance(value, dict):
        raise ValueError("Agent manifest must be a JSON object")
    return value


def optional_text(value: Any, location: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{location} must be a non-empty string when provided")
    return value.strip()


def optional_int(value: Any, location: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{location} must be a non-negative integer when provided")
    return value


def optional_float(value: Any, location: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
        raise ValueError(f"{location} must be a non-negative number when provided")
    return float(value)


def validate_agent_manifest(value: dict[str, Any]) -> dict[str, Any]:
    capture_status = value.get("capture_status")
    if capture_status is None:
        capture_status = "complete" if value.get("agents") else "not-collected"
    if capture_status not in CAPTURE_STATUSES:
        raise ValueError(f"capture_status must be one of: {', '.join(CAPTURE_STATUSES)}")

    raw_agents = value.get("agents", [])
    if not isinstance(raw_agents, list):
        raise ValueError("agents must be an array")
    if capture_status == "not-collected" and raw_agents:
        raise ValueError("capture_status not-collected cannot include agent entries")
    if capture_status == "complete" and not raw_agents:
        raise ValueError("capture_status complete requires at least one agent")

    agents: list[dict[str, Any]] = []
    ids: set[str] = set()
    aliases = {
        "parent_id": "parent_agent_id",
        "name": "display_name",
        "task": "task_summary",
    }
    recognized = set(AGENT_COLUMNS) | set(aliases) | {"metadata"}
    for index, raw_agent in enumerate(raw_agents):
        if not isinstance(raw_agent, dict):
            raise ValueError(f"agents[{index}] must be an object")
        normalized = dict(raw_agent)
        for alias, canonical in aliases.items():
            if canonical not in normalized and alias in normalized:
                normalized[canonical] = normalized[alias]

        agent_id = optional_text(normalized.get("agent_id"), f"agents[{index}].agent_id")
        if agent_id is None:
            raise ValueError(f"agents[{index}].agent_id is required")
        if agent_id in ids:
            raise ValueError(f"duplicate agent_id in manifest: {agent_id}")
        ids.add(agent_id)

        parent_id = optional_text(
            normalized.get("parent_agent_id"),
            f"agents[{index}].parent_agent_id",
        )
        if parent_id == agent_id:
            raise ValueError(f"agent {agent_id} cannot be its own parent")

        metadata = normalized.get("metadata")
        if metadata is None:
            metadata = {}
        if not isinstance(metadata, dict):
            raise ValueError(f"agents[{index}].metadata must be an object")
        metadata = {
            **metadata,
            **{key: item for key, item in raw_agent.items() if key not in recognized},
        }
        try:
            json.dumps(metadata, ensure_ascii=False)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"agents[{index}].metadata must be JSON serializable") from exc

        agent = {
            "agent_id": agent_id,
            "parent_agent_id": parent_id,
            "display_name": optional_text(normalized.get("display_name"), f"agents[{index}].display_name"),
            "role": optional_text(normalized.get("role"), f"agents[{index}].role"),
            "specialization": optional_text(normalized.get("specialization"), f"agents[{index}].specialization"),
            "model": optional_text(normalized.get("model"), f"agents[{index}].model"),
            "harness": optional_text(normalized.get("harness"), f"agents[{index}].harness"),
            "status": optional_text(normalized.get("status"), f"agents[{index}].status"),
            "task_summary": optional_text(normalized.get("task_summary"), f"agents[{index}].task_summary"),
            "depth": optional_int(normalized.get("depth"), f"agents[{index}].depth"),
            "started_at": optional_text(normalized.get("started_at"), f"agents[{index}].started_at"),
            "finished_at": optional_text(normalized.get("finished_at"), f"agents[{index}].finished_at"),
            "wall_time_ms": optional_int(normalized.get("wall_time_ms"), f"agents[{index}].wall_time_ms"),
            "compute_time_ms": optional_int(normalized.get("compute_time_ms"), f"agents[{index}].compute_time_ms"),
            "cost_usd": optional_float(normalized.get("cost_usd"), f"agents[{index}].cost_usd"),
            "metadata_json": json.dumps(metadata, ensure_ascii=False, sort_keys=True),
        }
        agents.append(agent)

    by_id = {agent["agent_id"]: agent for agent in agents}
    if capture_status == "complete":
        missing_parents = sorted({
            agent["parent_agent_id"]
            for agent in agents
            if agent["parent_agent_id"] and agent["parent_agent_id"] not in by_id
        })
        if missing_parents:
            raise ValueError(
                "complete capture references parents missing from the manifest: "
                + ", ".join(missing_parents)
            )

    def inferred_depth(agent: dict[str, Any], trail: set[str]) -> int | None:
        if agent["depth"] is not None:
            return int(agent["depth"])
        parent_id = agent["parent_agent_id"]
        if not parent_id:
            return 0
        parent = by_id.get(parent_id)
        if parent is None:
            return None
        if agent["agent_id"] in trail:
            raise ValueError("agent parent relationships contain a cycle")
        parent_depth = inferred_depth(parent, trail | {agent["agent_id"]})
        return None if parent_depth is None else parent_depth + 1

    for agent in agents:
        agent["depth"] = inferred_depth(agent, set())

    return {
        "capture_status": capture_status,
        "source": optional_text(value.get("source"), "source"),
        "notes": optional_text(value.get("notes"), "notes"),
        "agents": agents,
    }


def cmd_agents_record(args: argparse.Namespace) -> int:
    manifest = validate_agent_manifest(load_agent_manifest(args.manifest_json))
    now = utc_now()
    with connect() as conn:
        conn.execute("BEGIN IMMEDIATE")
        run = conn.execute(
            "SELECT id, model, harness FROM runs WHERE id=?",
            (args.run_id,),
        ).fetchone()
        if not run:
            raise ValueError(f"unknown run id: {args.run_id}")
        inherited = {"model": 0, "harness": 0}
        for agent in manifest["agents"]:
            # This is host-observed run metadata, not an inferred agent choice.
            # A manifest-provided value always wins.
            for field in ("model", "harness"):
                if agent[field] is None and run[field] is not None:
                    agent[field] = run[field]
                    inherited[field] += 1
        existing_count = int(conn.execute(
            "SELECT COUNT(*) FROM run_agents WHERE run_id=?",
            (args.run_id,),
        ).fetchone()[0])
        if manifest["capture_status"] == "not-collected" and existing_count:
            raise ValueError(
                "cannot mark execution not-collected while agent ledger entries already exist"
            )

        for agent in manifest["agents"]:
            conn.execute(
                """
                INSERT INTO run_agents(
                    run_id, agent_id, parent_agent_id, display_name, role, specialization,
                    model, harness, status, task_summary, depth, started_at, finished_at,
                    wall_time_ms, compute_time_ms, cost_usd, metadata_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(run_id, agent_id) DO UPDATE SET
                    parent_agent_id=excluded.parent_agent_id,
                    display_name=excluded.display_name,
                    role=excluded.role,
                    specialization=excluded.specialization,
                    model=excluded.model,
                    harness=excluded.harness,
                    status=excluded.status,
                    task_summary=excluded.task_summary,
                    depth=excluded.depth,
                    started_at=excluded.started_at,
                    finished_at=excluded.finished_at,
                    wall_time_ms=excluded.wall_time_ms,
                    compute_time_ms=excluded.compute_time_ms,
                    cost_usd=excluded.cost_usd,
                    metadata_json=excluded.metadata_json,
                    updated_at=excluded.updated_at
                """,
                (
                    args.run_id,
                    *(agent[column] for column in AGENT_COLUMNS),
                    agent["metadata_json"],
                    now,
                    now,
                ),
            )

        # A complete manifest is an authoritative snapshot. Partial manifests
        # remain additive so hosts can stream whatever subset they can observe.
        if manifest["capture_status"] == "complete":
            agent_ids = [agent["agent_id"] for agent in manifest["agents"]]
            placeholders = ", ".join("?" for _ in agent_ids)
            conn.execute(
                f"DELETE FROM run_agents WHERE run_id=? AND agent_id NOT IN ({placeholders})",
                (args.run_id, *agent_ids),
            )

        known_agents = int(conn.execute(
            "SELECT COUNT(*) FROM run_agents WHERE run_id=?",
            (args.run_id,),
        ).fetchone()[0])
        exact_count = known_agents if manifest["capture_status"] == "complete" else None
        conn.execute(
            """
            UPDATE runs SET
                execution_capture_status=?,
                execution_capture_source=?,
                execution_capture_notes=?,
                execution_captured_at=?,
                agent_count=COALESCE(?, agent_count)
            WHERE id=?
            """,
            (
                manifest["capture_status"],
                manifest["source"],
                manifest["notes"],
                now,
                exact_count,
                args.run_id,
            ),
        )
        conn.commit()

    emit(
        {
            "status": "agent-ledger-recorded",
            "run_id": args.run_id,
            "capture_status": manifest["capture_status"],
            "capture_source": manifest["source"],
            "agents_in_request": len(manifest["agents"]),
            "known_agents": known_agents,
            "agent_count_exact": manifest["capture_status"] == "complete",
            "inherited_from_run": {key: value for key, value in inherited.items() if value},
        }
    )
    return 0


def cmd_agents_show(args: argparse.Namespace) -> int:
    with connect() as conn:
        run = conn.execute(
            """
            SELECT id, task_summary, topology, agent_count, execution_capture_status,
                   execution_capture_source, execution_capture_notes, execution_captured_at
            FROM runs WHERE id=?
            """,
            (args.run_id,),
        ).fetchone()
        if not run:
            raise ValueError(f"unknown run id: {args.run_id}")
        rows = conn.execute(
            """
            SELECT * FROM run_agents
            WHERE run_id=?
            ORDER BY COALESCE(depth, 999), created_at, agent_id
            """,
            (args.run_id,),
        ).fetchall()

    agents: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        item["metadata"] = json.loads(item.pop("metadata_json") or "{}")
        agents.append(item)
    coverage = {
        field: sum(1 for agent in agents if agent.get(field) is not None)
        for field in TELEMETRY_FIELDS
    }
    emit(
        {
            "run": dict(run),
            "known_agents": len(agents),
            "agent_count_exact": run["execution_capture_status"] == "complete",
            "telemetry_coverage": {
                "agents": len(agents),
                "fields": coverage,
                "complete_optional_metadata": all(value == len(agents) for value in coverage.values()),
            },
            "agents": agents,
        }
    )
    return 0
