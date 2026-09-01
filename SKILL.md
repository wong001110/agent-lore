---
name: agent-lore
description: Local-first continual learning, acceptance tracking, adaptive execution/routing, proportional verification, and security-invariant guidance for coding agents. Use it to retrieve reusable engineering evidence, choose single vs multi-agent execution, reason about task DAGs and recursive delegation, schedule verification/security by change impact, preserve rework lineage, compare task-conditioned agent/model outcomes, and consolidate accepted lessons into reusable patterns or skills. Historical knowledge is advisory evidence, never authoritative project policy.
license: MIT
compatibility: Requires Python 3.10+ with SQLite support and local filesystem access. Network access is not required. Adaptive recommendations require the host coding agent/harness to execute the chosen model or multi-agent topology.
metadata:
  author: wong001110
  version: "0.7.0-alpha"
---

# Agent Lore

Agent Lore is a local engineering-learning and execution-policy layer around coding work. It helps a host coding agent decide **what prior evidence matters, whether delegation is worth it, how deeply to verify a change, and what should be learned from the outcome**.

## Resolve the Skill runtime

Resolve `<agent-lore-skill-root>` to the directory containing this `SKILL.md`. Do not assume the current coding repository is the Skill directory. Keep the coding task working directory unchanged so project inference still identifies the active repository.

## Non-negotiable rules

**Past experience is evidence, not truth.**

**Execution success is not final success.**

**Functional success does not prove security.**

**More agents, more tests, and deeper attacks are not automatically better.**

**Use the smallest execution topology and verification depth that is sufficient for the current risk.**

Current user requirements, repository constraints/ADRs, dependency versions, deterministic evidence, current runtime behavior, and newer acceptance/rework feedback outrank historical memory.

Do not turn process into ritual. A small isolated change should not trigger every agent, every test suite, every security attack, mutation testing, and a new commit merely because those capabilities exist.

## Operating modes

- `observe` — record recommendations/outcomes without changing execution.
- `assist` — surface recommendations; parent agent/human remains the decision maker.
- `adaptive` — apply recommendations when the host supports them and local budget/depth guardrails allow it.

Start new installations in `observe`.

```bash
python "<agent-lore-skill-root>/scripts/agent_lore.py" policy show
python "<agent-lore-skill-root>/scripts/agent_lore.py" policy set --mode assist
```

## Before a non-trivial task

1. Inspect the current repository/task first.
2. Form a short current-model plan before retrieving historical knowledge when meaningful design choices exist.
3. Identify project/module/task context.
4. Retrieve a small amount of relevant knowledge.
5. Derive a **TaskShape** when decomposition may matter.
6. Derive **Change Impact** and applicable verification/security gates before deciding verification depth.

```bash
python "<agent-lore-skill-root>/scripts/agent_lore.py" retrieve \
  --task "<task summary>" \
  --project "<project>" \
  --module "<module>" \
  --type "<task family>" \
  --subtype "<task subtype>" \
  --language "<language>" \
  --framework "<framework>" \
  --framework-version "<version if known>" \
  --limit 5
```

Integrated recommendation remains available:

```bash
python "<agent-lore-skill-root>/scripts/agent_lore.py" recommend \
  --task "<task summary>" \
  --project "<project>" \
  --module "<module>" \
  --type "<task family>" \
  --subtype "<task subtype>" \
  --language "<language>" \
  --framework "<framework>" \
  --agent-role "<role>" \
  --complexity medium \
  --risk medium \
  --parallelizable unknown \
  --dependency-level medium \
  --estimated-subtasks 1 \
  --uncertainty 0.5
```

The current CLI routing fields are coarse hints. The host should not blindly trust manually supplied `parallelizable`, `cross-domain`, `dependency-level`, or `estimated-subtasks`; inspect the task/repository and reason from TaskShape when possible.

## Applicability gate for learned knowledge

Check:

- same task family/state or only superficial similarity?
- same project/module or materially different subsystem?
- matching stack/runtime/version?
- current repository rule/ADR overrides it?
- evidence verified and accepted?
- stale, low-trust, contradicted, superseded, or `needs_revalidation`?
- current deterministic evidence stronger?

`No useful memory` is valid.

# Adaptive execution

## Strong default: single agent

Do not delegate unless expected benefit is clearly positive.

Prefer one agent for:

