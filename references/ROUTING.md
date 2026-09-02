# Adaptive Routing

Agent Lore chooses **whether delegation is worthwhile**, **how work should be coordinated and scheduled**, **which registered configurations fit each role**, and **whether additional challenge is worth its cost**.

The v0.8 CLI accepts a host-reasoned TaskShape, validates dependencies and mutable scopes, emits executable DAG waves plus coordination/schedule/depth, and persists the decision. Legacy topology labels and coarse hints remain compatibility inputs.

## 1. Strong default: single agent

Use one agent unless delegation has a clear expected benefit.

Prefer `single` when:

- the task is small or tightly coupled
- one workstream dominates
- mutable write scopes overlap heavily
- workers would need most of the same context
- integration cost is likely to exceed parallelism/specialization gain
- decomposition is unclear

Multi-agent is an optimization, not a default ritual.

## 2. TaskShape before topology

For non-trivial work, inspect the repository/task and derive a TaskShape instead of relying only on manually supplied labels.

Useful signals:

```text
workstreams / candidate subtasks
dependency DAG
read/write/contract scopes
cross-domain boundaries
risk + failure cost
context size / specialization need
parallelizable waves
integration points
verification/security surfaces
```

Supply TaskShape with --task-shape-json as inline JSON or @path. The shape contains an objective, non-empty workstreams, dependency/read/write/contract scopes, and an explicit delegation decision. Agent Lore rejects dependency cycles and serializes overlapping mutable scopes.

The legacy CLI inputs (`parallelizable`, `cross-domain`, `estimated-subtasks`, `dependency-level`) remain coarse fallback hints, not a substitute for TaskShape analysis.

## 3. Separate coordination, schedule, and depth

Do not mix organizational shape with execution scheduling.

Coordination shape:

```text
single
manager-worker
hierarchical
peer-handoff (special cases)
```

Schedule:

```text
serial
parallel
hybrid
```

Delegation depth:

```text
0 / 1 / 2+
```

Breadth is the number of active children at each level.

Legacy CLI compatibility mapping:

- `single` ≈ single coordination, depth 0
- `flat-parallel` ≈ manager-worker, depth 1, parallel schedule
- `lead-worker` ≈ manager-worker/hierarchical, depth >=1
- `sequential` ≈ serial schedule signal, not a complete coordination shape

The routing decision now stores both forms. New consumers should prefer coordination, schedule, delegation_depth, and execution_plan waves.

## 4. Task DAG and waves

Independent nodes with disjoint mutable scopes may execute in the same wave. Dependent nodes remain serial.

```text
A backend ─────┐
B frontend ────┼─> D integration
C fixture ─────┘

E migration -> F API -> G E2E
```

A task may therefore be hybrid rather than globally parallel or sequential.

Do not parallelize overlapping mutable write scopes merely to increase agent count. Compare write/contract ownership before spawning workers.

## 5. Delegation gain

Conceptually evaluate:

```text
Delegation Gain
= parallelism gain
+ context relief
+ specialization gain
+ independent-verification gain
- coordination cost
- integration risk
- shared-state risk
- duplicate work
- extra compute/token cost
```

If expected gain is not clearly positive, do not delegate.

## 6. Depth 1: main/manager + workers

Use the previous-generation main + sub-agent pattern for several stable workstreams whose children can complete their assigned scope without further orchestration.

Typical examples:

- backend + frontend + E2E slices
- independent investigation tracks
- disjoint modules with a clear integration contract

The parent owns decomposition, contracts, integration, and final verification.

## 7. Nested delegation

Nested delegation should emerge recursively, not from a simple `large task -> nested` rule.

For every child task, run the same delegation test again:

```text
route(child)
  ├─ expected delegation gain <= threshold -> child executes directly
  └─ expected delegation gain > threshold  -> child may become a domain lead
```

Use depth 2+ only when a child workstream itself contains meaningful local decomposition and coordination value.

`max_depth` is a safety ceiling, never a target.

## 8. Delegation contracts

Every child should receive a bounded contract:

