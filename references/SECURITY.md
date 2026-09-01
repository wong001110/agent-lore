# Security invariants and adversarial verification

Agent Lore treats security as a set of explicit invariants and trust boundaries, not as a generic instruction to "run a security scan".

The objective is to catch classes of failures that can remain functionally correct while leaking authority, private data, or control. Security depth must still be proportional to the change: unrelated attack families should not run merely because a security framework exists.

## Security gate model

For security-relevant work, define:

1. **Assets** — secrets, credentials, private data, identities, privileged tools, destructive capabilities.
2. **Trust boundaries** — user, tenant, project, agent, provider, origin, process, CI job, MCP/tool server, external network.
3. **Allowed flows** — which asset may move from which source to which sink under which condition.
4. **Invariants** — conditions that must remain true under stale state, retries, redirects, failures, concurrency, or untrusted inputs.

Example:

```text
Asset: OpenRouter API key
Trusted sink: https://openrouter.ai
Forbidden sinks: other providers, custom origins, logs, telemetry, browser bundles, unrelated projects
Invariant: the credential must never cross the OpenRouter trust boundary.
```

A passing functional test is not sufficient evidence for a security invariant.

## Security applicability and depth

Security is conditional. Derive applicable attack families from the change surface, trust boundaries, authority, blast radius, novelty, and failure cost.

Use adaptive depth:

```text
none
smoke
focused
deep
adversarial
```

Examples:

- UI copy/layout change -> normally `none`
- local input validation -> `smoke` or `focused` for relevant boundary cases
- provider/baseURL/credential change -> `focused` around origin/credential/log/retry flows
- auth/tenant/payment/MCP/agent-authority change -> `focused` to `deep`
- critical security architecture/release checkpoint -> `deep` or `adversarial`

Start with a few high-probability/high-impact attacks. Escalate attack variants and multi-step chains only when risk, novelty, findings, or residual uncertainty justify the cost.

Do not automatically run every security family for every change.

## Security verification sequence

```text
asset discovery
  -> trust-boundary model
  -> allowed flows
  -> explicit invariants
  -> applicable attack families
  -> smallest useful attack set
  -> canary leakage checks
  -> security-control mutation where useful
  -> enough evidence?
       yes -> stop
       no  -> escalate depth
```

High-impact invariant failure blocks delivery. Passing unrelated security tests does not compensate for an unverified applicable invariant.

## Reusable regression catalog

Baseline scenarios when applicable:

- `SEC-001 Provider Credential Isolation` — credentials for provider/origin A must not be sent to provider/origin B.
- `SEC-002 Cross-Origin Redirect Leakage` — redirects, proxy changes, scheme/host/port changes, retries/fallbacks must not carry credentials across an unauthorized origin.
- `SEC-003 Log/Error Secret Leakage` — secrets must not appear in stdout/stderr, structured logs, error objects, telemetry, traces, or crash reports.
- `SEC-004 Build Artifact Secret Leakage` — secrets must not appear in browser bundles, source maps, generated files, containers/layers, caches, packages, or build artifacts.
- `SEC-005 Repository/History Secret Leakage` — working tree, staged diff, patches, commits, and reachable history should be checked when credential exposure is plausible.
- `SEC-006 Cross-Context Isolation` — user/tenant/project/agent/session/provider/memory/cache context must not bleed into another context.
- `SEC-007 CI Untrusted-Code Secret Access` — untrusted PR/build code must not inherit deploy or repository secrets unless explicitly required and constrained.
- `SEC-008 Least-Privilege Credential Scope` — granted capability should not materially exceed required read/write/delete/admin scope.
- `SEC-009 Indirect Prompt Injection to Privileged Tool` — untrusted email/document/web/RAG/repository content must not silently cause privileged reads, writes, sends, or exfiltration.
- `SEC-010 MCP/Tool Poisoning` — tool descriptions, responses, changed metadata, or hidden arguments must not expand authority or exfiltrate data without policy checks.

Extend the catalog from validated failures/near-misses, not from speculation alone.

## Broader agentic attack families

When relevant, also consider:

- goal hijacking
- memory/context poisoning
- agent identity/impersonation
- inter-agent trust exploitation
- cascading multi-agent compromise
- approval/human-gate bypass
- excessive autonomy/authority
- denial-of-wallet/resource exhaustion
- skill/configuration poisoning
- tool permission escalation
- persistent prompt injection
- sandbox/host escape

These are not universal mandatory tests. Apply them when the changed system exposes the corresponding surface.

## Canary leakage testing

Use synthetic unique values instead of real credentials:

```text
CANARY_PROVIDER_A_8f2ac91
CANARY_PROJECT_A_912aa03
CANARY_USER_ALICE_f7201a
```

Inspect relevant observable sinks:

- outbound HTTP/tool requests
- stdout/stderr and application logs
- telemetry/traces/error reporting
- generated/build artifacts and source maps
- agent/tool arguments and model context when inspectable
- cache, memory, persistence, cross-project/session outputs

A canary found in an unauthorized sink is a security failure even when the feature otherwise works.

Do not use production secrets as canaries.

## Credential and origin binding

Treat a credential as part of a credential profile:

```text
CredentialProfile {
  provider
  origin/baseURL
  credential
  scope
}
```

Changing provider or trust origin must not silently retain authority. Known providers should prefer fixed/allowlisted origins. Request-layer checks should enforce the boundary even if UI state is stale or incorrect.

Applicable adversarial cases may include:

- hostname/subdomain change
- scheme/port change
- custom base URL
- redirects/redirect chains
- retry/fallback targets
- proxy changes
- stale persisted configuration
- provider switch without editing credential

## Cross-context isolation

Use distinct canaries for adjacent contexts:

```text
Project A -> CANARY_A
Project B -> CANARY_B
```

Exercise cache reuse, retries, cancellation, concurrency, session resume, agent delegation, RAG/memory retrieval, and tool calls when those mechanisms are in scope.

Seeing `CANARY_A` from Project B is a failure.

The same pattern applies to users, tenants, agents, sessions, providers, and other boundaries.

## Untrusted input to privileged action

For agentic systems:

```text
secret read permission != secret transmit permission
untrusted content != trusted instruction
```

When applicable, test hostile instructions embedded in repositories, issues, documents, web pages, emails, RAG content, tool descriptions, tool responses, memory, or inter-agent messages.

The objective is to verify that untrusted content cannot silently cause privileged reads/writes/sends or move protected data to an unauthorized sink.

## Permission differential testing

Compare required authority with granted authority:

```text
required: read one repository
actual token: repository admin + workflow write + delete
```

Flag materially excessive scope. For high-impact credentials, prefer narrow resources/actions, expiration, and independent rotation.

## Security-control mutation

Mutation testing is selective. Use it when an explicit security control is important enough to prove.

Examples:

- invert/remove an origin comparison
- remove credential clearing on provider change
- bypass tenant/user authorization
- disable secret redaction
- widen an allowlist
- enable credential forwarding across redirects
- remove agent/tool permission checks

If such a mutation survives, the security suite does not adequately prove the invariant.

Do not mutate production credentials or external systems. Use isolated fixtures.

## Failure-path testing

When relevant, exercise:

- timeout/retry
- malformed provider response
- 4xx/5xx
- connection reset/DNS/TLS failure
- cancellation/resume
- concurrency
- serialization/debug output
- partial initialization/stale state

Failure paths must not broaden authority or expose protected values.

## Red-team execution model

A Security Red-Team role is useful only when the risk warrants it.

Conceptual flow:

```text
Threat/Invariant model
        ↓
Attack planner
        ↓
small high-value attack set
        ↓
isolated execution
        ↓
invariant judge
        ↓
PASS -> stop when residual risk is acceptable
FAIL -> reproduce, fix, generate regression candidate
        ↓
optional attack mutation / chain escalation
```

The red-team should attempt to falsify invariants instead of merely reviewing implementation intent.

## Multi-step attack chains

For deep/adversarial checkpoints, allow bounded chains such as:

```text
poison repository/RAG content
 -> agent trusts instruction
 -> invokes tool/MCP
 -> reads protected data
 -> calls outbound sink
 -> exfiltration
```

Attack-chain depth and count must be budgeted. Do not run deep chains on unrelated low-risk changes.

## Continual security learning

A discovered incident/near-miss should enter a security-specific learning path:

```text
incident / escape
  -> established root cause
  -> attack/failure primitive
  -> generalized invariant
  -> regression candidate
  -> deterministic reproduction
  -> accepted/verified eval or pattern
```

Do not automatically promote internet/repository claims to permanent security lore. New tests require reproducible or otherwise strong validated evidence and must remain scoped to applicable contexts.

Track conceptual utility:

```text
Attack ROI = severity-weighted findings / execution cost
```

Use ROI to schedule optional attacks, but do not retire mandatory safety-critical invariants merely because they rarely fail.

## Recording security evidence

Record concise evidence, not secrets.

Good:

```text
SEC-001/002 passed with synthetic canaries; provider switch, cross-origin redirect, and retry target did not forward credentials.
```

Bad:

```text
Tested with production API key sk-...
```

Never persist real API keys, tokens, private keys, session cookies, or secret values into Agent Lore memory, reports, traces, prompts, or learned knowledge.

## Historical incident patterns

Historical incidents are prompts for adversarial thinking, not proof that a current project has the same vulnerability. Current repository evidence and deterministic verification remain authoritative.

See [Adaptive execution, verification, and commit policy](EXECUTION.md) for verification tiers, attack budgets, early stopping, batching, and checkpoint timing.
