# Sidecar architecture and model-freedom boundary

Agent Lore is a **cross-project sidecar**, not an agent methodology and not a universal coding runtime.

Its long-term design goal is:

> **Constrain capability, not cognition.**  
> **Observe execution, do not script it.**  
> **Expose history on demand, do not preload it.**  
> **Respect project structure, do not replace it.**

These rules are intended to survive changes in model families, coding harnesses, context windows, native delegation, computer-use capability, and tool protocols.

## Three planes

```text
┌────────────────────────────────────────────────────────────┐
│ Cognitive plane                                            │
│ current model / coding harness                             │
│ plan · decompose · delegate · implement · debug · review   │
│                                                            │
│ Agent Lore should not prescribe the reasoning procedure.   │
└────────────────────────────┬───────────────────────────────┘
                             │ tool/action requests
                             ▼
┌────────────────────────────────────────────────────────────┐
│ Control plane                                              │
│ permission · scope · budget · destructive approval         │
│ security boundary · sandbox · resource ceilings            │
│                                                            │
│ Prefer deterministic harness/tool enforcement when         │
│ technically possible instead of repeated prompt reminders. │
└────────────────────────────┬───────────────────────────────┘
                             │ execution events/outcomes
                             ▼
┌────────────────────────────────────────────────────────────┐
│ Evidence plane                                             │
│ runs · verification · acceptance · rework · incidents      │
│ agent ledger · timing/cost · scoped historical evidence    │
│                                                            │
│ Observation is after-the-fact and does not become a plan.  │
└────────────────────────────────────────────────────────────┘
```

## What Agent Lore may constrain

Hard constraints should be limited to independently justified capability boundaries such as:

- credential, tenant, network-origin, filesystem, and write scope
- destructive or irreversible production actions
- explicit human-approval boundaries
- sandbox/production separation
- hard agent/depth/cost/resource ceilings
- security invariants that must remain true

Where the host harness can enforce a boundary directly, enforcement should live there. A model should not need to spend context and reasoning budget remembering a restriction that a deterministic capability gate can enforce.

## What Agent Lore should not constrain

Do not hard-code:

- how the current model should think
- a mandatory decomposition style
- fixed agent roles for frontend/backend/database/etc.
- a permanent number of sub-agents
- a required testing recipe for every change
- a preferred implementation merely because an older model succeeded with it
- model-specific reasoning rituals

TaskShape, EvidencePlan, verification tiers, security depth, and structural roles are interoperability vocabulary and reasoning aids. They are not a hidden process engine.

## Policy and experience are separate lifecycles

Historical success must never automatically create a hard rule.

```text
Experience lifecycle                    Policy lifecycle
run/evidence                            independent justification
    ↓                                          ↓
experience                                advisory/default
    ↓                                          ↓
pattern                               explicit review/authority
                                               ↓
                                       strong-default / hard
```

There is deliberately no automatic bridge from the left side to the right side.

Learned evidence normally remains optional. A hard security/permission boundary requires independent justification, not popularity in historical runs.

## Model changes should be calibration, not migration

A new model/harness should normally require only:

- registering the executor/configuration
- observing task-conditioned acceptance/quality/cost/latency
- calibrating delegation/challenge usefulness
- measuring whether historical memory has positive lift for relevant task families

It should not require rewriting project memory, security invariants, run history, or Agent Lore's core architecture.

## Observability is a side channel

The host may emit events/telemetry such as:

```text
agent spawned/completed
tool called
file changed
test executed/result
verification completed
commit/checkpoint created
cost/timing/retry information
```

Agent Lore stores structured observations when supplied. The agent does not need to stop execution to write prose reports.

Human-readable Markdown/HTML reports are derived views. The SQLite event/run state remains the durable source. Optional semantic summaries are derived artifacts and should be regenerable from structured evidence rather than recursively summarized from older summaries.

## Repository intrusion budget

A project does **not** need to adopt an Agent Lore directory layout.

Normal zero-config use may leave the repository completely unchanged. Project-owned `AGENTS.md`, README/docs, ADRs, tests, source, and CI remain where that project already keeps them.

A future optional `.agent-lore.json` may be used only when a team wants to version-control semantic context mappings or project-specific Agent Lore integration. It must not become required for ordinary use.

See `PROJECT_CONTEXT.md` for the semantic project-context interface and `MEMORY.md` for pull-based historical evidence.
