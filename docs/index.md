---
hide:
  - navigation
  - toc
---

# A2A Events

<p style="font-size:1.25rem;max-width:46rem">
  AgentCard-native durable event subscriptions for the
  <a href="https://a2a-protocol.org">A2A protocol</a>.
  <strong>Subscribe to agents, not URLs.</strong>
</p>

A2A Events lets one A2A agent subscribe to another agent's future events using
AgentCard discovery, explicit topics, selectors, leases, durable cursors,
acknowledgements, replay, and signed delivery. It is an A2A *extension*
(`https://example.com/a2a-events/extensions/events/v1`), built strictly on
A2A v1.0 primitives.

This site is the **language-neutral source of truth** for the protocol — the
[specification](specification.md), JSON Schemas, conformance vectors, and docs.
The Python reference implementation lives in
[`a2a-events-python`](https://github.com/a2a-events/a2a-events-python).

[Read the Specification](specification.md){ .md-button .md-button--primary }
[Get Started](getting-started.md){ .md-button }

## Start here

<div class="grid cards" markdown>

-   :material-book-open-variant:{ .lg .middle } **Introduction**

    ---

    What A2A Events is, the problem it solves, the "subscribe to agents, not
    URLs" model, and how it relates to A2A core.

    [:octicons-arrow-right-24: Introduction](introduction.md)

-   :material-map-legend:{ .lg .middle } **Protocol Guide**

    ---

    A wire-level tour: discovery, the subscription lifecycle, topics &
    selectors, cursors, the event envelope, delivery, ack/replay, and the
    method surface.

    [:octicons-arrow-right-24: Protocol Guide](protocol-guide.md)

-   :material-rocket-launch:{ .lg .middle } **Getting Started**

    ---

    Run the full flow in code: in-memory first, then over HTTP, then across
    containers.

    [:octicons-arrow-right-24: Getting Started](getting-started.md)

-   :material-file-document-outline:{ .lg .middle } **Specification**

    ---

    The complete normative spec — the JSON-RPC surface, selector algebra,
    security model, delivery semantics, and error model.

    [:octicons-arrow-right-24: Specification](specification.md)

</div>

## What's in the protocol

- **Canonical JSON-RPC surface** — the `a2a.events.*` methods (`ListTopics`,
  `Subscribe`, `GetSubscription`, `ListSubscriptions`, `RenewSubscription`,
  `DeleteSubscription`, `Replay`, `Ack`, `ListDeliveryAttempts`) with opaque
  keyset cursors, plus an optional 1:1 HTTP+JSON binding and a gRPC binding.
- **AgentCard discovery & trust** — subscribers are resolved from their real A2A
  AgentCard; delivery endpoints come **only** from the card, under a configurable
  trust policy (HTTPS-only, same-origin, allowlist, AgentCard signature
  verification, domain-ownership challenge).
- **Durable subscriptions** — explicit topics, the normative selector algebra,
  leases with renewal, opaque per-topic cursors, replay, and at-least-once
  delivery with explicit/implicit ack.
- **Signed delivery** — Ed25519 (EdDSA) over the RFC 8785 (JCS) canonical event,
  with signing-key rotation via JWKS.
- **Security model** — control-plane authentication and topic authorization
  evaluated at both subscribe and delivery time, per-subscription delivery
  tokens, SSRF guards, and timestamp-skew rejection.
- **Operability** — retention compaction, a durable retry architecture, and an
  observability/metrics model.

See the [Specification](specification.md) for the normative details and the
[Protocol Guide](protocol-guide.md) for a guided tour. The
[`a2a-events-python`](https://github.com/a2a-events/a2a-events-python) repo
implements all of the above and is the place to run code.
