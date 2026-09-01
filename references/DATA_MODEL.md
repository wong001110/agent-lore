# Data Model

Agent Lore separates **what happened**, **whether it was verified**, **whether it was accepted**, **what was learned**, **which configuration performed the work**, and **what routing decision was made**.

## `runs`

One row per observed execution attempt.

Important fields:

```text
id
source_project
module
task_type / task_subtype / task_summary
task_scope / operation
task_group_id / parent_run_id / attempt_index
language / framework / version
agent_role / model / harness
outcome
verification / verification_status
acceptance_status / acceptance_reason / acceptance_source / accepted_at
quality_score
cost_usd
latency_ms
wall_time_ms / compute_time_ms
verification_time_ms / review_time_ms / coordination_time_ms
retry_count
files_touched / lines_changed / modules_touched
has_db_change / has_api_contract_change / test_count
run_kind: primary | shadow | challenge
topology
agent_count / merge_conflicts
challenge_level / challenge_useful
route_decision_id
experience_id
```

A run can exist without producing reusable knowledge.

`outcome=success` means the execution attempt completed successfully. It is not equivalent to final acceptance.

## Verification and acceptance

Verification:

```text
pending | passed | failed | not-required
```

Acceptance:

```text
pending | accepted | rework | rejected | invalidated | not-required
```

User-visible/product work should normally remain `pending` until human/reviewer acceptance exists.

## Rework lineage

`task_group_id` identifies one logical task across attempts.

```text
Task group X
├─ run A / attempt 1 / rework
├─ run B / attempt 2 / failed
└─ run C / attempt 3 / accepted
```

`parent_run_id` links a corrected attempt to the prior attempt. This supports first-pass acceptance, rework count, and accumulated work/cost to an accepted result.

## `run_feedback`

Preserves explicit feedback events:

```text
id
run_id
created_at
verdict: accept | rework | reject | invalidate
reason
source: human | reviewer | auto
related_run_id
```

The current acceptance state also lives on `runs` for efficient querying.

## `experiences`

A compact reusable claim distilled from runs.

```text
id
kind: experience | pattern | skill | eval
status: candidate | active | deprecated | archived
knowledge_name
source_project
module / task_type / task_subtype
lesson
failure_reason
solution_summary
confidence / utility
success_count / failure_count / evidence_count
reuse_count
trust
last_verified_at
needs_revalidation
status_reason
superseded_by
```

`confidence` is a weak metadata signal, not truth probability. `utility` is a lifecycle score, not authority.

Negative acceptance feedback can set `needs_revalidation=1`; such knowledge is down-ranked and cannot be promoted/materialized until revalidated.

## `experience_evidence`

Links knowledge to actual runs:

```text
experience_id
run_id
relation: supports | contradicts | related
```

A supporting relation should require an accepted/verified outcome when the knowledge represents a successful procedure. The lifecycle additionally computes acceptance metrics from linked runs instead of trusting the relation label alone.

## `agent_configs`

Configurations the Phase 4 router may choose:

```text
name
model
harness
agent_role
enabled
can_delegate
max_depth
quality_tier
cost_tier
priority
notes
```

`quality_tier` and `cost_tier` are cold-start priors only. They are not benchmark facts.

## `routing_decisions`

One row per integrated recommendation. It captures project/module/task context, risk/complexity/dependencies, recommended topology/configuration, challenge policy, confidence, and the final linked outcome run.

## Task-conditioned performance

Do not store one global model ranking.

Evaluate:

```text
project
× module
× task type/subtype
× language/framework
× agent role
× model
× harness
→ execution success
→ verification pass
→ acceptance / first-pass acceptance / rework
→ quality / cost / timing / retries
```

This prevents a fast model on easy tasks from being incorrectly treated as globally faster or better.

## Timing semantics

Keep multiple timing views when possible:

```text
latency_ms              model/inference latency
wall_time_ms             user-visible attempt duration
compute_time_ms          accumulated model/agent compute
verification_time_ms     tests/checks
review_time_ms           review/acceptance work
coordination_time_ms     multi-agent orchestration overhead
```

For multi-agent systems, wall time can decrease while total compute/cost increases. Report both instead of collapsing them into one latency number.

## Topology outcomes

Topology learning may use:

```text
topology
agent_count
merge_conflicts
execution success
acceptance
quality
wall time
cost
retries
```

This lets the router learn that one task distribution benefits from flat parallelism while another is harmed by coordination overhead.

## Learned skill files

An active item explicitly promoted to `kind=skill` can be materialized to:

```text
~/.agent-lore/knowledge/skills/<skill-name>/SKILL.md
```

Materialization requires accepted evidence and no `needs_revalidation` flag. The SQLite row remains the evidence/provenance source.

## Reports

Human-readable generated reports live under:

```text
~/.agent-lore/reports/
```

`latest.md` is derived output and can be regenerated from the SQLite source of truth.

## Privacy boundary

Do not store by default:

- source repositories
- full transcripts
- credentials/secrets
- `.env` values
- personal/private user data
- hidden chain-of-thought

The system should learn primarily from outcomes, concise lessons, acceptance feedback, and structured metadata.