```text
objective
scope / excluded scope
inputs / dependencies
read scope / write scope / contract scope
tools / authority
expected output
done-when criteria
verification responsibility
budget
```

Ambiguous child contracts increase duplicate work and integration failure; if a useful contract cannot be formed, keep the work with the parent.

## 9. Structural roles

Prefer a small role vocabulary:

- Orchestrator/Main
- Domain Lead
- Worker
- Verifier
- Challenger
- Security Red-Team

Domain labels such as frontend/backend/database/infra/mobile/research should usually be specializations/capabilities, not separate permanent agent classes.

A role should eventually describe more than a free-text name: tools, read/write scope, authority, delegation permission, expected output, and completion contract all matter.

## 10. Per-node model/config routing

A multi-agent execution tree should not assume one model/configuration for every node.

Conceptually select configurations per execution node:

```text
root orchestrator -> strong planning/integration config
backend worker    -> implementation config
verifier          -> fast deterministic/review config
security red-team -> adversarial/security-capable config
```

The current CLI chooses one primary delegation-capable configuration for the execution plan and should still be treated as incomplete for heterogeneous per-node execution trees.

## 11. Agent/model configuration router

Cold start uses:

```text
quality_tier
cost_tier
priority
```

Observed history may contribute:

```text
execution success
verification
acceptance / first-pass acceptance
quality
cost / wall time
retries
```

Task context narrows observations by project/module/task/subtype/language/framework/role where available.

Avoid confounding topology performance with model strength. A topology should not be declared superior merely because historically it happened to receive stronger models. Prefer matched or shadow/counterfactual evidence where practical.

## 12. Exploration

Policy contains an `exploration_rate` (default 0.10). Prefer shadow evaluation for under-sampled configurations.

Do not replace a proven production path with an unproven exploration candidate on high-risk work merely to collect data.

## 13. Challenge router

Inputs include:

```text
risk
uncertainty
cost of failure
memory conflict/staleness
deterministic evidence
```

Outputs remain:

```text
none
self-check
cheap-challenger
strong-challenger
```

Challenge is escalation, not a mandatory second execution.

## 14. Dynamic topology adaptation

Routing is not necessarily one-shot. Re-evaluate when:

- repository inspection reveals different scope/dependencies
- supposedly independent tasks become shared-state coupled
- a child expands into a locally decomposable workstream
- repeated conflicts or duplicate work reduce delegation value
- trust boundaries/risk change
- verification exposes a new failure class

Allowed transitions include:

```text
single -> manager-worker
parallel -> serial
manager-worker -> collapse to single
child -> nested delegation
```

## 15. Stop/collapse policy

Guardrails should eventually consider more than agent count/depth:

- token/compute cost
- wall time
- coordination overhead
- duplicate work
- merge/conflict rate
- idle/waiting agents
- retry count
- residual uncertainty

Stop spawning or collapse when marginal coordination benefit turns negative.

## 16. Modes

### Observe
Recommendation is logged only.

### Assist
Recommendation is surfaced; parent/human decides.

### Adaptive
Recommendation may be applied when host capabilities and policy guardrails allow it.

## 17. Feedback and learning

Every `recommend` returns a `decision_id`; later execution should record the route decision.

Agent Lore should learn **delegation lift**, not agent-count preference:

```text
Delegation Lift
= accepted-result improvement
- coordination/integration/compute cost
```

Future execution-tree telemetry should include parent/depth, node role/model, dependencies, write scope, timing/cost, verification, handoff quality, and integration rework so nested routing can be evaluated causally rather than from coarse correlations.

## 18. Effective cost

```text
Effective cost
= inference cost
+ retries
+ reviewer/challenger cost
+ failure recovery
+ coordination overhead
+ integration rework
```

## 19. Guardrails

Recommended defaults remain conservative:

```text
mode: observe
max_depth: 2
max_agents: 6
max_challenge_level: 3
exploration_rate: 0.10
```

Keep routing decisions inspectable until real-world evidence shows that added hierarchy produces positive lift.

See [Adaptive execution, verification, and commit policy](EXECUTION.md) for execution waves, verification scheduling, security/attack budgets, and commit batching.
