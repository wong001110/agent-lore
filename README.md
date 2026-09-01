# Agent Lore

**Local-first continual learning, acceptance tracking, adaptive multi-agent execution, proportional verification, and security-invariant guidance for coding agents.**

Agent Lore is an engineering-learning layer that helps a coding harness reuse accepted evidence, choose an execution shape, route models/roles, decide how much verification is justified, and learn from rework/failures without treating history as authority.

> Status: **Integrated Alpha / v0.7.0-alpha**. The learning/routing CLI is implemented; the richer TaskShape/DAG/recursive-execution-tree model is currently expressed as Skill policy for host agents and is a target for future runtime/data-model upgrades.

## Core principles

```text
Past experience is evidence, not truth.
Execution success is not final success.
Functional success does not prove security.
More agents/tests/attacks are not automatically better.
Use the smallest topology and verification depth sufficient for current risk.
```

## What Agent Lore covers

### Learning and acceptance

```text
run
 -> deterministic verification
 -> acceptance / rework / rejection
 -> reusable evidence
 -> pattern / skill / eval promotion when justified
```

It preserves rework lineage, first-pass acceptance, cost/timing, and revalidation signals instead of counting every technically successful run as a clean success.

### Adaptive execution

Single agent is the strong default. Delegation is only worthwhile when expected parallelism/context/specialization/independent-verification gain exceeds coordination, integration, shared-state, duplicate-work, and compute costs.

For non-trivial work, reason from a TaskShape:

```text
workstreams
+ dependency DAG
+ read/write/contract scopes
+ risk and failure cost
+ integration points
+ verification/security surfaces
```

Separate:

```text
coordination shape: single | manager-worker | hierarchical | peer-handoff
schedule:           serial | parallel | hybrid
depth:              0 | 1 | 2+
```

Nested delegation is recursive: every child must independently justify further delegation. `max_depth` is a safety ceiling, not a target.

See [`references/ROUTING.md`](references/ROUTING.md).

### Execution waves, verification timing, and commits

Independent DAG nodes with disjoint mutable scopes may execute in parallel waves. Workers run cheap scoped checks; expensive integrated checks are normally amortized at integration/feature/release checkpoints.

Verification is proportional:

```text
V0 trivial
V1 local
V2 feature
V3 cross-boundary / high-risk
V4 critical / release
```

Gate families are conditional: functional, migration/data integrity, compatibility/contracts, concurrency/idempotency, security, performance/resource, operational/rollback.

Security/attack depth is also adaptive:

```text
none | smoke | focused | deep | adversarial
```

Small related edits should normally accumulate into a coherent stable batch before expensive verification and final semantic commit. Child-agent completion is not automatically a Git commit boundary.

See [`references/EXECUTION.md`](references/EXECUTION.md).

### Security invariants

Security is modeled as:

```text
assets
 -> trust boundaries
 -> allowed flows
 -> invariants
 -> applicable attack families
 -> synthetic canaries
 -> selective security-control mutation
```

The baseline regression catalog includes provider credential isolation, redirect leakage, logs/artifacts/history leaks, cross-context isolation, CI secret exposure, least privilege, indirect prompt injection, and MCP/tool poisoning. Agentic attack families can extend to goal/context/memory poisoning, approval bypass, inter-agent trust exploitation, excessive authority, denial-of-wallet, skill/config poisoning, and sandbox boundaries when applicable.

Security incidents/near-misses may become new regression candidates only after root cause and deterministic/strong validation; internet/repository claims are not automatically promoted into permanent lore.

See [`references/SECURITY.md`](references/SECURITY.md).

## Structural agent roles

Prefer a small role vocabulary:

- **Orchestrator/Main** — TaskShape, routing, integration, checkpoints
- **Domain Lead** — local orchestration when a child workstream truly needs nested delegation
- **Worker** — scoped implementation/research
- **Verifier** — independent deterministic verification
- **Challenger** — independent critique for unresolved risk/uncertainty
- **Security Red-Team** — bounded adversarial attempts against explicit invariants

