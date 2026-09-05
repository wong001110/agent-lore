# Policy strength, capability guardrails, and model freedom

Agent Lore should improve engineering reliability without becoming a growing prompt-level rulebook.

Core architecture:

```text
independently justified hard capability boundaries
+ strong defaults
+ current project truth
+ deterministic evidence
+ optional historical evidence
        ↓
current model reasons and decides
```

See `SIDECAR.md` for the cognitive/control/evidence-plane boundary and `MEMORY.md` for historical retrieval.

## Constrain capability, not cognition

A hard rule should normally describe **what authority is allowed**, not how a model must think.

Prefer deterministic host/harness/tool enforcement for boundaries such as:

- credential and tenant scope
- filesystem/write scope
- network/origin scope
- production/destructive actions
- explicit approval requirements
- sandbox boundaries
- hard cost/agent/depth/resource ceilings

If the harness can block an unauthorized action directly, do not rely only on repeatedly reminding the model in prompt context.

## Policy strengths

### `hard`

Safety, permission, budget, or irreversible-action boundary that cannot be overridden in normal execution.

Examples:

- credentials may not be sent to an unauthorized origin
- explicit tenant isolation may not be bypassed
- destructive production action requires the configured approval
- configured hard agent/depth/cost ceilings may not be exceeded

Hard rules require independent justification. They are not learned because old runs happened to succeed with them.

### `strong-default`

Normally useful engineering choice that the current model may override with concrete current-task evidence.

Examples:

- prefer one agent when delegation benefit is unclear
- serialize overlapping mutable write scopes
- use focused security verification for meaningful auth/credential boundary changes
- batch related edits into coherent semantic commits

### `advisory`

Useful suggestion with no presumption that it is correct now.

Examples:

- consider parallelism for disjoint workstreams
- consider a verifier/challenger
- consider focused mutation around a critical guard

### `experimental`

Weak, under-sampled, newly observed, or uncertain hypothesis.

## No automatic Experience -> Policy promotion

Historical memory has a separate lifecycle from policy.

A repeated successful procedure may become a scoped pattern, but it must not silently become a `strong-default` or `hard` rule.

To strengthen policy, require an explicit independent reason such as:

- safety/permission boundary
- protocol/contract requirement
- deterministic evidence across applicable contexts
- explicit project/owner decision

Popularity in old runs is not sufficient.

## Avoid brittle recipes

Do not encode rules such as:

```text
files > 10 -> E2E
subtasks >= 3 -> multi-agent
risk=high -> always red-team
5 edits -> commit
old solution succeeded -> use it again
```

Use reasoning vocabulary such as impact, delegation gain, residual risk, evidence sufficiency, security depth, and attack applicability.

## Evidence plans, not test rituals

Verification planning should answer:

```text
What claims/invariants must be true?
What is the cheapest high-information evidence?
What would trigger escalation?
When is evidence sufficient to stop?
```

V0-V4 remain depth/risk signals, not mandatory checklists.

## Human escalation boundary

Main/Orchestrator normally handles routine decisions including:

- single vs multi-agent
- serial/parallel/hybrid scheduling
- child delegation and routine phase transitions
- verification/security depth
- retry/replan/collapse
- challenger/model selection
- semantic commit timing

Escalate owner-level decisions such as:

- irreversible/destructive production action
- lowering security/privacy protection
- materially expanding permissions/credentials
- major product ambiguity with multiple defensible outcomes
- durable high-cost architecture/infrastructure commitments
- legal/compliance ambiguity
- high-blast-radius migration without a safe established path

## Automation boundary

Agent Lore is not a universal coding runtime.

Host harness remains responsible for:

- model/tool invocation
- spawning/delegation
- filesystem/process execution
- sandboxing
- Git/tests/provider calls
- enforcing capability boundaries it can enforce deterministically

Agent Lore may validate host-supplied TaskShape/EvidencePlan structures, record after-the-fact topology/telemetry, maintain budgets/policy, and provide bounded advisory evidence.

## Counterfactual discipline

Do not infer that a topology/model/memory strategy is better from raw success rate alone.

Consider:

- task complexity/risk
- project/module/domain
- model + harness
- novelty
- verification depth
- failure cost
- memory mode and historical context supplied

Use matched history, shadow evaluation, exploration where safe, rework comparison, and explicit eval tasks. `Insufficient evidence` is valid.

## Knowledge scope

Historical evidence uses first-class scope:

```text
task | module | project | stack | global
```

Scope controls retrieval applicability; it does not grant authority. A project convention remains project-local unless deliberately generalized with adequate evidence.
