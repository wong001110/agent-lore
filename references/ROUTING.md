# Adaptive Routing

Phase 4 chooses **how work should be organized**, **which registered agent configuration is a good fit**, and **whether an additional challenge is worth its cost**.

## 1. Topology router

### `single`

Use for small or tightly coupled work where delegation overhead would dominate.

### `flat-parallel`

Use when multiple subtasks are genuinely independent/disjoint. Avoid when workers will modify overlapping mutable state or mostly wait on each other.

### `lead-worker`

Use for larger cross-domain tasks where a local lead can manage scoped workers. Requires:

- policy depth >= 2
- enough agent budget
- a registered `can_delegate` configuration
- host runtime support for nested delegation

### `sequential`

Use when later work materially depends on earlier state, such as schema → API → E2E.

Cold-start topology is heuristic. With enough matching runs, historical outcomes can override the heuristic if the evidence is strong.

## 2. Agent/model configuration router

The router ranks only explicitly registered configurations.

Cold start uses:

```text
quality_tier
cost_tier
priority
```

These are user-supplied priors, not benchmark claims.

Observed history gradually contributes:

```text
success rate
quality score
cost
latency
retries
sample count/confidence
```

Task context narrows observations by task type/language/framework/role where available.

## 3. Exploration

Without exploration, a previously successful model can keep receiving every task and new models never collect evidence.

Policy contains an `exploration_rate` (default 0.10). Agent Lore may emit an under-sampled exploration candidate in deterministic slots.

Preferred use:

```text
normal task → current best config
             + optional new config in shadow
```

For high-risk production work, do not replace the primary path with an unproven exploration candidate merely to gather data.

## 4. Challenge router

Inputs:

```text
risk
uncertainty
cost of failure
memory conflict
memory staleness
deterministic evidence
```

Outputs:

```text
none
self-check
cheap-challenger
strong-challenger
```

Challenge is capped by policy. Strong deterministic evidence normally reduces challenge level unless the task is critical.

## 5. Modes

### Observe

Recommendation is logged only. Use this to collect baseline data safely.

### Assist

Recommendation is surfaced to the parent agent/human. The host decides whether to follow it.

### Adaptive

The recommendation can be applied automatically when the host supports the requested topology/configuration and local guardrails allow it.

## 6. Feedback

Every `recommend` returns a `decision_id`.

The execution should later record:

```bash
python scripts/agent_lore.py record ... --route-decision-id <id>
```

This lets Agent Lore compare recommendation history with real outcomes instead of optimizing an unobserved proxy.

## 7. Effective cost

Do not optimize sticker price alone.

A useful conceptual objective is:

```text
Effective cost
= inference cost
+ retries
+ reviewer/challenger cost
+ failure recovery
+ coordination overhead
```

The current alpha records the observable pieces and uses a transparent weighted score rather than a trained router.

## 8. Guardrails

Recommended defaults:

```text
mode: observe
max_depth: 2
max_agents: 6
max_challenge_level: 3
exploration_rate: 0.10
```

Keep topology and routing decisions inspectable until real-world data proves a more complex policy produces positive lift.
