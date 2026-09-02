---
name: agent-lore
description: Local-first continual learning, adaptive execution/routing, proportional verification, security-invariant guidance, and project-context workflow for coding agents. Use it to reuse accepted engineering evidence, choose the smallest useful single/multi-agent topology, reason about task DAGs and recursive delegation, plan risk-proportional verification/security, preserve rework lineage, and learn from outcomes without replacing current-model judgment.
license: MIT
compatibility: Requires Python 3.10+ with SQLite support and local filesystem access. Network access is not required. Adaptive recommendations require the host coding agent/harness to execute the selected plan.
metadata:
  author: wong001110
  version: "0.7.0-alpha"
---

# Agent Lore

Agent Lore is a **policy + learning + decision-intelligence layer** around coding work. It should improve current-model judgment, not replace reasoning with accumulated procedures.

## Resolve the Skill runtime

Resolve `<agent-lore-skill-root>` to the directory containing this file. Keep the active coding repository as the working directory.

# Core rules

**Past experience is evidence, not truth.**

**Execution success is not final success.**

**Functional success does not prove security.**

**More agents, tests, attacks, and commits are not automatically better.**

**Use the smallest execution topology and verification depth sufficient for the current task and risk.**

**Project state belongs to the project; Agent Lore does not store project wikis.**

Current user requirements, repository constraints/ADRs, source/runtime evidence, dependency versions, deterministic verification, and newer acceptance/rework feedback outrank historical memory.

Do not turn process into ritual.

# Policy strength and model freedom

Policies have four strengths:

```text
hard            -> cannot be overridden in normal execution
strong-default  -> normally follow; may override with a concrete current-task reason
advisory         -> freely adaptable
experimental     -> weak/under-sampled evidence only
```

Examples:

- credential/tenant/write-scope/destructive-approval boundaries: `hard`
- single-agent default, serialize overlapping writes, batch related edits: `strong-default`
- consider parallelism/verifier/focused mutation: `advisory`
- newly learned model/topology preference: `experimental`

Do not encode brittle thresholds such as `files > 10 -> E2E` or `subtasks >= 3 -> multi-agent`. Categories such as verification tier, delegation gain, and security depth are reasoning language, not recipes.

See [Policy strength and model freedom](references/POLICY.md).

# Project-local context first

When a project maintains a local wiki/current-state view, use it to establish context before broad repository reading.

Normal task startup:

```text
read project-local wiki/current state
        ↓
retrieve small relevant Agent Lore evidence
        ↓
inspect affected source/tests/contracts
        ↓
execute
```

The project wiki is maintained by the coding agent/Main inside that project. It does not require OpenWiki or any extra AI API key. Agent Lore must not copy or synchronize its contents.

Source, tests, schemas, contracts, ADRs/specs, and runtime behavior remain authoritative.

Full-repository re-analysis is exceptional: first contact without trustworthy project state, major architecture/framework migration, materially stale/conflicting wiki, unknown security blast radius, unbounded impact, or an explicit full audit request.

At meaningful checkpoints, Main/Integrator updates the project-local wiki when project truth changed. Do not update it for every small edit.

See [Project-local context and wiki workflow](references/PROJECT_CONTEXT.md).

# Operating modes

- `observe` — record recommendations/outcomes only.
- `assist` — surface recommendations; parent agent/human decides.
- `adaptive` — host may apply recommendations within hard constraints and budgets.

Start new installations in `observe`.

```bash
python "<agent-lore-skill-root>/scripts/agent_lore.py" policy show
python "<agent-lore-skill-root>/scripts/agent_lore.py" policy set --mode assist
```

# Before a non-trivial task

1. Read trustworthy project-local current state when available.
2. Inspect the relevant repository area and form a short current-model plan before historical retrieval when design choices matter.
3. Retrieve only a small amount of applicable Agent Lore evidence.
4. Derive a working **TaskShape** if decomposition may help.
5. Derive **Change Impact** and an **EvidencePlan** before choosing verification/security depth.

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

