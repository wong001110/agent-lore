#!/usr/bin/env python3
"""Agent Lore CLI entry point."""

from lore_common import *  # noqa: F401,F403
from lore_memory import *  # noqa: F401,F403
from lore_feedback import *  # noqa: F401,F403
from lore_lifecycle import *  # noqa: F401,F403
from lore_registry import *  # noqa: F401,F403
from lore_routing import *  # noqa: F401,F403
from lore_execution import *  # noqa: F401,F403
from lore_ops import *  # noqa: F401,F403
from lore_report import *  # noqa: F401,F403


def add_context_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--project", help="Project label; defaults to current Git repository for record")
    parser.add_argument("--module", help="Project module/subsystem, e.g. auth, billing, frontend")
    parser.add_argument("--type", help="Task family, e.g. migration, debugging, test-generation")
    parser.add_argument("--subtype", help="Narrow task subtype, e.g. race-condition, api-endpoint")
    parser.add_argument("--language")
    parser.add_argument("--framework")
    parser.add_argument("--framework-version")


def add_canonical_task_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--task-canonical",
        help="Optional English/canonical task text supplied by the host; original text is preserved",
    )
    parser.add_argument("--source-language", help="Source language hint, e.g. zh-CN or en")


def add_memory_args(parser: argparse.ArgumentParser, default_mode: str | None = None) -> None:
    parser.add_argument(
        "--memory-mode",
        choices=MEMORY_MODES,
        default=default_mode,
        help="off=no history, guardrail=failures/invariants only, rescue/proactive=may expose historical solutions",
    )
    parser.add_argument(
        "--memory-token-budget",
        type=int,
        help="Approximate maximum historical-memory tokens returned for this request",
    )


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
        description=(
            "Cross-project sidecar for engineering evidence, observability, enforceable guardrails, "
            "and model/harness calibration without replacing current-model judgment."
        ),
    )
    parser.add_argument("--version", action="version", version=APP_VERSION)
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="Initialize or upgrade the local Agent Lore store.")
    p_init.set_defaults(func=cmd_init)

    p_retrieve = sub.add_parser("retrieve", help="Retrieve narrowly scoped historical engineering evidence.")
    p_retrieve.add_argument("--task", required=True)
    add_context_args(p_retrieve)
    add_canonical_task_args(p_retrieve)
    add_memory_args(p_retrieve, default_mode="guardrail")
    p_retrieve.add_argument("--limit", type=int, default=5)
    p_retrieve.set_defaults(func=cmd_retrieve)

    p_usage = sub.add_parser(
        "usage",
        help="Record whether retrieved knowledge was actually applied or intentionally ignored.",
    )
    p_usage.add_argument("id", help="Knowledge/experience id")
    p_usage.add_argument("--decision", required=True, choices=["applied", "ignored"])
    p_usage.add_argument("--run-id", help="Optional run in which the usage decision was made")
    p_usage.add_argument("--reason", help="Optional concise rationale for the usage decision")
    p_usage.add_argument("--source", default="host", help="Harness, agent, reviewer, or human source label")
    p_usage.set_defaults(func=cmd_usage)

    p_record = sub.add_parser("record", help="Record one execution attempt plus verification/acceptance state.")
    p_record.add_argument("--task", required=True)
    add_context_args(p_record)
    add_canonical_task_args(p_record)
    p_record.add_argument("--task-scope", help="Area such as backend, frontend, infra, mobile")
    p_record.add_argument("--operation", help="Operation such as implement, fix, refactor, test, review")
    p_record.add_argument("--outcome", required=True, choices=["success", "failure", "partial"], help="Execution outcome, not final user acceptance")
    p_record.add_argument("--agent-role")
    p_record.add_argument("--model")
    p_record.add_argument("--harness")
    p_record.add_argument("--verification")
    p_record.add_argument("--verification-status", choices=VERIFICATION_STATUSES, default="pending")
    p_record.add_argument("--acceptance-status", choices=ACCEPTANCE_STATUSES, default="pending")
    p_record.add_argument("--acceptance-reason")
    p_record.add_argument("--acceptance-source", choices=FEEDBACK_SOURCES)
    p_record.add_argument("--parent-run-id", help="Previous attempt when this run is a rework")
    p_record.add_argument("--task-group-id", help="Optional stable task group id; normally inferred")
    p_record.add_argument(
        "--knowledge-id",
        help=(
            "Explicitly link this run to existing knowledge. The evidence lineage is updated without rewriting "
            "the historical interpretation or solution."
        ),
    )

    # Evidence capsule. `--lesson` remains for backward compatibility and a
    # concise human-readable card, but new integrations should prefer the
    # structured fields below.
    p_record.add_argument("--lesson")
    p_record.add_argument("--lesson-canonical", help="Optional English/canonical compact card supplied by the host")
    p_record.add_argument("--knowledge-scope", choices=KNOWLEDGE_SCOPES, default="project")
    p_record.add_argument("--scope-ref", help="Optional explicit scope identity; inferred when omitted")
    p_record.add_argument("--experience-family", help="Stable failure/problem family, e.g. auth-refresh-race")
    p_record.add_argument("--observation", help="What was actually observed")
    p_record.add_argument("--invariant", help="Condition that should remain true independent of implementation")
    p_record.add_argument("--root-cause", help="Root-cause statement; pair with --root-cause-status")
    p_record.add_argument("--root-cause-status", choices=ROOT_CAUSE_STATUSES, default="unknown")
    p_record.add_argument("--applies-when", help="Comma-separated applicability signals")
    p_record.add_argument("--not-proven", help="Comma-separated claims this evidence does not establish")
    p_record.add_argument("--failure-reason")
    p_record.add_argument("--solution", help="Historical remedy/solution variant; not a future instruction")
    p_record.add_argument("--solution-status", choices=SOLUTION_STATUSES, default="candidate")
    p_record.add_argument("--solution-canonical", help="Optional English/canonical historical remedy supplied by host")
    p_record.add_argument("--canonicalizer", help="Translation/canonicalization model or process identifier")
    p_record.add_argument("--confidence", type=float, default=0.5)
    p_record.add_argument("--quality-score", type=float)
    p_record.add_argument("--cost-usd", type=float)
    p_record.add_argument("--latency-ms", type=int, help="Model/inference latency when known")
    p_record.add_argument("--wall-time-ms", type=int, help="User-visible task-attempt wall time")
    p_record.add_argument("--compute-time-ms", type=int, help="Accumulated agent/model compute time")
    p_record.add_argument("--verification-time-ms", type=int)
    p_record.add_argument("--review-time-ms", type=int)
    p_record.add_argument("--coordination-time-ms", type=int)
    p_record.add_argument("--retries", type=int, default=0)
    p_record.add_argument("--files-touched", type=int)
    p_record.add_argument("--lines-changed", type=int)
    p_record.add_argument("--modules-touched", type=int)
    p_record.add_argument("--has-db-change", action="store_true")
    p_record.add_argument("--has-api-contract-change", action="store_true")
    p_record.add_argument("--test-count", type=int)
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

    p_feedback = sub.add_parser("feedback", help="Record human/reviewer acceptance, rework, rejection, or invalidation for a run.")
    p_feedback.add_argument("run_id")
    p_feedback.add_argument("--verdict", required=True, choices=FEEDBACK_VERDICTS)
    p_feedback.add_argument("--reason")
    p_feedback.add_argument("--source", choices=FEEDBACK_SOURCES, default="human")
    p_feedback.add_argument("--related-run-id", help="Optional corrected/replacement run")
    p_feedback.set_defaults(func=cmd_feedback)

    p_revalidate = sub.add_parser(
        "revalidate",
        help="Clear a knowledge revalidation hold using linked accepted and verified evidence.",
    )
    p_revalidate.add_argument("id", help="Knowledge/experience id")
    p_revalidate.add_argument("--run-id", required=True, help="Linked successful run used as evidence")
    p_revalidate.add_argument("--reason", required=True)
    p_revalidate.add_argument("--source", choices=FEEDBACK_SOURCES, default="reviewer")
    p_revalidate.set_defaults(func=cmd_revalidate)

    p_consolidate = sub.add_parser("consolidate", help="Score lifecycle utility and conservatively promote/archive evidence.")
    p_consolidate.add_argument("--apply", action="store_true", help="Apply safe lifecycle changes; otherwise preview.")
    p_consolidate.set_defaults(func=cmd_consolidate)

    p_knowledge = sub.add_parser("knowledge", help="List learned evidence/patterns and acceptance metrics.")
    p_knowledge.add_argument("--status", choices=["candidate", "active", "deprecated", "archived"])
    p_knowledge.add_argument("--kind", choices=["experience", "pattern", "eval", "skill"], help="skill is legacy read-only")
    p_knowledge.add_argument("--scope", choices=KNOWLEDGE_SCOPES)
    p_knowledge.add_argument("--type")
    p_knowledge.add_argument("--limit", type=int, default=100)
    p_knowledge.set_defaults(func=cmd_knowledge)

    p_promote = sub.add_parser("promote", help="Explicitly promote accepted/verified evidence into a pattern or eval case.")
    p_promote.add_argument("id")
    p_promote.add_argument("--kind", required=True, choices=["pattern", "eval"])
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

    p_policy = sub.add_parser("policy", help="Inspect or change adaptive guardrails and default memory budget.")
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
    p_policy_set.add_argument("--memory-mode", choices=MEMORY_MODES)
    p_policy_set.add_argument("--memory-token-budget", type=int)
    p_policy_set.set_defaults(func=cmd_policy_set)

    p_recommend = sub.add_parser("recommend", help="Recommend topology/config/challenge; historical memory is off unless requested.")
    p_recommend.add_argument("--task", required=True)
    add_context_args(p_recommend)
    add_canonical_task_args(p_recommend)
    add_routing_args(p_recommend)
    add_memory_args(p_recommend, default_mode=None)
    p_recommend.add_argument("--task-shape-json", help="Machine-readable TaskShape JSON, or @path to a JSON file")
    p_recommend.add_argument("--evidence-plan-json", help="Machine-readable EvidencePlan JSON, or @path to a JSON file")
    p_recommend.add_argument("--mode", choices=["observe", "assist", "adaptive"])
    p_recommend.add_argument("--limit", type=int, default=3)
    p_recommend.set_defaults(func=cmd_recommend)

    p_stats = sub.add_parser("stats", help="Summarize project/module/task/model outcomes including acceptance.")
    add_context_args(p_stats)
    p_stats.add_argument("--model")
    p_stats.add_argument("--agent-role")
    p_stats.add_argument("--topology", choices=TOPOLOGIES)
    p_stats.set_defaults(func=cmd_stats)

    p_report = sub.add_parser("report", help="Generate a rolling Markdown or static HTML observability report.")
    p_report.add_argument("--project")
    p_report.add_argument("--module")
    p_report.add_argument("--type")
    p_report.add_argument("--subtype")
    p_report.add_argument("--format", choices=["markdown", "html"], default="markdown")
    p_report.add_argument("--full", action="store_true", help="Include full historical detail instead of the bounded rolling window.")
    p_report.add_argument("--output")
    p_report.set_defaults(func=cmd_report)

    p_agents = sub.add_parser(
        "agents",
        help="Record or inspect optional host-supplied per-run agent execution telemetry.",
    )
    agents_sub = p_agents.add_subparsers(dest="agents_command", required=True)
    p_agents_record = agents_sub.add_parser(
        "record",
        help="Upsert an after-the-fact agent ledger without controlling how agents execute.",
    )
    p_agents_record.add_argument("run_id")
    p_agents_record.add_argument(
        "--manifest-json",
        required=True,
        help="Inline JSON object or @path with capture_status/source/notes/agents.",
    )
    p_agents_record.set_defaults(func=cmd_agents_record)
    p_agents_show = agents_sub.add_parser("show", help="Show the agent ledger for one run.")
    p_agents_show.add_argument("run_id")
    p_agents_show.set_defaults(func=cmd_agents_show)

    p_export = sub.add_parser("export", help="Create a portable consistent snapshot.")
    p_export.add_argument("--output")
    p_export.set_defaults(func=cmd_export)

    p_import = sub.add_parser("import", help="Restore a portable snapshot and upgrade it if needed.")
    p_import.add_argument("bundle")
    p_import.set_defaults(func=cmd_import)

    p_doctor = sub.add_parser("doctor", help="Inspect local store, acceptance backlog, knowledge, config, and routing health.")
    p_doctor.set_defaults(func=cmd_doctor)
    return parser


def validate_args(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    for name in ("confidence", "quality_score", "uncertainty", "exploration_rate", "min_model_confidence"):
        if hasattr(args, name):
            value = getattr(args, name)
            if value is not None and not 0.0 <= value <= 1.0:
                parser.error(f"--{name.replace('_', '-')} must be between 0 and 1")
    for name in (
        "retries", "latency_ms", "wall_time_ms", "compute_time_ms", "verification_time_ms",
        "review_time_ms", "coordination_time_ms", "files_touched", "lines_changed", "modules_touched",
        "test_count", "agent_count", "merge_conflicts", "estimated_subtasks", "max_depth", "max_agents",
        "active_memory_limit", "memory_token_budget",
    ):
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
