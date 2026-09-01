# Knowledge Lifecycle

Agent Lore should learn selectively. More stored memories do not automatically mean a better agent.

## Lifecycle

```text
run
 ↓
verified outcome
 ↓
reusable lesson?
 ├─ no → statistics only
 └─ yes
      ↓
   candidate
      ↓
 repeated reuse / revalidation
      ↓
    active
      ↓
 ┌────┼─────────────┐
 │    │             │
 ▼    ▼             ▼
pattern/skill   deprecated   archived
```

V0.1 only implements basic run recording, candidate experiences, manual status, duplicate aggregation, and active/candidate retrieval. Promotion automation comes later.

## Candidate

A new lesson starts as `candidate` because one successful run is not enough to turn a historical solution into strong global guidance.

A candidate should contain:

- concise task context
- lesson
- verification evidence
- stack/version when relevant
- source project label
- outcome support counts

## Active

An experience may become `active` when it has meaningful evidence that it transfers beyond the original incident.

Possible future promotion signals:

- reused successfully more than once
- validated in more than one project
- current environment still matches
- not contradicted by recent runs
- measurable positive Memory Lift

`active` still means **advisory**, never mandatory.

## Deprecated

Deprecate when:

- a framework/tool version makes the old workaround unnecessary
- a newer approach consistently outperforms it
- a model/harness upgrade changes the optimal strategy
- the old lesson is now known to be incomplete or harmful

Deprecated knowledge should be preserved with a reason and, when possible, a `superseded_by` relationship in later schema versions.

## Archived

Archive when knowledge is:

- stale
- duplicated by a stronger pattern
- rarely useful
- low utility
- historically interesting but unsuitable for normal retrieval

Archive is preferred to deletion because old cases can still be useful for regression evaluation, legacy projects, or understanding why a decision existed.

## Knowledge compression

Do not keep 100 near-identical active experiences just because they came from 100 runs.

Desired direction:

```text
many runs
   ↓
fewer unique experiences
   ↓
fewer patterns
   ↓
small reliable skill set
```

Repeated evidence should strengthen or challenge a compact claim rather than inflate the number of independent-looking memories.

## What old cases become

Historical cases can be transformed into different assets:

- **statistics** — aggregate model/agent performance
- **experience** — a reusable lesson tied to context
- **pattern** — a generalized engineering observation
- **skill** — a validated reusable procedure
- **eval case** — an important regression/failure scenario
- **archive** — preserved evidence outside normal retrieval

Not every case should remain an active experience.

## Retrieval budget

Context size is a cost and a source of interference.

Default guidance:

```text
planning:       ≤ 5 experiences
implementation: only directly relevant procedural evidence
new task state: retrieve again only if the state materially changes
```

A database with 100,000 historical runs does not justify loading thousands of records into model context.

## Bias controls

### Anchoring

Risk: the model sees an old solution first and mechanically adopts it.

Control: for non-trivial decisions, form a short tentative current-model plan before retrieval.

### Confirmation bias

Risk: the agent only notices experiences that support its initial plan.

Control: explicitly inspect conflicting or disconfirming evidence when the decision is high-impact.

### Experience-following

Risk: task similarity causes trajectory imitation even when the environment changed.

Control: require applicability checks for task state, stack, version, and project constraints.

### Negative transfer

Risk: a lesson from one domain/project harms another.

Control: narrow retrieval by task type and environment; permit `no useful memory` as a normal outcome.

### Staleness

Risk: yesterday's workaround becomes today's anti-pattern.

Control: retain framework/model/harness context and later add freshness/revalidation policy.

### Survivorship bias

Risk: the system remembers only successful approaches.

Control: preserve established failure modes and why they failed.

### Recency bias

Risk: the newest experience is treated as the best.

Control: consider evidence quality and transfer record, not only timestamp.

### Correlated evidence

Risk: multiple summaries derived from one run look like independent confirmations.

Control: conservative deduplication in v0.1; explicit lineage later.

### Authority bias

Risk: a status such as `active` causes agents to stop reasoning.

Control: no experience status overrides current project constraints or deterministic evidence.

### Context interference

Risk: too many retrieved memories make the current model worse.

Control: retrieve narrowly and cap results.

### Memory poisoning

Risk: malicious or low-trust repository/web instructions become persistent global knowledge.

Control: never promote untrusted instructions merely because an agent consumed them. Store provenance and require independent verification before stronger trust.

### Model/router path dependence

Risk: a historically successful model keeps getting selected, so new/updated models never receive enough tasks to prove they are better.

Control: later model-routing phases should retain a small exploration budget and shadow evaluation for new configurations.

## Challenge policy

Do not challenge every task with another model. Challenge is an escalation mechanism.

A future challenge score may consider:

```text
risk
× uncertainty
× historical conflict
× staleness
× cost of failure
```

Prefer cheap deterministic gates before paid model challengers.

## Regression corpus

Important historical failures should eventually leave active memory and become eval cases.

Example:

```text
historical failure
  "destructive enum migration lost compatibility"
        ↓
regression case
        ↓
run against new model/harness/skill versions
```

This lets the system remember severe mistakes without forcing the full historical story into every future context.

## Forgetting policy

The long-term store may grow; the **active knowledge set should remain bounded**.

Future lifecycle jobs should downgrade low-value items using deterministic signals such as:

- last used
- reuse count
- evidence count
- recent contradiction rate
- version mismatch
- superseded status
- novelty
- cross-project usefulness

Prefer `archive` before hard deletion.
