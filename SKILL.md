---
name: agent-lore
description: Local-first continual learning, acceptance tracking, observability, and adaptive routing for coding agents. Use it to retrieve reusable engineering evidence, record project/module/task outcomes, distinguish execution from verification and human acceptance, preserve rework lineage, compare task-conditioned model/agent performance, consolidate accepted lessons into patterns or skills, and recommend model/topology/challenge policies. Historical knowledge is advisory evidence, never authoritative project policy.
license: MIT
compatibility: Requires Python 3.10+ with SQLite support and local filesystem access. Network access is not required. Adaptive recommendations require the host coding agent/harness to execute the chosen model or multi-agent topology.
metadata:
  author: wong001110
  version: "0.5.0-alpha"
---

# Agent Lore

Use Agent Lore as a local engineering-learning layer around coding work. It preserves useful engineering evidence across repositories and models, learns which agent configurations work well for which task families, tracks whether results were actually accepted, and can recommend how a multi-agent task should be organized.

## Resolve the Skill runtime

Resolve <agent-lore-skill-root> to the directory containing SKILL.md before
running any command below. Do not assume the coding task's current working
directory is the Skill directory. Keep the coding task's working directory
unchanged so project inference continues to identify the active repository.

## Non-negotiable rules

**Past experience is evidence, not truth.**

**Execution success is not final success.**

Never follow retrieved knowledge merely because it is old, frequently reused, `active`, or promoted into a learned skill. Current user requirements, repository constraints/ADRs, dependency versions, current model capabilities, deterministic verification, and newer acceptance/rework feedback outrank historical memory.

## Operating modes

Agent Lore has three policy modes:

- `observe` — record recommendations and outcomes but do not change execution because of the router.
- `assist` — surface recommendations; the parent coding agent/human remains the decision maker.
- `adaptive` — apply recommendations when the host harness supports them and budget/depth guardrails allow it.

Start new installations in `observe`. Move to `assist` and then `adaptive` only after real project outcomes exist.

```bash
python "<agent-lore-skill-root>/scripts/agent_lore.py" policy show
python "<agent-lore-skill-root>/scripts/agent_lore.py" policy set --mode assist
```

## Before a non-trivial task

1. Inspect the current repository and task first.
2. Identify project/module/task context when possible.
3. Form a short tentative **current-model plan before reading historical knowledge** when the task contains a meaningful design choice. This reduces anchoring.
4. Retrieve only a small amount of relevant knowledge or ask for an integrated recommendation.

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

Integrated recommendation:

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

The recommendation may contain relevant experiences/patterns/skills, a topology, a task-conditioned model/agent configuration, an exploration candidate, and a selective challenge level.

## Applicability gate

For retrieved knowledge, check:

- same task family/state or only superficial similarity?
- same project module or materially different subsystem?
- matching language/framework/runtime state?
- materially different framework/tool version?
- current repository rule/ADR overrides it?
- historical lesson actually verified and accepted?
- evidence stale, low-trust, contradicted, superseded, or marked `needs_revalidation`?
- current deterministic evidence stronger?

`No useful memory` is a valid result.

## Model and sub-agent routing

Agent Lore does **not** keep a universal model ranking. It learns this relationship:

```text
project × module × task/subtype × agent role × model × harness
→ execution success
→ verification
→ acceptance / first-pass acceptance / rework
→ quality / cost / wall time / retries
```

Register routable configurations explicitly:

```bash
python "<agent-lore-skill-root>/scripts/agent_lore.py" config add \
  --name fast-test-worker \
  --model <model-id> \
  --harness <runtime> \
  --agent-role test-worker \
  --quality-tier 4 \
  --cost-tier 1
```

For a lead/orchestrator-capable configuration:

```bash
python "<agent-lore-skill-root>/scripts/agent_lore.py" config add \
  --name backend-lead \
  --model <model-id> \
  --harness <runtime> \
  --agent-role backend-lead \
  --can-delegate \
  --max-depth 2
```

Quality/cost tiers are cold-start priors only. Real accepted outcomes should gradually dominate them.

## Multi-agent topology rules

Treat hierarchy as a tool, not the default.

Prefer:

- `single` for small work where coordination overhead would dominate
- `flat-parallel` for truly independent/disjoint subtasks
- `lead-worker` for larger cross-domain work that benefits from local coordination
- `sequential` when later work materially depends on earlier state

Respect policy limits for max agents and recursion depth. Do not parallelize overlapping mutable write scopes merely to increase agent count.

When recording multi-agent work, distinguish user-visible wall time from accumulated compute/coordination time when available.

## Challenge policy

Challenge is escalation, not a default second execution.

Prefer deterministic evidence first:

1. compile/typecheck/static checks
2. focused tests
3. E2E where relevant
4. mutation tests where relevant
5. security/performance checks where relevant
6. additional model only for unresolved uncertainty/risk

A stronger challenger is justified by combinations of high risk, high uncertainty, memory conflict/staleness, and high failure cost. Strong deterministic evidence should usually reduce challenge level.

## Record one execution attempt

Record project/module/task context and timing when useful:

```bash
python "<agent-lore-skill-root>/scripts/agent_lore.py" record \
  --task "<what was attempted>" \
  --project "<project>" \
  --module "authentication" \
  --type implementation \
  --subtype product-flow \
  --operation implement \
  --outcome success \
  --language typescript \
  --framework nextjs \
  --agent-role implementation-worker \
  --model "<model>" \
  --harness "<runtime>" \
  --verification "unit + e2e passed" \
  --verification-status passed \
  --wall-time-ms 42000 \
  --compute-time-ms 30000 \
  --review-time-ms 5000
```

