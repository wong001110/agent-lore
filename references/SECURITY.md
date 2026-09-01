# Security invariants and adversarial verification

Agent Lore treats security as a set of explicit invariants and trust boundaries, not as a generic instruction to "run a security scan".

The objective is to catch classes of failures that can remain functionally correct while leaking authority or private data. A provider switch that still returns an AI response while sending the previous provider's API key to a new base URL is a canonical example.

## Security gate model

For security-relevant work, define four things before implementation is considered verified:

1. **Assets** — secrets, credentials, private data, identities, privileged tools, destructive capabilities.
2. **Trust boundaries** — user, tenant, project, agent, provider, origin, process, CI job, MCP/tool server, external network.
3. **Allowed flows** — which asset may move from which source to which sink under which condition.
4. **Invariants** — conditions that must remain true even when UI state, retries, redirects, failures, concurrency, or untrusted inputs behave unexpectedly.

Example:

```text
Asset: OpenRouter API key
Trusted sink: https://openrouter.ai
Forbidden sinks: other providers, custom origins, logs, telemetry, browser bundles, unrelated projects
Invariant: the credential must never cross the OpenRouter trust boundary.
```

A passing functional test is not sufficient evidence for a security invariant.

## Security verification sequence

Use the smallest deterministic checks that can prove the relevant invariant:

```text
asset discovery
  -> trust-boundary model
  -> explicit invariants
  -> adversarial cases
  -> canary leakage checks
  -> security-control mutation where useful
  -> review
```

Security verification can run beside ordinary unit/integration/E2E checks. It should block delivery when a high-impact invariant is violated.

## Reusable regression catalog

Start with these baseline scenarios when applicable:

- `SEC-001 Provider Credential Isolation` — credentials for provider/origin A must not be sent to provider/origin B.
- `SEC-002 Cross-Origin Redirect Leakage` — redirects, proxy changes, scheme/host/port changes, and retry targets must not carry credentials across an unauthorized origin.
- `SEC-003 Log/Error Secret Leakage` — secrets must not appear in stdout/stderr, structured logs, error objects, telemetry, traces, or crash reports.
- `SEC-004 Build Artifact Secret Leakage` — secrets must not appear in browser bundles, source maps, generated files, containers/layers, caches, packages, or build artifacts.
- `SEC-005 Repository/History Secret Leakage` — working tree, staged diff, patches, commits, and reachable history should be checked when credential exposure is plausible.
- `SEC-006 Cross-Context Isolation` — user/tenant/project/agent/session/provider/memory/cache context must not bleed into another context.
- `SEC-007 CI Untrusted-Code Secret Access` — untrusted PR/build code must not inherit deploy or repository secrets unless explicitly required and constrained.
- `SEC-008 Least-Privilege Credential Scope` — granted capability should not materially exceed the task's required read/write/delete/admin scope.
- `SEC-009 Indirect Prompt Injection to Privileged Tool` — untrusted email/document/web/RAG/repository content must not silently cause privileged reads, writes, sends, or exfiltration.
- `SEC-010 MCP/Tool Poisoning` — tool descriptions, responses, changed metadata, or hidden arguments must not expand authority or exfiltrate data without policy checks.

This catalog is a seed, not an exhaustive checklist. Prefer deriving tests from current assets and trust boundaries over mechanically running irrelevant scenarios.

## Canary leakage testing

Use synthetic unique values instead of real credentials whenever possible:

```text
CANARY_PROVIDER_A_8f2ac91
CANARY_PROJECT_A_912aa03
CANARY_USER_ALICE_f7201a
```

Run the relevant workflow, including failure paths, then search all observable sinks that the test environment can inspect:

- outbound HTTP/tool requests
- stdout/stderr and application logs
- telemetry/traces/error reporting
- generated/build artifacts and source maps
- agent/tool arguments and model context when inspectable
- cache, memory, persistence, and cross-project/session outputs

