# Adaptive execution, verification, and commit policy

Agent Lore optimizes for **sufficient evidence at reasonable cost**. More agents, tests, attacks, and commits are not automatically better.

Policy categories here are reasoning aids unless explicitly marked hard. See `POLICY.md`.

## 1. Change impact

Judge more than diff size:

- scope and blast radius
- changed surfaces and contracts
- read/write/destructive authority
- trust/security boundaries
- novelty/new dependency/provider/architecture
- failure cost
- relevant historical escapes/failures

A tiny authorization change can justify deeper verification than a large isolated demo.

## 2. TaskShape, DAG, and execution waves

Use a working TaskShape when decomposition helps:

```text
objective
scope / risk / uncertainty
workstreams + dependencies
read/write/contract scopes
integration points
verification/security surfaces
```

Represent dependencies as a DAG when useful. Independent nodes with disjoint mutable scopes may share an execution wave; dependent nodes remain serial. A task may mix parallel, serial, and nested segments.

TaskShape is a working hypothesis and may change during execution.

## 3. Delegation and nested agents

Single agent is the strong default. Delegate only when expected benefits clearly outweigh coordination/integration cost.

Reason about:

```text
benefits: parallelism, context relief, specialization, independent verification
costs: coordination, integration, shared-state risk, duplicate work, compute/token cost
```

Nested delegation is recursive, not a `large-task` switch. Each child independently decides whether it can finish directly or needs local delegation. `max_depth` is a hard ceiling, not a target.

Coordination, schedule, and depth remain separate:

```text
Coordination: single | manager-worker | hierarchical | peer-handoff
Schedule:     serial | parallel | hybrid
Depth:        0 | 1 | 2+
```

The current runtime persists coordination, schedule, delegation depth, validated TaskShape, EvidencePlan, and DAG waves. Legacy topology labels remain compatibility signals.

## 4. Delegation contract and roles

Structural roles:

- Orchestrator/Main
- Domain Lead
- Worker
- Verifier
- Challenger
- Security Red-Team

Domain labels such as backend/frontend/database are specializations, not permanent role classes.

A child contract should bound objective, scope, dependencies, read/write/contract scope, tools/authority, expected output, done criteria, verification, and budget. Avoid parallel workers with overlapping mutable ownership unless the overlap is explicitly coordinated.

## 5. EvidencePlan

Verification should prove claims, not maximize test count.

A useful plan answers:

```text
claims: what must be true?
checks: what is the cheapest useful evidence?
escalation: what would justify deeper verification?
stop: when is evidence sufficient for current risk?
```

Example:

```yaml
claims:
  - provider routing still works
  - credentials stay bound to the trusted origin
checks:
  - targeted provider unit tests
  - one routing integration test
  - SEC-001 synthetic-canary check
skip:
  - unrelated browser regression
escalate_if:
  - unexpected redirect/fallback behavior
```

## 6. Verification depth

V0-V4 are **risk/depth signals, not recipes**:

- `V0` trivial
- `V1` local
- `V2` feature
- `V3` cross-boundary/high-risk
- `V4` critical/release

A model may escalate or reduce suggested depth when current evidence justifies it. Materially riskier deviation from a strong default should carry a concise reason.

Potential gate families:

- functional
- data integrity / migration
- compatibility / contracts
- concurrency / idempotency
- security
- performance / resource
- operational / deployment / rollback

Only activate applicable gates.

## 7. Progressive verification and early stopping

Run cheap/high-information evidence first.

```text
cheap evidence
      ↓
residual risk low enough?
  ├─ yes -> stop
  └─ no  -> escalate
```

Do not run an expensive suite merely because it exists. Hard invariants that apply to the change still require proof and cannot be skipped by early stopping.

**Verification frequency != verification depth.** Cheap local checks may run frequently; broad E2E/regression, mutation, red-team, and attack-chain work normally belongs at integration/feature/release checkpoints.

## 8. Security and attack budget

Security depth is applicability/risk language:

```text
none | smoke | focused | deep | adversarial
```

Select attack families from the changed attack surface. Start with high-probability/high-impact cases and escalate variants/chains only when risk, novelty, findings, or residual uncertainty justify it.

Security Red-Team attack simulation is limited to local/test/sandbox/ephemeral or explicitly authorized environments.

## 9. Mutation budget

Use mutation to prove important guards, not maximize mutation count. Prefer authorization/security conditions, validation boundaries, idempotency/concurrency controls, migration compatibility, and critical business rules. Skip broad mutation for low-risk presentation-only work.

## 10. Shared verification across agents

Workers run cheap checks scoped to their work. Expensive integrated checks belong at barriers.

```text
Worker A -> targeted backend checks
Worker B -> targeted frontend checks
Worker C -> fixture checks
              ↓
        integration barrier
              ↓
        integrated verification
```

Reuse valid evidence while relevant code/dependency/contract assumptions remain unchanged; invalidate it when affected assumptions change.

## 11. Checkpoint vs Git commit

Agent completion is not automatically a commit boundary.

Three concepts:

```text
working edits       -> no commit required
internal checkpoint -> optional harness/worktree/recovery commit
semantic commit     -> coherent final history boundary
```

Prefer a semantic commit when the logical change is coherent, integration state is stable, relevant focused verification passed, and the next work has a meaningful semantic boundary.

Small related edits should normally accumulate before expensive integrated verification and final commit. Internal checkpoint commits may be squashed/regrouped.

## 12. Project wiki checkpoint

At the same meaningful integration/feature checkpoint, Main/Integrator updates project-local wiki/current-state docs if project truth changed.

The project wiki is not an Agent Lore store. Agent Lore never needs to copy it.

## 13. Dynamic re-planning, stop, and collapse

Re-evaluate TaskShape/routing when repository inspection, conflicts, scope growth, dependencies, trust boundaries, or verification findings materially change the problem.

Valid transitions include:

```text
single -> manager-worker
parallel -> serial
manager-worker -> collapse to single
child -> nested delegation
```

Monitor coordination cost, duplicate work, conflicts, idle agents, retries, compute/token cost, wall time, and residual uncertainty. Stop spawning/collapse when marginal delegation value turns negative.

## 14. Learning utility without ritual

Conceptual signals:

```text
Test Utility    = severity-weighted defects caught / execution cost
Attack ROI      = severity-weighted findings / attack cost
Delegation Lift = accepted-result improvement - coordination/integration cost
```

These signals inform future recommendations; they are not hard formulas. Never remove a required safety invariant merely because it rarely fails.

## 15. Current and future runtime model

Version 0.8 accepts host-supplied TaskShape/EvidencePlan JSON, validates the dependency graph and scope conflicts, and records the bounded execution recommendation. The host still owns repository analysis and execution.

Future first-class execution-tree telemetry should capture enough information to separate topology effects from model/task confounders:

```text
node / parent / depth
role / specialization / model / harness
subtask + dependencies
read/write/contract scopes
cost/tokens/tool calls/retries
verification evidence
handoff/integration rework
```

Until then, the richer execution model remains Skill/host policy rather than falsely claimed runtime automation.
