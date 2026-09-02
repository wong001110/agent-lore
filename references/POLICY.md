# Policy strength and model freedom

Agent Lore should improve model judgment, not replace it with a growing rulebook.

## Core principle

```text
hard constraints
+ strong defaults
+ contextual evidence
+ advisory hints
        ↓
current model reasons and decides
```

The host model should remain free to choose a better plan when current repository evidence justifies it. Only explicit hard constraints are non-overridable.

## Policy strength

Every meaningful policy belongs to one of four strengths.

### `hard`

Safety, permission, budget, or irreversible-action boundary.

Examples:

- do not send credentials to an unauthorized origin
- do not cross an explicit tenant/authorization boundary
- do not exceed a configured hard agent/depth/cost ceiling
- do not bypass a required human approval for a destructive action
- do not write outside an explicitly restricted write scope

A model cannot override a hard rule merely because it believes an exception would be convenient.

### `strong-default`

The normal choice supported by engineering economics or repeated evidence, but overridable with a concrete current-task reason.

Examples:

- prefer one agent when delegation gain is unclear
- serialize overlapping mutable write scopes
- use focused security verification for a meaningful auth/credential boundary change
- batch related small edits before semantic commit

When overriding a strong default, preserve a concise reason in execution evidence when practical. This is for learning, not bureaucracy.

### `advisory`

Useful suggestion with no presumption that it is correct for the current task.

Examples:

- consider parallel execution for independent workstreams
- consider a verifier or challenger
- consider focused mutation for an important guard

The model may follow or ignore advisory guidance without special approval.

### `experimental`

Weak or under-sampled evidence, exploration result, newly learned pattern, or uncertain recommendation.

Treat it as a hypothesis. It must not silently become a strong default or hard rule.

## Override semantics

```text
hard            -> cannot override within normal execution
strong-default  -> may override with current evidence/reason
advisory         -> freely adaptable
experimental     -> weak evidence only
```

Do not require explanation for every local decision. Require explicit reasoning mainly when a model chooses a materially riskier path than a strong default.

## Model freedom

Do not encode policy as brittle thresholds such as:

```text
files > 10 -> run E2E
subtasks >= 3 -> multi-agent
risk=high -> always red-team
5 edits -> commit
```

Use categories such as verification tier, security depth, delegation gain, and attack budget as reasoning language rather than fixed recipes.

A model may escalate a tiny change because it touches a critical authorization boundary, or reduce verification for a large generated/isolated change when evidence supports that decision.

## Evidence plans, not test recipes

The verification planner should answer:

```text
What claims must be proven?
What is the cheapest useful evidence?
What would make us escalate?
When is evidence sufficient to stop?
```

V0-V4 are risk/depth signals, not mandatory checklists.

## Human escalation boundary

The Main/Orchestrator normally decides without asking the user:

- single vs multi-agent
- parallel vs serial/hybrid scheduling
- child delegation and routine phase transitions
- verification/security depth
- challenger/model selection
- retry/replan/collapse decisions
- semantic commit timing

Escalate when owner-level judgment is genuinely required, such as:

- irreversible production/destructive action
- high-blast-radius migration without a safe established path
- lowering a security/privacy protection to proceed
- materially expanding credential/permission scope
- major product ambiguity with multiple defensible outcomes
- significant long-term infrastructure/cost obligation
- legal/compliance ambiguity
- major architecture alternatives with durable consequences and insufficient evidence

## Automation boundary

Agent Lore is a **policy + learning + decision-intelligence layer**, not a universal coding runtime.

The host harness remains responsible for:

- spawning agents
- filesystem/process/tool execution
- sandboxing
- tests and Git operations
- provider calls

Agent Lore accepts machine-readable host-supplied TaskShape/EvidencePlan data and produces routing, budget, and DAG-wave guidance. Repository-derived planning and actual execution remain host responsibilities so Agent Lore stays harness-independent.

## Counterfactual discipline

Do not conclude that a topology, model, or verification strategy is superior from raw success rates alone.

Consider confounders such as:

- task complexity/risk
- model and harness
- domain/scope
- novelty
- verification depth
- failure cost

Use natural matched history, shadow evaluation, occasional exploration, rework comparisons, and benchmark/eval tasks where useful. `Insufficient evidence` is a valid conclusion.

## Knowledge scope

Not every lesson should become global.

Conceptual scopes:

```text
task
module
project
stack
global
```

A project-local convention can become useful project knowledge without cross-project evidence. Cross-project diversity matters when promoting a lesson to stack/global guidance.

Security invariants may be broader when independently justified, but implementation techniques remain scoped to the environments that support them.

The current runtime does not yet persist this scope as a first-class schema field; treat it as policy for future data-model work.
