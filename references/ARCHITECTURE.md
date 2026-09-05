# Architecture

Agent Lore v0.9 is a **model/harness-independent sidecar control + evidence system** around coding work.

It is deliberately not the agent's brain and not a universal coding runtime.

## System boundary

```text
┌──────────────────────────────────────────────────────────────┐
│ Project + current coding agent / harness                    │
│                                                            │
│ project AGENTS/docs/source/tests/ADRs                       │
│ model-native planning · delegation · implementation · debug │
└────────────────────────────┬─────────────────────────────────┘
                             │ SKILL.md + CLI / host adapter
                             ▼
┌──────────────────────────────────────────────────────────────┐
│ Agent Lore sidecar                                          │
│                                                            │
│ Control plane          Evidence plane        Calibration    │
│ policy/guardrails      runs/acceptance       model/config   │
│ hard budgets           rework/revalidation   routing stats  │
│ scope validation       scoped history        challenge ROI  │
│                        agent telemetry        memory lift    │
└────────────────────────────┬─────────────────────────────────┘
                             ▼
┌──────────────────────────────────────────────────────────────┐
│ ~/.agent-lore/agent-lore.db                                 │
│ canonical local structured state                            │
└──────────────────────────────────────────────────────────────┘
```

The host remains responsible for execution and for enforcing capability boundaries it can enforce deterministically.

## Cognitive / control / evidence split

### Cognitive plane

Owned by current model/harness:

- understand current repository/task
- choose plan/implementation
- decide whether decomposition/delegation helps
- debug/replan
- choose appropriate tools/checks within allowed authority

Agent Lore should not prescribe a reasoning procedure.

### Control plane

Agent Lore may define/record independently justified limits such as:

- permission/write/network/credential boundaries
- destructive-action approval
- sandbox/production separation
- hard budget / agent / delegation-depth ceilings

Actual deterministic enforcement belongs in the host/tool layer where possible.

### Evidence plane

Agent Lore stores/derives:

- run outcomes
- verification state
- acceptance/rework/rejection
- evidence lineage/revalidation
- scoped historical Evidence Capsules
- model/harness statistics
- routing decisions
- optional after-the-fact execution tree
- human-readable reports

Evidence does not automatically become policy.

## End-to-end loop

```text
Task
 ↓
Discover/read project-owned context
 ↓
Inspect current source/tests/contracts
 ↓
Current model forms native working plan
 ↓
Optional pull-based historical evidence
 ↓
Optional TaskShape / EvidencePlan
 ↓
Host execution (possibly delegated)
 ↓
Deterministic/proportional verification
 ↓
Record run + acceptance/rework + route outcome
 ↓
Optionally attach actual execution ledger
 ↓
Create/update scoped Evidence Capsule only when warranted
 ↓
Consolidate / revalidate / deprecate / supersede patterns
 ↓
Next task
```

Historical memory can be completely absent from the loop.

## Project-context boundary

Agent Lore does not own a project wiki and does not impose repository folders.

The host may discover semantic roles such as:

```text
agent instructions
current state
architecture
decisions/incidents
verification
security
```

from whatever paths the project already uses.

A future adapter may cache private/local semantic mappings under `~/.agent-lore/projects/`. Optional version-controlled mapping may be supported, but zero-config/no-repo-change remains the default.

## Historical evidence architecture

Canonical historical state remains structured in SQLite.

Knowledge lifecycle:

```text
run
 ↓
scoped evidence/experience
 ↓
active experience when justified
 ↓
reusable pattern when justified
```

v0.9 retires generated learned Agent Skills. Legacy `kind=skill` rows/files remain backward-compatible/read-only and are excluded from normal retrieval.

Evidence Capsule fields separate:

- observation/failure
- invariant
- root cause + epistemic status
- applicability / not-proven boundaries
- failure/problem family
- historical solution variant + status
- declared scope

This lets future models use historical facts without inheriting old procedures as instructions.

## Pull-based memory

Memory modes:

```text
off | guardrail | rescue | proactive
```

- `off`: zero historical context
- `guardrail`: compact failure/invariant cards, old procedures hidden
- `rescue`: historical remedies may be revealed after difficulty/failure
- `proactive`: deliberate reveal for high-risk/explicit historical analysis

Memory context is bounded by token budget and scope. `recommend` defaults to policy memory `off`; explicit `retrieve` defaults to `guardrail`.

## Adaptive execution boundary

TaskShape/EvidencePlan are host-supplied working hypotheses. Agent Lore validates/operationalizes them rather than pretending to understand a repository better than the current model.

Modern routing vocabulary:

```text
coordination: single | manager-worker | hierarchical
schedule: serial | parallel | hybrid
depth: 0 | 1 | 2+
DAG waves: [[workstream ids], ...]
```

Hard ceilings remain policy constraints. The current model may choose a smaller topology as capabilities improve.

Legacy heuristics remain fallback compatibility only.

## Model/harness calibration

`agent_configs` describes currently available executors. Observed runs provide task-conditioned evidence:

```text
task/project/module/stack
× model
× harness
× role
× topology
→ execution/verification/acceptance
→ quality/cost/timing/retries
```

The optimization unit is an executor/configuration in context, not a universal model leaderboard.

A new model should normally require only registration + evaluation. It should not trigger architecture migration.

Memory preference is also model/task dependent; use matched/shadow evaluation to estimate Memory Lift where useful.

## Security architecture

Security remains based on stable semantics:

```text
asset
→ trust boundary
→ allowed flow
→ invariant
→ applicable attack family
→ isolated evidence
```

The strength of a red-team executor can change without changing the invariant model.

## Observability

`run_agents` is an optional after-the-fact host observation of actual topology. It is not an execution plan.

Missing telemetry is first-class (`not-collected` / `partial` / `complete`) so absence cannot be mistaken for single-agent execution.

Reports are derived from SQLite. Semantic summaries/reports are not canonical memory and may be regenerated.

## Storage

Fresh install:

```text
~/.agent-lore/
└─ agent-lore.db
```

Lazy derived/operational directories:

```text
reports/   generated report views
exports/   default portable export output
archive/   import safety backups
```

Legacy upgraded installations may also contain `knowledge/` from pre-v0.9 learned-Skill materialization. These files remain portable for compatibility but are no longer created.

Empty `traces/` and `knowledge/skills/` placeholder directories are not part of the v0.9 runtime layout.

## Portable boundary

The conceptual durable interfaces are:

```text
record outcome/evidence
retrieve optional scoped evidence
record usage/revalidation/feedback
get capability statistics
recommend bounded route
attach execution telemetry
generate reports
export/import structured state
```

Future storage, retrieval, MCP, or cross-device services may replace local implementations without changing these semantics.
