# Introduction to A2A Events

> **Subscribe to agents, not URLs.**

A2A Events is an [A2A protocol](https://a2a-protocol.org) extension
(`https://example.com/a2a-events/extensions/events/v1`) that lets one agent durably
subscribe to another agent's future events — using AgentCard discovery, explicit
topics, selectors, leases, durable cursors, acknowledgements, replay, and signed
delivery. It is built strictly on A2A v1.0 primitives and adds no new transport.

This page is the conceptual on-ramp. For the wire-level details see the
[Protocol Guide](protocol-guide.md); to run code see
[Getting Started](getting-started.md); for the normative specification see
[the specification](https://a2a-events.github.io/a2a-events/specification/).

---

## The problem

A2A gives agents a way to *call* each other: an agent fetches another agent's
AgentCard, discovers its endpoints, and sends it a message or task. A2A core
also has **push notifications**, but those are **task-scoped** — they tell you
about the progress of one task you already started.

What A2A core does not give you is a way for Agent A to say:

> "Agent B, tell me whenever *anything of kind X* happens to you from now on —
> and keep telling me reliably, even across restarts, even if I miss some."

That is a **durable, topic-scoped subscription**, and it is what most real
multi-agent systems eventually need: an orchestrator watching a fleet of worker
agents, an indexer following a registry agent's discoveries, a monitor reacting
to another agent's state changes. People usually bolt this on with an external
message broker (Kafka, NATS, a webhook queue), which means the subscription
lives *outside* the A2A trust and discovery model — separate auth, separate
endpoints, separate identity.

A2A Events keeps the subscription *inside* the A2A model.

## The core idea: subscribe to an agent, by its card

In A2A Events you never hardcode a delivery URL or a broker topic. You point at
the **other agent's AgentCard** and the protocol does the rest:

1. **Discovery.** The publisher fetches the subscriber's AgentCard, finds its
   A2A Events extension declaration (`role: subscriber`), and reads the delivery
   endpoint *from the card* — never from a client-supplied URL. This is what
   makes delivery trustworthy and SSRF-resistant.
2. **Subscription.** The subscriber creates a subscription to one or more
   **topics**, optionally narrowed by a **selector**, with a **lease** (a TTL it
   must renew) and a starting **cursor**.
3. **Delivery.** When the publisher emits an event on that topic, it delivers a
   **signed** CloudEvent to the subscriber — either as a canonical A2A message
   (`a2a.SendMessage`) or as a webhook — and tracks per-subscription progress.
4. **Durability.** Cursors, acks, and delivery attempts are persisted, so a
   subscriber that was offline can **replay** missed events, and a publisher that
   restarted still knows every live subscription.

Because identity, discovery, and authorization all flow through the AgentCard,
"who is allowed to receive this" and "where does it get delivered" are answered
by the same trusted artifact you already use to talk to the agent.

## A 30-second mental model

| Concept           | One-liner                                                              |
| ----------------- | ---------------------------------------------------------------------- |
| **Topic**         | A named stream of events on the publisher (the routing key).           |
| **Selector**      | An optional server-side filter narrowing a topic to events you want.   |
| **Subscription**  | A subscriber's standing interest in topic(s), with a lease + cursor.   |
| **Lease**         | A TTL on the subscription; the subscriber renews it or it expires.     |
| **Cursor**        | An opaque, ordered position in a topic — how progress and replay work. |
| **Event**         | A signed CloudEvent envelope carrying your payload + routing metadata. |
| **Delivery mode** | How events reach you: an A2A message, or a webhook POST.               |
| **Ack**           | Confirmation a delivery was processed (advances the cursor).           |
| **Replay**        | Re-reading a topic from an earlier cursor to recover missed events.    |

The lifecycle in one line:

```
discover card → subscribe (topic + selector + lease) → receive signed events
            → ack → renew lease → (replay if you fell behind) → delete
```

## How it relates to A2A core

A2A Events is **additive** and reuses A2A's own machinery wherever possible:

- **Discovery** is the A2A AgentCard, with one extra `AgentExtension` entry.
- **Delivery** is plain A2A `a2a.SendMessage` (or a webhook), not a new channel.
- **Card authenticity** uses A2A's `AgentCardSignature` (JWS over JCS) — A2A
  Events does not invent its own card-signing scheme.
- **Transports** are A2A's transports: JSON-RPC is canonical, with optional
  HTTP+JSON and gRPC bindings that map 1:1 to the same methods.
- **Errors** are JSON-RPC 2.0 error objects, like A2A core.

What A2A Events *adds* on top is the subscription control plane (`a2a.events.*`
methods), the durable event store and cursors, the signed event envelope, and
the security model around delivery (topic authorization, per-subscription
delivery tokens, SSRF guard, timestamp-skew rejection).

It is **not** a general-purpose message bus and does not try to replace Kafka or
NATS — see [§36 of the design](https://a2a-events.github.io/a2a-events/specification/#36-why-this-is-not-just-pubsub-with-a2a-branding)
for why the AgentCard-native framing is the point, not the payload format.

## What's in the box

This repository is a reference implementation in Python (`a2a_events`) that
covers the full protocol surface:

- the canonical `a2a.events.*` JSON-RPC methods, plus HTTP+JSON and gRPC bindings;
- A2A-message and webhook delivery, in-memory and over HTTP;
- durable event and subscription stores (in-memory and Postgres) so state
  survives a publisher restart;
- Ed25519 signed delivery over RFC 8785 (JCS) with signing-key rotation;
- AgentCard discovery + trust policy, topic authorization, and per-subscription
  delivery tokens;
- a durable retry queue + worker, retention compaction, rate limiting, keyset
  pagination, observability metrics, and client-side automatic lease renewal.

Continue to the [Protocol Guide](protocol-guide.md) for how these pieces work on
the wire, or [Getting Started](getting-started.md) to run a publisher and
subscriber locally.
