# Protocol Guide

A guided tour of the A2A Events wire protocol: discovery, the subscription
lifecycle, selectors, the event envelope, delivery modes, cursors/replay/ack,
the method surface, and the error and security model.

This is an introduction, not the normative spec — where this guide and
[the specification](https://a2a-events.github.io/a2a-events/specification/) disagree, the design wins. Section references like
(§14) point into the design.

---

## 1. Discovery — the AgentCard extension (§12)

A2A Events rides on the A2A AgentCard. A subscriber advertises that it can
*receive* events by adding one `AgentExtension` to its card's
`capabilities.extensions`:

```jsonc
{
  "capabilities": {
    "extensions": [
      {
        "uri": "https://example.com/a2a-events/extensions/events/v1",
        "params": {
          "role": "subscriber",
          "receiveUrl": "https://agent-a.example.com/a2a-events/receive",
          "acceptedDeliveryModes": ["a2a-message", "webhook"]
        }
      }
    ]
  }
}
```

A publisher advertises the same extension with `role: publisher` (and its
subscription endpoint). **All A2A Events configuration lives in
`params`** — the extension never redefines core AgentCard fields.

The crucial rule: when a subscriber subscribes, the publisher resolves the
delivery endpoint **only from the subscriber's card**, fetched fresh and
optionally trust-checked (HTTPS-only, same-origin, allowlist, card signature,
or a domain-ownership challenge — see [§21](https://a2a-events.github.io/a2a-events/specification/#21-security-model)). A
client cannot hand the publisher an arbitrary URL to deliver to; this is the
foundation of the SSRF guard.

## 2. Topics and selectors (§11)

A **topic** is the authoritative routing key — a named stream of events on the
publisher. Topics are declared by the publisher and discoverable via
`a2a.events.ListTopics`. A topic carries its own policy:

| Field              | Meaning                                              |
| ------------------ | ---------------------------------------------------- |
| `name`             | The routing key (e.g. `agent_card.discovered`).      |
| `retentionSeconds` | How long events stay replayable (default 7 days).    |
| `replay`           | Whether replay is offered for this topic.            |
| `selectorTypes`    | Which selector kinds the topic supports.             |
| `filterableFields` | Which payload fields a `field_filter` may reference. |
| `deliveryModes`    | Which delivery modes are allowed.                    |

A **selector** is an *optional* server-side filter that narrows a topic to the
subset of events a subscriber actually wants. Two kinds are defined:

```jsonc
// field_filter — match on declared filterable fields (OR within a field).
{ "type": "field_filter", "where": { "data.capabilities": ["streaming"] } }

// keyword_search — match keywords across fields, all/any.
{ "type": "keyword_search", "keywords": ["code", "review"], "match": "all" }
```

Topic vs selector is a deliberate split: **the topic decides routing,
retention, and authorization; the selector only filters within a topic.** A
selector can never widen what a subscription sees beyond its topics. Selectors
are also size-bounded (§22) so a subscriber cannot push an unboundedly
expensive filter onto the publisher.

## 3. The subscription lifecycle (§14)

A subscription is a subscriber's standing interest in one or more topics. Its
lifecycle:

```
Subscribe ──> active ──(RenewSubscription)──> active ──> ... ──> DeleteSubscription
                 │                                  │
                 └── lease lapses without renew ────┴──> expired
```

**Subscribe** (`a2a.events.Subscribe`) takes the subscriber's card URL, the
topics, an optional selector, a delivery preference, a starting cursor, and a
requested lease:

```jsonc
{
  "subscriberCardUrl": "https://agent-a.example.com/.well-known/agent-card.json",
  "topics": ["agent_card.discovered"],
  "selector": { "type": "field_filter", "where": { "data.capabilities": ["streaming"] } },
  "delivery": { "mode": "a2a-message" },
  "fromCursor": "latest",        // or "earliest", or a specific cursor
  "leaseSeconds": 3600
}
```

The result is a `Subscription` with a server-assigned `subscriptionId`, a
`leaseUntil` timestamp, and — when delivery tokens are enabled — a
per-subscription bearer token under `delivery.auth` that the publisher will
present on every delivery.

**Leases.** A subscription is only live while its lease is valid. The subscriber
must call `RenewSubscription` before `leaseUntil`; the spec recommends renewing
once 50–70% of the lease has elapsed. Let the lease lapse and the subscription
becomes `expired` and stops receiving events. (The reference implementation
ships an `AutoLeaseRenewer` that does this for you.)

**Delete** (`a2a.events.DeleteSubscription`) ends a subscription immediately.

Because subscriptions, cursors, acks, and delivery attempts are persisted in a
durable `SubscriptionStore`, the **publisher holds no subscription state in
memory** — it survives a restart and still knows every live subscription.

## 4. Cursors (§10.9)

A **cursor** is an opaque, ordered position within a topic. Concretely it is the
topic name plus a monotonic offset, e.g.:

```
agent_card.discovered:0000000000000043
```

Cursors are how progress and recovery work. You treat them as opaque tokens; the
ordering guarantee is per-topic. The two reserved positions `"earliest"` and
`"latest"` let you start a subscription (or a replay) at the start of retention
or at the live head. A monotonic per-topic offset counter guarantees that even
after retention compaction physically deletes old events, an offset is **never
reused**, so a cursor a subscriber holds never silently points at the wrong
event.

## 5. The event envelope (§16)

Delivered events are **CloudEvents 1.0** JSON with an `a2aevents` extension
block carrying the routing metadata:

```jsonc
{
  "specversion": "1.0",
  "id": "evt_01HY8Z2V1ZF9B5M7A4N9D3E8GH",
  "source": "a2a://agent-b.example.com",
  "type": "org.example.a2a.agent_card.discovered.v1",
  "subject": "agent-card/https%3A%2F%2Fnew-agent.example.com%2F...",
  "time": "2026-06-19T20:30:00Z",
  "datacontenttype": "application/json",
  "data": { "cardUrl": "https://new-agent.example.com/...", "capabilities": ["streaming"] },
  "a2aevents": {
    "extension": "https://example.com/a2a-events/extensions/events/v1",
    "publisherCardUrl": "https://agent-b.example.com/.well-known/agent-card.json",
    "topic": "agent_card.discovered",
    "cursor": "agent_card.discovered:0000000000000043",
    "subscriptionId": "sub_01HY8Y5K3N7V4Z9WHE4RYMZG5G",
    "deliveryAttempt": 1,
    "traceId": "trace_01HY8Z3NQ8N9ZDE6R0V7M4T2C2"
  }
}
```

Required: `specversion`, `id`, `source`, `type`, `time`, `datacontenttype`,
`data`, and `a2aevents.{extension, publisherCardUrl, topic, cursor}`.
Recommended: `subject`, `a2aevents.{schemaUrl, subscriptionId, traceId}`.

**`topic` vs `type`:** `a2aevents.topic` is the authoritative routing key —
conformant implementations route on it. CloudEvents `type` is a descriptive
discriminator (typically a versioned reverse-DNS string) used for payload-schema
dispatch, **never** for routing. One topic can carry multiple `type`s over time
as a payload schema evolves.

## 6. Delivery modes (§18)

A subscriber chooses how events reach it via `delivery.mode`:

- **`a2a-message`** (canonical) — the publisher calls `a2a.SendMessage` on the
  subscriber's A2A endpoint with a `Message` (`role: ROLE_AGENT`) whose
  `DataPart` carries the CloudEvent. This is plain A2A core messaging; no new
  channel.
- **`webhook`** — the publisher POSTs the CloudEvent to the subscriber's
  `receiveUrl` (`POST /a2a-events/receive`).

Either way the endpoint comes from the subscriber's AgentCard (§1), and the
event is **signed** (§8 below). Delivery itself is *not* an `a2a.events.*`
method — it reuses A2A core messaging.

## 7. Delivery semantics, ack, and replay (§19, §20)

A2A Events is **at-least-once**. Each delivery advances toward an acknowledged
position:

- **Ack** (`a2a.events.Ack`) confirms a cursor was processed. Acks can be
  explicit (the subscriber calls `Ack`) or implicit (a successful synchronous
  delivery counts). The per-topic acked cursor is the subscriber's durable
  high-water mark.
- **Retries.** A failed delivery is retried with exponential backoff. With the
  optional durable `RetryQueue` + `RetryWorker`, a failed delivery is persisted
  with a `next_retry_at` and retried *off* the publish path, so a crash
  mid-retry never loses the event. Exhausted retries are **dead-lettered**.
- **Replay** (`a2a.events.Replay`) re-reads a topic from an earlier cursor
  (`earliest`, or any cursor within retention), so a subscriber that was offline
  or fell behind can recover missed events. Replay is bounded by the topic's
  `retentionSeconds`.

Because delivery is at-least-once, subscribers should treat events
**idempotently** — dedupe on `id`. (The reference receiver does this for you.)

## 8. Security model (§21)

Security is layered and all of it hangs off the AgentCard:

- **Card trust (§21.2).** Delivery endpoints are resolved only from the
  subscriber's card, optionally gated by a `CardTrustPolicy` (HTTPS-only,
  same-origin, domain-allowlist, A2A `AgentCardSignature` verification, or an
  out-of-band domain-ownership challenge). An **SSRF guard** rejects endpoints
  that resolve to loopback/private addresses (`DELIVERY_ENDPOINT_BLOCKED`).
- **Topic authorization (§21.4).** A `TopicAuthorizer` decides who may subscribe
  to which topic, evaluated **both at subscribe time and at delivery time** — so
  revoking a grant stops *future* deliveries, not just new subscriptions.
  Denials surface as `TOPIC_NOT_AUTHORIZED`.
- **Delivery tokens.** The publisher mints a per-subscription bearer token,
  returns it under `delivery.auth` at subscribe time, and presents it on every
  delivery; the receiver authenticates incoming events against it. A tampered or
  missing token blocks delivery (and dead-letters it).
- **Signed events (§21.3).** Every event is signed with **Ed25519 (EdDSA)** over
  the **RFC 8785 (JCS)** canonical form of the full envelope, including
  ECMAScript-correct number serialization. Subscribers fetch publisher public
  keys from a **JWKS** endpoint by `kid`, with support for key rotation
  (pre-publish the next key, activate, retire). Subscribers also **reject
  timestamp-skewed** events to bound replay windows.

## 9. The method surface (§29)

JSON-RPC is the canonical transport. Method names use the `a2a.events.*`
namespace, mirroring A2A core's `a2a.*`. The optional HTTP+JSON binding maps each
method 1:1; an optional gRPC binding does the same over `grpc.aio`.

| Operation              | JSON-RPC method (canonical)       | HTTP+JSON (optional)                            |
| ---------------------- | --------------------------------- | ----------------------------------------------- |
| List topics            | `a2a.events.ListTopics`           | `GET /a2a-events/topics`                        |
| Create subscription    | `a2a.events.Subscribe`            | `POST /a2a-events/subscriptions`                |
| Get subscription       | `a2a.events.GetSubscription`      | `GET /a2a-events/subscriptions/{id}`            |
| List subscriptions     | `a2a.events.ListSubscriptions`    | `GET /a2a-events/subscriptions`                 |
| Renew subscription     | `a2a.events.RenewSubscription`    | `POST /a2a-events/subscriptions/{id}:renew`     |
| Delete subscription    | `a2a.events.DeleteSubscription`   | `DELETE /a2a-events/subscriptions/{id}`         |
| Replay events          | `a2a.events.Replay`               | `POST /a2a-events/subscriptions/{id}:replay`    |
| Ack event              | `a2a.events.Ack`                  | `POST /a2a-events/subscriptions/{id}:ack`       |
| List delivery attempts | `a2a.events.ListDeliveryAttempts` | `GET /a2a-events/subscriptions/{id}/deliveries` |

List methods return an opaque keyset `nextPageToken` for pagination. Every
request carries the `A2A-Extensions` header and authenticates via the
publisher's A2A `securitySchemes`. **Delivery** (publisher → subscriber) is not
in this namespace — it is A2A `a2a.SendMessage` or the webhook (§6).

## 10. The error model (§30)

Errors are **JSON-RPC 2.0 error objects**. The numeric `code` is a JSON-RPC
code; the symbolic A2A Events code and structured details ride in `data`:

```jsonc
{
  "jsonrpc": "2.0",
  "id": "1",
  "error": {
    "code": -32010,
    "message": "Topic agent.deleted does not exist.",
    "data": { "code": "TOPIC_NOT_FOUND", "topic": "agent.deleted" }
  }
}
```

Protocol errors use the `-32000..-32099` server-error range (and the standard
JSON-RPC codes where applicable). The HTTP+JSON binding maps them to HTTP status
(404 for `TOPIC_NOT_FOUND`, 401/403 for auth failures, 429 for `RATE_LIMITED`,
…). Symbolic `data.code` values include `TOPIC_NOT_FOUND`,
`TOPIC_NOT_AUTHORIZED`, `INVALID_SELECTOR`, `INVALID_CURSOR`, `CURSOR_EXPIRED`,
`SUBSCRIPTION_NOT_FOUND`, `SUBSCRIPTION_EXPIRED`, `SIGNATURE_INVALID`,
`RATE_LIMITED`, `LEASE_TOO_LONG`/`LEASE_TOO_SHORT`, and the delivery/card codes —
see [§30](https://a2a-events.github.io/a2a-events/specification/#30-error-model) for the full list.

---

## Putting it together

```
1. Subscriber publishes an AgentCard with the events extension (role: subscriber).
2. Subscriber calls a2a.events.Subscribe(topic, selector, delivery, lease).
3. Publisher fetches + trust-checks the card, resolves the delivery endpoint,
   authorizes the topic, mints a delivery token, persists the subscription.
4. Publisher.publish(topic, type, data) → signed CloudEvent → delivered to the
   subscriber (a2a-message or webhook), retried/dead-lettered on failure.
5. Subscriber verifies signature (JWKS), dedupes on id, processes, acks.
6. Subscriber renews the lease before it lapses; replays if it fell behind.
7. Subscriber deletes the subscription when done.
```

Next: [Getting Started](getting-started.md) runs exactly this flow in code. The
full normative details are in [the specification](https://a2a-events.github.io/a2a-events/specification/), with machine-readable
[JSON Schemas](https://github.com/a2a-events/a2a-events/tree/main/schemas) and [conformance vectors](https://github.com/a2a-events/a2a-events/tree/main/conformance).
