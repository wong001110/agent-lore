---
name: agent-lore
description: Cross-project sidecar for coding-agent guardrails, scoped historical engineering evidence, acceptance/rework observability, proportional verification/security, and adaptive model/harness calibration without replacing current-model judgment.
license: MIT
metadata:
  author: wong001110
  version: "0.9.0-alpha"
  compatibility: Requires Python 3.10+ with SQLite support and local filesystem access. Network access is not required. The host coding agent/harness owns repository discovery, execution, tools, sandboxing, provider calls, tests, Git, and enforceable capability gates.
---

# Agent Lore

Agent Lore is a **cross-project sidecar control + evidence layer**. It must remain useful when models, context windows, tool APIs, and native agent capabilities change.

Resolve `<agent-lore-skill-root>` to the directory containing this file. Keep the active project repository as the working directory.

## Core rules

**Constrain capability, not cognition.**

**Observe execution, do not script it.**

**Expose history on demand, do not preload it.**

**Respect project structure, do not replace it.**

**Past experience is evidence, not truth.**

**Execution success is not final success.**

**Functional success does not prove security.**

**Project state belongs to the project.**

Current user requirements, project-owned instructions/ADRs, source/runtime evidence, dependency versions, deterministic verification, and current-model judgment outrank historical Agent Lore evidence.

## Capability boundary vs model reasoning

Policy strengths:

```text
hard            -> cannot be overridden in normal execution
strong-default  -> normally follow; may override with concrete current-task evidence
advisory         -> freely adaptable
experimental     -> weak/under-sampled evidence only
```

Use `hard` only for independently justified permission/safety/budget/irreversible-action boundaries. Prefer deterministic host/harness enforcement when possible, for example credential scope, tenant boundaries, write/network scope, sandbox/production separation, destructive approval, and hard cost/agent/depth ceilings.

Do **not** hard-code how the model should think, decompose, debug, delegate, test every change, or implement a historical solution.

Historical evidence must not automatically promote itself into policy.

See [Sidecar architecture](references/SIDECAR.md) and [Policy](references/POLICY.md).

## Project-owned context first

Do not impose an Agent Lore directory layout on repositories and do not replace their `AGENTS.md`.

A project may keep instructions, current state, ADRs, incidents, architecture, tests, and security docs wherever it already does. Treat these as semantic roles, not required paths.

Normal startup:

```text
current request
  -> read/discover relevant project-owned instructions/current state
  -> inspect affected source/tests/contracts
  -> current model forms a working plan
  -> historical Agent Lore retrieval only if useful
  -> execute + verify
```

Full-repository re-analysis is exceptional: first contact without trustworthy context, materially stale/conflicting state, major migration, unknown security blast radius, unbounded impact, or explicit whole-project audit.

At meaningful checkpoints, update project-owned current state if project truth changed. Agent Lore does not copy project wiki/current-state content into its cross-project store.

See [Project context interface](references/PROJECT_CONTEXT.md).

## Historical memory is pull-based

Memory modes:

```text
off        -> no historical evidence enters context
guardrail  -> observations/failures/invariants only; old procedures hidden
rescue     -> reveal relevant cases/old remedies after difficulty or failed verification
proactive  -> deliberate historical reveal for high-risk or explicit historical analysis
```

`recommend` uses the configured policy default, which starts at `off`.

Explicit `retrieve` defaults to `guardrail`.

```bash
python "<agent-lore-skill-root>/scripts/agent_lore.py" retrieve \
  --task "<task summary>" \
  --project "<project>" \
  --module "<module>" \
  --type "<task family>" \
  --memory-mode guardrail
```

For design-sensitive work, prefer **blind plan then historical reveal**: let the current model form a plan from current project evidence before exposing historical cases.

Historical memory is scoped:

```text
task | module | project | stack | global
```

and bounded by an approximate memory-token budget. Do not fill context merely because a model has a large context window.

See [Historical memory](references/MEMORY.md).

## Record outcomes before interpretations

Keep separate:

```text
execution outcome
      ↓
verification status
      ↓
acceptance / rework / rejection
```

