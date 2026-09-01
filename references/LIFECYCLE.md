# Knowledge Lifecycle and Bias Controls

Agent Lore should become more selective as data grows. A larger memory database is not automatically a better engineering system.

## Lifecycle

```text
run attempt
 ↓
execution outcome
 ↓
verification
 ↓
acceptance / rework feedback
 ↓
reusable lesson?
 ├─ no → capability/routing statistics only
 └─ yes
      ↓
 candidate experience
      ↓
 accepted + verified cross-project evidence
      ↓
 active experience
      ↓
 generalized pattern
      ↓
 explicit skill or regression-eval promotion
```

At any point, knowledge may be flagged for revalidation, deprecated, or archived.

## Why acceptance matters

A run can be technically successful and still be a poor delivered result.

Examples:

```text
Tests pass + user requests redesign
→ execution success
→ verification passed
→ acceptance rework
```

```text
Implementation completes + integration fails
→ execution success or partial
→ verification failed
→ not accepted evidence
```

Automatic knowledge promotion therefore uses accepted and verified linked runs rather than raw `outcome=success` counts.

## Conservative automatic maintenance

`consolidate` calculates acceptance ratio, accepted/verified run count, accepted project diversity, reuse, freshness, and utility.

With `--apply`, it can safely promote a strongly supported candidate to `active`, generalize broad accepted evidence into a `pattern`, or archive an extremely stale single-use candidate.

It intentionally does not automatically turn everything into a Skill or automatically delete disputed knowledge.

## Negative feedback and revalidation

If a run linked to knowledge receives `rework`, `reject`, or `invalidate` feedback:

```text
negative feedback
      ↓
linked evidence becomes contradictory
      ↓
knowledge.needs_revalidation = true
      ↓
retrieval warning / lower ranking
      ↓
no automatic promotion or materialization
```

Preserve the historical evidence. Do not silently erase the earlier case, because it may still explain why an approach existed or reveal a context boundary.

## Skill promotion

A Skill is a stronger procedural artifact. Promote it only when there is a useful procedure and accepted/verified evidence supports it.

Knowledge flagged `needs_revalidation` cannot be promoted/materialized until revalidated.

Materialized Skills remain advisory.

## Rework lineage

Rework attempts should share a logical task group:

```text
Task X
├─ attempt 1 → verified, rework requested
├─ attempt 2 → failed verification
└─ attempt 3 → verified + accepted
```

This prevents the first attempt from appearing as a clean success and makes these metrics possible:

- first-pass acceptance rate
- number of reworks
- accumulated work to accepted result
- total cost to accepted result

## Old cases

Historical cases should gradually move into the right representation:

```text
raw run → statistic
       ↘ experience
       ↘ pattern
       ↘ skill
       ↘ eval case
       ↘ archive
```

Do not keep hundreds of near-identical active memories. Aggregate evidence and preserve representative or important failures/reworks.

## Retrieval budget

Default planning retrieval should be small, normally 3–5 items. Retrieve again only when task state materially changes. The number of stored records must not determine context size.

## Bias and failure modes

### Anchoring

Old solutions can anchor a stronger current model. Form a tentative current-model plan before retrieval for meaningful decisions.

### Confirmation bias

Agents may selectively read history that supports their initial plan. For high-impact choices, inspect disconfirming evidence.

### Experience-following and negative transfer

Similarity does not prove applicability. Require task-state, module, stack, version, and project-constraint checks.

### Staleness

Frameworks, harnesses, and foundation models evolve. Old knowledge should lose freshness and be revalidated.

### Survivorship bias

Failures, reworks, rejections, and near-misses can be more informative than clean successes. Preserve established reasons.

### Acceptance bias

A user may accept something for schedule reasons even if it is technically mediocre, or reject something for product reasons even though it is technically correct. Keep verification and acceptance as separate dimensions rather than collapsing them into one label.

### Recency bias

Latest is not automatically best; evidence quality and transfer history matter.

### Correlated evidence

Several summaries derived from one run are not independent validation. `experience_evidence` preserves root run relationships.

### Authority bias

`active` and `skill` never mean mandatory.

### Project dominance

A project with many runs should not make its local convention a global truth. Cross-project accepted evidence is a promotion signal.

### Retrieval and context interference

Too much relevant-looking context can still reduce performance. Keep retrieval bounded.

### Router path dependence

A historically selected model can monopolize tasks and prevent a new model proving itself. Retain a small exploration or shadow-evaluation budget.

### Reviewer herding and self-preference

Do not treat several agents reading the same plan and evidence as independent reviewers. When warranted, use independently scoped review inputs.

### Metric gaming

Agents may optimize weak visible checks instead of the actual engineering goal. Prefer diverse deterministic gates, mutation testing where justified, and product-level acceptance for user-facing behavior.

### Untrusted-source contamination

Repository or web content is untrusted evidence. Do not turn instructions discovered in project content into global engineering guidance without independent verification and provenance.

## Challenge ROI

Challenge should be measured, not ritualized. Track challenge level, whether it changed or corrected the result, and the added cost or latency.

If a task family rarely benefits from challenge, reduce challenge frequency. If high-risk migrations are frequently corrected by challenge, preserve it.

## Memory Lift

Long-term success metric:

```text
Memory Lift = performance(memory-assisted) - performance(model-only baseline)
```

For real product work, benchmark `performance` with acceptance-aware measures such as first-pass acceptance, rework, time/cost to accepted result, and verification quality—not only execution success.

A negative Memory Lift means the knowledge or retrieval policy is technical debt and should be revalidated, narrowed, or disabled.
