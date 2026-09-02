# Verification, Acceptance, and Rework

Agent Lore separates **execution success**, **technical verification**, and **acceptance**. A coding agent saying "done" is not enough evidence to teach the system that an approach is good.

## Three layers of correctness

```text
Execution outcome
  did the agent complete the attempted work?
        ↓
Verification outcome
  do deterministic checks / review support correctness?
        ↓
Acceptance outcome
  is the result actually acceptable for the task/product/user?
```

Examples:

- code compiles but tests fail → execution may be `success`, verification is `failed`
- tests pass but the UX is too complicated → verification `passed`, acceptance `rework`
- deterministic maintenance task fully passes objective acceptance criteria → acceptance may be `not-required`
- user reviews a product/UI change and approves it → acceptance `accepted`

## Run states

### Execution

Existing `outcome` values remain:

```text
success | failure | partial
```

This is an execution observation, not final delivery quality.

### Verification

```text
pending | passed | failed | not-required
```

Do not infer `passed` merely because a verification note exists. Record it explicitly.

### Acceptance

```text
pending | accepted | rework | rejected | invalidated | not-required
```

`pending` is the safe default for user-visible/product work.

Use `not-required` only when final acceptance is genuinely machine-verifiable and no human/product judgment is needed.

## Feedback CLI

When a user or reviewer accepts a run:

```bash
python scripts/agent_lore.py feedback <run-id> \
  --verdict accept \
  --reason "meets expected behavior"
```

When the implementation technically works but needs another attempt:

```bash
python scripts/agent_lore.py feedback <run-id> \
  --verdict rework \
  --reason "interaction has too many steps"
```

Other verdicts:

```text
reject
invalidate
```

Negative feedback flags linked knowledge as `needs_revalidation` instead of silently keeping it authoritative.

## Completing revalidation

Revalidation is an explicit, audited operation. First record a corrected run against the same knowledge, with successful execution, passed/not-required verification, and accepted/not-required acceptance. Then run:

~~~bash
python scripts/agent_lore.py revalidate <knowledge-id> \
  --run-id <corrected-run-id> \
  --reason "the corrected evidence resolves the prior failure" \
  --source reviewer
~~~

Agent Lore rejects unrelated, unverified, unsuccessful, or unaccepted runs. A successful revalidation clears needs_revalidation, refreshes last_verified_at, and records knowledge_revalidations evidence. It deliberately preserves deprecated/archived status.

## Rework lineage

A rework is not an unrelated task. Record the corrected attempt with:

```bash
python scripts/agent_lore.py record \
  --task "<same task>" \
  --parent-run-id <previous-run-id> \
  --outcome success \
  --verification-status passed \
  --acceptance-status accepted \
  --acceptance-source human
```

Agent Lore inherits the task group from the parent and increments `attempt_index`.

```text
Task group
├─ Attempt 1: tests passed, user requested rework
├─ Attempt 2: tests failed
└─ Attempt 3: tests passed, accepted
```

This enables metrics such as:

- first-pass acceptance rate
- rework count
- accumulated work time to accepted result
- cost to accepted result

## Learning policy

Execution success alone must not promote reusable knowledge.

Automatic lifecycle promotion requires accepted and verified evidence. A candidate can still preserve a useful failure or observation, but it should not become a strong reusable pattern merely because an agent produced code and tests happened to run.

If negative feedback contradicts an experience/pattern/skill:

```text
linked run rejected/reworked
        ↓
knowledge.needs_revalidation = true
        ↓
retrieval warning + lower ranking
        ↓
no automatic promotion/materialization
```

Do not automatically delete old evidence. Preserve the lineage so future revalidation can distinguish an outdated approach from an implementation-specific problem.

## Human feedback should stay lightweight

The intended user interaction is conceptually:

```text
Accept
Rework
Reject
```

A reason is useful for rework/rejection but should not become mandatory form-filling for every successful engineering task.

When an agent observes a clear user request such as "this is too complicated, redo it", it should treat that as rework feedback for the relevant prior run rather than recording the previous run as final success.

## Observed correction vs inferred lesson

Keep these separate:

```text
Observed:
user changed a modal flow into an inline interaction

User-provided reason:
too many steps

Possible inferred lesson:
prefer inline interaction here
```

The inferred lesson should not be promoted as global knowledge without further evidence.
