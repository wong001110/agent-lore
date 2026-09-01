# Data Model

Agent Lore separates **what happened**, **what was learned**, **who/what configuration performed the work**, and **what routing decision was made**.

## `runs`

One row per observed execution.

Important fields:

```text
id
source_project
task_type / task_summary
language / framework / version
agent_role / model / harness
outcome / quality_score
verification
cost_usd / latency_ms / retry_count
run_kind: primary | shadow | challenge
topology
agent_count / merge_conflicts
challenge_level / challenge_useful
route_decision_id
experience_id
```

A run can exist without producing reusable knowledge.

## `experiences`

A compact reusable claim distilled from runs.

```text
id
kind: experience | pattern | skill | eval
status: candidate | active | deprecated | archived
knowledge_name
source_project
task context
lesson
failure_reason
solution_summary
confidence / utility
success_count / failure_count / evidence_count
reuse_count
trust
last_verified_at
status_reason
superseded_by
```

`confidence` is a weak metadata signal, not truth probability. `utility` is a lifecycle score, not authority.

## `experience_evidence`

Links a knowledge item to actual runs:

```text
experience_id
run_id
relation: supports | contradicts | related
```

This enables cross-project evidence counts and reduces correlated-evidence inflation.

## `agent_configs`

Configurations that the Phase 4 router is allowed to choose.

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

`quality_tier` and `cost_tier` are only cold-start priors. They must not be presented as benchmark facts.

## `routing_decisions`

One row per integrated recommendation.

It captures:

```text
mode
task fingerprint
complexity / risk
parallelizable / dependency level / cross-domain
estimated subtasks
uncertainty
memory conflict / stale memory
deterministic evidence
cost of failure
recommended topology
recommended agent config/model/harness
model score/confidence
topology confidence
challenge level/score
reasons
applied
outcome_run_id
```

The `outcome_run_id` closes the feedback loop when `record --route-decision-id ...` is used.

## Task-conditioned performance

Do not store one global model ranking.

Evaluate:

```text
task type
× language/framework
× agent role
× model
× harness
→ outcome / quality / effective cost / latency / retries
```

A cheap model that causes repeated retries can be worse economically than a stronger model that completes once.

## Topology outcomes

Topology learning derives from run fields:

```text
topology
agent_count
merge_conflicts
success
quality
cost
retries
```

This allows future recommendations to learn that one task distribution may benefit from flat parallelism while another is harmed by coordination overhead.

## Learned skill files

An `active` knowledge item explicitly promoted to `kind=skill` can be materialized to:

```text
~/.agent-lore/knowledge/skills/<skill-name>/SKILL.md
```

The SQLite row remains the evidence/provenance source. The generated Skill is an execution-facing representation, not a replacement for evidence history.

## Privacy boundary

Do not store by default:

- source repositories
- full transcripts
- credentials/secrets
- `.env` values
- personal/private user data
- hidden chain-of-thought

The system should learn primarily from outcomes, concise lessons, and metadata.