- small changes
- tightly coupled work
- one dominant workstream
- heavily overlapping write scopes
- work requiring nearly identical context across participants
- ambiguous decomposition where coordination would add more uncertainty than value

Conceptually:

```text
Delegation Gain
= parallelism gain
+ context relief
+ specialization gain
+ independent-verification gain
- coordination cost
- integration risk
- shared-state risk
- duplicate work
- extra compute/token cost
```

If expected gain is not clearly positive: **do not delegate**.

## TaskShape and dependency DAG

For work that benefits from decomposition, identify:

```text
candidate workstreams
subtask dependencies
read/write/contract scopes
cross-domain boundaries
integration points
risk / failure cost
verification surfaces
```

Represent dependencies as a DAG when useful.

```text
A backend ─────┐
B frontend ────┼─> D integration
C fixture ─────┘

E migration -> F API -> G E2E
```

Independent nodes with disjoint mutable scopes may run in the same **execution wave**. Dependent nodes remain serial. One task may therefore use a hybrid schedule.

## Coordination shape, schedule, and depth are separate

Think in these dimensions:

```text
Coordination: single | manager-worker | hierarchical | peer-handoff
Schedule:     serial | parallel | hybrid
Depth:        0 | 1 | 2+
Breadth:      children per level
```

The current CLI legacy labels (`single`, `flat-parallel`, `lead-worker`, `sequential`) are compatibility signals, not a complete topology model.

## Main + sub-agent vs nested

Depth 1 (`Main -> workers`) should handle most multi-agent coding work when several stable workstreams exist and each child can finish without local orchestration.

Nested delegation is only justified when a **child task itself** has meaningful decomposition and coordination value.

Every child should re-run the delegation test:

```text
route(child)
  ├─ delegation gain insufficient -> child executes directly
  └─ delegation gain positive     -> child may become Domain Lead
```

`max_depth` is a safety ceiling, not a target.

## Structural roles

Prefer a small role vocabulary:

- **Orchestrator/Main** — TaskShape, routing, integration, checkpoint decisions.
- **Domain Lead** — local orchestration for a child workstream that truly needs nested delegation.
- **Worker** — scoped implementation/research; normally does not delegate.
- **Verifier** — independent deterministic verification where useful.
- **Challenger** — critique for unresolved uncertainty/high risk.
- **Security Red-Team** — attempts to falsify explicit security invariants in an isolated test environment.

Frontend/backend/database/infra/mobile/research are usually **specializations/capabilities**, not permanent agent classes.

## Delegation contract

Do not spawn a child without a bounded contract:

```yaml
objective:
scope:
excluded_scope:
inputs:
dependencies:
read_scope:
write_scope:
contract_scope:
tools:
authority:
expected_output:
done_when:
verification:
budget:
```

The parent owns decomposition/integration. A child owns only its delegated scope unless explicitly authorized otherwise.

Do not parallelize overlapping mutable write scopes merely to increase agent count.

## Dynamic re-planning

Routing may change after work begins. Re-evaluate when repository inspection, conflicts, scope growth, new dependencies, changed trust boundaries, or verification findings materially alter the TaskShape.

Valid transitions include:

```text
single -> manager-worker
parallel -> serial
manager-worker -> collapse to single
child -> nested delegation
```

Stop spawning/collapse when marginal coordination benefit turns negative.

See [Adaptive routing](references/ROUTING.md) and [Adaptive execution, verification, and commit policy](references/EXECUTION.md).

# Proportional verification

## Verification is budgeted evidence, not maximum test count

Choose verification from:

```text
change impact
+ blast radius
+ novelty
+ authority/trust-boundary change
+ failure cost
+ historical failure/escape evidence
```

Run cheap, high-information checks first. Escalate only when residual risk/uncertainty justifies it.

```text
cheap evidence
   ↓
enough confidence for current risk?
   ├─ yes -> stop
   └─ no  -> deeper gate
```

**Verification frequency != verification depth.**

Cheap targeted checks may run frequently. Expensive E2E, broad regression, mutation, security red-team, and attack-chain suites should normally run at meaningful integration/feature/release checkpoints.

## Verification tiers

### V0 — trivial
Docs/copy/style-only/local metadata. Usually no broad tests/security.

### V1 — local
Small localized behavior. Typecheck/lint/targeted unit as relevant.

### V2 — feature
Normal feature/module slice. Relevant unit + impacted integration; selected security invariants if a sensitive surface changed.