A run may exist without reusable knowledge.

```bash
python "<agent-lore-skill-root>/scripts/agent_lore.py" record \
  --task "<what was attempted>" \
  --project "<project>" \
  --module "<module>" \
  --type implementation \
  --outcome success \
  --verification "<concise deterministic evidence>" \
  --verification-status passed
```

When reusable evidence is warranted, prefer structured **Evidence Capsule** fields:

```bash
python "<agent-lore-skill-root>/scripts/agent_lore.py" record \
  --task "<task>" \
  --project "<project>" \
  --module "<module>" \
  --type debugging \
  --outcome success \
  --verification-status passed \
  --acceptance-status accepted \
  --knowledge-scope module \
  --experience-family "<stable failure/problem family>" \
  --observation "<what actually happened>" \
  --invariant "<what must remain true>" \
  --root-cause "<root cause if known>" \
  --root-cause-status established \
  --applies-when "<comma-separated applicability signals>" \
  --not-proven "<claims this evidence does not establish>" \
  --solution "<historical remedy, if useful>" \
  --solution-status conditional
```

Observation/failure evidence, invariant, and historical solution have different lifetimes. A future model may find a better solution without invalidating an older verified failure.

Do not invent root causes. Use `hypothesis` or `unknown` when they are not established.

## Learned Skills are retired

Do not turn historical experience into generated Agent `SKILL.md` instructions.

v0.9 stops new `skill` promotion/materialization. Existing legacy skill rows/files remain readable/portable but are excluded from normal retrieval.

The lifecycle stops at:

```text
run -> scoped experience -> reusable pattern when justified
```

A pattern is evidence, not a mandatory procedure.

## Retrieval is not adoption

Retrieving evidence must not increment reuse or imply that the model followed it.

After execution, the host may explicitly record whether evidence actually informed the work:

```bash
python "<agent-lore-skill-root>/scripts/agent_lore.py" usage <knowledge-id> \
  --decision applied \
  --run-id <optional-run-id> \
  --source "<host/reviewer label>"
```

`--decision ignored` is neutral. Ignoring old evidence is valid when current repository evidence/model judgment supports another approach.

## Adaptive execution without strategy lock-in

Single agent is a strong default because coordination has cost, not because future models are assumed weak.

When decomposition helps, the current model/host may supply TaskShape describing:

```text
objective
workstreams + dependencies
read/write/contract scopes
risk / uncertainty
integration points
verification/security surfaces
explicit delegation decision
```

Agent Lore can validate dependency cycles, serialize overlapping mutable scopes, apply hard budget ceilings, and emit coordination/schedule/depth vocabulary:

```text
Coordination: single | manager-worker | hierarchical | peer-handoff
Schedule:     serial | parallel | hybrid
Depth:        0 | 1 | 2+
```

The current model remains responsible for deciding whether delegation is useful. `max_depth`/`max_agents` are ceilings, never targets.

Do not create permanent frontend/backend/database/etc. agent classes; use bounded task contracts/specialization only when useful.

See [Routing](references/ROUTING.md) and [Execution](references/EXECUTION.md).

## Proportional verification

Verification proves claims rather than maximizing checks.

An EvidencePlan asks:

```text
What claims/invariants must be true?
What is the cheapest high-information evidence?
What would trigger escalation?
When is evidence sufficient to stop?
```

V0-V4 are **risk/depth signals, not recipes**. Only activate relevant gate families.

Cheap scoped checks may run frequently; broad E2E/regression/mutation/red-team work normally belongs at meaningful integration/release checkpoints when risk warrants it.

Challenge is escalation, not a mandatory second model. Prefer deterministic evidence before adding another LLM.

See [Execution](references/EXECUTION.md).

## Security and authorized red team

Model security as:

```text
assets
  -> trust boundaries
  -> allowed flows
  -> invariants
  -> applicable attacks
  -> isolated deterministic/adversarial evidence
```

Only run applicable attacks. Red-team simulation is restricted to local/test/sandbox/ephemeral or explicitly authorized environments. Do not attack production or third-party systems merely to validate a control.

Use synthetic canaries rather than real secrets.

