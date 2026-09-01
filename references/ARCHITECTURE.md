# Architecture

Agent Lore Integrated Alpha implements Phase 1–4 locally while keeping the foundation model and coding harness replaceable.

## System boundary

```text
┌───────────────────────────────────────────────────────────┐
│ Coding agent / harness                                    │
│ planner · lead · worker · reviewer                        │
└──────────────────────────┬────────────────────────────────┘
                           │ SKILL.md + CLI
                           ▼
┌───────────────────────────────────────────────────────────┐
│ Agent Lore                                                │
│                                                           │
│ Knowledge       Capability         Adaptive routing       │
│ retrieve        model/role stats   topology               │
│ record          agent configs      model config           │
│ consolidate                        challenge               │
└──────────────────────────┬────────────────────────────────┘
                           ▼
┌───────────────────────────────────────────────────────────┐
│ ~/.agent-lore/                                            │
│ agent-lore.db · knowledge/skills · archive · exports      │
└───────────────────────────────────────────────────────────┘
```

The repository is the **learning engine**. User-specific learning state is outside Git.

## End-to-end loop

```text
Task
 ↓
Current project inspection
 ↓
Tentative model-native plan
 ↓
Relevant knowledge retrieval
 ↓
Topology + agent configuration + challenge recommendation
 ↓
Execution by host harness
 ↓
Deterministic verification
 ↓
Record run + route decision outcome
 ↓
Capability statistics + knowledge evidence
 ↓
Consolidate / promote / revalidate / deprecate
 ↓
Next task
```

## Phase 1 — Local foundation

Operations:

- `init`
- `retrieve`
- `record`
- `stats`
- `export`
- `import`
- `doctor`

SQLite is an operational catalog, not a transcript dump.

## Phase 2 — Knowledge lifecycle

Agent Lore distinguishes runs from learned knowledge.

```text
run observation
 ↓
candidate experience
 ↓
active experience
 ↓
pattern
 ↓
explicit skill/eval promotion
```

Knowledge can be deprecated or archived without deletion. `experience_evidence` links runs to knowledge so project diversity can be measured instead of pretending repeated summaries are independent evidence.

`consolidate` is intentionally conservative: it may promote repeated cross-project candidates and generalize strong experiences into patterns, but skill promotion and deprecation remain explicit decisions.

## Phase 3 — Capability intelligence

`agent_configs` describes what the router is allowed to select:

```text
model
harness
agent role
can_delegate
max_depth
quality-tier cold-start prior
cost-tier cold-start prior
priority
```

Observed runs then add task-conditioned evidence:

```text
task × language/framework × role × model × harness
→ success / quality / cost / latency / retries
```

The unit of optimization is an **agent configuration**, not a universal model leaderboard.

## Phase 4 — Adaptive routing

### Topology router

Possible shapes:

```text
single
flat-parallel
lead-worker
sequential
```

Cold start is heuristic and constrained by task dependencies, parallelizability, cross-domain scope, max depth, and max agents. Once enough outcomes exist, historical topology performance may override the heuristic when evidence is strong.

### Model/agent router

Selection blends:

- task-conditioned observed success
- observed quality
- observed cost/latency/retries
- cold-start quality/cost tiers
- configuration priority

Low-sample observations are smoothed and remain low-confidence.

### Challenge router

Challenge is an escalation policy. Inputs include:

- risk
- uncertainty
- cost of failure
- memory conflict
- stale memory
- deterministic evidence strength

Strong deterministic evidence should usually reduce reliance on another LLM.

### Exploration

Path dependence is controlled with a small exploration rate. Agent Lore exposes an under-sampled exploration candidate in deterministic slots. Shadow evaluation is preferred where possible, especially for new models.

## Operating modes

```text
observe  → recommendation logged, execution unchanged
assist   → recommendation surfaced, parent decides
adaptive → recommendation may be applied within guardrails
```

This separation allows the complete Phase 4 architecture to exist before enough historical data has accumulated to trust adaptive routing.

## Host-harness responsibility

Agent Lore is a Skill + local CLI. It does not itself provide universal process spawning or provider APIs.

The host coding agent/harness is responsible for:

- invoking a selected model/configuration
- spawning sub-agents if supported
- enforcing file/write scope
- stopping runaway delegation
- passing real outcome metadata back to Agent Lore

## Recursion and budget

Default local policy:

```text
max_depth = 2
max_agents = 6
```

A lead-worker topology is only useful if a registered configuration can delegate and the host runtime actually exposes that capability.

## Storage strategy

```text
agent-lore.db
  structured runs
  knowledge metadata
  evidence lineage
  agent configurations
  routing decisions
  policy

knowledge/skills/
  materialized learned Agent Skills

archive/
  safety backups / future cold artifacts

exports/
  portable snapshots
```

Large raw traces remain optional/deferred.

## Phase 5 boundary

Cross-device synchronization is deliberately outside this alpha. The future service can replace local-only storage without changing the conceptual interfaces:

```text
retrieve
record outcome
get capability stats
recommend route
consolidate knowledge
```
