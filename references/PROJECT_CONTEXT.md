# Project-local context interface

Agent Lore is cross-project, but **project truth belongs to each project**.

Agent Lore must not impose a repository layout, replace a project's `AGENTS.md`, or copy the project wiki/current state into the cross-project knowledge store.

## Goal

Avoid rebuilding the entire repository model from scratch for every task while respecting whatever structure the project already uses.

Normal startup:

```text
current user request
  -> discover/read project-owned instructions and current-state context
  -> inspect affected source/tests/contracts
  -> current model forms a working plan
  -> optionally retrieve narrowly scoped Agent Lore evidence
  -> execute + verify
```

Historical Agent Lore evidence is not required for every task.

## Semantic interface, not directory convention

Agent Lore reasons about semantic roles such as:

```text
agent_instructions  project-owned AGENTS.md/instruction files
current_state       current phase/features/known limitations
architecture        architecture/modules/boundaries
 decisions          ADRs/design decisions/specs
incidents           project-local incident/postmortem history
verification        tests/CI/evidence/status
security            project-specific assets/trust boundaries/invariants
```

A repository may map these roles however it wants.

Example A:

```text
AGENTS.md
docs/state.md
docs/architecture.md
docs/adr/
```

Example B:

```text
.ai/instructions.md
wiki/current.md
architecture/decisions/
postmortems/
```

Both are valid. Agent Lore should not rename or relocate them merely to fit a framework.

## Zero-config discovery

The preferred default is zero repository changes.

A capable host agent/harness may discover common project context from existing files such as:

- `AGENTS.md` and other host-native instruction files
- README / CONTRIBUTING / docs / wiki directories
- architecture/ADR/spec documents
- package/build manifests
- tests and CI workflows
- project-specific security documentation

Discovery produces a **runtime semantic view**, not a new repository structure.

A future/host implementation may persist local mappings under something like:

```text
~/.agent-lore/projects/<repo-id>.json
```

so one user's integration can remember where this project keeps its context without modifying the repository.

If a team explicitly wants to version-control this mapping, an optional `.agent-lore.json` may be supported. It must remain optional.

## Project `AGENTS.md` remains authoritative project context

Agent Lore's own `SKILL.md` does not replace project-local `AGENTS.md`.

Conceptual precedence:

```text
current user requirement
  ↓
project-owned instructions / ADRs / explicit constraints
  ↓
current source, tests, schemas, contracts, runtime evidence
  ↓
independently justified Agent Lore hard capability boundaries
  ↓
current-model judgment
  ↓
optional historical Agent Lore evidence
```

A project-specific instruction may be wrong or stale, so source/runtime verification still matters. Historical Agent Lore memory is never allowed to silently override project truth.

## What current-state material should contain

When a project chooses to maintain a wiki/current-state view, keep it compact and current. Useful semantic content includes:

- current phase/milestone
- completed / in-progress / next work
- major architecture/modules/boundaries
- implemented/partial/deprecated feature state
- important contracts/invariants
- known limitations/risks/issues
- meaningful recent architecture/feature changes

Do not turn it into a function-by-function repository dump or transcript.

Source code, tests, schemas, contracts, explicit ADRs/specs, and runtime behavior remain authoritative.

## Update timing

Update project-owned state only at meaningful checkpoints, for example:

- feature/module slice completed
- milestone/phase changed
- architecture/contract changed
- security/data invariant materially changed
- known limitation introduced/removed
- major migration/deprecation completed

Do not update project state for every small edit or child-agent completion.

Workers may suggest a `wiki_delta`; Main/Integrator owns coherent project-state updates.

## Freshness

Where practical, project state may record a source commit/checkpoint and per-module freshness hints.

A checkpoint older than `HEAD` does not automatically justify a full repository scan. Inspect the delta from the checkpoint and revalidate affected areas first.

## Full-repository review remains exceptional

Broaden to a whole-project audit/re-understanding when justified, including:

- first contact with no trustworthy project context
- materially stale/conflicting current-state docs
- major architecture/framework migration
- security incident with unknown blast radius
- ownership/dependency changes that invalidate module boundaries
- impact cannot be bounded with reasonable confidence
- explicit full-project review/audit request

A stronger future model may perform these audits more effectively, but the trigger is the project/risk condition, not the model name.

## End-of-checkpoint flow

```text
workers/current model complete scoped work
        ↓
Main integrates
        ↓
proportional deterministic verification
        ↓
meaningful checkpoint
        ├─ update project-owned current state if truth changed
        ├─ record run/telemetry in Agent Lore when available
        └─ record scoped reusable evidence only when warranted
```

Project progress/status remains in the project. Agent Lore stores cross-project-compatible run evidence, scoped historical cases, model/harness observations, and policy/guardrail state.

See `SIDECAR.md` and `MEMORY.md`.
