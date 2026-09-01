# Agent Lore

**Local-first continual learning, acceptance tracking, observability, and adaptive routing for coding agents.**

Agent Lore turns coding-agent outcomes into reusable engineering evidence across projects, modules, models, and agent roles. It also tracks whether changes were technically verified and actually accepted, preserves rework lineage, compares model performance by real task context, and recommends model/topology/challenge policies.

> Status: **Integrated Alpha / v0.5.0-alpha (Phase 1–4 + acceptance/observability)**. Cross-device synchronization/service mode remains deferred to Phase 5.

## What is implemented

```text
Phase 1 — Local foundation
  SQLite · retrieve · record · stats · export/import

Phase 2 — Knowledge lifecycle
  candidate/active/deprecated/archive
  evidence lineage · utility/freshness · conservative consolidation
  pattern/skill/eval promotion · learned skill materialization

Phase 3 — Capability intelligence
  project × module × task/subtype × role × model × harness
  execution · verification · acceptance · quality · cost · timing · retries

Phase 4 — Adaptive multi-agent
  observe / assist / adaptive modes
  model/agent config router
  single / flat-parallel / lead-worker / sequential topology router
  selective challenge escalation
  routing-decision → outcome feedback loop

Acceptance / observability extension
  execution ≠ verification ≠ acceptance
  accept / rework / reject / invalidate feedback
  parent-run rework lineage + attempt_index
  first-pass acceptance + rework-aware benchmark
  Markdown project/module/task reports
```

## Core principles

**Past experience is evidence, not truth.**

**Agent execution success is not final delivery success.**

A run may compile and pass tests yet still be rejected because the requirement, product behavior, UX, maintainability, or integration result is wrong. Agent Lore therefore keeps execution, verification, and acceptance separate.

```text
execution outcome
        ↓
verification status
        ↓
acceptance status
        ↓
learning outcome
```

Automatic knowledge promotion requires accepted and verified evidence.

## Repository layout

```text
agent-lore/
├─ SKILL.md
├─ scripts/
│  ├─ agent_lore.py
│  ├─ lore_common.py
│  ├─ lore_memory.py
│  ├─ lore_feedback.py
│  ├─ lore_lifecycle.py
│  ├─ lore_registry.py
│  ├─ lore_routing.py
│  ├─ lore_ops.py
│  └─ lore_report.py
├─ references/
│  ├─ ARCHITECTURE.md
│  ├─ DATA_MODEL.md
│  ├─ LIFECYCLE.md
│  ├─ ROUTING.md
│  └─ ACCEPTANCE.md
├─ tests/
│  └─ test_smoke.py
├─ .github/workflows/test.yml
├─ LICENSE
└─ README.md
```

Runtime data stays outside the repository:

```text
~/.agent-lore/
├─ agent-lore.db
├─ knowledge/
│  └─ skills/
├─ reports/
│  └─ latest.md
├─ traces/
├─ archive/
└─ exports/
```

Override with `AGENT_LORE_HOME`.

## Install as an Agent Skill

Agent Lore uses the open Agent Skills `SKILL.md` format. Put this repository in a project/user/custom skill directory supported by your coding agent.

For DeepSeek Harness, one project-level location is:

```text
<project>/.agents/skills/agent-lore/
```

Initialize or upgrade the local database:

```bash
python scripts/agent_lore.py init
```

The CLI uses only the Python standard library (Python 3.10+).

## Start safely

Fresh installations default to `observe`:

```bash
python scripts/agent_lore.py policy show
```

Then move to `assist` and `adaptive` only after real outcomes exist:

```bash
python scripts/agent_lore.py policy set --mode assist
python scripts/agent_lore.py policy set --mode adaptive
```

## Register model/agent configurations

Cold-start tiers are priors, not benchmark claims.

```bash
python scripts/agent_lore.py config add \
  --name fast-implementation-worker \
  --model my-fast-model \
  --harness my-harness \
  --agent-role implementation-worker \
  --quality-tier 4 \
  --cost-tier 1
```

Delegation-capable lead:

```bash
python scripts/agent_lore.py config add \
  --name backend-lead \
  --model my-lead-model \
  --agent-role backend-lead \
  --can-delegate \
  --max-depth 2
```

## Integrated recommendation

```bash
python scripts/agent_lore.py recommend \
  --task "implement three independent validation checks" \
  --project my-project \
  --module authentication \
  --type test-generation \
  --subtype boundary-validation \
  --language typescript \
  --framework nextjs \
  --agent-role test-worker \
  --complexity medium \
  --risk low \
  --parallelizable yes \
  --dependency-level low \
  --estimated-subtasks 3 \
  --uncertainty 0.25
```

The result includes relevant knowledge, topology, selected config, alternatives, exploration candidate, challenge level, and a `decision_id`.

## Record an execution attempt

