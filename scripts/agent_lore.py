#!/usr/bin/env python3
"""Agent Lore CLI entry point."""

from lore_common import *  # noqa: F401,F403
from lore_memory import *  # noqa: F401,F403
from lore_lifecycle import *  # noqa: F401,F403
from lore_registry import *  # noqa: F401,F403
from lore_routing import *  # noqa: F401,F403
from lore_ops import *  # noqa: F401,F403

def add_context_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--type", help="Task family, e.g. migration, debugging, test-generation")
    parser.add_argument("--language")
    parser.add_argument("--framework")
    parser.add_argument("--framework-version")


def add_routing_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--agent-role")
    parser.add_argument("--complexity", choices=["low", "medium", "high"], default="medium")
    parser.add_argument("--risk", choices=["low", "medium", "high", "critical"], default="medium")
    parser.add_argument("--parallelizable", choices=["yes", "no", "unknown"], default="unknown")
    parser.add_argument("--dependency-level", choices=["low", "medium", "high"], default="medium")
    parser.add_argument("--cross-domain", action="store_true")
    parser.add_argument("--estimated-subtasks", type=int, default=1)
    parser.add_argument("--uncertainty", type=float, default=0.5)
    parser.add_argument("--memory-conflict", action="store_true")
    parser.add_argument("--stale-memory", action="store_true")
    parser.add_argument("--deterministic-evidence", choices=["none", "weak", "strong"], default="none")
    parser.add_argument("--cost-of-failure", choices=["low", "medium", "high", "critical"], default="medium")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agent-lore",
        description="Local-first continual learning and adaptive routing for coding agents.",
    )
    parser.add_argument("--version", action="version", version=APP_VERSION)
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="Initialize or upgrade the local Agent Lore store.")
    p_init.set_defaults(func=cmd_init)

    p_retrieve = sub.add_parser("retrieve", help="Retrieve narrowly scoped reusable engineering knowledge.")
    p_retrieve.add_argument("--task", required=True)
    add_context_args(p_retrieve)
    p_retrieve.add_argument("--limit", type=int, default=5)
    p_retrieve.set_defaults(func=cmd_retrieve)

    p_record = sub.add_parser("record", help="Record a verified run and optional reusable lesson.")
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
    p_record.add_argument("--quality-score", type=float)
    p_record.add_argument("--cost-usd", type=float)
    p_record.add_argument("--latency-ms", type=int)
    p_record.add_argument("--retries", type=int, default=0)
    p_record.add_argument("--notes")
    p_record.add_argument("--tags", help="Comma-separated tags")
    p_record.add_argument("--trust", choices=["local-verified", "independent-verified", "untrusted", "unknown"], default="local-verified")
    p_record.add_argument("--run-kind", choices=["primary", "shadow", "challenge"], default="primary")
    p_record.add_argument("--topology", choices=TOPOLOGIES)
    p_record.add_argument("--agent-count", type=int)
    p_record.add_argument("--merge-conflicts", type=int)
    p_record.add_argument("--challenge-level", choices=CHALLENGE_LEVELS)
    useful = p_record.add_mutually_exclusive_group()
    useful.add_argument("--challenge-useful", dest="challenge_useful", action="store_true")
    useful.add_argument("--challenge-not-useful", dest="challenge_useful", action="store_false")
    p_record.set_defaults(challenge_useful=None)
    p_record.add_argument("--route-decision-id")
    p_record.set_defaults(func=cmd_record)

    p_consolidate = sub.add_parser("consolidate", help="Score lifecycle utility and conservatively promote/archive knowledge.")
    p_consolidate.add_argument("--apply", action="store_true", help="Apply safe lifecycle changes; otherwise preview.")
    p_consolidate.set_defaults(func=cmd_consolidate)

    p_knowledge = sub.add_parser("knowledge", help="List learned knowledge.")
    p_knowledge.add_argument("--status", choices=["candidate", "active", "deprecated", "archived"])
    p_knowledge.add_argument("--kind", choices=["experience", "pattern", "skill", "eval"])
    p_knowledge.add_argument("--type")
    p_knowledge.add_argument("--limit", type=int, default=100)
    p_knowledge.set_defaults(func=cmd_knowledge)

    p_promote = sub.add_parser("promote", help="Explicitly promote knowledge into a pattern, skill, or eval case.")
    p_promote.add_argument("id")
    p_promote.add_argument("--kind", required=True, choices=["pattern", "skill", "eval"])
    p_promote.add_argument("--name")
    p_promote.add_argument("--reason")
    p_promote.set_defaults(func=cmd_promote)

    p_deprecate = sub.add_parser("deprecate", help="Deprecate knowledge while preserving its history.")
    p_deprecate.add_argument("id")
    p_deprecate.add_argument("--reason", required=True)
    p_deprecate.add_argument("--superseded-by")
    p_deprecate.set_defaults(func=cmd_deprecate)

    p_archive = sub.add_parser("archive", help="Move knowledge out of normal retrieval without deleting it.")
    p_archive.add_argument("id")
    p_archive.add_argument("--reason", required=True)
    p_archive.set_defaults(func=cmd_archive)

    p_materialize = sub.add_parser("materialize-skills", help="Write active learned skills as Agent Skills directories.")
    p_materialize.set_defaults(func=cmd_materialize)

    p_config = sub.add_parser("config", help="Manage task-routable model/agent configurations.")
    config_sub = p_config.add_subparsers(dest="config_command", required=True)
    p_config_add = config_sub.add_parser("add")
    p_config_add.add_argument("--name", required=True)
    p_config_add.add_argument("--model", required=True)
    p_config_add.add_argument("--harness")
    p_config_add.add_argument("--agent-role")
    p_config_add.add_argument("--can-delegate", action="store_true")
    p_config_add.add_argument("--max-depth", type=int, default=0)
    p_config_add.add_argument("--quality-tier", type=int, choices=range(1, 6), default=3)
    p_config_add.add_argument("--cost-tier", type=int, choices=range(1, 6), default=3, help="1=cheapest, 5=most expensive")
    p_config_add.add_argument("--priority", type=int, default=50)
    p_config_add.add_argument("--notes")
    p_config_add.set_defaults(func=cmd_config_add)
    p_config_list = config_sub.add_parser("list")
    p_config_list.add_argument("--agent-role")
    p_config_list.add_argument("--all", action="store_true")
    p_config_list.set_defaults(func=cmd_config_list)
    p_config_disable = config_sub.add_parser("disable")
    p_config_disable.add_argument("name")
    p_config_disable.set_defaults(func=cmd_config_disable)

    p_policy = sub.add_parser("policy", help="Inspect or change adaptive-routing guardrails.")
    policy_sub = p_policy.add_subparsers(dest="policy_command", required=True)
    p_policy_show = policy_sub.add_parser("show")
    p_policy_show.set_defaults(func=cmd_policy_show)
    p_policy_set = policy_sub.add_parser("set")
    p_policy_set.add_argument("--mode", choices=["observe", "assist", "adaptive"])
    p_policy_set.add_argument("--exploration-rate", type=float)
    p_policy_set.add_argument("--max-depth", type=int)
    p_policy_set.add_argument("--max-agents", type=int)
    p_policy_set.add_argument("--max-challenge-level", type=int, choices=range(0, 4))
    p_policy_set.add_argument("--min-model-confidence", type=float)
    p_policy_set.add_argument("--active-memory-limit", type=int)
    p_policy_set.set_defaults(func=cmd_policy_set)

    p_recommend = sub.add_parser("recommend", help="Recommend knowledge, topology, agent config, and challenge level for a task.")
    p_recommend.add_argument("--task", required=True)
    add_context_args(p_recommend)
    add_routing_args(p_recommend)
    p_recommend.add_argument("--mode", choices=["observe", "assist", "adaptive"])
    p_recommend.add_argument("--limit", type=int, default=3)
    p_recommend.set_defaults(func=cmd_recommend)

    p_stats = sub.add_parser("stats", help="Summarize observed model/agent/topology outcomes and routing decisions.")
    add_context_args(p_stats)
    p_stats.add_argument("--model")
    p_stats.add_argument("--agent-role")
    p_stats.add_argument("--topology", choices=TOPOLOGIES)
    p_stats.set_defaults(func=cmd_stats)

    p_export = sub.add_parser("export", help="Create a portable consistent snapshot.")
    p_export.add_argument("--output")
    p_export.set_defaults(func=cmd_export)

    p_import = sub.add_parser("import", help="Restore a portable snapshot and upgrade it if needed.")
    p_import.add_argument("bundle")
    p_import.set_defaults(func=cmd_import)

    p_doctor = sub.add_parser("doctor", help="Inspect local store, knowledge, config, and routing health.")
    p_doctor.set_defaults(func=cmd_doctor)
    return parser


