# Architecture

Agent Lore v0.1 is intentionally small: a portable local SQLite catalog, a dependency-free CLI, and an Agent Skills instruction layer.

## Boundaries

```text
┌──────────────────────────────────────────────────────┐
│ Coding agent / harness                               │
│ Codex · DeepSeek Harness · Claude Code · others      │
└───────────────────────┬──────────────────────────────┘
                        │
                        │ SKILL.md workflow + CLI
                        ▼
┌──────────────────────────────────────────────────────┐
│ Agent Lore                                           │
│                                                      │
│ retrieve   record   stats   export/import   doctor   │
└───────────────────────┬──────────────────────────────┘
                        │
                        ▼
┌──────────────────────────────────────────────────────┐
│ ~/.agent-lore/                                       │
│                                                      │
│ agent-lore.db      structured operational data       │
│ knowledge/         future distilled local artifacts  │
│ traces/            optional future raw evidence      │
│ archive/           cold historical artifacts         │
│ exports/           portable snapshots                │
└──────────────────────────────────────────────────────┘
```

The Git repository contains the **learning engine and skill instructions**. The user's learned data lives outside the repository.

## V0.1 components

### 1. Skill layer

`SKILL.md` defines when and how an agent should use Agent Lore. It is deliberately opinionated about:

- historical evidence being advisory
- reducing anchoring before retrieval
- deterministic verification before LLM review
- selective recording
- privacy and untrusted provenance
- cross-project learning

### 2. Local CLI

`scripts/agent_lore.py` is the operational interface. V0.1 uses only the Python standard library so the skill can work without a package installation or network service.

Commands:

- `init` — create the local directory and schema
- `retrieve` — rank a small set of relevant active/candidate experiences
- `record` — save a run and optionally aggregate a reusable lesson
- `stats` — summarize observed model/agent task outcomes
- `export` — create a consistent SQLite backup and portable ZIP
- `import` — restore a portable snapshot with a safety backup
- `doctor` — inspect the local store

### 3. SQLite catalog

SQLite is an operational catalog, not a transcript dump. It stores:

- structured run metadata
- reusable experience summaries
- evidence/reuse counts
- model/agent outcome observations
- lifecycle fields

It does **not** need to contain complete source files, chain-of-thought, full terminal logs, or full conversations.

## Runtime flow

```text
Current task
    │
    ▼
inspect current project/state
    │
    ▼
tentative model-native plan
    │
    ▼
retrieve ≤ N historical experiences
    │
    ▼
applicability gate
    │
    ├─ irrelevant/stale ─> ignore
    │
    └─ useful evidence
            │
            ▼
        implementation
            │
            ▼
 deterministic verification
            │
            ▼
      record run outcome
            │
            ├─ no reusable lesson ─> stats only
            │
            └─ reusable lesson ─> candidate experience
```

## Retrieval philosophy

V0.1 does not use a vector database. That is deliberate.

The first version combines:

- token overlap with the current task
- exact task-type match
- language/framework/version match
- status
- confidence
- evidence count
- freshness

This keeps retrieval inspectable while the project validates whether external experience actually improves coding-agent performance. Embeddings can be added later if they produce measurable lift.

## Experience versus run

A **run** is an observation:

> A specific model/agent configuration attempted a task and produced an outcome.

An **experience** is a distilled reusable claim:

> Under a particular context, this lesson/failure/solution may be useful again.

One run does not automatically deserve an experience. Multiple runs may support the same experience.

## Cross-project scope

The local database is global to the user, not the current repository:

```text
Project A ─┐
Project B ─┼─> ~/.agent-lore/agent-lore.db
Project C ─┘
```

Project identifiers should be human-meaningful labels, usually the Git repository directory name. Do not store absolute filesystem paths by default.

## Agent/model independence

The learned layer should survive model replacement.

Record configuration dimensions independently:

```text
agent role
model
harness/runtime
reasoning/effort (later)
toolset (later)
```

Do not encode assumptions such as "the test worker is always Model X". Model selection is a later policy derived from observed task-conditioned performance.

## Not in v0.1

The following are architectural extension points, not current requirements:

### Knowledge lifecycle automation

```text
candidate → active → pattern/skill → deprecated/archive
```

### Model/capability router

```text
task fingerprint
      ↓
historical configuration outcomes
      ↓
cheapest configuration meeting quality threshold
```

### Multi-agent topology router

```text
single agent | flat parallel | lead/worker | sequential | challenger
```

### Challenge router

Challenge should be escalation, not a default second execution. A future policy should consider risk, uncertainty, historical conflict, failure cost, and challenge ROI.

### MCP/local daemon

A later daemon can expose operations such as:

```text
retrieve_experience
record_outcome
get_model_stats
recommend_agent_config
```

The CLI intentionally comes first so the learning model can be tested without infrastructure complexity.

### Cross-device sync

Future cross-device architecture may use a remote source of truth plus local cache/event synchronization. V0.1 only supports explicit portable export/import.

## Key success metric

Long term, the project should measure **Memory Lift**:

```text
Memory Lift = performance(with Agent Lore) - performance(model-only baseline)
```

A growing knowledge store is not success by itself. If memory-assisted performance is equal or worse, the retrieval/lifecycle policy must change even if the database contains many experiences.
