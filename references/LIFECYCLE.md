# Knowledge lifecycle and bias controls

Agent Lore should learn selectively. More historical memory is not automatically better.

Historical knowledge exists to preserve **evidence, failure space, invariants, applicability, and solution variants** without turning old agents' interpretations into instructions for future models.

## Lifecycle

```text
run attempt
  -> execution outcome
  -> verification
  -> acceptance / rework / rejection
  -> reusable evidence?
       ├─ no -> run/statistics only
       └─ yes
            -> scoped candidate experience
            -> accepted/verified evidence
            -> active experience when justified
            -> reusable pattern when justified
```

There is no learned-Skill terminal stage in v0.9.

At any point, historical knowledge may require revalidation, be deprecated, be superseded, or be archived without deleting its evidence lineage.

## Acceptance matters

Execution success is not final delivery success.

A passing implementation sent back for rework is negative evidence for first-pass quality. Promotion therefore depends on linked accepted+verified evidence rather than raw `outcome=success` counts.

## First-class knowledge scope

v0.9 persists:

```text
task
module
project
stack
global
```

Typical meaning:

- `task` — one narrow task family/subtype in one project
- `module` — reusable only inside a project module/subsystem
- `project` — repository-specific historical evidence/convention
- `stack` — deliberately transferable language/framework evidence
- `global` — explicitly generalized evidence with broad applicability

Project/module evidence can become useful locally without proving cross-project transfer. Stronger transfer evidence is required as knowledge moves toward `stack`/`global` scope.

Scope constrains retrieval; it does not create authority.

## Evidence Capsule over eternal lesson

Prefer structured fields:

```text
experience_family
observation
invariant
root_cause + root_cause_status
applies_when
not_proven
historical solution + solution_status
scope + scope_ref
accepted/verified evidence lineage
```

Legacy `lesson` / `solution_summary` remain for compatibility and compact human-readable context, but a free-form lesson should not be treated as an eternal instruction.

### Different lifetimes

```text
verified observation/failure  -> long-lived historical evidence
invariant/insight             -> long-lived but revisable
a historical solution         -> contextual, replaceable variant
```

A future model may supersede a historical solution while the old failure evidence remains valid.

Solution status:

```text
candidate | preferred | conditional | fallback | superseded | invalid
```

`preferred` means current evidence favors it; it does not mean future models must use it.

## Experience families

Where useful, connect multiple solution variants through one stable problem/failure family rather than collapsing them into a single answer.

Example:

```text
AUTH-REFRESH-RACE
├─ lock                    accepted in context A
├─ optimistic concurrency  accepted in context B
└─ versioned token         accepted in context C
```

The durable knowledge is the failure/invariant/applicability space. Procedures remain alternatives.

## Project state is separate

Do not store project wiki/current-state snapshots in Agent Lore.

Current feature state, roadmap, architecture truth, milestones, and project progress remain project-owned. Agent Lore stores cross-project-compatible execution evidence and scoped historical cases, not a duplicate project knowledge base.

## Conservative consolidation

`consolidate` uses acceptance, verification, scope, project diversity where relevant, reuse, freshness, and negative feedback.

Do not silently generalize a project-local observation to stack/global evidence.

Do not silently delete disputed evidence.

## Negative feedback and revalidation

```text
rework / reject / invalidate
        ↓
contradictory linked evidence
        ↓
needs_revalidation
        ↓
down-rank / withhold promotion
```

Preserve the old case because it may explain failure modes, context boundaries, or why one solution stopped working.

Clear a hold only with the explicit revalidation operation and a linked run that is successful, verified, and accepted. Revalidation restores eligibility; it does not reactivate deprecated/archived knowledge or rewrite the old record.

## Supersession is not deletion

When a newer solution/pattern replaces an older one, preserve the old evidence and use explicit status/supersession metadata. Old cases may still apply in legacy contexts.

Do not infer:

```text
newer == universally better
older == useless
```

Current applicability and deterministic evidence decide.

## Bilingual/canonical representations

Preserve original-language evidence. A host may attach an English/canonical representation for cross-language retrieval with provenance.

Canonicalization is derived data, not a replacement for original evidence. Agent Lore makes no hidden network translation calls.

## Learned Skills are legacy read-only

v0.9 stops new historical `skill` promotion and stops `materialize-skills` output.

Reason: generated Agent Skills are instruction-shaped artifacts and therefore have a higher risk of anchoring future models to old procedures.

Existing old `kind=skill` rows/files remain readable and portable for backward compatibility, but:

- they are excluded from normal retrieval
- no new skill may be promoted
- no new learned Skill file is materialized

Experience/Pattern evidence is sufficient for continual learning.

## Retrieval and memory modes

Historical memory is pull-based:

```text
off
guardrail
rescue
proactive
```

See `MEMORY.md`.

`guardrail` should generally expose observations/failures/invariants without exposing the old procedure. `rescue`/`proactive` may reveal historical remedies when deliberately useful.

Use an approximate token budget in addition to item-count caps. Large context windows do not justify large memory payloads automatically.

## No summary-of-summary accumulation

Structured run/evidence state is canonical.

Cards, reports, translations, and semantic summaries are derived views that should be regenerable from source evidence. Avoid recursively summarizing older model summaries as the only remaining truth.

## Security learning

Security incidents/near-misses use a stricter path:

```text
incident/finding
  -> established root cause when possible
  -> attack/failure primitive
  -> invariant
  -> deterministic regression candidate
  -> accepted/verified pattern/eval when justified
```

Do not convert an LLM claim or internet/repository text into a global security policy because it sounds plausible.

## Experience and policy are separate

Historical evidence normally remains auxiliary.

There is no automatic:

```text
many successes -> strong-default/hard policy
```

Hard permission/security boundaries require independent justification. See `POLICY.md` and `SIDECAR.md`.

## Bias and failure modes

Actively guard against:

- anchoring and confirmation bias
- negative transfer and staleness
- survivorship / acceptance / recency bias
- correlated evidence and self-reinforcement
- authority bias (`active`/`pattern` is not mandatory)
- project dominance and scope leakage
- retrieval/context interference
- router path dependence
- reviewer herding/self-preference
- metric gaming / Goodhart effects
- untrusted-source contamination
- inherited preferences from weaker/older models

For meaningful design choices, form a current-model plan from current project evidence before revealing historical solutions when practical.

## Counterfactual discipline

Do not conclude that one model/topology/memory/verification strategy is better from raw historical success alone.

Consider task, model, harness, project/scope, novelty, verification depth, failure cost, memory mode, and other confounders.

Use matched history, shadow evaluation, occasional safe exploration, rework comparisons, and explicit eval tasks. `Insufficient evidence` is valid.

## Memory Lift

Conceptually:

```text
Memory Lift = performance(memory-assisted) - model-only baseline
```

Prefer acceptance-aware outcomes: first-pass acceptance, rework, deterministic verification quality, time/cost to accepted result, and failure/incident escape rate.

A new model must not automatically inherit an older model's memory preference. Negative or negligible Memory Lift should narrow or disable memory for that model/task context.
