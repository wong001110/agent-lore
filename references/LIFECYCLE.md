# Knowledge Lifecycle and Bias Controls

Agent Lore should become more selective as data grows. A larger memory database is not automatically a better engineering system.

## Lifecycle

```text
run
 ↓
verified outcome
 ↓
reusable lesson?
 ├─ no → capability/routing statistics only
 └─ yes
      ↓
 candidate experience
      ↓
 repeated cross-project evidence
      ↓
 active experience
      ↓
 generalized pattern
      ↓
 explicit skill or regression-eval promotion
```

At any point, knowledge may be deprecated or archived.

## Conservative automatic maintenance

`consolidate` calculates success ratio, independent project count, evidence count, reuse count, freshness, and utility.

With `--apply`, it can safely promote a strongly repeated candidate to `active`, generalize strong cross-project experience into a `pattern`, or archive an extremely stale single-use candidate. It intentionally does not automatically turn everything into a Skill or automatically deprecate disputed knowledge.

## Skill promotion

A Skill is a stronger procedural artifact. Promote it explicitly when there is a useful procedure, evidence transfers across comparable contexts, current versions still match, and it has not shown meaningful recent contradiction. Materialized Skills remain advisory.

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

Do not keep hundreds of near-identical active memories. Aggregate evidence and preserve representative or important failures.

## Retrieval budget

Default planning retrieval should be small, normally 3–5 items. Retrieve again only when task state materially changes. The number of stored records must not determine context size.

## Bias and failure modes

### Anchoring

Old solutions can anchor a stronger current model. Form a tentative current-model plan before retrieval for meaningful decisions.

### Confirmation bias

Agents may selectively read history that supports their initial plan. For high-impact choices, inspect disconfirming evidence.

### Experience-following and negative transfer

Similarity does not prove applicability. Require task-state, stack, version, and project-constraint checks.

### Staleness

Frameworks, harnesses, and foundation models evolve. Old knowledge should lose freshness and be revalidated.

### Survivorship bias

Failures and near-misses can be more informative than successes. Preserve established failure reasons.

### Recency bias

Latest is not automatically best; evidence quality and transfer history matter.

### Correlated evidence

Several summaries derived from one run are not independent validation. `experience_evidence` preserves root run relationships.

### Authority bias

`active` and `skill` never mean mandatory.

### Project dominance

A project with many runs should not make its local convention a global truth. Cross-project evidence is a promotion signal.

### Retrieval and context interference

Too much relevant-looking context can still reduce performance. Keep retrieval bounded.

### Router path dependence

A historically selected model can monopolize tasks and prevent a new model proving itself. Retain a small exploration or shadow-evaluation budget.

### Reviewer herding and self-preference

Do not treat several agents reading the same plan and evidence as independent reviewers. When warranted, use independently scoped review inputs.

### Metric gaming

Agents may optimize weak visible checks instead of the actual engineering goal. Prefer diverse deterministic gates, mutation testing where justified, and product-level evidence for important behavior.

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

A negative Memory Lift means the knowledge or retrieval policy is technical debt and should be revalidated, narrowed, or disabled.
