# Historical memory without model anchoring

Agent Lore treats historical memory as a **queryable evidence library**, not a preload and not a substitute for current-model reasoning.

The long-term objective is to avoid a growing **memory tax** where every future model must spend tokens, latency, and attention on old agent interpretations before it can work.

## Core rule

> **Memory should be queryable, not preloaded.**

Current repository truth, current user requirements, project instructions/ADRs, source/runtime behavior, deterministic verification, and current-model judgment come first.

Historical evidence is pulled only when it can materially improve the task.

## Memory modes

Agent Lore defines four memory modes:

```text
off        no historical evidence enters model context
guardrail  expose relevant observations/failures/invariants, hide old procedures
rescue     after difficulty/failure, expose relevant cases and historical remedies
proactive  high-risk/explicit historical analysis may expose relevant cases before execution
```

Recommended use:

- ordinary low-risk implementation/refactor: `off`
- known failure-prone surface where old solution could anchor the model: `guardrail`
- first attempt failed or residual uncertainty remains: `rescue`
- security/incident/release work where repeating a known failure is expensive: `proactive`

`rescue` is a host decision: Agent Lore does not infer that a model has failed merely because a task is difficult.

## Blind-plan then historical reveal

For high-value work where history may both help and anchor, prefer:

```text
current project evidence
       ↓
current model forms its own plan
       ↓
retrieve historical incidents/invariants
       ↓
compare blind plan with historical failure space
       ↓
revise only when evidence warrants it
```

This preserves the new model's native capability while still using organizational memory as a challenger/safety net.

## Evidence Capsule

A reusable historical item should prefer structured evidence over a free-form procedural lesson.

Conceptual capsule:

```yaml
id: EXP-...
scope: module
scope_ref: project-x:realtime
family: websocket-reconnect-duplicate

observation: reconnect caused duplicate event processing
invariant: one logical event must not be processed twice

root_cause:
  status: established
  value: replay lacked idempotency protection

applies_when:
  - reconnect behavior changes
  - retry behavior changes
  - replay semantics change

not_proven:
  - serialization is universally required

historical_solution:
  value: add idempotency guard
  status: conditional

evidence:
  - accepted/verified run lineage
```

The current schema keeps legacy `lesson`/`solution_summary` fields for compatibility, but new integrations should populate the structured capsule fields where possible.

## Evidence and solution have different lifetimes

Keep these concepts separate:

1. **Observation/failure evidence** — what actually happened; long-lived if verified.
2. **Invariant/insight** — what must remain true; long-lived but revisable.
3. **Solution/procedure** — how one historical attempt solved it; temporary, contextual, replaceable.

A newer model may discover a better solution without invalidating the historical failure evidence.

Historical solution status vocabulary:

```text
candidate
preferred
conditional
fallback
superseded
invalid
```

`preferred` means supported by current evidence, not mandatory for future models.

## Experience families and solution variants

Related cases should converge on a stable problem/failure family rather than a single eternal solution.

```text
Family: AUTH-REFRESH-RACE

Case A (older)
  solution: lock
  accepted: yes

Case B
  solution: optimistic concurrency
  accepted: yes

Case C (newer)
  solution: versioned refresh token
  accepted: yes
```

The durable knowledge is the failure space, invariant, applicability, and evidence. Solution variants remain context-dependent alternatives.

## Scope is first-class

Knowledge scope is persisted as:

```text
task | module | project | stack | global
```

Normal retrieval rules are intentionally conservative:

- `task` — same project and matching task family/subtype
- `module` — same project + module
- `project` — same project
- `stack` — matching language/framework context
- `global` — explicitly generalized evidence only

This prevents one repository's convention from silently becoming another repository's operating rule.

## Progressive disclosure

Historical memory should conceptually support:

```text
search/index
    ↓
compact evidence card
    ↓
full case detail when requested
    ↓
raw run/artifact/source when genuinely needed
```

Current CLI retrieval implements the compact-card boundary and approximate token budget. Future richer retrieval should preserve this progressive-disclosure model.

Do not load every matched case because the context window is large.

## Token budget, not memory-count ritual

A fixed `3-5 items` limit is only a safety cap. Context cost should be bounded primarily by an approximate memory-token budget.

A fresh install defaults to historical memory `off` for recommendations and a small token budget. Explicit `retrieve` defaults to `guardrail`, where historical procedures are hidden.

Large models do not justify large memory payloads automatically.

## No summary-of-summary chain

Avoid:

```text
raw run
  ↓
model-A summary
  ↓
model-B summary of summaries
  ↓
model-C generalized summary
```

This gradually turns uncertainty and exceptions into false certainty.

Prefer:

```text
structured/raw evidence
   ├─ derived card v1
   ├─ derived card v2
   └─ future regenerated card
```

Structured evidence remains the canonical source. Summaries/cards are derived and versionable.

## New-model onboarding and Memory Lift

A new model should not inherit a previous model's memory preference.

Where practical, compare matched tasks or shadow evaluations:

```text
new model, memory off
vs
new model, memory on
```

Measure acceptance-aware outcomes such as:

- first-pass acceptance
- rework
- deterministic verification quality
- time/cost to accepted result
- incident/failure escape rate

Conceptually:

```text
Memory Lift = performance(memory-assisted) - model-only baseline
```

If Memory Lift is negative or negligible for a task family, historical memory should remain off or narrower for that model/harness/task combination.

If history materially improves high-risk review or incident work, use `guardrail`, `rescue`, or `proactive` selectively.

## Failure escalation

A model saying "I can handle this" is not evidence that historical memory is unnecessary.

For low/medium-risk work it may try its native plan first. If deterministic verification fails or residual uncertainty remains:

```text
native attempt
     ↓
verification failure / unresolved risk
     ↓
rescue retrieval
     ↓
historical failures + root causes + solution variants
     ↓
current model replans
```

For high-risk work, known applicable incidents/invariants may be shown before execution without showing old procedures.

## Experience must not silently become policy

Historical evidence may influence retrieval ranking and advisory patterns. It must not automatically create hard constraints or mandatory procedures.

Hard policy requires independent justification and belongs to the control-plane lifecycle described in `SIDECAR.md` and `POLICY.md`.

## Legacy learned Skills

v0.9 stops creating/materializing learned Agent Skills from historical experience.

Reasons:

- a Skill is instruction-shaped and therefore more likely to anchor future models
- verified experience/pattern evidence already preserves the useful history
- a historical successful procedure should remain one solution variant, not become an injected agent brain

Existing `kind=skill` database rows and old `knowledge/` files remain portable/readable for backward compatibility, but they are excluded from normal retrieval and cannot be newly promoted/materialized.

The intended shape is:

```text
many runs
  ↓
scoped evidence/experiences
  ↓
fewer reusable patterns
```

No learned-Skill terminal stage is required.
