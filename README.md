# Agent Lore

**Local-first continual learning and adaptive execution policy for coding agents.**

Agent Lore helps a coding harness reuse accepted engineering evidence, choose when delegation is worth it, plan proportional verification/security, and learn from outcomes without replacing current-model judgment.

> Status: **Integrated Alpha / v0.8.0-alpha**. The learning/routing CLI, bilingual canonical memory, audited revalidation, host-supplied TaskShape/DAG waves, and EvidencePlan routing output are implemented. Repository-derived planning, per-node execution telemetry, persisted knowledge scope, and richer recursive runtime routing remain future work.

## Core principles

```text
Past experience is evidence, not truth.
Execution success is not final success.
Functional success does not prove security.
More agents/tests/attacks/commits are not automatically better.
Use the smallest topology and verification depth sufficient for current risk.
Project state belongs to the project, not Agent Lore.
```

## Model freedom

Agent Lore uses four policy strengths:

```text
hard
strong-default
advisory
experimental
```

Hard rules protect safety/permission/budget boundaries. Strong defaults may be overridden with current-task evidence. Advisory and experimental guidance should not constrain a stronger current model.

Agent Lore is therefore a **constraint + evidence layer**, not a large if/else workflow engine.

See [`references/POLICY.md`](references/POLICY.md).

## Project-local wiki/context workflow

Agent Lore adopts the useful concept of an AI-maintained project wiki without depending on the OpenWiki service or an extra AI API key.

The current coding agent maintains project-local state inside each repository:

```text
new task
  -> read project-local wiki/current state
  -> retrieve small relevant Agent Lore evidence
  -> inspect affected source/tests/contracts
  -> work + verify
  -> meaningful checkpoint
       -> update project-local wiki if project truth changed
       -> record reusable Agent Lore evidence only when warranted
```

Agent Lore never copies or stores project wiki content. Full-repository re-analysis is exceptional rather than the default.

See [`references/PROJECT_CONTEXT.md`](references/PROJECT_CONTEXT.md).

## Adaptive execution

Single agent is the strong default. Multi-agent execution is justified only when expected parallelism/context/specialization benefits outweigh coordination and integration cost.

Important distinctions:

```text
Coordination: single | manager-worker | hierarchical | peer-handoff
Schedule:     serial | parallel | hybrid
Depth:        0 | 1 | 2+
```

Nested delegation emerges recursively: each child independently decides whether it can finish directly or benefits from local delegation. `max_depth` is a ceiling, not a target.

TaskShape/DAG reasoning supports parallel execution waves for independent/disjoint workstreams and serial barriers for dependencies.

## Proportional verification

Verification produces evidence rather than maximizing test count.

```text
change impact + risk + novelty + blast radius
                 ↓
              EvidencePlan
                 ↓
       cheap/high-value checks first
                 ↓
        enough evidence? -> stop/escalate
```

V0-V4 are depth signals, not recipes. Expensive E2E/regression/mutation/red-team work should normally be amortized at meaningful integration/feature/release checkpoints.

Security depth is similarly adaptive:

```text
none | smoke | focused | deep | adversarial
```

Only applicable attack families should run.

See [`references/EXECUTION.md`](references/EXECUTION.md) and [`references/SECURITY.md`](references/SECURITY.md).

## Roles

Keep structural roles small:

- Orchestrator/Main
- Domain Lead
- Worker
- Verifier
- Challenger
- Security Red-Team

Frontend/backend/database/infra/mobile/research are specializations, not permanent agent classes.

## Commits and checkpoints

Agent completion is not a Git commit boundary. Batch related small edits into coherent logical changes, verify proportionally, then create semantic commits. Internal worktree/checkpoint commits may be squashed/regrouped.

## Human escalation

Main/Orchestrator normally handles routing, routine phase transitions, verification depth, replanning, and commit timing.

Escalate owner-level decisions such as irreversible production actions, lowering protections, materially expanding permissions, major product ambiguity, or durable architecture/cost/legal decisions.

## Learning

Agent Lore keeps execution, verification, and acceptance separate and preserves rework lineage.

Original-language knowledge is preserved. A host may additionally supply English canonical text for cross-language retrieval; the CLI never performs a hidden network translation. Native CJK bigram retrieval is the local fallback.

Conceptually, learned knowledge is scoped as:

```text
task | module | project | stack | global
```

Project progress/status remains in project-local docs. Agent Lore stores reusable engineering evidence, routing/verification outcomes, and learned patterns.

Negative feedback places linked knowledge on revalidation hold. The revalidate command clears that hold only when a linked run is successful, verified, and accepted, and writes an audit event without changing deprecated/archived lifecycle state.

## Repository layout

```text
agent-lore/
├─ SKILL.md
├─ scripts/
├─ references/
│  ├─ POLICY.md
│  ├─ PROJECT_CONTEXT.md
│  ├─ EXECUTION.md
│  ├─ ROUTING.md
│  ├─ SECURITY.md
│  ├─ ACCEPTANCE.md
│  ├─ LIFECYCLE.md
│  ├─ ARCHITECTURE.md
│  └─ DATA_MODEL.md
├─ tests/
├─ .github/workflows/test.yml
└─ README.md
```

Runtime learning state stays outside the repository under `~/.agent-lore/` (or `AGENT_LORE_HOME`).

## Start

```bash
python scripts/agent_lore.py init
python scripts/agent_lore.py policy show
python scripts/agent_lore.py revalidate --help
python scripts/agent_lore.py recommend --help
```

Fresh installs start in `observe`, then can move to `assist`/`adaptive` after useful outcome evidence exists.

## Runtime boundary

Agent Lore remains harness-independent. The host harness owns agent/process spawning, tools/filesystem, sandboxing, tests, Git, provider calls, and optional translation/canonicalization. Agent Lore validates host-supplied TaskShape/EvidencePlan data, emits bounded execution guidance, and stores policy, evidence, recommendations, learning, and audit history.

## License

MIT
