# Agent Lore

**Local-first continual learning for coding agents.**

Agent Lore turns verified coding-agent outcomes into reusable engineering experience across projects, models, and agent roles. The foundation model remains replaceable; the learned engineering evidence stays local and portable.

> Status: **experimental / v0.1 foundation**. The first milestone intentionally focuses on local learning, retrieval, evidence capture, portability, and model-performance observations before adaptive routing or cloud sync.

## Why

Coding agents repeatedly rediscover the same failure modes. A project-local memory can reduce repetition inside one repository, but it does not preserve engineering lessons across projects or across different coding agents.

Agent Lore adds a local learning layer:

```text
Project A ─┐
Project B ─┼─> Coding Agent ─> Agent Lore ─> reusable evidence
Project C ─┘                      │
                                 ├─ experiences
                                 ├─ failures / solutions
                                 ├─ model + agent observations
                                 └─ later: patterns / skills / routing
```

The goal is not to make historical memory authoritative. **Past experience is evidence, not truth.** Current project constraints, current framework versions, deterministic verification, and the current model's reasoning remain first-class inputs.

## Design principles

- **Local-first** — operational data lives under `~/.agent-lore/` by default.
- **Cross-project** — one local knowledge store can learn from many repositories.
- **Agent/model agnostic** — Codex, DeepSeek Harness, Claude Code, or another compatible agent can contribute to and reuse the same local evidence.
- **Evidence over authority** — retrieved experience is advisory and may be stale, mismatched, or wrong.
- **Selective memory** — do not turn every tool call or transcript into active knowledge.
- **Privacy by default** — store concise metadata and lessons; do not persist secrets or raw source code by default.
- **Portable** — export a consistent snapshot to move the local learning state to another device manually.
- **Measurable** — retain task/model/agent outcome metadata so later versions can learn which configurations are cost-effective for which tasks.

## Repository layout

```text
agent-lore/
├─ SKILL.md                    # Agent Skills entry point
├─ scripts/
│  └─ agent_lore.py            # dependency-free local CLI
├─ references/
│  ├─ ARCHITECTURE.md
│  ├─ DATA_MODEL.md
│  └─ LIFECYCLE.md
├─ tests/
│  └─ test_smoke.py
├─ LICENSE
└─ README.md
```

User data is deliberately kept outside the repository:

```text
~/.agent-lore/
├─ agent-lore.db
├─ knowledge/
├─ traces/
├─ archive/
└─ exports/
```

Set `AGENT_LORE_HOME` to override this location.

## Install as an Agent Skill

Agent Lore follows the open Agent Skills `SKILL.md` format. Install or copy this repository as an `agent-lore` skill directory in the location supported by your agent client.

For DeepSeek Harness, a project-level installation can be placed at:

```text
<project>/.agents/skills/agent-lore/
```

Other Agent Skills clients should use their documented project or user skill location.

Then initialize the local store:

```bash
python scripts/agent_lore.py init
```

No network service or external Python package is required for the v0.1 CLI.

## CLI

Initialize:

```bash
python scripts/agent_lore.py init
```

Retrieve related experience before a non-trivial coding decision:

```bash
python scripts/agent_lore.py retrieve \
  --task "add a safe PostgreSQL enum migration" \
  --type migration \
  --language typescript \
  --framework prisma
```

Record a verified run and, when useful, a reusable lesson:

```bash
python scripts/agent_lore.py record \
  --task "change user-role enum without breaking existing rows" \
  --type migration \
  --outcome success \
  --language typescript \
  --framework prisma \
  --model deepseek-v4-flash \
  --agent-role implementation-worker \
  --verification "migration test + e2e passed" \
  --lesson "Prefer transitional enum migrations when existing rows depend on legacy values" \
  --solution "add transitional value, migrate data, then remove legacy value"
```

Inspect observed model/agent outcomes:

```bash
python scripts/agent_lore.py stats
```

Create a consistent portable snapshot:

```bash
python scripts/agent_lore.py export --output agent-lore-backup.zip
```

Restore it on another device:

```bash
python scripts/agent_lore.py import agent-lore-backup.zip
```

## v0.1 scope

Included now:

- local SQLite knowledge catalog
- cross-project experience retrieval
- verified run/outcome recording
- basic duplicate aggregation
- model/agent performance observations
- portable export/import
- privacy and provenance rules

Intentionally deferred:

- automatic pattern → skill promotion
- embeddings/vector database
- autonomous challenge routing
- adaptive model routing
- multi-agent topology routing
- MCP/local daemon
- cross-device synchronization
- cloud database/object storage

Those are later layers only after the core question is measurable: **does retrieved engineering experience improve future agent outcomes without degrading current-model judgment?**

## Learning model

```text
Agent run
   ↓
verification
   ↓
run evidence
   ↓
reusable lesson? ── no ──> statistics only
   │
  yes
   ↓
candidate experience
   ↓
reuse + revalidation
   ↓
active experience
   ↓
later: pattern / skill / eval / archive
```

See [`references/LIFECYCLE.md`](references/LIFECYCLE.md) for the intended knowledge lifecycle and anti-bias rules.

## License

MIT
