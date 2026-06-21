# A2A Events Design

- Status: Draft
- Target version: `v0.1`
- A2A baseline: **A2A v1.0** (Linux Foundation)
- Project name: **A2A Events**
- Package name placeholder: `a2a-events`
- Extension URI placeholder: `https://example.com/a2a-events/extensions/events/v1`

---

## 1. Summary

A2A Events is an AgentCard-native event subscription protocol and SDK/runtime for A2A agent networks.

It lets one A2A agent subscribe to another agent's future events using AgentCard discovery, explicit topics, selectors, leases, durable cursors, acknowledgements, replay, event signatures, and transport adapters.

The core application-level flow is:

```text
Agent A -> Agent B:
  Subscribe to topic(s), provide my AgentCard URL, selector, lease, and delivery preference.

Agent B -> Agent A:
  Accept subscription, return subscriptionId, leaseUntil, and cursor.

Agent A -> Agent B:
  Renew lease periodically.

Agent B:
  While the lease is valid, publish matching diffs/events and deliver them to Agent A by resolving Agent A's AgentCard.

Agent A -> Agent B:
  Ack eventId/cursor and replay from cursor if events were missed.
```

A2A Events is not intended to replace A2A, CloudEvents, Webhooks, Kafka, NATS, Redis Streams, Postgres, or other brokers. Instead, it defines the agent-to-agent subscription semantics above them.

The project should provide both:

1. A protocol/specification layer.
2. A battery-included reference implementation.

However, the protocol must not require a specific backend implementation. A publisher agent may use Postgres, Redis Streams, Kafka, NATS, webhooks, queues, in-memory logs, Postgres `LISTEN/NOTIFY`, or custom infrastructure internally, as long as it satisfies the external A2A Events semantics and conformance requirements.

---

## 2. One-sentence Pitch

**Subscribe to agents, not URLs.**

Longer version:

**A2A Events provides durable event subscriptions for AgentCard-native A2A systems, with leases, cursors, replay, signed delivery, and SDKs that hide the operational glue.**

---

## 3. Motivation

A2A provides a foundation for agent discovery, AgentCards, task delegation, messages, artifacts, streaming, and task-scoped push notifications.

However, many agent-network use cases need a different communication pattern:

```text
Subscribe once.
Receive future independent events.
Renew the subscription lease.
Recover from missed events.
Authenticate publisher and subscriber as agents.
Route by AgentCard-declared capability instead of raw callback URLs.
```

Examples:

1. An agent directory notifies subscribers when new AgentCards are discovered.
2. A crawler agent notifies enrichment agents when new blocks are created.
3. A monitoring agent notifies remediation agents when another agent becomes unhealthy.
4. A marketplace agent broadcasts capability, pricing, reputation, or availability changes.
5. A search agent notifies subscribers when a keyword query result set changes.
6. A long-running research agent emits new artifacts to subscribed downstream agents.

A2A task push notifications are useful for long-running tasks, but they are task-scoped. A2A Events defines a durable, topic-based, agent-to-agent subscription layer.

---

## 4. Goals

A2A Events should provide:

1. AgentCard-native discovery and addressing.
2. A standard AgentCard extension declaration.
3. Topic discovery.
4. Topic + selector subscription semantics.
5. Subscription creation, renewal, deletion, listing, and replay.
6. Lease-based lifecycle management.
7. CloudEvents-compatible event envelopes.
8. Durable cursors.
9. At-least-once delivery.
10. Explicit idempotency semantics.
11. Acknowledgement and replay semantics.
12. Event signatures and publisher verification.
13. SSRF-resistant endpoint resolution.
14. Pluggable transports and internal backends.
15. A simple SDK experience for publishers and subscribers.
16. A battery-included reference implementation.
17. Conformance tests across SDKs and runtimes.

---

## 5. Non-goals

A2A Events does not try to:

1. Replace A2A core task semantics.
2. Replace CloudEvents as a general event envelope.
3. Replace Kafka, NATS, Redis Streams, Postgres, Google Pub/Sub, AWS SNS/SQS, or other brokers.
4. Guarantee exactly-once delivery.
5. Define a global agent registry.
6. Require every A2A agent to support this extension.
7. Require WebSocket as the primary transport.
8. Treat arbitrary callback URLs as trusted delivery targets.
9. Expose an agent's private memory, tools, chain of thought, or internal state.
10. Become a generic high-throughput message queue.
11. Standardize the publisher's internal storage or dispatch implementation.

---

## 6. Core Design Principle

The central design separation is:

```text
Protocol semantics are standardized.
Implementation choices are not.
```

A2A Events should standardize:

```text
AgentCard extension declaration
topic discovery
subscription lifecycle
selector semantics
lease renewal
event envelope
cursor and replay
acknowledgement
delivery modes
error codes
signature verification
conformance behavior
```

A2A Events should not require:

```text
Kafka
Redis
Postgres
NATS
WebSocket
a specific worker architecture
a specific database schema
a specific retry queue implementation
```

A compliant Agent B may internally implement the publisher side using any architecture, as long as Agent A observes the same external behavior.

### 6.1 Relationship to A2A core (normative)

A2A Events is an **A2A extension**, identified by the extension URI
`https://example.com/a2a-events/extensions/events/v1` and declared in
`AgentCard.capabilities.extensions` per the A2A `AgentExtension` schema
(`uri`, `description`, `required`, `params`). It targets **A2A v1.0**
(Linux Foundation).

A2A Events must reuse A2A core primitives verbatim and must not redefine
anything A2A already specifies. Specifically:

```text
- Discovery & addressing: A2A AgentCard. A2A Events adds an AgentExtension
  entry; it does not define a new card format or a new registry.
- Extension declaration: AgentCard.capabilities.extensions[] (AgentExtension
  with uri/description/required/params). All A2A Events config lives in
  `params`.
- Extension activation: the A2A `A2A-Extensions` request header (comma-
  separated extension URIs). A2A Events does not invent its own negotiation.
- AgentCard authenticity: A2A `AgentCardSignature` (JWS / RFC 7515 over a
  JCS / RFC 8785 canonicalization of the card). A2A Events does NOT define
  its own card-signing scheme; "signed AgentCards" everywhere in this
  document means A2A AgentCardSignature.
- Authentication: A2A `securitySchemes` + `security`. A2A Events adds topic
  authorization and a per-subscription delivery credential, but does not
  define a new login protocol (§21.1).
- Transports: A2A transport bindings `JSONRPC`, `GRPC`, and `HTTP+JSON`,
  declared via `preferredTransport` / `additionalInterfaces`. **A2A Events'
  canonical surface is JSON-RPC** — `a2a.events.*` methods (§29), mirroring
  A2A core's `a2a.*` methods. Publishers should advertise `JSONRPC` as
  `preferredTransport`. The REST-style paths shown throughout this document
  are an optional `HTTP+JSON` binding that maps 1:1 to the JSON-RPC methods
  and is provided only for non-JSON-RPC clients.
- Messaging: A2A `Message` and `Part` types. A2A-message delivery (§18.2)
  uses a `Message` with `role: ROLE_AGENT` and a `DataPart` (`data`); it
  does not define a new message envelope.
- Task push notifications: A2A `PushNotificationConfig` remains the
  mechanism for task-scoped updates. A2A Events is deliberately the
  separate, durable, topic-scoped layer (§3) and does not replace or
  redefine A2A push notifications.
```