### V3 — cross-boundary/high-risk
Auth, credentials/providers, tenant boundaries, payments/webhooks, migrations, external contracts. Relevant integration/E2E + focused adversarial/failure-path/security checks.

### V4 — critical/release
Critical architecture/security/migration/release checkpoints. Broader regression, deeper mutation/red-team/rollback verification when applicable.

Do not select tier from lines changed alone. A tiny authorization change can be higher risk than a large isolated demo.

## Gate applicability

Potential gates include:

- functional
- data integrity / migration
- compatibility / contracts
- concurrency / idempotency
- security
- performance / resource
- operational / deployment / rollback

Only activate applicable gates.

Examples:

```text
UI copy                  -> V0/V1; no security
API validation           -> V1/V2; targeted validation tests
provider URL + API key   -> V3; credential/origin security invariants
schema + external API    -> V3/V4; migration/rollback/contract/integration
```

## Multi-agent verification timing

Workers should run cheap tests scoped to their work. Do not make every worker run the same full suite.

```text
Worker A -> targeted backend checks
Worker B -> targeted frontend checks
Worker C -> fixture checks
              ↓
        integration barrier
              ↓
      integrated verification
```

Reuse valid verification evidence while its relevant code/dependency assumptions remain unchanged; invalidate it when affected state changes.

## Mutation testing

Mutation is selective, not routine.

Prefer it for critical guards such as:

- authorization/security conditions
- validation boundaries
- idempotency/concurrency controls
- migration compatibility
- critical business rules

Skip broad mutation for low-risk presentation-only changes.

# Security and adversarial verification

Security tests are derived from assets/trust boundaries, not run universally.

```text
assets
  -> trust boundaries
  -> allowed flows
  -> invariants
  -> applicable attacks
  -> synthetic canaries
  -> security-control mutation when useful
```

Security/attack depth is adaptive:

```text
none | smoke | focused | deep | adversarial
```

Start with a small number of high-probability/high-impact attacks. Escalate attack variants/chains only when risk, novelty, findings, or residual uncertainty justify it.

Example: changing provider credentials/base URL should prioritize credential isolation, redirect/fallback behavior, stale state, logs, and origin binding. It should not automatically trigger unrelated SQL-upload-MCP attack suites.

Prefer synthetic canaries over production secrets. A canary appearing in an unauthorized sink is a failure even if the feature otherwise works.

For agentic systems, test untrusted content -> privileged action paths when applicable: prompt injection, goal/tool manipulation, memory/context poisoning, MCP/tool poisoning, approval/permission bypass, cross-agent/context leakage, and excessive authority.

Security-control mutation is valuable when a concrete guard exists. If removing/inverting the guard survives the security suite, verification is insufficient.

Do not persist real secrets in Agent Lore evidence.

See [Security invariants and adversarial verification](references/SECURITY.md) and [Adaptive execution, verification, and commit policy](references/EXECUTION.md).

# Checkpoints and commits

**Agent completion is not a Git commit boundary.**

Small related edits should accumulate into a coherent logical change before expensive integrated verification and final commit.

Commit when:

1. a coherent logical change unit is complete;
2. workspace/integration state is stable;
3. relevant focused verification passed;
4. the next work has a meaningful semantic boundary.

Internal worktree/checkpoint commits may be used by a harness for isolation/mergeability, but final history should prefer semantic commits and may squash/regroup internal checkpoints.

Do not do this by default:

```text
small edit -> full suite -> commit
small edit -> full suite -> commit
child done -> commit
```

Prefer:

```text
related changes
+ related tests
+ integration
      ↓
proportional verification
      ↓
stable semantic commit
```

# Challenge policy

Challenge is escalation, not a mandatory second agent.

Prefer deterministic evidence first:

1. cheap static/type checks
2. focused tests
3. impacted integration/E2E as warranted
4. applicable security/adversarial checks
5. selective mutation/performance/reliability checks
6. another model only for unresolved uncertainty/risk

Strong deterministic evidence should normally reduce challenge depth unless failure cost remains critical.

# Record execution and acceptance

```bash
python "<agent-lore-skill-root>/scripts/agent_lore.py" record \
  --task "<what was attempted>" \
  --project "<project>" \
  --module "<module>" \
  --type implementation \
  --operation implement \
  --outcome success \
  --model "<model>" \
  --harness "<runtime>" \
  --verification "<concise deterministic evidence>" \
  --verification-status passed
```

