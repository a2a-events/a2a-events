# Prior Art and Positioning

> Research date: 2026-06-19
> Scope: does a durable, AgentCard-native, topic-based event subscription
> protocol already exist for A2A — officially or in the community?
> Companion: [`docs/a2a-reference.md`](a2a-reference.md) (A2A v1.0 primitives we build on).

**Conclusion: genuine whitespace.** No official or third-party project
defines a durable, AgentCard-native, topic-based agent-to-agent event
subscription protocol with leases, cursors, and replay. Demand is documented
but the design space is empty. A2A Events is not duplicating existing work,
and its extension-based approach is idiomatic to A2A's extension framework.

---

## 1. A2A official status

### 1.1 No events / pub-sub extension exists

A2A maintains an official extension registry under the `a2aproject` GitHub
org (`ext-*` / `experimental-ext-*` repos) and the
`https://a2a-protocol.org/extensions/` URI prefix. As of the research date
the only published/example extensions are:

| Extension                    | Purpose                                  |
| ---------------------------- | ---------------------------------------- |
| Secure Passport              | Contextual personalization layer         |
| Timestamp ("Hello World")    | Augments `Message` / `Artifact` metadata |
| Traceability                 | Request tracing (Python)                 |
| Agent Gateway Protocol (AGP) | Routing via squads/capabilities          |
| OID4VP Auth (experimental)   | In-task authorization                    |

None are event-, subscription-, pub/sub-, or notification-oriented.

### 1.2 A2A core only covers task-scoped patterns

A2A core provides task-scoped asynchronous mechanisms only:

- **Push notifications** — webhook updates bound to a single task
  (`PushNotificationConfig`).
- **SSE streaming** — live status/artifact updates for an active task.
- **`a2a.SubscribeToTask`** — subscribe to one task's event stream.

All three are scoped to a task lifecycle. There is no durable, topic-based,
publisher-declared event stream that a subscriber can subscribe to across
many future, independent events — which is precisely the gap A2A Events
fills (see spec §3, §81).

### 1.3 The extension framework fits this design

A2A formally defines four extension types, and A2A Events maps onto them
cleanly:

| A2A extension type | A2A Events usage                                                            |
| ------------------ | --------------------------------------------------------------------------- |
| Data-only          | AgentCard `params` (topics URL, signing keys URL, delivery modes)           |
| Profile            | CloudEvents envelope + selector/lease/cursor semantics overlaid on messages |
| Method             | the `a2a.events.*` JSON-RPC methods                                         |
| State machine      | subscription lifecycle (active → expired → deleted)                         |

The approach is idiomatic rather than working against the protocol.

---

## 2. Demand signal

- **[a2aproject/A2A#1593 — "Built-in Pub/Sub support in the A2A protocol"](https://github.com/a2aproject/A2A/issues/1593)**
  is **open but early-stage**: no maintainer response, no labels/milestone,
  and **no design** (no mention of durability, topics, leases, cursors, or
  replay). It is a brief feature request citing Vertex AI's Cloud Pub/Sub
  integration. This validates demand and is an open door for A2A Events to be
  posted as a concrete community proposal.
- **[a2aproject/A2A#585 — "A2A API Extensions"](https://github.com/a2aproject/A2A/issues/585)**
  is the discussion that produced the *method-extension* capability A2A
  Events relies on (adding new RPC methods to an A2A server).

---

## 3. Adjacent third-party projects (not competitors)

Several event-driven A2A projects exist, but they operate one layer *below*
this protocol — they use brokers as **transport/backend**, which the spec
§8 explicitly treats as an internal implementation detail, not protocol
surface:

| Project                       | What it is                                                   | Relationship                     |
| ----------------------------- | ------------------------------------------------------------ | -------------------------------- |
| Apache RocketMQ A2A           | RocketMQ as an A2A transport binding                         | Internal transport               |
| Solace Agent Mesh             | Event-driven multi-agent orchestration over Solace messaging | Internal backend / orchestration |
| AgentAnycast                  | libp2p P2P runtime for A2A                                   | Internal transport               |
| Redis / Temporal integrations | Task persistence & durable workflow execution                | Internal backend                 |

None define agent-to-agent durable **topic subscriptions** with AgentCard
addressing, leases, cursors, and replay. They validate the "broker is an
internal backend" model rather than competing with it.

---

## 4. Naming and namespace

- No existing `a2a-events` package/project usage was found — the name appears
  free in package-registry space.
- The `a2a.events` domain is already registered, so the extension URI uses the
  RFC 2606 demo domain: `https://example.com/a2a-events/extensions/events/v1`.
  This is a valid **third-party** namespace; A2A allows anyone to publish
  extensions under their own URI.
- If A2A Events were ever adopted as an **official** extension, convention
  would move it to `https://a2a-protocol.org/extensions/...` with an
  `a2aproject/ext-events` repo.

---

## 5. Implications for A2A Events

1. **Proceed** — the design fills a documented gap and does not duplicate
   official or community work.
2. **Stay idiomatic** — reuse A2A primitives verbatim (spec §6.1);
   the extension framework already supports everything needed.
3. **Activation handshake** — A2A extension activation is a negotiation: the
   agent must echo activated extension URIs in the `A2A-Extensions` response
   header (folded into spec §12.3).
4. **Engage upstream** — consider posting the design to issue #1593 to gauge
   maintainer appetite before heavy investment.

---

## Sources

- A2A specification — https://a2a-protocol.org/latest/specification/
- A2A extensions framework — https://a2a-protocol.org/latest/topics/extensions/
- Issue #1593 (Built-in Pub/Sub) — https://github.com/a2aproject/A2A/issues/1593
- Issue #585 (API Extensions) — https://github.com/a2aproject/A2A/issues/585
- a2aproject org repositories — https://github.com/a2aproject
- awesome-a2a — https://github.com/ai-boost/awesome-a2a
