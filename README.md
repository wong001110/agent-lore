# Agent Lore

**Local-first continual learning and adaptive routing for coding agents.**

Agent Lore turns verified coding-agent outcomes into reusable engineering evidence across projects, models, and agent roles. It can also learn which agent configuration is cost-effective for a task and recommend how multi-agent work should be organized.

> Status: **Integrated Alpha / v0.4.0-alpha (Phase 1–4)**. Local learning, knowledge lifecycle, capability intelligence, and adaptive routing are implemented. Cross-device synchronization/service mode remains deferred.

## What is implemented

```text
Phase 1 — Local foundation
  SQLite · retrieve · record · stats · export/import

Phase 2 — Knowledge lifecycle
  candidate/active/deprecated/archive
  evidence lineage · utility/freshness · conservative consolidation
  pattern/skill/eval promotion · learned skill materialization

Phase 3 — Capability intelligence
  task × role × model × harness outcomes
  quality · success · cost · latency · retries
  delegation capability registry

Phase 4 — Adaptive multi-agent
  observe / assist / adaptive modes
  model/agent config router
  single / flat-parallel / lead-worker / sequential topology router
  selective challenge escalation
  routing-decision → outcome feedback loop
```

Phase 5 (not implemented) is remote sync/service mode.

## Core principle

**Past experience is evidence, not truth.**

Agent Lore is designed to avoid becoming a stale rulebook. Current project constraints, dependency versions, current-model reasoning, and deterministic tests remain authoritative inputs. Historical knowledge may be challenged, revalidated, deprecated, archived, or replaced.

## Architecture

```text
                       Coding agent / harness
                Codex · DeepSeek Harness · others
                              │
                              ▼
                       Agent Lore Skill
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
 Engineering knowledge   Capability registry    Adaptive router
 experiences/patterns    model/role/harness     model/topology/challenge
        │                     │                     │
        └─────────────────────┼─────────────────────┘
                              ▼
                      ~/.agent-lore/
                      agent-lore.db
                      knowledge/skills/
                      archive/ exports/
```

The GitHub repository contains the learning engine and skill instructions. Personal learned data stays outside the repository.

## Repository layout

```text
agent-lore/
├─ SKILL.md
├─ scripts/
│  ├─ agent_lore.py          # CLI entry
│  ├─ lore_common.py         # schema/utilities
│  ├─ lore_memory.py         # retrieve/record
│  ├─ lore_lifecycle.py      # consolidate/promote/materialize
│  ├─ lore_registry.py       # agent/model capability registry
│  ├─ lore_routing.py        # topology/model/challenge routing
│  └─ lore_ops.py            # stats/export/import/doctor
├─ references/
│  ├─ ARCHITECTURE.md
│  ├─ DATA_MODEL.md
│  ├─ LIFECYCLE.md
│  └─ ROUTING.md
├─ tests/
│  └─ test_smoke.py
├─ .github/workflows/test.yml
├─ LICENSE
└─ README.md
```

Runtime data:

```text
~/.agent-lore/
├─ agent-lore.db
├─ knowledge/
│  └─ skills/
├─ traces/
├─ archive/
└─ exports/
```

Override with `AGENT_LORE_HOME`.

## Install as an Agent Skill

Agent Lore uses the open Agent Skills `SKILL.md` format. Place the repository as an `agent-lore` skill directory in a project/user/custom skill location supported by your coding agent.

For DeepSeek Harness, one project-level location is:

```text
<project>/.agents/skills/agent-lore/
```

Initialize or upgrade the local database:

```bash
python scripts/agent_lore.py init
```

The CLI uses only the Python standard library (Python 3.10+).

## Start safely: observe → assist → adaptive

Fresh installations default to `observe`:

```bash
python scripts/agent_lore.py policy show
```

After collecting outcomes:

```bash
python scripts/agent_lore.py policy set --mode assist
```

