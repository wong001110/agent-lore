"""Agent/model capability registry and task-conditioned ranking."""

from lore_common import *  # noqa: F401,F403

def cmd_config_add(args: argparse.Namespace) -> int:
    now = utc_now()
    with connect() as conn:
        existing = conn.execute("SELECT id FROM agent_configs WHERE name = ?", (args.name,)).fetchone()
        config_id = existing["id"] if existing else stable_id("cfg-")
        conn.execute(
            """
            INSERT INTO agent_configs(
                id, created_at, updated_at, name, model, harness, agent_role,
                enabled, can_delegate, max_depth, quality_tier, cost_tier, priority, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET
                updated_at=excluded.updated_at,
                model=excluded.model,
                harness=excluded.harness,
                agent_role=excluded.agent_role,
                enabled=1,
                can_delegate=excluded.can_delegate,
                max_depth=excluded.max_depth,
                quality_tier=excluded.quality_tier,
                cost_tier=excluded.cost_tier,
                priority=excluded.priority,
                notes=excluded.notes
            """,
            (
                config_id,
                now,
                now,
                args.name,
                args.model,
                args.harness,
                args.agent_role,
                1 if args.can_delegate else 0,
                args.max_depth,
                args.quality_tier,
                args.cost_tier,
                args.priority,
                args.notes,
            ),
        )
        conn.commit()
    emit({"status": "saved", "config_id": config_id, "name": args.name})
    return 0


def cmd_config_list(args: argparse.Namespace) -> int:
    clauses = ["1=1"]
    params: list[Any] = []
    if not args.all:
        clauses.append("enabled = 1")
    if args.agent_role:
        clauses.append("COALESCE(agent_role, '') = COALESCE(?, '')")
        params.append(args.agent_role)
    with connect() as conn:
        rows = conn.execute(
            f"SELECT * FROM agent_configs WHERE {' AND '.join(clauses)} ORDER BY priority DESC, name",
            params,
        ).fetchall()
    emit({"count": len(rows), "configs": [dict(row) for row in rows]})
    return 0


def cmd_config_disable(args: argparse.Namespace) -> int:
    with connect() as conn:
        changed = conn.execute(
            "UPDATE agent_configs SET enabled=0, updated_at=? WHERE name=?",
            (utc_now(), args.name),
        ).rowcount
        conn.commit()
    if not changed:
        raise ValueError(f"unknown config name: {args.name}")
    emit({"status": "disabled", "name": args.name})
    return 0


def cmd_policy_show(_: argparse.Namespace) -> int:
    with connect() as conn:
        current = policy(conn)
    emit(current)
    return 0


def cmd_policy_set(args: argparse.Namespace) -> int:
    updates: dict[str, str] = {}
    if args.mode is not None:
        updates["policy.mode"] = args.mode
    if args.exploration_rate is not None:
        updates["policy.exploration_rate"] = str(args.exploration_rate)
    if args.max_depth is not None:
        updates["policy.max_depth"] = str(args.max_depth)
    if args.max_agents is not None:
        updates["policy.max_agents"] = str(args.max_agents)
    if args.max_challenge_level is not None:
        updates["policy.max_challenge_level"] = str(args.max_challenge_level)
    if args.min_model_confidence is not None:
        updates["policy.min_model_confidence"] = str(args.min_model_confidence)
    if args.active_memory_limit is not None:
        updates["policy.active_memory_limit"] = str(args.active_memory_limit)
    with connect() as conn:
        for key, value in updates.items():
            set_meta(conn, key, value)
        conn.commit()
        current = policy(conn)
    emit({"status": "updated", "policy": current})
    return 0


