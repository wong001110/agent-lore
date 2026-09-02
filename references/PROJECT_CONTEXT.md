# Project-local context and wiki workflow

Agent Lore does not store project wikis. Each project owns its own current-state documentation inside that project/repository.

This workflow borrows the useful idea of an AI-maintained project wiki, but it does **not** require the OpenWiki product/service or any extra AI API key. The current coding agent maintains the project-local context directly.

## Purpose

Avoid rebuilding the entire repository model from scratch for every task.

Normal startup:

```text
new task
  -> read project-local current-state/wiki docs
  -> read relevant Agent Lore evidence
  -> inspect only affected source/tests/contracts
  -> execute
```

Do not rescan the whole repository by default when a trustworthy current-state view already exists.

## Project-local ownership

The wiki/current-state material belongs only to that project.

```text
Project A
  repo source
  project-local wiki/state

Project B
  repo source
  project-local wiki/state

Agent Lore
  reusable engineering evidence only
  no copied Project A/B wiki
```

Agent Lore should neither mirror nor synchronize project wiki content into its own knowledge store.

## What the project wiki should contain

Keep it compact and current. Typical sections:

- current phase/milestone
- completed, in-progress, next work
- major architecture/modules and important boundaries
- implemented/partial/deprecated feature status
- important contracts/invariants
- known limitations/risks/issues
- recent meaningful architecture/feature changes

Do not turn the wiki into a function-by-function repository dump or a transcript of every edit.

Source code, tests, schemas, contracts, explicit ADRs/specs, and runtime behavior remain authoritative. If wiki and source conflict, verify source and repair the wiki.

## Update timing

Update project-local wiki/state at meaningful checkpoints, for example:

- feature/module slice completed
- milestone/phase status changed
- architecture or important contract changed
- security/data invariant materially changed
- a known limitation was introduced/removed
- a major migration/deprecation completed

Do not update the wiki for every small edit, style tweak, or child-agent completion.

## Main/Integrator ownership

Workers may return a small `wiki_delta` in their handoff, but the Main/Integrator owns the coherent project-state update after integration.

Example:

```yaml
wiki_delta:
  completed:
    - provider credential isolation
  architecture_changes:
    - credentials are now bound to provider/origin profiles
  known_limitations:
    - custom-provider redirect policy remains pending
```

Avoid several parallel workers editing the same project-state document without clear ownership.

## Freshness and targeted revalidation

When practical, project state may record a source commit/checkpoint and per-module freshness hints.

A wiki checkpoint older than current HEAD does not automatically require a full-repo scan. First inspect the delta from the documented checkpoint to current state and revalidate affected areas.

## Full-repository re-analysis is exceptional

Broaden to full-repo or architecture-wide re-analysis when justified, such as:

- first contact with a repository that has no trustworthy project state
- wiki/current-state documentation is materially stale or contradicts source
- major architecture/framework migration
- security incident with unknown blast radius
- module/dependency ownership changed substantially
- task impact cannot be bounded with reasonable confidence
- user explicitly requests a complete audit/re-understanding

Otherwise prefer targeted source inspection.

## End-of-checkpoint flow

```text
workers complete scoped work
        ↓
Main integrates
        ↓
proportional verification
        ↓
meaningful checkpoint
        ├─ update project-local wiki/state if current truth changed
        └─ record only reusable engineering evidence in Agent Lore if warranted
```

Project progress/status remains in the project. Agent Lore learns reusable engineering lessons, routing outcomes, verification value, and rework evidence—not project status snapshots.
