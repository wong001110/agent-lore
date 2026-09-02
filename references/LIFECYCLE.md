# Knowledge lifecycle and bias controls

Agent Lore should learn selectively. A larger memory database is not automatically better.

## Lifecycle

```text
run attempt
  -> execution outcome
  -> verification
  -> acceptance / rework
  -> reusable lesson?
       ├─ no -> statistics only
       └─ yes
            -> candidate experience
            -> accepted/verified evidence
            -> active experience
            -> pattern
            -> explicit skill/eval promotion when justified
```

At any point, knowledge may require revalidation, be deprecated, or be archived.

## Acceptance matters

Execution success is not final delivery success. A passing implementation that the user/reviewer sends back for rework is negative learning evidence for first-pass quality.

Automatic promotion therefore relies on linked verified/accepted outcomes rather than raw `outcome=success` counts.

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

Examples:

- a one-off recovery fact: `task`
- a module-specific migration convention: `module`
- a repository workflow/architecture convention: `project`
- a repeatable Prisma/Next.js lesson: `stack`
- a broadly transferred engineering invariant: `global`

Project-local knowledge may become useful without cross-project evidence. Cross-project diversity is increasingly important as a lesson is generalized toward stack/global scope.

The current runtime does not yet persist knowledge scope as a first-class field; this is policy for future schema work.

## Project state is not Agent Lore knowledge

Do not store project wiki/current-state snapshots in Agent Lore. Current feature status, milestones, architecture state, and project progress belong to the project-local wiki/docs.

Agent Lore stores reusable engineering evidence and outcome history, not a duplicate project knowledge base.

## Conservative maintenance

`consolidate` uses acceptance, verification, project diversity, reuse, freshness, and utility to make conservative lifecycle suggestions.

Do not automatically turn everything into a Skill, and do not silently delete disputed evidence.

## Negative feedback and revalidation

```text
rework / reject / invalidate
        ↓
contradictory linked evidence
        ↓
needs_revalidation
        ↓
lower trust/ranking and no automatic promotion
```

Preserve the historical case because it may explain context boundaries or recurring failure modes.

Clear a revalidation hold only through the formal revalidate command and a linked run that is successful, verified, and accepted. The audit event records who/what supplied the decision and why. Revalidation restores eligibility for retrieval/promotion; it does not silently reactivate deprecated or archived knowledge.

## Bilingual canonical memory

Preserve original-language task, lesson, and procedure text. A host may attach an English canonical representation for cross-language retrieval, together with source language and canonicalizer provenance.

Translation/canonicalization belongs to the host boundary. Agent Lore performs no hidden network call. If canonical text is absent, native Unicode/CJK retrieval remains available. Never translate secrets merely to improve retrieval.

## Skill promotion

A Skill is a stronger procedural artifact. Promote it only when there is a useful procedure with accepted/verified evidence. Materialized Skills remain advisory unless a separate hard policy explicitly says otherwise.

## Rework lineage

Attempts on the same logical task should preserve lineage so first-pass acceptance, rework count, accumulated time, and cost-to-accepted-result remain measurable.

## Retrieval budget

Planning retrieval should normally stay small (roughly 3-5 items). Retrieve again when task state materially changes rather than allowing stored-record count to determine context size.

## Security learning

Security incidents and near-misses require stricter promotion:

```text
incident/finding
  -> established root cause
  -> attack/failure primitive
  -> invariant
  -> regression candidate
  -> deterministic reproduction
  -> reusable pattern/eval if validated
```

Do not turn a repository/web claim into a global security rule merely because an LLM says it sounds plausible.

## Policy strength of learned knowledge

Learned knowledge normally begins as `experimental` or `advisory`. Repeated accepted evidence may justify stronger defaults, but learning does not automatically create hard constraints.

Hard security/permission invariants require independent justification, not popularity in historical runs.

## Bias and failure modes

Actively guard against:

- anchoring and confirmation bias
- negative transfer and staleness
- survivorship/acceptance/recency bias
- correlated evidence and self-reinforcement
- authority bias (`active`/`skill` is not mandatory)
- project dominance
- retrieval/context interference
- router path dependence
- reviewer herding/self-preference
- metric gaming / Goodhart effects
- untrusted-source contamination

Form a current-model plan before retrieval for meaningful choices. For high-impact decisions, inspect disconfirming evidence.

## Counterfactual discipline

Do not conclude that one model/topology/verification strategy is better from raw historical success rates alone. Consider task complexity, risk, model/harness, novelty, scope, verification depth, and other confounders.

Use natural matched history, shadow evaluation, occasional exploration, rework comparisons, and explicit benchmark/eval tasks when useful. `Insufficient evidence` is a valid result.

## Challenge and verification ROI

Challenge, tests, attacks, and multi-agent execution should be measured for useful lift rather than ritual frequency. A low observed ROI may reduce optional frequency, but required hard invariants remain required.

## Memory Lift

Long-term objective:

```text
Memory Lift = performance(memory-assisted) - model-only baseline
```

For real product work, prefer acceptance-aware measures such as first-pass acceptance, rework, time/cost to accepted result, and verification quality.

Negative Memory Lift means the knowledge/retrieval policy should be narrowed, revalidated, or disabled rather than trusted because it exists.