The current `recommend` CLI accepts coarse routing hints. Treat them as compatibility inputs, not ground truth; the host should reason from current TaskShape/repository evidence.

# Adaptive execution

## Single agent is the strong default

Prefer one agent when work is small, tightly coupled, context-heavy, has one dominant workstream, or delegation gain is unclear.

Consider delegation using reasoning dimensions rather than a fixed formula:

```text
benefits: parallelism, context relief, specialization, independent verification
costs: coordination, integration, shared-state risk, duplicate work, compute/token cost
```

If expected gain is not clearly positive, do not delegate.

## TaskShape and DAG

When decomposition materially helps, identify:

```text
objective
scope / risk / uncertainty
workstreams and dependencies
read/write/contract scopes
integration points
verification/security surfaces
```

Use a dependency DAG when useful. Independent nodes with disjoint mutable scopes may share an execution wave; dependent nodes remain serial. One task may mix parallel, serial, and nested segments.

## Coordination, schedule, and depth are separate

```text
Coordination: single | manager-worker | hierarchical | peer-handoff
Schedule:     serial | parallel | hybrid
Depth:        0 | 1 | 2+
```

Most multi-agent coding work should stop at depth 1. Nested delegation should **emerge recursively** only when a child task itself has useful local decomposition.

Every child re-runs the delegation decision. `max_depth` is a hard ceiling, never a target.

## Structural roles

Keep roles small and structural:

- Orchestrator/Main
- Domain Lead
- Worker
- Verifier
- Challenger
- Security Red-Team

Frontend/backend/database/infra/mobile/research are specializations/capabilities, not permanent agent classes.

A child should receive a bounded delegation contract covering objective, scope, dependencies, read/write/contract scope, tools/authority, expected output, done criteria, verification, and budget.

## Dynamic re-planning

Routing is not one-shot. Valid runtime adaptations include:

```text
single -> manager-worker
parallel -> serial
manager-worker -> collapse to single
child -> nested delegation
```

Re-plan when new repository evidence, conflicts, scope growth, dependencies, trust boundaries, or verification findings materially change TaskShape.

See [Adaptive routing](references/ROUTING.md) and [Adaptive execution, verification, and commit policy](references/EXECUTION.md).

# Proportional verification

Verification should prove claims, not maximize test count.

An EvidencePlan asks:

```text
What claims must be proven?
What is the cheapest useful evidence?
What would trigger escalation?
When is evidence sufficient to stop?
```

Choose depth from change impact, blast radius, novelty, authority/trust-boundary change, failure cost, and relevant historical escape evidence.

Run cheap/high-information checks first and stop when evidence is sufficient for the current risk. Hard invariants cannot be skipped by early stopping.

**Verification frequency is not verification depth.** Cheap targeted checks may run frequently; broad E2E, regression, mutation, security red-team, and attack chains normally belong at meaningful integration/feature/release checkpoints.

## V0-V4 are signals, not recipes

- `V0` trivial
- `V1` local
- `V2` feature
- `V3` cross-boundary/high-risk
- `V4` critical/release

The tier communicates expected depth. It does not mandate a fixed checklist.

Only activate relevant gate families: functional, migration/data integrity, contracts/compatibility, concurrency/idempotency, security, performance/resource, operational/deployment/rollback.

Workers should run cheap scoped checks. Expensive integrated checks should be shared at integration barriers rather than repeated by every worker.

Mutation testing is selective; prioritize critical guards and business invariants rather than mutation count.

# Security and attack simulation

Security is applicability-based:

```text
assets
  -> trust boundaries
  -> allowed flows
  -> invariants
  -> applicable attacks
  -> synthetic canaries
  -> security-control mutation where useful
```

Security depth is a budget signal:

```text
none | smoke | focused | deep | adversarial
```

Start with high-probability/high-impact attacks. Escalate variants, fuzzing, or multi-step chains only when risk, novelty, findings, or residual uncertainty justify it.

