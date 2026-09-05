# Data Model

Agent Lore separates **execution**, **verification**, **acceptance**, **historical evidence**, **model/harness observations**, and **routing decisions** so none is mistaken for another.

SQLite is the canonical runtime store. Reports/cards are derived views.

## `runs`

One row per observed execution attempt.

Important fields include:

```text
id / created_at
source_project / module
task_type / task_subtype / task_summary
task_summary_canonical / source_language / canonicalizer
task_scope / operation
task_group_id / parent_run_id / attempt_index
language / framework / framework_version
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
topology / agent_count / merge_conflicts
execution_capture_status / execution_capture_source / execution_capture_notes
challenge_level / challenge_useful
route_decision_id
experience_id
```

`outcome=success` means the attempt executed successfully. It does not imply verified, accepted, or safe.

## Verification and acceptance

Verification:

```text
pending | passed | failed | not-required
```

Acceptance:

```text
pending | accepted | rework | rejected | invalidated | not-required
```

User-visible/product/architecture work may remain acceptance-pending after technical verification.

## Rework lineage

`task_group_id` groups attempts on one logical task. `parent_run_id` records correction/rework lineage.

```text
Task group
├─ attempt 1 / rework
├─ attempt 2 / failed
└─ attempt 3 / accepted
```

This supports first-pass acceptance and cost/time-to-accepted-result metrics.

## `run_feedback`

Explicit feedback events:

```text
id
run_id
created_at
verdict: accept | rework | reject | invalidate
reason
source: human | reviewer | auto
related_run_id
```

## `experiences` — scoped Evidence Capsules

A reusable historical item is evidence, not an instruction.

Legacy/common fields:

```text
id
kind: experience | pattern | eval | legacy skill
status: candidate | active | deprecated | archived
knowledge_name
source_project
module / task_type / task_subtype
language / framework / framework_version
lesson / canonical representations
failure_reason
solution_summary
confidence / utility
success_count / failure_count / evidence_count / reuse_count
trust
last_verified_at
needs_revalidation
status_reason / superseded_by
```

v0.9 Evidence Capsule fields:

```text
knowledge_scope: task | module | project | stack | global
scope_ref
experience_family
observation
invariant
root_cause
root_cause_status: unknown | hypothesis | established | disputed
applies_when: JSON array
not_proven: JSON array
solution_status: candidate | preferred | conditional | fallback | superseded | invalid
summary_version
```

### Meaning

- `observation` — what was actually observed.
- `invariant` — what should remain true independent of a specific implementation.
- `root_cause` — explanation with explicit epistemic status; do not treat hypotheses as established facts.
- `applies_when` — signals that make the case relevant.
- `not_proven` — boundaries preventing over-generalization.
- `solution_summary` — one historical remedy/variant, not future instruction.
- `solution_status` — how current evidence regards that variant.
- `experience_family` — stable problem/failure family that may contain multiple solution variants.

`confidence` is metadata, not truth probability. `utility` is lifecycle/retrieval metadata, not authority.

## Knowledge scope

Scope is persisted and used to prevent cross-project leakage:

```text
task    -> narrow task context inside the source project
module  -> same project/module
project -> source project
stack   -> deliberately transferable language/framework context
global  -> explicitly generalized evidence
```

A project-specific convention must not silently become another project's instruction.

## Legacy learned Skills

Pre-v0.9 data may contain:

```text
kind='skill'
```

and legacy files under `~/.agent-lore/knowledge/`.

They are preserved for backward compatibility but are read-only legacy state:

- excluded from normal retrieval
- cannot be newly promoted
- cannot be newly materialized

The active learning lifecycle now stops at Experience/Pattern/Eval.

## `experience_evidence`

Links historical knowledge to source runs:

```text
experience_id
run_id
relation: supports | contradicts | related
created_at
```

Linked run state—outcome, verification, acceptance—remains authoritative over the relation label.

## `knowledge_revalidations`

Immutable explicit revalidation event:

```text
id
experience_id
run_id
created_at
reason
source
```

The linked run must be successful, verified, and accepted. Revalidation clears a hold but does not reactivate deprecated/archived evidence or rewrite old interpretation text.

## `knowledge_usage`

Audits whether retrieved evidence was actually used:

```text
id
experience_id
run_id
created_at
decision: applied | ignored
reason
source
```

Retrieval alone does not count as reuse. `ignored` is neutral.

## `run_agents`

Optional after-the-fact execution-tree observations:

```text
run_id / agent_id
parent_agent_id
display_name
role / specialization
model / harness / status
task_summary
depth
started_at / finished_at
wall_time_ms / compute_time_ms / cost_usd
metadata_json
```

`execution_capture_status` on the run is:

```text
complete | partial | not-collected
```

Missing rows are not evidence of single-agent execution.

## `agent_configs`

Available executor configurations:

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

`quality_tier` / `cost_tier` are cold-start priors, not universal benchmark facts.

A new model normally adds/configures an executor rather than changing Agent Lore architecture.

## `routing_decisions`

One row per recommendation, including task context and bounded execution guidance.

Fields include:

```text
project/module/task/subtype
model/harness/config recommendation
legacy topology
TaskShape JSON
EvidencePlan JSON
coordination / schedule / delegation_depth
verification_tier / security_depth
memory_mode (schema slot for route/memory calibration)
challenge recommendation
confidence/reasons
outcome_run_id
```

TaskShape is host/current-model supplied when available; Agent Lore validates structural constraints rather than claiming it derived repository truth itself.

## Task-conditioned performance

Do not store one global model ranking.

Evaluate contextual combinations such as:

```text
project/module/task/stack
× model
× harness
× role
× topology
→ execution success
→ verification
→ acceptance / first-pass acceptance / rework
→ quality / cost / timing / retries
```

Memory-on/off evaluation should also be matched by task/model/harness where possible before concluding historical memory is helpful.

## Timing semantics

Keep distinct timing views:

```text
latency_ms              inference latency
wall_time_ms            user-visible attempt duration
compute_time_ms         accumulated agent/model compute
verification_time_ms    checks/tests
review_time_ms          review/acceptance work
coordination_time_ms    orchestration overhead
```

Parallelism may reduce wall time while increasing total compute/cost.

## Reports and derived summaries

Generated reports live under lazy-created:

```text
~/.agent-lore/reports/
```

Reports are derived from SQLite and can be regenerated. They are not canonical memory.

Likewise, compact memory cards/canonical translations are derived representations. Avoid summary-of-summary chains that discard original structured evidence.

## Runtime filesystem

Fresh v0.9 runtime:

```text
~/.agent-lore/
└─ agent-lore.db
```

Lazy directories:

```text
reports/
exports/
archive/
```

Legacy `knowledge/` may exist after upgrade/import and remains portable. `traces/` and `knowledge/skills/` are no longer pre-created.

## Privacy boundary

Do not persist by default:

- credentials/secrets/tokens/private keys/`.env` values
- personal/private user data
- hidden chain-of-thought
- full source repositories or transcripts merely because available
- project wiki/current-state snapshots
- untrusted external/repository text as global truth

Store concise structured evidence, provenance, acceptance/rework, scope, verified observations/invariants, model/harness telemetry, and non-sensitive metadata.