What A2A Events legitimately adds on top of A2A (because A2A core does not
provide them): durable topic subscriptions, leases, durable cursors and
replay, selectors, and **event-payload signatures** (A2A signs cards, not
events; §21.3 mirrors A2A's JCS canonicalization for consistency).

A snapshot of the A2A v1.0 primitives this design depends on is kept at
[`docs/a2a-reference.md`](docs/a2a-reference.md) for offline review and drift
detection. It is non-authoritative. Prior-art research establishing that no
official or third-party A2A event-subscription protocol exists — and that
this extension approach is idiomatic — is recorded in
[`docs/prior-art.md`](docs/prior-art.md).

When this document and the A2A specification disagree on anything A2A
already defines, the A2A specification wins and this document must be
corrected.

---

## 7. Architecture Layers

A2A Events has four conceptual layers.

### 7.1 Protocol Layer

The protocol layer defines the interoperable wire-level and semantic contract.

It includes:

```text
AgentCard extension schema
topic discovery schema
subscription request/response schema
event envelope schema
ack/replay semantics
error model
security requirements
conformance test vectors
```

### 7.2 SDK Layer

The SDK layer makes the protocol easy to use.

It includes:

```text
typed models
schema validation
AgentCard helpers
topic discovery client
subscription client
lease auto-renewal
event receiver middleware
event signature verification
deduplication helpers
cursor parsing
ack/replay helpers
```

### 7.3 Runtime Layer

The runtime layer provides a working server implementation for publisher agents.

It includes:

```text
topic registry
subscription manager
lease manager
event store
dispatcher
delivery worker
retry manager
dead-letter handling
replay implementation
observability hooks
```

The runtime layer is part of the battery-included reference implementation. It is not mandatory for all compliant implementations.

### 7.4 Backend Adapter Layer

The backend adapter layer maps runtime concepts to real infrastructure.

Possible internal backends:

```text
In-memory dev store
Postgres event table
Postgres LISTEN/NOTIFY wakeup
Redis Streams
Kafka
NATS JetStream
Dapr Pub/Sub
custom queue
```

These are internal implementation choices unless explicitly exposed as external delivery modes.

In the Python reference implementation this layer is a contract/implementation
seam. The publisher depends only on the typed Protocols in
`a2a_events.runtime.contracts` (the backend SPI): `EventStore`,
`SubscriptionStore`, `RetryQueue`, and `Transport`, plus the plain data records
exchanged across them. Implementations live behind that seam:

```text
a2a_events.runtime.contracts   # the SPI — Protocols + data records, no deps
a2a_events.runtime.memory      # zero-dependency in-memory reference (default)
a2a_events.runtime.postgres    # optional batteries-included durable reference
                               #   (requires the `postgres` extra)
```

The in-memory backends are the default the publisher uses when none is supplied;
Postgres is *a* batteries-included reference, not *the* backend. Because the
contracts carry no third-party imports, any adapter that satisfies them — Redis
Streams, Kafka, NATS JetStream, DynamoDB, a custom queue — plugs in without
touching the publisher. The in-memory and Postgres backends pass identical
cross-backend contract suites, which is what keeps the seam honest.

---

## 8. Internal Backend vs External Delivery Mode

This distinction is critical.

### 8.1 Internal backend

If Agent B uses Kafka internally:

```text
Agent B publish event
  -> Kafka topic
  -> Agent B dispatcher
  -> signed webhook delivery to Agent A
```

Then Kafka is an internal implementation detail. Agent A does not need to know Kafka exists.

### 8.2 External delivery mode

If Agent B tells Agent A to consume directly from Kafka:

```text
Agent A subscribes
  -> Agent B returns Kafka topic/consumer config
  -> Agent A consumes from Kafka directly
```

Then Kafka is part of the external protocol surface. In that case, the specification must define:

```text
broker endpoint discovery
authentication
topic name mapping
event encoding
offset/cursor mapping
ack/replay behavior
authorization
failure handling
```

MVP should avoid exposing Kafka/Redis/NATS as external delivery modes. They may be supported early as internal runtime adapters, but not as protocol-visible delivery modes.

---

## 9. Recommended MVP Boundary

The MVP should standardize:

```text
AgentCard extension
JSON-RPC method surface (a2a.events.*) as the canonical transport
topic discovery
subscribe
renew
delete
replay
CloudEvents-compatible envelope
A2A-message delivery (canonical, via a2a.SendMessage)
webhook delivery (HTTP alternative)
optional HTTP+JSON binding for the control plane
lease semantics
cursor semantics
event signatures
ack semantics
error codes
conformance fixtures
```

The MVP should ship:

```text
Python reference implementation
FastAPI integration
Postgres event store
in-memory dev store
webhook delivery worker
subscriber receiver middleware
auto lease renewal
CLI inspect/topics/subscribe/replay
JSON Schemas
OpenAPI spec
```

The MVP should not ship:

```text
external Kafka delivery mode
external Redis delivery mode
external NATS delivery mode
WebSocket transport
semantic query language
global registry
multi-region ordering
exactly-once delivery
```

---

## 10. Core Concepts

### 10.1 Publisher Agent

An A2A agent that declares topics and publishes events.

Example:

```text
Agent B is a crawler agent.
It publishes "agent_card.discovered" when it discovers a new AgentCard.
```

### 10.2 Subscriber Agent

An A2A agent that subscribes to a publisher's topics.

Example:

```text
Agent A is an enrichment agent.
It subscribes to Agent B's "agent_card.discovered" topic.
```

### 10.3 Topic

A stable, low-cardinality event stream declared by the publisher.

Examples:

```text
agent_card.discovered
agent_card.updated
agent.status_changed
agent.capability_changed
block.created
block.updated
artifact.created
search.results.updated
```

Topics should not be arbitrary user strings.

### 10.4 Selector

A selector narrows a topic to the subset of events the subscriber cares about.

Examples:

```json
{
  "type": "field_filter",
  "where": {
    "data.kind": ["agent_card"],
    "data.source": ["crawler"]
  }
}
```

```json
{
  "type": "keyword_search",
  "keywords": ["a2a", "agentcard", "subscription"],
  "match": "all",
  "fields": ["title", "description", "content"]
}
```

Search keywords should live in a selector, not in the topic name.

#### Selector matching semantics

Selector matching is part of the wire contract: two conformant publishers
must match the same selector against the same event identically. The
following semantics are normative.

**Field path resolution.** A field path such as `data.skills.tags` is
resolved against the event envelope by splitting on `.` and walking nested
JSON objects from the root of the CloudEvent. A path resolves to:

```text
- a scalar (string, number, boolean, null), or
- an array of scalars, or
- "absent" if any segment is missing.
```

Paths that resolve to an object (rather than a scalar or array of scalars)
are treated as a selector error and rejected with `INVALID_SELECTOR`.

**`field_filter` semantics.** `where` is a map of `fieldPath -> [values]`.

```text
- A single field matches if ANY of its declared values matches the event
  field (set membership / "any-of").
- When the event field is itself an array, the field matches if the
  intersection of the event array and the declared values is non-empty.
- Multiple fields in `where` are combined with AND: every field clause
  must match.
- A clause whose field path is "absent" in the event does not match.
- Value comparison is exact and type-sensitive: `1` (number) does not
  match `"1"` (string). No implicit coercion is performed.
```

Example: the clause `"data.capabilities": ["streaming", "pushNotifications"]`
matches any event whose `data.capabilities` array contains `"streaming"` OR
`"pushNotifications"`.

**`keyword_search` semantics.**

```text
- `fields` lists the field paths to search; each must resolve to a string
  or array of strings. If omitted, the publisher's topic-declared default
  search fields are used.
- Matching is case-insensitive substring matching by default.
- `match: "all"` requires every keyword to appear in at least one searched
  field (AND across keywords).
- `match: "any"` requires at least one keyword to appear (OR across
  keywords). Default is `"all"`.
```

A selector that references a `type` not listed in the topic's
`selectorTypes`, or that uses a field outside the topic's declared
`filterableFields` (when the topic declares them), must be rejected with
`SELECTOR_NOT_SUPPORTED`.

### 10.5 Subscription

A lease-bound contract between a subscriber and a publisher.

It includes:

```text
subscriptionId
subscriber AgentCard URL
publisher AgentCard URL
topics
selector
delivery preference
lease expiration
last acknowledged cursor
authorization context
```

### 10.6 Lease

A subscription is active only while its lease is valid.

Agent A must periodically renew the lease. If Agent A disappears, stops caring, or loses authorization, the lease expires and Agent B can garbage-collect the subscription.

### 10.7 Event

A CloudEvents-compatible envelope with A2A Events extension attributes.

### 10.8 Diff

The event payload may contain a diff rather than a full object.

For example, an `agent_card.updated` event may contain:

```json
{
  "op": "updated",
  "diff": {
    "added": {
      "capabilities.streaming": true
    },
    "removed": {},
    "changed": {
      "version": {
        "old": "1.0.0",
        "new": "1.0.1"
      }
    }
  }
}
```

MVP should prefer:

```text
event diff + cursor replay
```

over complex per-subscriber state diff.

### 10.9 Cursor

A stable position in the publisher's event log.

Cursors are used for:

```text
acknowledgement
resume
replay
debugging
backfill
ordering within a topic partition
```

A cursor must not be a timestamp only.

#### Canonical cursor grammar

Cursors are **opaque to subscribers**. A subscriber must not parse, split,
or construct cursors; it only stores them and passes them back. The
following rules are the full contract:

```text
- A cursor is a non-empty string, scoped to a single topic.
- Within a topic, cursors are totally ordered by ordinary byte-wise
  lexicographic comparison. If cursor X sorts before cursor Y, the event
  at X precedes the event at Y in the topic log.
- Cursors are publisher-defined and monotonically non-decreasing within a
  topic. Two events in the same topic never share a cursor.
- The two sentinel values "earliest" and "latest" are reserved (see
  fromCursor below) and are never returned as event cursors.
```

The reference implementation's cursor encoding (`topic:partition:offset`
with zero-padded fixed-width offsets so lexicographic order equals numeric
order) is an implementation detail, not a protocol requirement. Examples in
this document that show that shape are illustrative only.

#### Cursors index the topic log, not the filtered delivery stream

This is the most important cursor rule when selectors are involved:

```text
- A cursor identifies a position in the publisher's per-topic event log.
- It does NOT identify a position in the subscriber's filtered delivery
  stream.
- Because a selector may filter out events, the cursors a subscriber
  observes on delivered events are typically sparse (gaps are expected and
  are not lost events).
- Acking cursor N means "I have durably handled every event at or before N
  in this topic that matched my selector." The publisher may advance its
  ack state to N even though some events at or before N were never
  delivered (they were filtered out).
```

This lets a subscriber ack the highest cursor it has seen without worrying
about gaps, and lets the publisher garbage-collect delivery state safely.

#### Per-topic cursor state