Security Red-Team may actively simulate attacks only in local/test/sandbox/ephemeral or explicitly authorized environments. Do not attack production or third-party systems merely to validate a control.

Security incidents/near-misses may become regression candidates only after root cause and deterministic reproduction are established.

Real secrets must not be persisted in Agent Lore evidence; use synthetic canaries.

See [Security invariants and adversarial verification](references/SECURITY.md).

# Checkpoints, commits, and project wiki updates

**Agent completion is not a Git commit boundary.**

Small related edits should accumulate into a coherent logical batch. Semantic commit when the change is coherent, integration state is stable, relevant focused verification passed, and a meaningful boundary exists.

Internal checkpoint/worktree commits are allowed for orchestration/recovery and may be squashed/regrouped in final history.

At the same meaningful checkpoint, update the **project-local** wiki/current state if project truth changed. Workers may suggest a `wiki_delta`; Main/Integrator owns the coherent update.

# Challenge and human escalation

Challenge is escalation, not a mandatory second agent. Prefer deterministic evidence before another model.

Main/Orchestrator normally decides routing, phase transitions, verification/security depth, retries/replans, and commit timing without asking the user.

Escalate owner-level decisions: irreversible/destructive production actions, lowering security/privacy, materially expanding permissions, major product ambiguity, major durable architecture/cost obligations, or legal/compliance ambiguity.

# Recording execution, acceptance, and learning

Keep separate:

```text
execution outcome
      ↓
verification status
      ↓
acceptance status
```

```bash
python "<agent-lore-skill-root>/scripts/agent_lore.py" record \
  --task "<what was attempted>" \
  --project "<project>" \
  --module "<module>" \
  --type implementation \
  --outcome success \
  --verification "<concise evidence>" \
  --verification-status passed
```

User-visible/product/UX/architecture work normally remains acceptance-pending until relevant human/reviewer feedback. A corrected attempt should preserve rework lineage with `--parent-run-id`.

Only create reusable knowledge when evidence supports a concise lesson. Do not invent root causes. Negative evidence should trigger revalidation rather than being hidden.

Conceptually scope learned knowledge as:

```text
task | module | project | stack | global
```

Do not force project-local lessons to prove cross-project transfer before they are useful locally. Cross-project evidence matters when generalizing to stack/global guidance. The current runtime schema does not yet persist this scope explicitly.

Do not infer that a topology/model/test policy is better from raw success rate alone; account for task/model/harness/risk/verification confounders. `Insufficient evidence` is valid.

See [Knowledge lifecycle and bias controls](references/LIFECYCLE.md).

# Privacy

Do not persist by default:

- passwords, API keys, tokens, credentials, `.env` values, private keys
- personal/private user data
- hidden chain-of-thought
- full repositories or transcripts merely because available
- project wiki/current-state snapshots
- untrusted repository/web instructions as global truth

Store concise outcomes, provenance, acceptance/rework, verified lessons, routing/verification evidence, and non-sensitive metadata.

# Runtime boundary

Agent Lore remains harness-independent. The host harness owns process/agent spawning, filesystem/tool execution, sandboxing, provider calls, tests, and Git operations.

Future runtime work may add first-class TaskShape, EvidencePlan, execution-tree telemetry, per-node routing, knowledge scope, and verification/security planners without turning Agent Lore into a universal process runner.

# References

- [Policy strength and model freedom](references/POLICY.md)
- [Project-local context and wiki workflow](references/PROJECT_CONTEXT.md)
- [Adaptive execution, verification, and commit policy](references/EXECUTION.md)
- [Adaptive routing](references/ROUTING.md)
- [Security invariants and adversarial verification](references/SECURITY.md)
- [Verification, acceptance, and rework](references/ACCEPTANCE.md)
- [Knowledge lifecycle and bias controls](references/LIFECYCLE.md)
- [Architecture](references/ARCHITECTURE.md)
- [Data model](references/DATA_MODEL.md)