```bash
python scripts/agent_lore.py record \
  --task "simplify refresh token controls" \
  --project my-project \
  --module authentication \
  --type implementation \
  --subtype product-flow \
  --operation implement \
  --outcome success \
  --model my-fast-model \
  --harness my-harness \
  --agent-role implementation-worker \
  --verification "unit + e2e passed" \
  --verification-status passed \
  --wall-time-ms 42000 \
  --compute-time-ms 30000 \
  --review-time-ms 5000
```

For user-visible/product work, acceptance remains `pending` until relevant human/reviewer feedback exists.

For a completely machine-verifiable task, record `--acceptance-status not-required` only when human/product judgment is genuinely unnecessary.

## Accept / rework / reject

Accept:

```bash
python scripts/agent_lore.py feedback <run-id> \
  --verdict accept \
  --reason "meets expected behavior"
```

Rework:

```bash
python scripts/agent_lore.py feedback <run-id> \
  --verdict rework \
  --reason "technically correct but interaction is too complicated"
```

Record the corrected attempt as the same logical task:

```bash
python scripts/agent_lore.py record \
  --task "simplify refresh token controls" \
  --parent-run-id <previous-run-id> \
  --outcome success \
  --verification-status passed \
  --acceptance-status accepted \
  --acceptance-source human
```

Agent Lore preserves the task group and increments the attempt index. This makes first-pass acceptance, rework count, accumulated work-to-final-result, and cost-to-final-result measurable.

Negative feedback on a run linked to learned knowledge flags that knowledge as `needs_revalidation` rather than silently trusting it.

## Human-readable report

Generate a Markdown report:

```bash
python scripts/agent_lore.py report
```

Default:

```text
~/.agent-lore/reports/latest.md
```

Drill down:

```bash
python scripts/agent_lore.py report \
  --project my-project \
  --module authentication \
  --type debugging
```

The report contains:

- project/module/task/subtype model benchmark
- execution success vs acceptance
- first-pass acceptance and rework count
- quality and cost
- wall/compute/verification/review/coordination timing
- rework/task-group history
- accumulated recorded work time to final accepted result
- knowledge health and revalidation backlog

JSON stats remain available:

```bash
python scripts/agent_lore.py stats --project my-project --module authentication
```

## Knowledge lifecycle

Record a reusable lesson only when evidence exists:

```bash
python scripts/agent_lore.py record \
  --task "safe enum migration" \
  --project project-a \
  --module data-model \
  --type migration \
  --outcome success \
  --verification "migration test + e2e passed" \
  --verification-status passed \
  --acceptance-status accepted \
  --acceptance-source reviewer \
  --lesson "Prefer a transitional migration when existing rows depend on legacy values" \
  --solution "add transitional value, migrate data, then remove legacy value"
```

Lifecycle maintenance:

```bash
python scripts/agent_lore.py consolidate
python scripts/agent_lore.py consolidate --apply
```

Promotion:

```bash
python scripts/agent_lore.py promote <knowledge-id> --kind pattern
python scripts/agent_lore.py promote <knowledge-id> --kind skill --name safe-enum-migration
python scripts/agent_lore.py materialize-skills
```

Execution success by itself does not qualify for automatic promotion.

## Model and topology benchmark semantics

Agent Lore does not claim that one model is globally better. It asks:

```text
In this project/module/task context,
which model/harness/role produced accepted results
with the best quality / time / cost / rework profile?
```

This matters because a fast first generation can still be slower overall if it needs repeated correction.

Prefer metrics such as:

- acceptance rate
- first-pass acceptance rate
- reworks
- wall time
- accumulated work to accepted result
- cost to accepted result
- quality
- deterministic verification

rather than raw generation latency alone.

## Multi-agent guardrails

Default policy:

```text
max_depth = 2
max_agents = 6
```

Supported topology recommendations:

- `single`
- `flat-parallel`
- `lead-worker`
- `sequential`

Wall time and accumulated compute/coordination time should be recorded separately when possible; multi-agent can reduce user waiting time while increasing total compute/cost.

## Portability

```bash
python scripts/agent_lore.py export --output agent-lore-backup.zip
python scripts/agent_lore.py import agent-lore-backup.zip
```

SQLite is backed up consistently before export. Import creates a safety backup and upgrades older schemas when opened.

## Phase 5 remains deferred

Not implemented yet:

- remote source of truth
- automatic multi-device synchronization
- event replication/local cache
- long-running MCP/daemon service
- object storage for large traces

Until then, portable ZIP transfer is the supported device migration path.

## Success criteria

The goal is not a large memory database. Measure whether Agent Lore improves real delivery:

```text
Memory Lift = performance(with Agent Lore) - model-only baseline
```

Also track:

- acceptance / first-pass acceptance lift
- retry and rework reduction
- time/cost to accepted result
- challenge ROI
- topology overhead/conflicts
- per-task model configuration utility

If memory or routing produces negative lift, revalidate or disable it rather than trusting history because it exists.

## License

MIT
