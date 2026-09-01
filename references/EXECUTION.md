# Adaptive execution, verification, and commit policy

Agent Lore should optimize for sufficient evidence at reasonable cost. More agents, more tests, deeper security attacks, and more commits are not automatically better.

## Core rule

Use the **smallest execution topology and verification depth that is sufficient for the current task and risk**.

```text
change impact + blast radius + novelty + failure cost + history
                         ↓
                 verification budget
                         ↓
            cheapest high-value evidence first
                         ↓
                  enough evidence?
                  ├─ yes → stop
                  └─ no  → escalate
```

Verification frequency and verification depth are different. Cheap local checks can run frequently; expensive E2E, mutation, broad security, red-team, and full regression checks should normally be amortized across meaningful checkpoints.

## 1. Change impact model

Classify a change by more than diff size.

Consider:

- scope: local / module / cross-module / system
- blast radius: isolated / shared / critical path
- surfaces: UI, API, database, auth, secrets, external network, storage, CI/CD, agent tools/MCP, infra
- contract changes: none / internal / external
- data authority: read / write / destructive / privileged
- novelty: known pattern / new dependency / new provider / new trust boundary / new architecture
- failure cost: low / medium / high / critical
- historical escape/failure rate for similar changes

A three-line authorization change may deserve more verification than a 500-line isolated demo page.

## 2. Task DAG and execution waves

Represent non-trivial work as a dependency graph when decomposition materially helps.

```text
A backend ─────┐
B frontend ────┼─> D integration
C test fixture ┘

E migration -> F API contract -> G E2E
```

Independent nodes with disjoint mutable scopes may share an execution wave. Dependent nodes remain serial. A single task may contain parallel, serial, and nested segments.

Before parallel execution, compare read/write/contract scopes. Overlapping mutable write scopes increase conflict risk and should normally serialize or receive explicit ownership boundaries.

## 3. Delegation gain

Do not delegate merely because sub-agents are available.

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

If the expected gain is not clearly positive, keep the task with one agent.

## 4. Recursive routing and nested agents

Nested delegation is not a size flag. Each child task must independently justify further delegation.

```text
route(root)
  ├─ child A -> single
  ├─ child B -> route(B)
  │              ├─ B1
  │              └─ B2
  └─ child C -> single
```

Default progression:

- depth 0: single agent for small/tightly-coupled work
- depth 1: main/manager + scoped workers for several stable workstreams
- depth 2+: only when a child workstream itself has meaningful local decomposition and coordination value

`max_depth` is a safety ceiling, not a target.

## 5. Coordination shape vs schedule

Do not collapse organization and scheduling into one concept.

Coordination shape:

```text
single
manager-worker
hierarchical
peer-handoff (special cases)
```

Execution schedule:

```text
serial
parallel
hybrid
```

Delegation depth and breadth are separate dimensions.

The current alpha CLI still emits legacy topology labels (`single`, `flat-parallel`, `lead-worker`, `sequential`). Treat them as coarse compatibility signals; the host should reason in the richer dimensions above until the runtime data model/router is upgraded.

## 6. Delegation contract

Do not spawn a child without a useful contract.

```yaml
objective:
scope:
excluded_scope:
inputs:
dependencies:
read_scope:
write_scope:
contract_scope:
tools:
expected_output:
done_when:
verification:
budget:
```

The parent owns decomposition and integration. A child owns only the delegated scope unless explicitly authorized otherwise.

## 7. Structural roles

Prefer a small set of structural roles rather than dozens of fixed domain-agent classes:

- Orchestrator/Main — task shape, routing, integration, phase/checkpoint decisions
- Domain Lead — local coordination for a child workstream that justifies nested delegation
- Worker — scoped implementation/research work; normally no delegation
- Verifier — independent deterministic verification where useful
- Challenger — independent critique for unresolved risk/uncertainty
- Security Red-Team — attempts to falsify explicit security invariants in an isolated test environment

Frontend/backend/database/infra/mobile/research should usually be capabilities or specializations attached to a structural role, not permanent agent classes.

## 8. Verification tiers

Use proportional verification depth.

### V0 — trivial

Examples: docs, copy, isolated style-only change.

Typical evidence:

- syntax/format sanity if relevant
- no broad tests
- no security/red-team unless the change unexpectedly touches a sensitive boundary

### V1 — local

Examples: small localized implementation change.

Typical evidence:

- typecheck/lint or targeted unit checks
- cheap static/security checks only when applicable

### V2 — feature

Examples: normal feature slice or module behavior change.

Typical evidence:

- relevant unit + impacted integration tests
- selected security invariants if a sensitive surface changed
- focused mutation only when it proves a meaningful guard

### V3 — cross-boundary/high-risk

Examples: auth, external provider credentials, DB migration, cross-module contract, payment/webhook, tenant isolation.

Typical evidence:

- integration + relevant E2E
- focused adversarial/security tests
- failure-path testing
- security-control or high-value mutation where relevant

### V4 — critical/release

Examples: critical architecture/security change, release checkpoint, major migration.