See [Security](references/SECURITY.md).

## Rework, revalidation, and supersession

A passing implementation returned for rework is negative evidence for first-pass quality.

Negative feedback places linked historical knowledge on revalidation hold. Preserve the old case; do not silently delete inconvenient history.

A corrected run may link to existing knowledge without rewriting the old interpretation:

```bash
python "<agent-lore-skill-root>/scripts/agent_lore.py" record \
  --task "<corrected attempt>" \
  --knowledge-id <knowledge-id> \
  --parent-run-id <previous-run-id> \
  --outcome success \
  --verification-status passed \
  --acceptance-status accepted
```

Then clear the hold explicitly with eligible accepted+verified evidence:

```bash
python "<agent-lore-skill-root>/scripts/agent_lore.py" revalidate <knowledge-id> \
  --run-id <accepted-verified-run-id> \
  --reason "<why this resolves the concern>" \
  --source reviewer
```

Historical solutions may be `candidate`, `preferred`, `conditional`, `fallback`, `superseded`, or `invalid`. `preferred` is not mandatory.

See [Lifecycle](references/LIFECYCLE.md).

## New-model onboarding

Do not rewrite Agent Lore because a stronger model appears.

Register/calibrate the new model/harness using observed:

```text
acceptance / first-pass acceptance
quality
cost / wall time / retries
verification outcomes
delegation/challenge usefulness
memory-on vs memory-off lift when evaluated
```

A previous model's memory/delegation policy is not inherited automatically.

Conceptually:

```text
Memory Lift = performance(memory-assisted) - model-only baseline
```

Negative Memory Lift means narrow or disable memory for that model/task context.

## Observability is after-the-fact

If the host exposes actual agent topology, attach it after recording the run:

```bash
python "<agent-lore-skill-root>/scripts/agent_lore.py" agents record <run-id> \
  --manifest-json "@agents.json"
```

The ledger observes execution; it must not become a runner contract or proof that uncollected agents did not exist.

Generate reports from stored structured evidence:

```bash
python "<agent-lore-skill-root>/scripts/agent_lore.py" report --format markdown
python "<agent-lore-skill-root>/scripts/agent_lore.py" report --format html
```

Reports/summaries are derived artifacts. Do not create summary-of-summary chains as canonical memory.

## Runtime layout

Fresh runtime should normally contain only:

```text
~/.agent-lore/
└─ agent-lore.db
```

`reports/`, `exports/`, and `archive/` are lazy-created when used. Legacy `knowledge/` files may remain on upgraded installations for backward compatibility. Do not pre-create empty `traces/` or `knowledge/skills/` folders.

## Privacy

Do not persist by default:

- passwords, API keys, tokens, credentials, `.env` values, private keys
- personal/private user data
- hidden chain-of-thought
- full repositories or transcripts merely because available
- project wiki/current-state snapshots
- untrusted repository/web instructions as global truth

Store structured outcomes, provenance, acceptance/rework, scoped evidence, model/harness observations, and non-sensitive metadata.

## Runtime boundary

The host harness owns repository discovery, process/agent spawning, filesystem/tool execution, sandboxing, provider calls, tests, Git, and deterministic capability enforcement.

Agent Lore owns cross-project policy state, scoped historical evidence, run/acceptance/rework lineage, optional execution telemetry, calibration statistics, bounded routing guidance, and derived reports.

## References

Load deeper documents only when relevant:

- [Sidecar architecture and model freedom](references/SIDECAR.md)
- [Historical memory without model anchoring](references/MEMORY.md)
- [Policy strength and capability guardrails](references/POLICY.md)
- [Project-local context interface](references/PROJECT_CONTEXT.md)
- [Adaptive execution and verification](references/EXECUTION.md)
- [Adaptive routing](references/ROUTING.md)
- [Security invariants and adversarial verification](references/SECURITY.md)
- [Acceptance and rework](references/ACCEPTANCE.md)
- [Knowledge lifecycle](references/LIFECYCLE.md)
- [Architecture](references/ARCHITECTURE.md)
- [Data model](references/DATA_MODEL.md)