def validate_args(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    for name in ("confidence", "quality_score", "uncertainty", "exploration_rate", "min_model_confidence"):
        if hasattr(args, name):
            value = getattr(args, name)
            if value is not None and not 0.0 <= value <= 1.0:
                parser.error(f"--{name.replace('_', '-')} must be between 0 and 1")
    for name in ("retries", "latency_ms", "agent_count", "merge_conflicts", "estimated_subtasks", "max_depth", "max_agents", "active_memory_limit"):
        if hasattr(args, name):
            value = getattr(args, name)
            if value is not None and value < 0:
                parser.error(f"--{name.replace('_', '-')} must be >= 0")
    if hasattr(args, "estimated_subtasks") and args.estimated_subtasks < 1:
        parser.error("--estimated-subtasks must be >= 1")
    if hasattr(args, "cost_usd") and args.cost_usd is not None and args.cost_usd < 0:
        parser.error("--cost-usd must be >= 0")
    if hasattr(args, "priority") and not 0 <= args.priority <= 100:
        parser.error("--priority must be between 0 and 100")


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    validate_args(parser, args)
    try:
        return int(args.func(args))
    except (OSError, sqlite3.Error, ValueError, zipfile.BadZipFile) as exc:
        emit({"status": "error", "error": str(exc)})
        return 1


if __name__ == "__main__":
    sys.exit(main())
