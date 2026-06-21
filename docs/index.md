---
hide:
  - navigation
  - toc
---

<div class="aae-hero" markdown="0">
  <div class="aae-hero__inner">
    <p class="aae-eyebrow">A2A extension <span>·</span> events/v1</p>
    <h1 class="aae-title">Subscribe to agents,<br><em>not URLs.</em></h1>
    <p class="aae-lede">
      Durable, AgentCard-native event subscriptions between A2A agents —
      explicit topics, a normative selector algebra, leases, opaque cursors,
      replay, and signed at-least-once delivery.
    </p>
    <div class="aae-actions">
      <a class="aae-btn aae-btn--primary" href="specification/">Read the specification</a>
      <a class="aae-btn" href="getting-started/">Get started</a>
    </div>
    <div class="aae-stream" role="img" aria-label="Events flowing from a publisher agent to a subscriber agent">
      <span class="aae-node aae-node--pub">publisher</span>
      <span class="aae-wire">
        <span class="aae-track" aria-hidden="true">
          <i class="aae-evt">&#8249;&#8250;</i><i class="aae-evt">&#8249;&#8250;</i><i class="aae-evt">&#8249;&#8250;</i><i class="aae-evt">&#8249;&#8250;</i><i class="aae-evt">&#8249;&#8250;</i><i class="aae-evt">&#8249;&#8250;</i><i class="aae-evt">&#8249;&#8250;</i><i class="aae-evt">&#8249;&#8250;</i><i class="aae-evt">&#8249;&#8250;</i><i class="aae-evt">&#8249;&#8250;</i><i class="aae-evt">&#8249;&#8250;</i><i class="aae-evt">&#8249;&#8250;</i><i class="aae-evt">&#8249;&#8250;</i><i class="aae-evt">&#8249;&#8250;</i><i class="aae-evt">&#8249;&#8250;</i><i class="aae-evt">&#8249;&#8250;</i><i class="aae-evt">&#8249;&#8250;</i><i class="aae-evt">&#8249;&#8250;</i><i class="aae-evt">&#8249;&#8250;</i><i class="aae-evt">&#8249;&#8250;</i>
        </span>
      </span>
      <span class="aae-node aae-node--sub">subscriber</span>
    </div>
  </div>
</div>

A2A Events is an A2A *extension*
(`https://example.com/a2a-events/extensions/events/v1`) built strictly on A2A
v1.0 primitives. A subscriber discovers a publisher through its real AgentCard
and subscribes to the agent — the publisher resolves delivery endpoints only
from that card. This site is the language-neutral source of truth: the
[specification](specification.md), JSON Schemas, conformance vectors, and guides.
The Python reference implementation lives in
[`a2a-events-python`](https://github.com/a2a-events/a2a-events-python).

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

See the [specification](specification.md) for the normative details and the
[Protocol Guide](protocol-guide.md) for a guided tour. The
[`a2a-events-python`](https://github.com/a2a-events/a2a-events-python) repo
implements all of the above and is the place to run code.