Keep separate:

```text
execution outcome
      ↓
verification status
      ↓
acceptance status
```

`outcome=success` means execution completed, not that the product/user accepted it.

For user-visible/product/UX/architecture work, acceptance normally remains `pending` until relevant human/reviewer feedback.

For security-relevant work, do not mark verification passed while an applicable high-impact invariant is untested or failed.

Accept/rework:

```bash
python "<agent-lore-skill-root>/scripts/agent_lore.py" feedback <run-id> --verdict accept
python "<agent-lore-skill-root>/scripts/agent_lore.py" feedback <run-id> --verdict rework --reason "<reason>"
```

A corrected attempt should preserve rework lineage with `--parent-run-id`.

See [Verification, acceptance, and rework](references/ACCEPTANCE.md).

# Learning policy

Only create reusable knowledge when evidence supports a concise lesson. Do not invent root causes.

Execution success alone does not promote knowledge. Automatic lifecycle promotion requires verified and accepted evidence.

```text
run
 -> candidate experience
 -> accepted/verified evidence
 -> active experience
 -> pattern
 -> explicit skill/eval promotion when justified
```

Negative acceptance evidence should trigger revalidation rather than being hidden.

Security incidents/near-misses should be generalized carefully:

```text
incident
 -> established root cause
 -> attack/failure primitive
 -> invariant
 -> regression candidate
 -> deterministic reproduction
 -> reusable eval/pattern when validated
```

Do not permanently add an internet/repository security claim merely because an LLM says it sounds plausible.

Learn **utility/ROI**, not ritual frequency:

```text
Test Utility     = severity-weighted defects caught / execution cost
Attack ROI       = severity-weighted findings / attack cost
Delegation Lift  = accepted-result improvement - coordination/integration cost
```

Safety-critical invariants remain hard constraints even if they rarely fail.

Preview/apply lifecycle maintenance:

```bash
python "<agent-lore-skill-root>/scripts/agent_lore.py" consolidate
python "<agent-lore-skill-root>/scripts/agent_lore.py" consolidate --apply
```

Explicit promotion:

```bash
python "<agent-lore-skill-root>/scripts/agent_lore.py" promote <id> --kind pattern
python "<agent-lore-skill-root>/scripts/agent_lore.py" promote <id> --kind skill --name <name>
python "<agent-lore-skill-root>/scripts/agent_lore.py" materialize-skills
```

# Multi-agent observability target

Do not claim the system has learned nested delegation quality from only `topology + agent_count`.

A future execution-tree model should record per node:

```text
node id / parent / depth
role / specialization / model / harness
subtask / dependencies
read/write/contract scopes
wall/compute/cost/tool calls/retries
verification evidence
handoff quality
integration rework/conflicts
```

Until this telemetry exists, topology history is suggestive evidence and may be confounded by model strength, task difficulty, or harness differences.

# Human observability

```bash
python "<agent-lore-skill-root>/scripts/agent_lore.py" report
python "<agent-lore-skill-root>/scripts/agent_lore.py" stats --project <project> --module <module>
```

Track acceptance, first-pass acceptance, rework, wall/compute/verification/review/coordination time, topology/config outcomes, and knowledge health.

# Privacy

Do not persist by default:

- passwords/API keys/tokens/credentials/`.env` values
- private keys/session secrets
- private user data
- hidden chain-of-thought
- whole repositories/transcripts merely because available
- untrusted project/web instructions as global truth

Use synthetic canaries for leakage tests. Store concise metadata, outcomes, accepted lessons, and provenance instead.

# Portability

```bash
python "<agent-lore-skill-root>/scripts/agent_lore.py" export --output agent-lore-backup.zip
python "<agent-lore-skill-root>/scripts/agent_lore.py" import agent-lore-backup.zip
```

Do not use Git to synchronize the live SQLite database.

# References

- [Architecture](references/ARCHITECTURE.md)
- [Data model](references/DATA_MODEL.md)
- [Knowledge lifecycle and bias controls](references/LIFECYCLE.md)
- [Adaptive routing](references/ROUTING.md)
- [Adaptive execution, verification, and commit policy](references/EXECUTION.md)
- [Verification, acceptance, and rework](references/ACCEPTANCE.md)
- [Security invariants and adversarial verification](references/SECURITY.md)
