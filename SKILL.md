---
name: agent-lore
description: Local-first bilingual continual learning, adaptive execution/routing, proportional verification, security-invariant guidance, and project-context workflow for coding agents. Use it to reuse accepted engineering evidence, choose the smallest useful single/multi-agent topology, reason about task DAGs and recursive delegation, plan risk-proportional verification/security, preserve rework/revalidation lineage, and learn from outcomes without replacing current-model judgment.
license: MIT
metadata:
  author: wong001110
  version: "0.8.2-alpha"
  compatibility: Requires Python 3.10+ with SQLite support and local filesystem access. Network access is not required. Adaptive recommendations require the host coding agent/harness to execute the selected plan.
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
  --task-canonical "<optional English canonical summary>" \
  --project "<project>" \
  --module "<module>" \
  --type "<task family>" \
  --subtype "<task subtype>" \
  --language "<language>" \
  --framework "<framework>" \
  --framework-version "<version if known>" \
  --limit 5
```

Preserve original-language text. When the host can safely provide an English canonical form, store/query both forms; Agent Lore performs no hidden translation or network call. Native CJK bigram matching remains available as a local fallback.

Retrieval is not adoption and does not increment reuse. After the host decides whether retrieved evidence actually informed the work, it may record that decision explicitly:

~~~bash
python "<agent-lore-skill-root>/scripts/agent_lore.py" usage <knowledge-id> \
  --decision applied \
  --run-id <optional-run-id> \
  --reason "<optional concise context>" \
  --source "<host or reviewer label>"
~~~

Use `--decision ignored` to retain a neutral audit event when evidence was considered but not used. Ignoring knowledge must not reduce utility by itself; current constraints and model judgment may legitimately favor another approach.

The recommend CLI accepts host-reasoned TaskShape and EvidencePlan JSON, produces DAG execution waves and modern coordination/schedule/depth output, and retains coarse routing hints for compatibility:

~~~bash
python "<agent-lore-skill-root>/scripts/agent_lore.py" recommend \
  --task "<task summary>" \
  --task-shape-json "@task-shape.json" \
  --evidence-plan-json "@evidence-plan.json"
~~~

Repository evidence and model judgment should produce these inputs; the CLI validates and operationalizes them rather than pretending coarse labels are ground truth.

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

If the host exposes actual agent topology, attach it after recording the run:

~~~bash
python "<agent-lore-skill-root>/scripts/agent_lore.py" agents record <run-id> \
  --manifest-json "@agents.json"
python "<agent-lore-skill-root>/scripts/agent_lore.py" agents show <run-id>
~~~

This ledger is optional observational telemetry, not a runner contract. It must not decide how agents spawn, delegate, select models/tools, or verify work. Use `capture_status=complete` only for a complete in-manifest tree; use `partial` when the host can expose only some nodes. Missing telemetry remains `not-collected` and is not evidence of single-agent execution. Generated reports default to English and render genuinely uncollected values as `-`; keep `Pending` and `N/A` explicit, and preserve stored source text in its original language.

When a recorded run already has host-observed `model` or `harness`, `agents record` fills only missing values in its agent rows from that run. A manifest value always wins. Agent specialization is never guessed. Reports include per-run telemetry coverage and flag complete trees with optional metadata omitted as an observability follow-up only; this never blocks execution, changes topology, or becomes a verification gate.

`report` defaults to a bounded rolling summary (recent detail plus all-history aggregates). Use `--full` only for a deliberate historical export. `--format html` writes a self-contained static dashboard with local table filtering; it starts no server and never loads remote assets.

User-visible/product/UX/architecture work normally remains acceptance-pending until relevant human/reviewer feedback. A corrected attempt should preserve rework lineage with --parent-run-id.

When corrected evidence belongs to existing knowledge but its lesson wording changed or should not be repeated, link it explicitly during recording:

~~~bash
python "<agent-lore-skill-root>/scripts/agent_lore.py" record \
  --task "<corrected attempt>" \
  --knowledge-id <knowledge-id> \
  --parent-run-id <previous-run-id> \
  --outcome success \
  --verification-status passed \
  --acceptance-status accepted
~~~

`--knowledge-id` must reference existing knowledge and establishes evidence lineage without relying on lesson-text equality. It does not rewrite the stored lesson or bypass revalidation eligibility. Verification techniques remain host-selected and proportional to the current task.

After negative feedback, clear a knowledge hold only with a linked run that is successful, verified, and accepted:

~~~bash
python "<agent-lore-skill-root>/scripts/agent_lore.py" revalidate <knowledge-id> \
  --run-id <accepted-verified-run-id> \
  --reason "<why the new evidence resolves the concern>" \
  --source reviewer
~~~

Revalidation is audited and does not silently reactivate deprecated or archived knowledge.

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

The current runtime accepts first-class host-supplied TaskShape/EvidencePlan data, returns bounded execution guidance, and can store an optional after-the-fact execution tree. Future work may add repository-derived planning, per-node routing, knowledge scope, and richer verification/security planners without turning Agent Lore into a universal process runner.

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