A subscription may span multiple topics. Cursor and ack state are tracked
**per topic**, never as a single value across topics. Wherever this
document shows a single `cursor` or `lastAckedCursor` string, that is a
shorthand for the single-topic case; the general representation is a map of
`topic -> cursor` (see [§23.1](#231-subscription)).

### 10.10 Ack and Nack

A subscriber acknowledges event receipt and responsibility.

For MVP webhook delivery, acknowledgement is **implicit on HTTP 2xx**: a 2xx
response means the subscriber has durably accepted responsibility for the
event, and the publisher may advance ack state for that subscription/topic
to the event's cursor. This is the load-bearing ack path for v0.1.

The explicit ack endpoint (`:ack`, see [§29](#29-json-rpc-method-surface)) is an
optional affordance, primarily useful for out-of-band acknowledgement (e.g.
after asynchronous processing) and for delivery modes without a synchronous
response channel. It is not required for webhook-mode conformance.

**Nack.** A subscriber may signal that it received an event but could not
process it, separately from a transport failure:

```text
- A 2xx response                 -> ack (accepted responsibility)
- A retriable failure            -> HTTP 5xx / 429, or an explicit nack with
                                    "retry": true; the publisher retries per
                                    its backoff policy (§19.4)
- A permanent / poison failure   -> an explicit nack with "retry": false, or
                                    HTTP 422; the publisher should dead-letter
                                    the event immediately without exhausting
                                    the retry budget
```

Explicit nack body (returned from the receive endpoint, or posted to
`:ack`):

```json
{
  "ack": false,
  "eventId": "evt_01HY8Z2V1ZF9B5M7A4N9D3E8GH",
  "retry": false,
  "reason": "schema unsupported by this subscriber version"
}
```

### 10.11 Replay

A subscriber can request events from a previous cursor if events are still within the topic retention window.

---

## 11. Topic vs Selector

A core design rule:

```text
topic = stable event stream declared by Agent B
selector = dynamic subscription condition provided by Agent A
```

Good:

```json
{
  "topics": ["search.results.updated"],
  "selector": {
    "type": "keyword_search",
    "keywords": ["SpaceX", "secondary market", "valuation"],
    "match": "all"
  }
}
```

Bad:

```json
{
  "topics": ["SpaceX secondary market valuation"]
}
```

Why topics should not be arbitrary strings:

```text
topic explosion
unclear schema ownership
unclear retention policy
unclear authorization policy
hard-to-map broker adapters
messy observability
easy abuse
```

Selectors may be high-cardinality. Topics should not be.

---

## 12. AgentCard Extension Declaration

The cards below are A2A AgentCards. Only the `capabilities.extensions[]`
entry for `https://example.com/a2a-events/extensions/events/v1` is defined by A2A
Events; every other field (including `preferredTransport`,
`additionalInterfaces`, `securitySchemes`, `security`, and `signatures` /
`AgentCardSignature`) is governed by the A2A v1.0 AgentCard schema and is
shown here only illustratively. A2A Events does not constrain those fields
beyond what A2A core requires. The examples omit some required A2A card
fields for brevity.

### 12.1 Publisher declaration

```json
{
  "name": "Crawler Agent",
  "description": "Discovers AgentCards and publishes event streams.",
  "url": "https://agent-b.example.com/a2a/v1",
  "version": "1.0.0",
  "capabilities": {
    "streaming": true,
    "pushNotifications": true,
    "extensions": [
      {
        "uri": "https://example.com/a2a-events/extensions/events/v1",
        "description": "Topic-based durable event subscriptions for A2A agents.",
        "required": false,
        "params": {
          "role": "publisher",
          "topicsUrl": "https://agent-b.example.com/a2a-events/topics",
          "subscribeUrl": "https://agent-b.example.com/a2a-events/subscriptions",
          "signingKeysUrl": "https://agent-b.example.com/a2a-events/keys",
          "eventFormat": "cloudevents-1.0",
          "deliveryModes": ["webhook", "a2a-message"],
          "replay": true,
          "maxLeaseSeconds": 604800
        }
      }
    ]
  },
  "skills": [
    {
      "id": "events.publish",
      "name": "Publish A2A Events",
      "description": "Publishes durable event streams for subscribed A2A agents.",
      "tags": ["events", "subscription", "pubsub"],
      "inputModes": ["application/json"],
      "outputModes": ["application/json"]
    }
  ]
}
```

### 12.2 Subscriber declaration

```json
{
  "name": "Enrichment Agent",
  "description": "Receives event deliveries from trusted A2A agents.",
  "url": "https://agent-a.example.com/a2a/v1",
  "version": "1.0.0",
  "capabilities": {
    "streaming": true,
    "pushNotifications": true,
    "extensions": [
      {
        "uri": "https://example.com/a2a-events/extensions/events/v1",
        "description": "Receives durable A2A event deliveries.",
        "required": false,
        "params": {
          "role": "subscriber",
          "receiveUrl": "https://agent-a.example.com/a2a-events/receive",
          "ackUrl": "https://agent-a.example.com/a2a-events/ack",
          "eventFormat": "cloudevents-1.0",
          "acceptedDeliveryModes": ["webhook", "a2a-message"]
        }
      }
    ]
  },
  "skills": [
    {
      "id": "events.receive",
      "name": "Receive A2A Events",
      "description": "Receives subscribed event notifications from trusted A2A agents.",
      "tags": ["events", "subscription", "webhook"],
      "inputModes": ["application/cloudevents+json", "application/json"],
      "outputModes": ["application/json"]
    }
  ]
}
```

### 12.3 Transport and invocation (JSON-RPC primary)

A2A Events operations are invoked as **A2A JSON-RPC calls**. JSON-RPC is the
canonical transport surface, consistent with A2A core (whose methods are
`a2a.SendMessage`, `a2a.GetTask`, and so on). A2A Events methods live in the
`a2a.events.*` namespace and are listed in [§29](#29-json-rpc-method-surface).

Publishers should advertise `JSONRPC` as `preferredTransport`. A publisher
may additionally offer an `HTTP+JSON` binding via `additionalInterfaces`;
the REST-style paths shown throughout this document are exactly that binding
and map 1:1 to the JSON-RPC methods. A publisher may likewise offer an
optional **gRPC binding** (service `a2a.events.v1.A2AEvents`, one unary RPC
per `a2a.events.*` method), mirroring A2A core's gRPC binding; it too maps 1:1
to the JSON-RPC methods, with protocol errors carried as gRPC status codes plus
the symbolic A2A Events code in trailing metadata. Both the HTTP+JSON and gRPC
bindings are optional and are not required for conformance.

Request envelope (standard JSON-RPC 2.0, as in A2A core):

```json
{
  "jsonrpc": "2.0",
  "id": "1",
  "method": "a2a.events.Subscribe",
  "params": { }
}
```

For each operation below, the request JSON body is the method's `params`
object and the response JSON body is the method's `result` object; the HTTP
verb/path is the equivalent HTTP+JSON binding. Requests authenticate using
the publisher's A2A `securitySchemes` ([§21.1](#211-agent-identity)) and
errors use the JSON-RPC error object ([§30](#30-error-model)).

**Extension activation handshake (normative).** A2A Events follows A2A's
standard extension-activation negotiation, not a bespoke one:

```text
- The caller sends the `A2A-Extensions` request header listing the extension
  URI(s) it wants to activate, e.g.
    A2A-Extensions: https://example.com/a2a-events/extensions/events/v1
- The responding agent activates the supported extensions and MUST echo the
  successfully activated URIs back in the `A2A-Extensions` response header.
- The caller should confirm the extension URI appears in the response header
  before relying on A2A Events semantics; absence means the peer did not
  activate the extension.
- If the extension is declared required (`required: true`) and the caller
  does not request activation, the agent rejects the request
  (`EXTENSION_NOT_SUPPORTED`, §30).
```

This activation handshake applies on every A2A Events request, over both the
JSON-RPC and HTTP+JSON bindings.

---

## 13. Topic Discovery

A publisher exposes topic discovery.

JSON-RPC method: **`a2a.events.ListTopics`** (no params, or an optional
`{ "pageToken": "..." }`). HTTP+JSON binding:

```http
GET /a2a-events/topics
Accept: application/json
```

Example `result` (also the HTTP+JSON response body):

```json
{
  "publisher": {
    "agentCardUrl": "https://agent-b.example.com/.well-known/agent-card.json",
    "agentId": "agent-b.example.com"
  },
  "extension": "https://example.com/a2a-events/extensions/events/v1",
  "eventFormat": "cloudevents-1.0",
  "topics": [
    {
      "name": "agent_card.discovered",
      "description": "Emitted when a new AgentCard is discovered.",
      "schemaUrl": "https://agent-b.example.com/a2a-events/schemas/agent_card.discovered.v1.json",
      "retentionSeconds": 604800,
      "replay": true,
      "selectorTypes": ["field_filter", "keyword_search"],
      "filterableFields": [
        "data.cardUrl",
        "data.domain",
        "data.capabilities",
        "data.skills.tags"
      ],
      "deliveryModes": ["webhook", "a2a-message"]
    },
    {
      "name": "search.results.updated",
      "description": "Emitted when a subscribed search result set changes.",
      "schemaUrl": "https://agent-b.example.com/a2a-events/schemas/search.results.updated.v1.json",
      "retentionSeconds": 259200,
      "replay": true,
      "selectorTypes": ["keyword_search"],
      "deliveryModes": ["webhook", "a2a-message"]
    }
  ]
}
```

---

## 14. Subscription Lifecycle

### 14.1 Create subscription

Agent A creates a subscription with Agent B.

JSON-RPC method: **`a2a.events.Subscribe`**. Canonical (JSON-RPC) request:

```json
{
  "jsonrpc": "2.0",
  "id": "1",
  "method": "a2a.events.Subscribe",
  "params": {
    "subscriberCardUrl": "https://agent-a.example.com/.well-known/agent-card.json",
    "topics": ["agent_card.discovered"],
    "selector": {
      "type": "field_filter",
      "where": {
        "data.capabilities": ["streaming", "pushNotifications"],
        "data.skills.tags": ["coding", "search"]
      }
    },
    "delivery": {
      "mode": "a2a-message",
      "endpointRef": "agent-card:events.receive"
    },
    "fromCursor": "latest",
    "leaseSeconds": 86400,
    "metadata": {
      "purpose": "enrich newly discovered AgentCards"
    }
  }
}
```

Canonical (JSON-RPC) response:

```json
{
  "jsonrpc": "2.0",
  "id": "1",
  "result": {
    "subscriptionId": "sub_01HY8Y5K3N7V4Z9WHE4RYMZG5G",
    "status": "active",
    "publisherCardUrl": "https://agent-b.example.com/.well-known/agent-card.json",
    "subscriberCardUrl": "https://agent-a.example.com/.well-known/agent-card.json",
    "topics": ["agent_card.discovered"],
    "delivery": {
      "mode": "a2a-message",
      "resolvedEndpoint": "https://agent-a.example.com/a2a/v1"
    },
    "createdAt": "2026-06-19T20:00:00Z",
    "leaseUntil": "2026-06-20T20:00:00Z",
    "cursors": {
      "agent_card.discovered": "agent_card.discovered:0000000000000000"
    }
  }
}
```

The same operation over the optional HTTP+JSON binding (`params` becomes the
request body, `result` becomes the response body):

```http
POST /a2a-events/subscriptions
Content-Type: application/json
Authorization: Bearer <subscriber-token>
A2A-Extensions: https://example.com/a2a-events/extensions/events/v1
```

`fromCursor` accepts:

```text
"latest"   -> deliver only events published after subscription creation
              (default).
"earliest" -> deliver from the oldest event still within the topic's
              retention window (backfill from start of retention).
<cursor>   -> resume from a specific opaque cursor previously observed by
              this subscriber. If the cursor is outside retention, creation
              fails with CURSOR_EXPIRED (see §31).
```

Agent B must verify:

```text
subscriberCardUrl is reachable
subscriber AgentCard declares the A2A Events extension
requested receive endpoint or skill is declared in the AgentCard
requested delivery mode is supported
subscriber is authorized for the requested topics
selector is valid for the requested topics
```

### 14.2 Search-style subscription

Search keywords belong in `selector`, not in `topic`. Same
`a2a.events.Subscribe` method; the object below is the `params` (the
JSON-RPC envelope is omitted for brevity).

```json
{
  "subscriberCardUrl": "https://agent-a.example.com/.well-known/agent-card.json",
  "topics": ["search.results.updated"],
  "selector": {
    "type": "keyword_search",
    "keywords": ["A2A", "AgentCard", "subscription"],
    "match": "all",
    "fields": ["title", "description", "content"],
    "freshness": {
      "from": "subscription_start"
    },
    "sources": {
      "domains": ["github.com", "a2a-protocol.org"]
    }
  },
  "delivery": {
    "mode": "a2a-message",
    "endpointRef": "agent-card:events.receive"
  },
  "fromCursor": "latest",
  "leaseSeconds": 86400
}
```

### 14.3 Renew subscription

Agent A should renew before the lease expires, usually when 50% to 70% of the lease has elapsed.

JSON-RPC method: **`a2a.events.RenewSubscription`**, with
`params: { "subscriptionId": "...", "leaseSeconds": 86400 }`. HTTP+JSON
binding:

```http
POST /a2a-events/subscriptions/{subscriptionId}:renew
Content-Type: application/json
Authorization: Bearer <subscriber-token>
```

`result` (HTTP+JSON response body):

```json
{
  "subscriptionId": "sub_01HY8Y5K3N7V4Z9WHE4RYMZG5G",
  "status": "active",
  "leaseUntil": "2026-06-21T20:00:00Z"
}
```

### 14.4 Delete subscription

JSON-RPC method: **`a2a.events.DeleteSubscription`**, with
`params: { "subscriptionId": "..." }`. HTTP+JSON binding:

```http
DELETE /a2a-events/subscriptions/{subscriptionId}
Authorization: Bearer <subscriber-token>
```

`result` (HTTP+JSON response body):

```json
{
  "subscriptionId": "sub_01HY8Y5K3N7V4Z9WHE4RYMZG5G",
  "status": "deleted"
}
```

Deletion must be idempotent.

### 14.5 List subscriptions

JSON-RPC method: **`a2a.events.ListSubscriptions`**, with optional
`params: { "pageToken": "..." }`. HTTP+JSON binding:

```http
GET /a2a-events/subscriptions
Authorization: Bearer <subscriber-token>
```

`result` (HTTP+JSON response body):

```json
{
  "subscriptions": [
    {
      "subscriptionId": "sub_01HY8Y5K3N7V4Z9WHE4RYMZG5G",
      "status": "active",
      "topics": ["agent_card.discovered"],
      "leaseUntil": "2026-06-20T20:00:00Z",
      "cursors": {
        "agent_card.discovered": "agent_card.discovered:0000000000000042"
      }
    }
  ],
  "nextPageToken": null
}
```

**Pagination (normative).** List endpoints (`subscriptions`,
`deliveries`) and cursor-bounded reads (`replay`) are paginated. A response
includes `nextPageToken` (for list endpoints) or `nextCursor` (for replay);
a `null` value means no further pages. Clients pass the token back via a
`pageToken` query parameter (list) or `fromCursor` (replay) to fetch the
next page. Tokens are opaque and must not be constructed by the client.
Publishers should bound page size and apply a default limit when none is
given.

---

## 15. Event Delivery

When Agent B has a new event matching Agent A's active subscription, Agent B should:

```text
load subscription
check lease is still valid
match topic and selector
resolve Agent A's current AgentCard
resolve delivery endpoint from AgentCard
sign event
deliver event
record delivery attempt
retry if necessary
advance ack state when acknowledged
```

Agent B should not blindly post to arbitrary URLs from the subscription request.

The safe routing model is:

```text
A gives B subscriberCardUrl.
B fetches A's AgentCard.
B resolves the declared receive capability from the AgentCard.
B delivers only to an endpoint declared in the AgentCard or extended AgentCard.
```

---

## 16. Event Envelope

Events should use CloudEvents-compatible JSON with A2A Events extension attributes.

Example:

```json
{
  "specversion": "1.0",
  "id": "evt_01HY8Z2V1ZF9B5M7A4N9D3E8GH",
  "source": "a2a://agent-b.example.com",
  "type": "org.example.a2a.agent_card.discovered.v1",
  "subject": "agent-card/https%3A%2F%2Fnew-agent.example.com%2F.well-known%2Fagent-card.json",
  "time": "2026-06-19T20:30:00Z",
  "datacontenttype": "application/json",
  "data": {
    "cardUrl": "https://new-agent.example.com/.well-known/agent-card.json",
    "domain": "new-agent.example.com",
    "contentHash": "sha256:5f6f1d2d8f...",
    "summary": {
      "name": "New Coding Agent",
      "capabilities": ["streaming", "pushNotifications"],
      "skills": ["code.review", "repo.search"]
    }
  },
  "a2aevents": {
    "extension": "https://example.com/a2a-events/extensions/events/v1",
    "publisherCardUrl": "https://agent-b.example.com/.well-known/agent-card.json",
    "topic": "agent_card.discovered",
    "cursor": "agent_card.discovered:0000000000000043",
    "schemaUrl": "https://agent-b.example.com/a2a-events/schemas/agent_card.discovered.v1.json",
    "subscriptionId": "sub_01HY8Y5K3N7V4Z9WHE4RYMZG5G",
    "deliveryAttempt": 1,
    "traceId": "trace_01HY8Z3NQ8N9ZDE6R0V7M4T2C2"
  }
}
```

Required fields:

```text
specversion
id
source
type
time
datacontenttype
data
a2aevents.extension
a2aevents.publisherCardUrl
a2aevents.topic
a2aevents.cursor
```

Recommended fields:

```text
subject
a2aevents.schemaUrl
a2aevents.subscriptionId
a2aevents.traceId
```

### 16.1 `topic` vs CloudEvents `type`

These two fields overlap and their relationship is normative:

```text
- a2aevents.topic is the authoritative routing key. Subscription matching,
  selectors, cursors, retention, and authorization are all defined in terms
  of topic. Conformant implementations must route on a2aevents.topic.
- type is a descriptive CloudEvents discriminator (typically a versioned,
  reverse-DNS string such as org.example.a2a.agent_card.discovered.v1). It
  is useful for payload-schema dispatch but must not be used for routing.
- A single topic may carry more than one type over time (e.g. as the
  payload schema version evolves), but every event in a topic shares that
  topic's selector and retention semantics.
```

---

## 17. Diff Event Example

For updates, Agent B may send a diff.

```json
{
  "specversion": "1.0",
  "id": "evt_01HY8Z5MG71X9F3M9Y2JH5T71C",
  "source": "a2a://agent-b.example.com",
  "type": "org.example.a2a.agent_card.updated.v1",
  "subject": "agent-card/https%3A%2F%2Fsome-agent.example.com%2F.well-known%2Fagent-card.json",
  "time": "2026-06-19T21:00:00Z",
  "datacontenttype": "application/json",
  "data": {
    "cardUrl": "https://some-agent.example.com/.well-known/agent-card.json",
    "op": "updated",
    "diff": {
      "added": {
        "capabilities.pushNotifications": true
      },
      "removed": {},
      "changed": {
        "version": {
          "old": "1.0.0",
          "new": "1.0.1"
        }
      }
    },
    "previousHash": "sha256:old...",
    "currentHash": "sha256:new..."
  },
  "a2aevents": {
    "extension": "https://example.com/a2a-events/extensions/events/v1",
    "publisherCardUrl": "https://agent-b.example.com/.well-known/agent-card.json",
    "topic": "agent_card.updated",
    "cursor": "agent_card.updated:0000000000000108",
    "subscriptionId": "sub_01HY8Y5K3N7V4Z9WHE4RYMZG5G"
  }
}
```

---

## 18. Delivery Modes

Because the canonical transport is JSON-RPC, the canonical delivery mode is
**A2A-message delivery** (§18.1): the publisher delivers events by calling
the subscriber's A2A endpoint with the A2A core method `a2a.SendMessage`.
This reuses A2A messaging end to end and is the recommended default.
**Webhook delivery** (§18.2) remains fully supported as a simpler HTTP
option for subscribers that do not expose a JSON-RPC A2A endpoint.

### 18.1 A2A message delivery (canonical)

The publisher invokes the A2A core method **`a2a.SendMessage`** on the
subscriber's A2A endpoint (resolved from the subscriber's AgentCard), with a
`Message` (`role: ROLE_AGENT`) whose CloudEvent is carried in an A2A
`DataPart` (the part's `data` field). A2A Events does not define a new
message envelope — only the `metadata` key that marks the message as an
event delivery. The subscriber's `a2a.SendMessage` result conveys ack/nack
(§10.10): an empty/success result is an ack; an error or an explicit
`{ "ack": false, ... }` data result is a nack.

Event authenticity in this mode does not use HTTP signature headers; instead
the signature, timestamp, and `keyId` travel in the delivery `metadata`
under the extension key:

```json
{
  "message": {
    "role": "ROLE_AGENT",
    "parts": [
      {
        "data": {
          "specversion": "1.0",
          "id": "evt_01HY8Z2V1ZF9B5M7A4N9D3E8GH",
          "source": "a2a://agent-b.example.com",
          "type": "org.example.a2a.agent_card.discovered.v1",
          "time": "2026-06-19T20:30:00Z",
          "datacontenttype": "application/json",
          "data": {
            "cardUrl": "https://new-agent.example.com/.well-known/agent-card.json"
          },
          "a2aevents": {
            "extension": "https://example.com/a2a-events/extensions/events/v1",
            "publisherCardUrl": "https://agent-b.example.com/.well-known/agent-card.json",
            "topic": "agent_card.discovered",
            "cursor": "agent_card.discovered:0000000000000043",
            "subscriptionId": "sub_01HY8Y5K3N7V4Z9WHE4RYMZG5G"
          }
        }
      }
    ],
    "metadata": {
      "https://example.com/a2a-events/extensions/events/v1": {
        "kind": "event.delivery",
        "signature": "v1=<base64url-signature>",
        "timestamp": "2026-06-19T20:30:00Z",
        "keyId": "key_2026_06",
        "subscriptionId": "sub_01HY8Y5K3N7V4Z9WHE4RYMZG5G"
      }
    }
  }
}
```

This mode is the default when both agents expose authenticated A2A
endpoints.

### 18.2 Webhook delivery (HTTP alternative)

Webhook delivery is the simpler HTTP option for subscribers without a
JSON-RPC endpoint. The publisher POSTs the signed CloudEvent to the
subscriber's declared `receiveUrl`. Unlike the A2A-message mode, the
signature/timestamp/keyId travel in HTTP headers.

```http
POST /a2a-events/receive
Content-Type: application/cloudevents+json
Authorization: Bearer <delivery-token>
A2A-Event-Signature: v1=<signature>
A2A-Event-Timestamp: 2026-06-19T20:30:00Z
A2A-Event-Key-ID: key_2026_06
A2A-Subscription-ID: sub_01HY8Y5K3N7V4Z9WHE4RYMZG5G
```

The request body is the CloudEvent envelope (§16). A successful response:

```http
HTTP/1.1 204 No Content
```

or:

```json
{
  "ack": true,
  "eventId": "evt_01HY8Z2V1ZF9B5M7A4N9D3E8GH",
  "cursor": "agent_card.discovered:0000000000000043"
}
```

A 2xx response means the subscriber has accepted responsibility for the
event (§10.10). It does not necessarily mean all downstream processing has
completed.

### 18.3 SSE delivery

SSE may be supported for live connected sessions, aligned with A2A's own
streaming model (A2A uses SSE over the JSONRPC binding for
`a2a.SendStreamingMessage` / `a2a.SubscribeToTask`). This is the live-session
counterpart to the durable delivery modes above.

```http
GET /a2a-events/subscriptions/{subscriptionId}/stream?fromCursor=agent_card.discovered:0000000000000042
Accept: text/event-stream
Authorization: Bearer <subscriber-token>
```

Example:

```text
event: a2a.event
id: agent_card.discovered:0000000000000043
data: {"specversion":"1.0","id":"evt_01HY8Z2V1ZF9B5M7A4N9D3E8GH","source":"a2a://agent-b.example.com","type":"org.example.a2a.agent_card.discovered.v1","data":{"cardUrl":"https://new-agent.example.com/.well-known/agent-card.json"}}
```

SSE may be post-MVP.

---

## 19. Delivery Semantics

### 19.1 Guarantee

A2A Events provides:

```text
at-least-once delivery
best-effort ordering per topic partition
idempotent subscriber handling by event ID
cursor-based replay within retention period
```

### 19.2 No exactly-once guarantee

Exactly-once delivery is not guaranteed.

Subscribers must deduplicate by:

```text
event.id
subscriptionId + event.id
topic + cursor
```

The recommended primary deduplication key is:

```text
event.id
```

### 19.3 Ordering

The publisher should preserve ordering per topic partition, where order is
defined by lexicographic comparison of cursors within the topic
([§10.9](#109-cursor)).

Because selectors filter events, a subscriber observes a sparse cursor
sequence on its delivered stream; gaps are expected and are not lost events.
A subscriber must treat cursors as opaque and rely only on their ordering,
never on contiguity. Acking the highest cursor seen is always safe (see the
topic-log-vs-delivery-stream contract in [§10.9](#109-cursor)).

If the publisher partitions a topic internally, the cursor encoding must
still yield a single total order per topic via lexicographic comparison so
that subscribers need no knowledge of partitioning. Partitioning is a
publisher implementation detail and is not exposed to subscribers.

### 19.4 Retry

Publishers should retry failed delivery attempts with exponential backoff.

Recommended defaults:

```text
initialDelay: 1 second
maxDelay: 5 minutes
maxAttempts: 12
timeout: 10 seconds
deadLetterAfter: maxAttempts exhausted
```

### 19.5 Dead letter

When delivery repeatedly fails, the event should be moved to a dead-letter queue for that subscription.

Dead-letter records should be replayable manually.

```bash
a2a-events replay-dead-letter sub_01HY8Y5K3N7V4Z9WHE4RYMZG5G
```

---

## 20. Replay

### 20.1 Replay events

JSON-RPC method: **`a2a.events.Replay`**. The object below is the `params`
(plus a `subscriptionId`); over the HTTP+JSON binding it is the request body:

```http
POST /a2a-events/subscriptions/{subscriptionId}:replay
Content-Type: application/json
Authorization: Bearer <subscriber-token>
```

`params` / request body:

```json
{
  "subscriptionId": "sub_01HY8Y5K3N7V4Z9WHE4RYMZG5G",
  "fromCursor": "agent_card.discovered:0000000000000040",
  "toCursor": "agent_card.discovered:0000000000000043",
  "limit": 100
}
```

`result` / response body:

```json
{
  "subscriptionId": "sub_01HY8Y5K3N7V4Z9WHE4RYMZG5G",
  "events": [
    {
      "specversion": "1.0",
      "id": "evt_01HY8Z2V1ZF9B5M7A4N9D3E8GH",
      "source": "a2a://agent-b.example.com",
      "type": "org.example.a2a.agent_card.discovered.v1",
      "time": "2026-06-19T20:30:00Z",
      "datacontenttype": "application/json",
      "data": {
        "cardUrl": "https://new-agent.example.com/.well-known/agent-card.json"
      },
      "a2aevents": {
        "topic": "agent_card.discovered",
        "cursor": "agent_card.discovered:0000000000000043"
      }
    }
  ],
  "nextCursor": null
}
```

### 20.2 Replay rules

Replay should only return events that:

```text
belong to the requested subscription's authorized topics
match the subscription's selector
are still within retention
are visible to the authenticated subscriber
```

---

## 21. Security Model

### 21.1 Agent identity

Both publisher and subscriber should be identified by AgentCard URL plus
authenticated runtime identity. A2A Events reuses A2A's existing security
machinery rather than inventing a new one: the AgentCard's
`securitySchemes` / `security` declarations (A2A core) define how each agent
authenticates, and A2A Events layers topic authorization and event
signatures on top.

**Credential acquisition (subscriber -> publisher calls).** Subscription
management calls (`subscribe`, `renew`, `delete`, `list`, `replay`,
`:ack`) are ordinary authenticated A2A requests: the subscriber obtains
credentials for the publisher using the auth scheme the publisher's
AgentCard declares (e.g. OAuth2 client-credentials, API key, mTLS), exactly
as for any other A2A call. A2A Events does not define a new login handshake.

**Delivery credential issuance (publisher -> subscriber calls).** The
`Bearer <delivery-token>` shown in delivery examples is a per-subscription
delivery credential **minted by the publisher and returned to the
subscriber at subscription creation**, so the subscriber can authenticate
incoming deliveries as coming from this subscription. The create-subscription
response therefore also carries delivery auth material:

```json
{
  "subscriptionId": "sub_01HY8Y5K3N7V4Z9WHE4RYMZG5G",
  "delivery": {
    "mode": "webhook",
    "resolvedUrl": "https://agent-a.example.com/a2a-events/receive",
    "auth": {
      "scheme": "bearer",
      "token": "dtok_...",
      "expiresAt": "2026-06-20T20:00:00Z",
      "rotates": true
    }
  }
}
```

Alternatively, when both agents expose mTLS-authenticated A2A endpoints, the
delivery credential may be the publisher's mTLS identity and no bearer token
is issued. The delivery token (when used) follows the least-privilege rules
in [§21.5](#215-least-privilege-tokens).

The publisher should verify:

```text
subscriberCardUrl is reachable
subscriber AgentCard declares A2A Events
subscriber AgentCard declares a valid receive endpoint or skill
subscriber authentication matches the expected identity
subscriber is authorized for requested topics
```

The subscriber should verify:

```text
publisherCardUrl is expected or trusted
publisher AgentCard declares A2A Events
event signature is valid
delivery token or mTLS identity is valid
event topic and subscriptionId are expected
event timestamp is within allowed skew
```

### 21.2 SSRF prevention

Publishers must not blindly deliver to arbitrary URLs submitted in a subscription request.

Recommended rule:

```text
The subscriber provides subscriberCardUrl.
The publisher fetches the AgentCard.
The publisher resolves delivery endpoints from the AgentCard extension declaration.
The publisher only delivers to endpoints declared in the AgentCard or extended AgentCard.
```

Optional stricter policies:

```text
require same-origin between subscriberCardUrl and receiveUrl
block private IP ranges by default
block localhost by default
block link-local addresses by default
require HTTPS in production
require domain ownership challenge
require A2A AgentCardSignature (JWS over JCS-canonicalized card) verification
```

### 21.3 Event signatures

Each delivered event should be signed.

Recommended signature input:

```text
timestamp + "." + canonical_json(event)
```

Canonicalization uses JCS (RFC 8785) over the full event envelope so that
publisher and subscriber compute byte-identical input independent of JSON
key ordering or whitespace.

Recommended headers:

```http
A2A-Event-Signature: v1=<base64url-signature>
A2A-Event-Timestamp: 2026-06-19T20:30:00Z
A2A-Event-Key-ID: key_2026_06
```

#### Signing key discovery

Signature verification is only interoperable if the subscriber can fetch the
publisher's public key without out-of-band coordination. This is mandatory,
not optional:

```text
- The publisher declares a JWKS URL in its A2A Events extension params:
    "params": { "signingKeysUrl": "https://agent-b.example.com/a2a-events/keys" }
- The JWKS endpoint returns a standard JWKS document (RFC 7517). Each key
  carries a `kid` matching the A2A-Event-Key-ID delivery header.
- Signatures use EdDSA (Ed25519) by default; RS256 and ES256 are permitted
  and identified by the JWK `alg`.
- Subscribers resolve the key by (publisherCardUrl -> signingKeysUrl -> kid),
  may cache keys, and must honor key rotation by refetching on an unknown
  `kid`.
- Publishers should publish the next key before activating it so rotation
  does not cause verification gaps.
```

The `signingKeysUrl` is itself authenticated as a publisher-controlled
endpoint: subscribers must confirm it is same-origin with, or declared by,
the publisher's AgentCard before trusting keys from it.

Subscribers should reject events when:

```text
signature is invalid
timestamp is too old
event.id has already been processed with different content
publisherCardUrl does not match the expected publisher
subscriptionId is unknown
topic is not part of the subscription
```

### 21.4 Authorization

Topic authorization should be evaluated both at subscription creation and delivery time.

A subscriber may be authorized for:

```text
all public topics
partner-only topics
tenant-specific topics
allowlisted domains
allowlisted selector types
rate-limited search subscriptions
```

### 21.5 Least privilege tokens

Delivery tokens should be:

```text
unique per subscription
scoped to event receipt only
rotatable
revocable
not reused for normal A2A task calls
```

---

## 22. Selector Safety and Resource Limits

Selectors can be user-generated and potentially expensive. Publishers should enforce limits.

Recommended limits:

```text
maximum selector size
maximum keyword count
maximum keyword length
maximum subscriptions per subscriber
maximum delivery rate
maximum replay window
maximum result count per event
minimum and maximum lease duration
allowed selector types per topic
domain/source allowlists where applicable
```

MVP should avoid:

```text
arbitrary SQL
unbounded regex
eval-like filters
unbounded semantic search
unbounded historical replay
```

MVP selector types:

```text
field_filter
keyword_search
```

Future selector types:

```text
JSONPath
CEL
CloudEvents SQL
semantic similarity
hybrid keyword + vector query
```

---

## 23. Data Model

### 23.1 Subscription

```json
{
  "subscriptionId": "sub_01HY8Y5K3N7V4Z9WHE4RYMZG5G",
  "publisherAgentId": "agent-b.example.com",
  "publisherCardUrl": "https://agent-b.example.com/.well-known/agent-card.json",
  "subscriberAgentId": "agent-a.example.com",
  "subscriberCardUrl": "https://agent-a.example.com/.well-known/agent-card.json",
  "topics": ["agent_card.discovered"],
  "selector": {
    "type": "field_filter",
    "where": {
      "data.capabilities": ["streaming"]
    }
  },
  "delivery": {
    "mode": "webhook",
    "resolvedUrl": "https://agent-a.example.com/a2a-events/receive"
  },
  "status": "active",
  "createdAt": "2026-06-19T20:00:00Z",
  "leaseUntil": "2026-06-20T20:00:00Z",
  "cursors": {
    "agent_card.discovered": "agent_card.discovered:0000000000000042"
  },
  "metadata": {
    "purpose": "enrichment"
  }
}
```

`cursors` is a per-topic map of `topic -> lastAckedCursor`
([§10.9](#per-topic-cursor-state)). For single-topic subscriptions this map
has one entry. Earlier sections that show a single `lastAckedCursor` string
are the single-topic shorthand for this map.

### 23.2 Event record

```json
{
  "eventId": "evt_01HY8Z2V1ZF9B5M7A4N9D3E8GH",
  "topic": "agent_card.discovered",
  "cursor": "agent_card.discovered:0000000000000043",
  "type": "org.example.a2a.agent_card.discovered.v1",
  "subject": "agent-card/https%3A%2F%2Fnew-agent.example.com%2F.well-known%2Fagent-card.json",
  "source": "a2a://agent-b.example.com",
  "payload": {},
  "createdAt": "2026-06-19T20:30:00Z",
  "contentHash": "sha256:5f6f1d2d8f..."
}
```

### 23.3 Delivery attempt

```json
{
  "deliveryAttemptId": "da_01HY8Z4PR4X4M1KQQZ8T1Z4X5D",
  "subscriptionId": "sub_01HY8Y5K3N7V4Z9WHE4RYMZG5G",
  "eventId": "evt_01HY8Z2V1ZF9B5M7A4N9D3E8GH",
  "attempt": 2,
  "status": "retrying",
  "lastStatusCode": 503,
  "lastError": "subscriber unavailable",
  "nextRetryAt": "2026-06-19T20:35:00Z",
  "createdAt": "2026-06-19T20:31:00Z",
  "updatedAt": "2026-06-19T20:32:00Z"
}
```

### 23.4 Ack record

```json
{
  "subscriptionId": "sub_01HY8Y5K3N7V4Z9WHE4RYMZG5G",
  "eventId": "evt_01HY8Z2V1ZF9B5M7A4N9D3E8GH",
  "cursor": "agent_card.discovered:0000000000000043",
  "ackedAt": "2026-06-19T20:30:03Z"
}
```

---

## 24. Reference Implementation

A2A Events should include a battery-included reference implementation.

The reference implementation is not the protocol. It is a canonical, runnable implementation that:

```text
validates the protocol design
provides developer experience
anchors conformance tests
reduces adoption friction
demonstrates best practices
```

### 24.1 Recommended reference stack

The first reference implementation should use:

```text
Python
FastAPI
JSON-RPC endpoint (a2a.events.*) + optional HTTP+JSON binding
Postgres event store
A2A-message delivery (canonical) + webhook delivery (fallback)
in-memory dev store
background delivery worker
JSON Schema validation
event signing and verification
CLI tooling
```

### 24.2 Publisher runtime API

```python
import httpx
from a2a_events import A2AEventsPublisher, PublisherConfig, SigningKey, Topic
from a2a_events.runtime.http_delivery import HttpxTransport
from a2a_events.runtime.postgres import PostgresEventStore

publisher = A2AEventsPublisher(
    agent_card_url="https://agent-b.example.com/.well-known/agent-card.json",
    # The transport carries both delivery modes: canonical A2A-message
    # (a2a.SendMessage) and webhook (the HTTP fallback for subscribers with no
    # JSON-RPC endpoint). Everything else is optional config.
    transport=HttpxTransport(httpx.AsyncClient()),
    signing_key=SigningKey.generate("key_2026_06"),
    config=PublisherConfig(
        store=PostgresEventStore("postgresql://..."),
    ),
)

publisher.declare_topic(
    Topic(
        name="agent_card.discovered",
        description="Emitted when a new AgentCard is discovered.",
        schema_url="https://agent-b.example.com/a2a-events/schemas/agent_card.discovered.v1.json",
        retention_seconds=604800,
        replay=True,
    )
)

await publisher.publish(
    topic="agent_card.discovered",
    type="org.example.a2a.agent_card.discovered.v1",
    subject="agent-card:https://new-agent.example.com/.well-known/agent-card.json",
    data={
        "cardUrl": "https://new-agent.example.com/.well-known/agent-card.json",
        "domain": "new-agent.example.com",
        "capabilities": ["streaming", "pushNotifications"],
    },
)
```

### 24.3 Subscriber client API

```python
from a2a_events import A2AEventsClient, event_handler

client = A2AEventsClient(
    agent_card_url="https://agent-a.example.com/.well-known/agent-card.json"
)

subscription = await client.subscribe(
    publisher_card_url="https://agent-b.example.com/.well-known/agent-card.json",
    topic="agent_card.discovered",
    selector={
        "type": "field_filter",
        "where": {
            "data.capabilities": ["streaming"]
        }
    },
    delivery="agent-card:events.receive",
    from_cursor="latest",
    lease_seconds=86400,
)

@event_handler(subscription)
async def handle_agent_card_discovered(event):
    card_url = event.data["cardUrl"]

    await enrich_agent_card(card_url)

    await event.ack()
```

### 24.4 FastAPI receiver

```python
from fastapi import FastAPI, Request
from a2a_events.fastapi import A2AEventsReceiver

app = FastAPI()

receiver = A2AEventsReceiver(
    agent_card_url="https://agent-a.example.com/.well-known/agent-card.json"
)

@app.post("/a2a-events/receive")
async def receive_event(request: Request):
    return await receiver.handle_request(request)
```

### 24.5 Local development mode

```python
from a2a_events.testing import InMemoryEventBus

bus = InMemoryEventBus()

publisher = A2AEventsPublisher(
    transport=bus.transport(),
    config=PublisherConfig(store=bus.store()),
)

subscriber = A2AEventsClient(
    transport=bus.transport(),
)
```

---

## 25. Reference Storage Schema

The reference Postgres implementation may use a schema like this.

```sql
CREATE TABLE a2a_event_topics (
    topic TEXT PRIMARY KEY,
    schema_url TEXT,
    retention_seconds INTEGER NOT NULL,
    replay_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE a2a_events (
    event_id TEXT PRIMARY KEY,
    topic TEXT NOT NULL REFERENCES a2a_event_topics(topic),
    cursor TEXT NOT NULL UNIQUE,
    subject TEXT,
    event_type TEXT NOT NULL,
    payload JSONB NOT NULL,
    content_hash TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE a2a_subscriptions (
    subscription_id TEXT PRIMARY KEY,
    publisher_card_url TEXT NOT NULL,
    subscriber_card_url TEXT NOT NULL,
    topics TEXT[] NOT NULL,
    selector JSONB NOT NULL DEFAULT '{}',
    delivery JSONB NOT NULL,
    status TEXT NOT NULL,
    lease_until TIMESTAMPTZ NOT NULL,
    -- per-topic last-acked cursor map: { "<topic>": "<cursor>", ... }
    cursors JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE a2a_delivery_attempts (
    delivery_attempt_id TEXT PRIMARY KEY,
    subscription_id TEXT NOT NULL REFERENCES a2a_subscriptions(subscription_id),
    event_id TEXT NOT NULL REFERENCES a2a_events(event_id),
    attempt INTEGER NOT NULL,
    status TEXT NOT NULL,
    last_status_code INTEGER,
    last_error TEXT,
    next_retry_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE a2a_event_acks (
    subscription_id TEXT NOT NULL REFERENCES a2a_subscriptions(subscription_id),
    event_id TEXT NOT NULL REFERENCES a2a_events(event_id),
    cursor TEXT NOT NULL,
    acked_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (subscription_id, event_id)
);
```

This schema is a reference implementation detail, not a protocol requirement.

---

## 26. SDK Layering

The SDKs should be split into three levels.

### 26.1 Protocol SDK

Available in every supported language.

Includes:

```text
types
JSON Schema validation
CloudEvents helpers
AgentCard extension helpers
JSON-RPC envelope + error helpers
signature sign/verify
opaque cursor handling (store + compare, no parsing)
error model
conformance fixtures
```

### 26.2 Client SDK

Used by subscriber agents.

Includes:

```text
discover topics
create subscription
renew lease automatically
delete subscription
receive event
verify signature
deduplicate event IDs
ack event
replay missed events
```

### 26.3 Server/runtime SDK

Used by publisher agents.

Includes:

```text
declare topics
accept subscriptions
validate selectors
manage leases
store events
match events to subscriptions
deliver events
retry
dead-letter
replay
observability
```

Not every language needs a full server runtime in v0.1.

Recommended v0.1 language coverage:

```text
Python: protocol SDK + client SDK + full reference runtime
TypeScript/JavaScript: protocol SDK + client SDK + receiver helpers
Go: protocol SDK + client SDK
```

---

## 27. Repository Strategy

The project has split into two repositories, designed to stay independent while
referencing each other:

```text
a2a-events          # this repo — the language-neutral source of truth
                    #   DESIGN.md, docs/, schemas/, conformance/, cross-language tests
a2a-events-python   # the Python SDK and reference runtime
```

- **`a2a-events`** owns the contract: the spec (`DESIGN.md`), the published JSON
  Schemas (`schemas/`), the conformance vectors (`conformance/`), the docs, and
  the cross-language conformance runner. It is language-neutral.
- **`a2a-events-python`** holds the implementation. For self-containment it
  *vendors* a copy of `schemas/` and `conformance/fixtures/` from this repo
  (refreshed by its `scripts/sync_spec.py`) so its tests and CI need no second
  checkout. The schemas are generated from the Python models
  (`scripts/export_schemas.py`); this repo remains the published source of truth.

Future language SDKs (`a2a-events-js`, `a2a-events-go`, …) follow the same
pattern: their own repo, vendoring the contract from here.

The `a2a-events` repository remains the source of truth for the protocol spec,
the AgentCard extension, schemas, conformance tests and vectors, the security
model, and the versioning policy. Each language SDK consumes the schemas and
conformance vectors from this repo.

---

## 28. CLI Design

### 28.1 Inspect AgentCard

```bash
a2a-events inspect https://agent-b.example.com/.well-known/agent-card.json
```

Output:

```text
Agent: Crawler Agent
A2A Events: supported
Role: publisher
Topics:
  - agent_card.discovered
  - agent_card.updated
  - search.results.updated
Delivery modes:
  - webhook
  - a2a-message
Replay: supported
```

### 28.2 List topics

```bash
a2a-events topics https://agent-b.example.com/.well-known/agent-card.json
```

### 28.3 Subscribe

```bash
a2a-events subscribe \
  --publisher https://agent-b.example.com/.well-known/agent-card.json \
  --subscriber https://agent-a.example.com/.well-known/agent-card.json \
  --topic agent_card.discovered \
  --from latest
```

### 28.4 Subscribe to search results

```bash
a2a-events subscribe-search \
  --publisher https://agent-b.example.com/.well-known/agent-card.json \
  --subscriber https://agent-a.example.com/.well-known/agent-card.json \
  --keywords "A2A,AgentCard,subscription" \
  --match all
```

### 28.5 Replay

```bash
a2a-events replay \
  --subscription sub_01HY8Y5K3N7V4Z9WHE4RYMZG5G \
  --from agent_card.discovered:0000000000000040
```

### 28.6 Validate event

```bash
a2a-events validate-event event.json
```

---

## 29. JSON-RPC Method Surface

JSON-RPC is the canonical A2A Events transport ([§12.3](#123-transport-and-invocation-json-rpc-primary)).
Method names use the `a2a.events.*` namespace, mirroring A2A core's `a2a.*`
methods. Each method's `params` and `result` are the request/response bodies
shown for the corresponding operation above. Every request carries the
`A2A-Extensions` header and authenticates via the publisher's A2A
`securitySchemes`.

The optional `HTTP+JSON` binding (selected via `preferredTransport` /
`additionalInterfaces`) maps each method to the verb/path in the right-hand
column. That binding is provided for non-JSON-RPC clients and is not
required for conformance.

| Operation              | JSON-RPC method (canonical)       | HTTP+JSON binding (optional)                                |
| ---------------------- | --------------------------------- | ----------------------------------------------------------- |
| List topics            | `a2a.events.ListTopics`           | `GET /a2a-events/topics`                                    |
| Create subscription    | `a2a.events.Subscribe`            | `POST /a2a-events/subscriptions`                            |
| Get subscription       | `a2a.events.GetSubscription`      | `GET /a2a-events/subscriptions/{subscriptionId}`            |
| List subscriptions     | `a2a.events.ListSubscriptions`    | `GET /a2a-events/subscriptions`                             |
| Renew subscription     | `a2a.events.RenewSubscription`    | `POST /a2a-events/subscriptions/{subscriptionId}:renew`     |
| Delete subscription    | `a2a.events.DeleteSubscription`   | `DELETE /a2a-events/subscriptions/{subscriptionId}`         |
| Replay events          | `a2a.events.Replay`               | `POST /a2a-events/subscriptions/{subscriptionId}:replay`    |
| Ack event              | `a2a.events.Ack`                  | `POST /a2a-events/subscriptions/{subscriptionId}:ack`       |
| List delivery attempts | `a2a.events.ListDeliveryAttempts` | `GET /a2a-events/subscriptions/{subscriptionId}/deliveries` |

**Delivery (publisher → subscriber)** is not in the `a2a.events.*` namespace
because it reuses A2A core messaging: canonical delivery is A2A
`a2a.SendMessage` to the subscriber's endpoint (§18.1); the webhook
alternative is `POST /a2a-events/receive` (§18.2).

---

## 30. Error Model

Errors are returned as **JSON-RPC 2.0 error objects**, consistent with A2A
core. The numeric `code` is a JSON-RPC code; the symbolic A2A Events code and
any structured details travel in `data`.

```json
{
  "jsonrpc": "2.0",
  "id": "1",
  "error": {
    "code": -32010,
    "message": "Topic agent.deleted does not exist.",
    "data": {
      "code": "TOPIC_NOT_FOUND",
      "topic": "agent.deleted"
    }
  }
}
```

A2A Events uses the JSON-RPC server-error range `-32000..-32099` for its
protocol errors and reuses the standard JSON-RPC codes (`-32600` invalid
request, `-32601` method not found, `-32602` invalid params, `-32700` parse
error) where applicable. The HTTP+JSON binding maps these to the
corresponding HTTP status codes (e.g. 404 for `TOPIC_NOT_FOUND`, 401/403 for
authorization failures, 429 for `RATE_LIMITED`).

Symbolic codes (carried in `data.code`):

```text
EXTENSION_NOT_SUPPORTED
TOPIC_NOT_FOUND
TOPIC_NOT_AUTHORIZED
SELECTOR_NOT_SUPPORTED
INVALID_SELECTOR
INVALID_CURSOR
CURSOR_EXPIRED
SUBSCRIPTION_NOT_FOUND
SUBSCRIPTION_EXPIRED
DELIVERY_MODE_NOT_SUPPORTED
SUBSCRIBER_CARD_UNREACHABLE
SUBSCRIBER_CARD_INVALID
DELIVERY_ENDPOINT_NOT_DECLARED
SIGNATURE_INVALID
REPLAY_NOT_SUPPORTED
RATE_LIMITED
LEASE_TOO_LONG
LEASE_TOO_SHORT
```

---

## 31. Retention

Each topic declares its retention policy.

Example:

```json
{
  "name": "agent_card.discovered",
  "retentionSeconds": 604800,
  "replay": true
}
```

**Lease validity does not guarantee replayability.** A subscription's lease
and a topic's retention are independent. If `retentionSeconds` is shorter
than `maxLeaseSeconds`, a subscriber whose lease is still valid may still
have an expired cursor after being offline longer than retention. In that
case replay (or resuming `fromCursor`) fails with `CURSOR_EXPIRED` even
though the subscription is active; the subscriber should resume from
`oldestAvailableCursor` or `latest` and accept the gap. Publishers should
document this relationship per topic.

If a subscriber asks to replay from an expired cursor, the publisher should
return (JSON-RPC error object, §30):

```json
{
  "jsonrpc": "2.0",
  "id": "1",
  "error": {
    "code": -32016,
    "message": "The requested cursor is outside the topic retention window.",
    "data": {
      "code": "CURSOR_EXPIRED",
      "fromCursor": "agent_card.discovered:0000000000000040",
      "oldestAvailableCursor": "agent_card.discovered:0000000000000088"
    }
  }
}
```

---

## 32. Observability

The runtime should expose:

```text
published events count
delivery attempts count
delivery success rate
delivery latency
retry count
dead-letter count
subscription count
expired subscription count
oldest unacked cursor
subscriber error rate
selector match rate
lease renewal rate
```

Recommended tracing fields:

```text
traceId
event.id
topic
cursor
subscriptionId
publisherAgentId
subscriberAgentId
deliveryAttemptId
selector.type
```

---

## 33. Conformance

A2A Events should include conformance test cases.

Example cases:

```text
valid minimal subscription is accepted
unknown topic is rejected
invalid selector is rejected
unsupported delivery mode is rejected
subscription expires without renewal
renew extends lease
event with invalid signature is rejected
event with unknown subscriptionId is rejected
duplicate eventId is deduplicated
replay from valid cursor returns matching events
replay from expired cursor returns CURSOR_EXPIRED
publisher refuses arbitrary callback URL not declared in AgentCard
```

Conformance is what allows multiple implementations to exist without forcing a single backend.

---

## 34. Versioning

The extension URI must include a major version.

```text
https://example.com/a2a-events/extensions/events/v1
```

Breaking changes require a new URI.

```text
https://a2a.events/extensions/events/v2
```

Non-breaking capabilities may be declared as feature flags.

```json
{
  "params": {
    "features": [
      "replay",
      "signed-events",
      "dead-letter",
      "a2a-message-delivery",
      "sse"
    ]
  }
}
```

---

## 35. Example End-to-End Flow

### Step 1: Agent B publishes its AgentCard

```text
https://agent-b.example.com/.well-known/agent-card.json
```

The card declares:

```text
A2A Events extension
publisher role
topicsUrl
subscribeUrl
supported delivery modes
```

### Step 2: Agent A publishes its AgentCard

```text
https://agent-a.example.com/.well-known/agent-card.json
```

The card declares:

```text
A2A Events extension
subscriber role
receive endpoint
accepted delivery modes
```

### Step 3: Agent A discovers Agent B's topics

```http
GET /a2a-events/topics
```

### Step 4: Agent A creates a subscription

```http
POST /a2a-events/subscriptions
```

Agent B verifies Agent A's AgentCard and resolves the receive endpoint from the card.

### Step 5: Agent A renews the lease periodically

```http
POST /a2a-events/subscriptions/{subscriptionId}:renew
```

### Step 6: Agent B publishes a matching event

Agent B writes the event to its durable event log.

### Step 7: Agent B delivers the event

Agent B sends a signed CloudEvent to Agent A.

### Step 8: Agent A verifies and acknowledges

Agent A validates:

```text
publisher identity
signature
subscriptionId
topic
timestamp
event ID uniqueness
```

Then it returns a 2xx response or explicit ack.

### Step 9: Agent A recovers after downtime

If Agent A missed events, it replays from its last acknowledged cursor.

---

## 36. Why This Is Not Just Pub/Sub with A2A Branding

Generic Pub/Sub usually models:

```text
publisher -> topic -> subscriber endpoint
```

A2A Events models:

```text
agent -> declared capabilities -> authorized subscription -> AgentCard-addressed delivery -> recoverable event stream
```

The value is not in reinventing Pub/Sub. The value is in standardizing the glue required by agent networks:

```text
AgentCard discovery
extension negotiation
agent identity
capability-aware routing
safe endpoint resolution
lease lifecycle
selector validation
signed event delivery
cursor replay
A2A-message fallback
conformance across SDKs
```

If AgentCard can be removed without changing the project, the design is too thin.

AgentCard should be fundamental to:

```text
subscriber identity
delivery endpoint resolution
accepted delivery modes
skills
security requirements
extension negotiation
```

---

## 37. Open Questions

### 37.1 Resolved in this draft

These were previously open but are now decided normatively above and are no
longer blockers for v0.1 interop:

```text
- Signing key discovery: publisher declares a JWKS signingKeysUrl (§21.3).
- Agent authentication: reuse A2A securitySchemes; delivery token is minted
  per subscription at creation (§21.1).
- Cursor grammar: opaque to subscribers, lexicographically ordered per
  topic; cursors index the topic log, not the filtered stream (§10.9).
- Selector matching semantics: field_filter is any-of within a field, AND
  across fields, exact typed comparison; keyword_search is case-insensitive
  substring with match all|any (§10.4).
- Ack: implicit on HTTP 2xx for MVP webhook; explicit ack/nack optional
  (§10.10).
- Routing key: a2aevents.topic is authoritative; CloudEvents type is
  descriptive only (§16.1).
- Multi-topic cursor state: per-topic cursor map (§10.9, §23.1).
- Transport: JSON-RPC is canonical (`a2a.events.*`); HTTP+JSON is an
  optional binding; canonical delivery is A2A `a2a.SendMessage` (§12.3,
  §18.1, §29).
```

### 37.2 Still open

1. Should the optional HTTP+JSON binding ship in v0.1, or should v0.1 be JSON-RPC-only?
2. Should webhook delivery be required in v0.1, or is A2A-message delivery alone sufficient for MVP?
3. Should A2A `AgentCardSignature` verification be required or only recommended for A2A Events participants?
4. Should same-origin between `subscriberCardUrl` and `receiveUrl` be mandatory?
5. Should search subscriptions be part of the core spec or a separate topic profile?
6. Should the Python reference runtime live in the main repo initially?
7. Should external broker delivery modes be postponed until v0.2 or v1.0?
8. Should topic naming follow a recommended namespace convention?
9. Should replay return full event envelopes only, or allow compact batches?

---

## 38. Recommended Initial Scope

Build the first version around one strong use case:

```text
AgentCard-native event subscriptions for an A2A agent directory/crawler.
```

Initial topics:

```text
agent_card.discovered
agent_card.updated
agent.status_changed
block.created
block.updated
search.results.updated
```

Initial implementation:

```text
Python
FastAPI
Postgres
webhook delivery
in-memory dev mode
CLI
JSON Schema
OpenAPI
conformance fixtures
```

This gives the project a narrow but meaningful wedge.

---

## 39. Final Positioning

A2A Events should not be positioned as:

```text
better Kafka
better WebSocket
generic Pub/Sub
webhook wrapper
```

It should be positioned as:

```text
the missing subscription layer for AgentCard-native A2A systems
```

This positioning is backed by prior-art research ([`docs/prior-art.md`](docs/prior-art.md)):
A2A core only offers task-scoped push notifications and SSE, no official or
third-party durable topic-subscription protocol exists, and the open demand
signal ([a2aproject/A2A#1593](https://github.com/a2aproject/A2A/issues/1593))
has no competing design.

The project defines the protocol and provides SDKs and a battery-included reference runtime. Publisher agents are free to implement the backend however they want, as long as they satisfy the protocol and conformance requirements.

The product-level promise is:

```text
Give agents durable, safe, replayable subscriptions to other agents' future events.
```