Only enable autonomous application when you trust the observed results and host-harness integration:

```bash
python scripts/agent_lore.py policy set --mode adaptive
```

The skill itself does not magically spawn arbitrary external models. It recommends a configuration/topology; the host coding harness must support executing it.

## Register agent/model configurations

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

List configurations:

```bash
python scripts/agent_lore.py config list
```

## Integrated recommendation

```bash
python scripts/agent_lore.py recommend \
  --task "implement three independent validation checks" \
  --type test-generation \
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

The output includes:

- relevant knowledge (small retrieval budget)
- recommended topology
- recommended registered agent/model configuration
- alternative configurations
- optional exploration/shadow candidate
- challenge level
- a `decision_id`

Feed the real outcome back:

```bash
python scripts/agent_lore.py record \
  --task "implement three independent validation checks" \
  --type test-generation \
  --outcome success \
  --model my-fast-model \
  --harness my-harness \
  --agent-role test-worker \
  --topology flat-parallel \
  --agent-count 3 \
  --quality-score 0.93 \
  --cost-usd 0.05 \
  --route-decision-id <decision-id>
```

That closes the routing learning loop.

## Knowledge lifecycle

Record a reusable lesson only when evidence exists:

```bash
python scripts/agent_lore.py record \
  --task "safe enum migration" \
  --type migration \
  --outcome success \
  --language typescript \
  --framework prisma \
  --verification "migration test + e2e passed" \
  --lesson "Prefer a transitional migration when existing rows depend on legacy values" \
  --solution "add transitional value, migrate data, then remove legacy value"
```

Preview consolidation:

```bash
python scripts/agent_lore.py consolidate
```

Apply conservative lifecycle changes:

```bash
python scripts/agent_lore.py consolidate --apply
```

Promote deliberately:

```bash
python scripts/agent_lore.py promote <knowledge-id> --kind pattern
python scripts/agent_lore.py promote <knowledge-id> --kind skill --name safe-enum-migration
python scripts/agent_lore.py materialize-skills
```

Old knowledge can be retained without normal retrieval:

```bash
python scripts/agent_lore.py deprecate <id> --reason "framework now has a safer native API"
python scripts/agent_lore.py archive <id> --reason "stale low-utility historical case"
```

## Challenge is selective

Agent Lore does not recommend a second model for every task. Its challenge score considers risk, uncertainty, failure cost, historical conflict/staleness, and deterministic evidence.

```text
low value       → none
small uncertainty → self-check
meaningful risk → cheap challenger
critical conflict/uncertainty → strong challenger
```

Deterministic gates should be preferred when they can answer the question.

## Multi-agent guardrails

Default policy keeps hierarchy shallow:

```text
max_depth = 2
max_agents = 6
```

The router distinguishes:

- `single`
- `flat-parallel`
- `lead-worker`
- `sequential`

It should not create parallel workers for strongly dependent tasks or overlapping mutable write scopes merely to increase concurrency.

## Portability

```bash
python scripts/agent_lore.py export --output agent-lore-backup.zip
python scripts/agent_lore.py import agent-lore-backup.zip
```

SQLite is backed up consistently before export. Import creates a safety backup of an existing local database and upgrades older Agent Lore schemas when opened.

## What remains for Phase 5

Not part of the current alpha:

- remote source of truth
- automatic multi-device synchronization
- local cache/event replication
- long-running MCP/daemon service
- object storage for large traces

Until then, manual portable ZIP transfer is the supported device migration path.

## Success criteria

The goal is not a large memory database. Measure whether the system actually helps:

```text
Memory Lift = performance(with Agent Lore) - model-only baseline
```

Also track:

- retry reduction
- success/quality lift
- cost and latency
- challenge ROI
- topology overhead/conflicts
- per-task model configuration utility

If memory or routing produces negative lift, it should be revalidated or disabled rather than trusted because it is historical.

## License

MIT