def historical_config_stats(conn: sqlite3.Connection, config: sqlite3.Row, args: argparse.Namespace) -> dict[str, Any]:
    clauses = ["model = ?"]
    params: list[Any] = [config["model"]]
    if config["harness"]:
        clauses.append("COALESCE(harness, '') = ?")
        params.append(config["harness"])
    if config["agent_role"]:
        clauses.append("COALESCE(agent_role, '') = ?")
        params.append(config["agent_role"])
    elif getattr(args, "agent_role", None):
        clauses.append("COALESCE(agent_role, '') = ?")
        params.append(args.agent_role)

    specificity = 0
    for column, value in (
        ("task_type", getattr(args, "type", None)),
        ("language", getattr(args, "language", None)),
        ("framework", getattr(args, "framework", None)),
    ):
        if value:
            clauses.append(f"COALESCE({column}, '') = ?")
            params.append(value)
            specificity += 1

    query = f"""
        SELECT
            COUNT(*) AS runs,
            SUM(CASE WHEN outcome='success' THEN 1 ELSE 0 END) AS successes,
            AVG(CASE WHEN quality_score IS NOT NULL THEN quality_score END) AS avg_quality,
            AVG(cost_usd) AS avg_cost,
            AVG(latency_ms) AS avg_latency,
            AVG(retry_count) AS avg_retries
        FROM runs
        WHERE {' AND '.join(clauses)}
          AND run_kind IN ('primary', 'shadow', 'challenge')
    """
    row = conn.execute(query, params).fetchone()
    runs = int(row["runs"] or 0)
    successes = int(row["successes"] or 0)
    success_rate = (successes + 1.0) / (runs + 2.0)
    avg_quality = float(row["avg_quality"]) if row["avg_quality"] is not None else success_rate
    confidence = min(1.0, runs / 10.0) * (0.7 + 0.1 * specificity)
    return {
        "runs": runs,
        "success_rate": success_rate,
        "avg_quality": avg_quality,
        "avg_cost": float(row["avg_cost"]) if row["avg_cost"] is not None else None,
        "avg_latency": float(row["avg_latency"]) if row["avg_latency"] is not None else None,
        "avg_retries": float(row["avg_retries"]) if row["avg_retries"] is not None else None,
        "confidence": min(1.0, confidence),
    }


def minmax_inverse(value: float | None, values: list[float]) -> float:
    if value is None or not values:
        return 0.5
    lo, hi = min(values), max(values)
    if math.isclose(lo, hi):
        return 0.5
    return 1.0 - ((value - lo) / (hi - lo))


def rank_configs(conn: sqlite3.Connection, args: argparse.Namespace, require_delegate: bool) -> list[dict[str, Any]]:
    clauses = ["enabled=1"]
    params: list[Any] = []
    if args.agent_role:
        clauses.append("(agent_role IS NULL OR agent_role = ?)")
        params.append(args.agent_role)
    if require_delegate:
        clauses.append("can_delegate = 1")
    configs = conn.execute(
        f"SELECT * FROM agent_configs WHERE {' AND '.join(clauses)} ORDER BY priority DESC, name",
        params,
    ).fetchall()
    if not configs:
        return []

    candidates: list[dict[str, Any]] = []
    for cfg in configs:
        stats = historical_config_stats(conn, cfg, args)
        candidates.append({"config": cfg, "stats": stats})

    observed_costs = [item["stats"]["avg_cost"] for item in candidates if item["stats"]["avg_cost"] is not None]
    observed_latencies = [item["stats"]["avg_latency"] for item in candidates if item["stats"]["avg_latency"] is not None]

    ranked: list[dict[str, Any]] = []
    for item in candidates:
        cfg = item["config"]
        stats = item["stats"]
        history_confidence = stats["confidence"]
        cold_quality = max(0.0, min(1.0, (int(cfg["quality_tier"]) - 1) / 4.0))
        cold_cost = 1.0 - max(0.0, min(1.0, (int(cfg["cost_tier"]) - 1) / 4.0))
        priority_score = max(0.0, min(1.0, int(cfg["priority"]) / 100.0))
        cold_score = 0.55 * cold_quality + 0.30 * cold_cost + 0.15 * priority_score

        if stats["runs"]:
            cost_score = minmax_inverse(stats["avg_cost"], observed_costs)
            latency_score = minmax_inverse(stats["avg_latency"], observed_latencies)
            retry_score = 1.0 / (1.0 + max(0.0, stats["avg_retries"] or 0.0))
            learned_score = (
                0.50 * stats["success_rate"]
                + 0.22 * stats["avg_quality"]
                + 0.12 * cost_score
                + 0.08 * latency_score
                + 0.08 * retry_score
            )
            score = history_confidence * learned_score + (1.0 - history_confidence) * cold_score
        else:
            score = cold_score

        ranked.append(
            {
                "config_id": cfg["id"],
                "name": cfg["name"],
                "model": cfg["model"],
                "harness": cfg["harness"],
                "agent_role": cfg["agent_role"],
                "can_delegate": bool(cfg["can_delegate"]),
                "max_depth": cfg["max_depth"],
                "score": round(score, 4),
                "confidence": round(history_confidence, 4),
                "historical_runs": stats["runs"],
                "success_rate": round(stats["success_rate"], 4),
                "avg_quality": round(stats["avg_quality"], 4),
                "avg_cost_usd": stats["avg_cost"],
                "avg_latency_ms": stats["avg_latency"],
                "avg_retries": stats["avg_retries"],
                "source": "learned+bootstrap" if stats["runs"] else "bootstrap",
            }
        )
    ranked.sort(key=lambda item: (item["score"], item["confidence"], item["historical_runs"]), reverse=True)
    return ranked