Typical evidence:

- broader regression
- deeper mutation where valuable
- red-team/attack-chain tests for applicable surfaces
- rollback/operational verification where relevant

Do not map tiers from lines changed alone.

## 9. Gate applicability

Gates are conditional, not ritual.

Potential gate families:

- functional
- data integrity / migration
- compatibility / contracts
- concurrency / idempotency
- security
- performance / resource
- operational / deployment / rollback

Derive applicable gates from changed surfaces, authority, contracts, trust boundaries, and failure cost.

Examples:

```text
UI copy -> V0/V1; no security gate
API validation -> V1/V2; targeted input tests
provider baseURL + credential -> V3; credential/origin security invariants
schema + API contract -> V3/V4; migration + rollback + contract + integration
```

## 10. Progressive verification and early stopping

Run cheap, high-information checks first.

```text
cheap probe
   ↓
pass + low residual risk
   -> stop

uncertainty/failure remains
   -> escalate depth
```

Do not continue into an expensive suite merely because the suite exists.

## 11. Security and attack budget

Security depth should be selected by applicability and risk:

```text
none
smoke
focused
deep
adversarial
```

Examples:

- provider credential change: prioritize credential isolation, redirects/fallbacks, stale state, logs
- ordinary UI layout change: security normally not applicable
- MCP/tool authority change: prioritize tool poisoning, prompt injection, approval bypass, privilege boundaries

Red-team work should start with a few high-probability attacks and escalate to attack mutation/chains only when risk, novelty, findings, or residual uncertainty justify it.

## 12. Mutation budget

Mutation is expensive and should prove important tests rather than maximize mutation count.

Prefer mutation for:

- authorization/security guards
- validation branches
- idempotency/concurrency controls
- migration compatibility guards
- critical business rules

Skip broad mutation for low-risk presentation-only changes.

## 13. Shared verification across agents

Workers should run cheap checks scoped to their work. Expensive integrated checks belong at integration barriers.

```text
Worker A -> targeted backend checks
Worker B -> targeted frontend checks
Worker C -> fixture/test validation
              ↓
        integration barrier
              ↓
        one integrated E2E
```

Avoid each worker independently running the same full suite.

When safe, verification evidence can be reused while the relevant code/dependency fingerprint remains unchanged. Invalidate cached evidence when its assumptions or affected dependency graph change.

## 14. Checkpoint vs Git commit

Agent completion is not automatically a commit boundary.

Use internal checkpoints/worktree commits when the harness needs isolation or mergeability, but final history should prefer coherent semantic commits.

Commit when:

1. a coherent logical change unit is complete;
2. the workspace is at a stable integration state;
3. relevant focused verification has passed;
4. the next work has a meaningful semantic boundary.

Do not commit every small edit or every child-agent completion.

Small related changes should normally accumulate into a meaningful batch before verification/commit. Large or risky changes may use several semantic checkpoints when each checkpoint is independently coherent and recoverable.

## 15. Commit batching examples

Bad:

```text
change two lines -> full tests -> commit
change three lines -> full tests -> commit
child agent done -> commit
```

Better:

```text
credential-profile refactor
+ provider switching logic
+ origin guard
+ related tests
      ↓
focused + security verification
      ↓
commit: fix: bind provider credentials to trusted origins
```

## 16. Dynamic re-planning

Routing is not necessarily one-shot.

Re-evaluate when:

- repository inspection reveals materially different scope/dependencies
- a supposedly independent task becomes shared-state coupled
- a child task expands into a locally decomposable workstream
- repeated conflicts/duplicate work reduce delegation value
- risk/trust boundary changes
- verification reveals a new failure class

Allow:

```text
single -> manager-worker
parallel -> serial
manager-worker -> collapse to single
child -> nested delegation
```

within budget and depth limits.

## 17. Stop and collapse policy

Besides max agents/depth, monitor:

- token/compute cost
- wall time
- coordination overhead
- duplicate work
- merge/conflict rate
- idle/waiting agents
- retry count
- residual uncertainty

Stop spawning or collapse topology when marginal coordination benefit turns negative.

## 18. Learning verification and delegation ROI

Agent Lore should learn not only which model succeeds, but which verification/delegation choices provide lift.

Useful conceptual metrics:

```text
Test Utility = severity-weighted defects caught / execution cost
Attack ROI = severity-weighted security findings / attack cost
Delegation Lift = accepted-result improvement - coordination/integration cost
```

Do not automatically remove a safety-critical check merely because it rarely fails. Historical utility informs scheduling; current risk and required invariants remain hard constraints.

## 19. Future runtime data model

The policy expects future execution-tree observability to include:

```text
execution/task node id
parent node / depth
role / specialization / model / harness
subtask + dependencies
read/write/contract scopes
started/finished timestamps
cost/tokens/tool calls/retries
verification evidence
handoff quality
integration rework/conflicts
```

This is required before Agent Lore can reliably learn whether nested delegation itself produced positive lift rather than merely correlating with stronger models or easier/harder tasks.