A canary found in an unauthorized sink is a security failure even when the feature otherwise works.

Do not use production secrets as canaries.

## Credential and origin binding

Treat a credential as part of a credential profile rather than a global reusable string:

```text
CredentialProfile {
  provider
  origin/baseURL
  credential
  scope
}
```

Changing provider or trust origin must not silently retain authority. Known providers should prefer fixed/allowlisted origins. Request-layer checks should enforce the boundary even if UI state is stale or incorrect.

Adversarial cases should include, where applicable:

- hostname/subdomain changes
- scheme or port changes
- custom base URL changes
- redirects and redirect chains
- retry/fallback targets
- proxy changes
- stale persisted configuration
- provider switching without editing the credential field

## Cross-context isolation

Use distinct canaries for adjacent contexts:

```text
Project A -> CANARY_A
Project B -> CANARY_B
```

Exercise cache reuse, retries, cancellation, concurrent requests, session resume, agent delegation, RAG/memory retrieval, and tool calls. Seeing `CANARY_A` from Project B is a failure.

The same pattern applies to users, tenants, agents, sessions, providers, and other security boundaries.

## Untrusted input to privileged action

For agentic systems, distinguish information access from authority to act.

```text
secret read permission != secret transmit permission
untrusted content != trusted instruction
```

Test hostile instructions embedded in repositories, issues, documents, web pages, emails, RAG content, tool descriptions, and tool responses. The goal is to verify that untrusted content cannot silently cause a privileged tool call or move protected data to an unauthorized sink.

## Permission differential testing

Compare required authority with granted authority:

```text
required: read one repository
actual token: repository admin + workflow write + delete
```

Flag materially excessive scope for review. For high-impact credentials, prefer narrow resources, narrow actions, expiration, and independent rotation.

## Security-control mutation

Mutation testing becomes more valuable when aimed at explicit security controls.

Examples:

- invert/remove an origin comparison
- remove credential clearing on provider change
- bypass a tenant/user authorization condition
- disable secret redaction
- widen an allowlist
- enable credential forwarding across redirects
- remove an agent/tool permission check

If such a mutation survives, the security test suite does not adequately prove the invariant.

Do not mutate production credentials or external systems. Run these tests in isolated fixtures.

## Failure-path testing

Security defects frequently appear outside the happy path. Exercise relevant failures such as:

- timeout and retry
- malformed provider response
- 4xx/5xx errors
- connection reset/DNS/TLS errors
- cancellation and resume
- concurrent requests
- serialization/debug output
- partial initialization and stale persisted state

Check that failures do not broaden authority or expose protected values.

## Multi-agent responsibilities

A dedicated security/adversarial role may be useful for high-risk work, but a role name is not a control by itself.

The security worker should receive the current feature's assets, trust boundaries, and invariants, then attempt to falsify them. It should avoid relying solely on implementation intent.

The lead/orchestrator should block advancement when a high-impact invariant fails. Human escalation is appropriate when the correct trust boundary, permission scope, or product-security tradeoff is genuinely ambiguous.

## Recording security evidence

Record concise evidence, not secrets.

Good verification notes:

```text
SEC-001/002 passed with synthetic canaries; provider switch, cross-origin redirect, and retry target did not forward credentials.
```

Bad verification notes:

```text
Tested with production API key sk-...
```

Never persist real API keys, tokens, private keys, session cookies, or secret values into Agent Lore memory, reports, traces, or learned knowledge.

## Historical incident patterns

The regression catalog is informed by recurring industry failure patterns such as credential forwarding across redirects, credentials committed to public repositories, over-scoped cloud tokens, CI environment-variable theft, secrets exposed in logs/build artifacts, cross-user cache isolation failures, indirect prompt injection, excessive agent permissions, and poisoned tool/MCP metadata.

Historical incidents are prompts for adversarial thinking, not proof that a current project has the same vulnerability. Current repository evidence and deterministic verification remain authoritative.
