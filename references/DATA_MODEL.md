# Data Model

Agent Lore separates **observed runs** from **distilled experiences**.

## Runs

A run records what happened during one engineering task execution.

Core fields:

```text
id
created_at
source_project
task_type
task_summary
language
framework
framework_version
agent_role
model
harness
outcome
verification
latency_ms
cost_usd
retry_count
notes
experience_id
```

### Why runs are separate

Runs support questions such as:

- Which model has the best success/cost ratio for TypeScript test generation?
- Does a particular agent role require more retries?
- Does one harness perform better than another on the same task family?
- Did a retrieved experience actually coincide with improved outcomes?

A run can exist without producing reusable knowledge.

## Experiences

An experience is a compact reusable engineering claim distilled from one or more runs.

Core fields:

```text
id
created_at
updated_at
status
source_project
task_type
task_summary
language
framework
framework_version
lesson
failure_reason
solution_summary
confidence
utility
evidence_count
success_count
failure_count
reuse_count
last_used_at
tags
```

### Status

V0.1 recognizes:

- `candidate` — useful but not yet strongly validated
- `active` — intentionally trusted as reusable advisory evidence
- `deprecated` — preserved historically but normally excluded from retrieval
- `archived` — cold evidence; preserved but normally excluded

New reusable experiences should default to `candidate`.

## Exact duplicate aggregation

V0.1 performs conservative aggregation. If a newly recorded lesson normalizes to the same lesson, task type, language, and framework as an existing candidate/active experience, the existing experience is updated instead of creating another independent-looking knowledge item.

This does **not** prove independent validation. Future versions should preserve stronger lineage/provenance and distinguish independent evidence from copied or derived evidence.

## Model and agent statistics

Do not maintain one global ranking such as:

```text
1. Model A
2. Model B
3. Model C
```

Compare configuration performance within task context:

```text
task type
× language/framework
× agent role
× model
× harness
→ success rate / cost / latency / retries
```

A later router may optimize an effective-cost objective such as:

```text
Effective Cost = inference cost + retry cost + reviewer cost + failure-recovery cost
```

## Confidence

`confidence` is intentionally not treated as truth probability. It is a weak metadata signal about how strongly the experience is currently supported.

Future versions should split this into multiple dimensions, for example:

```text
source_quality
execution_evidence
transfer_confidence
environment_match
freshness
```

## Utility

`utility` is reserved for later lifecycle policies. Useful inputs may include:

```text
reuse_count
success_rate
independent_project_count
novelty
freshness
transfer_value
```

A low-utility experience should normally be archived, not immediately deleted.

## Tags

Tags are stored as a small JSON list of lower-case strings. They should add retrieval context, not duplicate the entire task description.

Good:

```json
["migration", "enum", "production-data"]
```

Poor:

```json
["this-is-a-very-long-copy-of-the-task-description"]
```

## Privacy boundary

Do not store by default:

- full source files
- absolute project paths
- `.env` contents
- credentials or tokens
- private keys
- personal/private user data
- hidden chain-of-thought
- full transcripts solely for convenience

The operational data model is designed to learn from **outcomes and lessons**, not to mirror the user's repositories.

## Future lineage model

Later versions should add explicit provenance relationships:

```text
experience
  ├─ supported_by run A
  ├─ supported_by run B
  ├─ contradicted_by run C
  └─ derived_from experience X
```

This prevents three summaries derived from the same original run from being miscounted as three independent confirmations.