Frontend/backend/database/infra/mobile/research are usually specializations/capabilities, not permanent agent classes.

## Current CLI

Initialize:

```bash
python scripts/agent_lore.py init
```

Fresh installations default to `observe`:

```bash
python scripts/agent_lore.py policy show
python scripts/agent_lore.py policy set --mode assist
```

Retrieve knowledge:

```bash
python scripts/agent_lore.py retrieve \
  --task "safe enum migration" \
  --project my-project \
  --module data-model \
  --type migration \
  --language typescript \
  --framework prisma
```

Register an agent/model configuration:

```bash
python scripts/agent_lore.py config add \
  --name fast-worker \
  --model my-model \
  --harness my-harness \
  --agent-role implementation-worker \
  --quality-tier 4 \
  --cost-tier 1
```

Integrated recommendation:

```bash
python scripts/agent_lore.py recommend \
  --task "implement three independent validation checks" \
  --project my-project \
  --module authentication \
  --type test-generation \
  --parallelizable yes \
  --dependency-level low \
  --estimated-subtasks 3
```

The current CLI topology fields are coarse compatibility signals. v0.7 policy requires the host to reason about TaskShape/DAG, recursive delegation, execution waves, and proportional verification rather than blindly treating those flags as complete analysis.

Record an attempt:

```bash
python scripts/agent_lore.py record \
  --task "simplify refresh token controls" \
  --project my-project \
  --module authentication \
  --type implementation \
  --operation implement \
  --outcome success \
  --model my-model \
  --verification "focused unit + integration passed" \
  --verification-status passed
```

Acceptance/rework:

```bash
python scripts/agent_lore.py feedback <run-id> --verdict accept
python scripts/agent_lore.py feedback <run-id> --verdict rework --reason "<reason>"
```

Lifecycle:

```bash
python scripts/agent_lore.py consolidate
python scripts/agent_lore.py consolidate --apply
python scripts/agent_lore.py promote <id> --kind pattern
python scripts/agent_lore.py promote <id> --kind skill --name <name>
python scripts/agent_lore.py materialize-skills
```

Reports:

```bash
python scripts/agent_lore.py report
python scripts/agent_lore.py stats --project my-project --module authentication
```

Portability:

```bash
python scripts/agent_lore.py export --output agent-lore-backup.zip
python scripts/agent_lore.py import agent-lore-backup.zip
```

## Repository layout

```text
agent-lore/
├─ SKILL.md
├─ scripts/
├─ references/
│  ├─ ARCHITECTURE.md
│  ├─ DATA_MODEL.md
│  ├─ LIFECYCLE.md
│  ├─ ROUTING.md
│  ├─ EXECUTION.md
│  ├─ ACCEPTANCE.md
│  └─ SECURITY.md
├─ tests/
├─ .github/workflows/test.yml
└─ README.md
```

Runtime state remains under `~/.agent-lore/` by default and should not be synchronized through Git.

## Current limitations / next runtime work

The policy is ahead of the runtime data model in several areas. Future implementation should add:

- automatic TaskShape extraction instead of relying primarily on caller-supplied routing hints
- explicit task DAG and execution waves
- coordination shape/schedule/depth as separate data
- per-node execution tree, parent/depth, role/model, scopes, costs, handoffs and integration rework
- per-node model/config selection for heterogeneous teams
- recursive runtime routing and dynamic collapse/replan
- verification/gate/attack-budget telemetry and Test Utility / Attack ROI
- knowledge scope (task/module/project/stack/global) and appropriately scoped promotion
- executable red-team/security learner rather than policy guidance alone

Do not claim these are fully automated until the runtime/host actually supplies them.

## Success criteria

Measure accepted delivery lift rather than agent activity:

```text
Memory Lift     = performance(with Agent Lore) - model-only baseline
Delegation Lift = accepted-result improvement - coordination/integration cost
Test Utility    = severity-weighted defects caught / verification cost
Attack ROI      = severity-weighted findings / attack cost
```

If added memory, hierarchy, verification, or attacks produce negative lift, narrow/revalidate the policy rather than keeping them because they exist.

## License

MIT