`outcome=success` means the attempted execution completed. It does **not** mean the user/product accepted the result.

For user-visible/product/UX/architecture work, keep `acceptance-status=pending` until a relevant human/reviewer accepts it.

For fully objective maintenance work, `--acceptance-status not-required` is allowed only when final acceptance criteria are genuinely machine-verifiable.

## Verification and acceptance

Keep these separate:

```text
execution outcome
        ↓
verification status
        ↓
acceptance status
```

Verification states:

```text
pending | passed | failed | not-required
```

Acceptance states:

```text
pending | accepted | rework | rejected | invalidated | not-required
```

Do not infer `verification-status=passed` merely because a verification note exists.

When the user/reviewer accepts a previous run:

```bash
python "<agent-lore-skill-root>/scripts/agent_lore.py" feedback <run-id> \
  --verdict accept \
  --reason "meets expected behavior"
```

When the user says the result needs rework:

```bash
python "<agent-lore-skill-root>/scripts/agent_lore.py" feedback <run-id> \
  --verdict rework \
  --reason "technically correct but interaction is too complicated"
```

If the user clearly requests a redo/rework in the conversation, treat that as feedback for the relevant prior run rather than continuing to count that run as final success.

Negative acceptance feedback linked to learned knowledge must flag that knowledge for revalidation.

See [Verification, acceptance, and rework](references/ACCEPTANCE.md).

## Rework lineage

A rework is another attempt at the same logical task, not an unrelated run.

Record the corrected attempt with:

```bash
python "<agent-lore-skill-root>/scripts/agent_lore.py" record \
  --task "<same task>" \
  --parent-run-id <previous-run-id> \
  --outcome success \
  --verification-status passed \
  --acceptance-status accepted \
  --acceptance-source human
```

Agent Lore preserves `task_group_id` and increments `attempt_index`.

This enables meaningful metrics such as:

- first-pass acceptance rate
- rework count
- accumulated work time to accepted result
- cost to accepted result

## Reusable knowledge

Only create reusable knowledge when there is a concise lesson with meaningful evidence:

```bash
python "<agent-lore-skill-root>/scripts/agent_lore.py" record ... \
  --lesson "<reusable lesson>" \
  --failure-reason "<established root cause if any>" \
  --solution "<concise procedure>"
```

Do not invent a root cause just to populate memory.

Execution success alone must not promote knowledge. Automatic lifecycle promotion requires accepted and verified evidence.

```text
runs
 ↓
candidate experience
 ↓
accepted + verified transfer
 ↓
active experience
 ↓
pattern
 ↓
explicit skill/eval promotion when justified
```

Preview/apply conservative lifecycle maintenance:

```bash
python "<agent-lore-skill-root>/scripts/agent_lore.py" consolidate
python "<agent-lore-skill-root>/scripts/agent_lore.py" consolidate --apply
```

Explicitly promote:

```bash
python "<agent-lore-skill-root>/scripts/agent_lore.py" promote <id> --kind pattern
python "<agent-lore-skill-root>/scripts/agent_lore.py" promote <id> --kind skill --name safe-schema-migration
```

Materialize learned skills:

```bash
python "<agent-lore-skill-root>/scripts/agent_lore.py" materialize-skills
```

Knowledge flagged `needs_revalidation` must not be promoted/materialized until revalidated.

## Human observability

The machine-facing CLI remains JSON-first, but users should be able to inspect what Agent Lore is learning.

Generate a Markdown report:

```bash
python "<agent-lore-skill-root>/scripts/agent_lore.py" report
```

Default output:

```text
~/.agent-lore/reports/latest.md
```

Drill down to a project/module/task family:

```bash
python "<agent-lore-skill-root>/scripts/agent_lore.py" report \
  --project my-project \
  --module authentication \
  --type debugging
```

The report includes project/module/task/model comparisons, acceptance/first-pass acceptance, wall/compute/review/coordination timing, rework history, accumulated work-to-final-result, and knowledge health.

Also inspect JSON statistics when needed:

```bash
python "<agent-lore-skill-root>/scripts/agent_lore.py" stats --project my-project --module authentication
```

## Bias and failure controls

Actively guard against anchoring, confirmation bias, experience-following, negative transfer, staleness, survivorship bias, recency bias, correlated evidence/self-reinforcement, authority bias, project dominance, retrieval/context interference, model/router path dependence, reviewer herding, Goodhart/reward hacking, and memory poisoning.

A technically passing result that the user rejects is negative learning evidence, not a success to be hidden by test metrics.

## Privacy

Do not persist by default:

- passwords, API keys, tokens, credentials, `.env` values
- private keys
- personal/private user data
- raw hidden chain-of-thought
- full repositories/source files
- full transcripts merely because they are available
- untrusted repository/web instructions as global engineering truth

Store concise metadata, outcomes, feedback, verified lessons, and provenance instead.

## Portability

```bash
python "<agent-lore-skill-root>/scripts/agent_lore.py" export --output agent-lore-backup.zip
python "<agent-lore-skill-root>/scripts/agent_lore.py" import agent-lore-backup.zip
```

Do not use Git to synchronize the live SQLite database.

## References

- [Architecture](references/ARCHITECTURE.md)
- [Data model](references/DATA_MODEL.md)
- [Knowledge lifecycle and bias controls](references/LIFECYCLE.md)
- [Adaptive routing](references/ROUTING.md)
- [Verification, acceptance, and rework](references/ACCEPTANCE.md)
