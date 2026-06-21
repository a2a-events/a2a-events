# A2A v1.0 Reference Snapshot

> Snapshot date: 2026-06-19
> Source of truth: the official A2A specification, not this file.
> Spec: https://a2a-protocol.org/latest/specification/
> Repo: https://github.com/a2aproject/A2A
> Governance: Linux Foundation. Version baseline for A2A Events: **A2A v1.0**.

This file is a **non-authoritative snapshot** of the A2A core definitions
that A2A Events depends on. It exists so the design can be reviewed without a
live network round-trip and so we can detect drift. If anything here
conflicts with the official A2A specification, the official specification
wins and this file (and `DESIGN.md`) must be corrected.

A2A Events is an extension on top of these primitives and must not redefine
them (see `DESIGN.md` §6.1).

---

## 1. AgentCard (selected fields)

| Field                  | Type                      | Notes                                                         |
| ---------------------- | ------------------------- | ------------------------------------------------------------- |
| `id`                   | string                    | Unique agent identifier.                                      |
| `name`                 | string                    | Human-readable agent name.                                    |
| `description`          | string                    | Agent purpose.                                                |
| `capabilities`         | `AgentCapabilities`       | Declared optional features (below).                           |
| `securitySchemes`      | map                       | Authentication methods the agent supports.                    |
| `security`             | array                     | Which schemes apply to which operations.                      |
| `preferredTransport`   | string                    | Primary transport binding (`JSONRPC` / `GRPC` / `HTTP+JSON`). |
| `additionalInterfaces` | array of `AgentInterface` | Alternative endpoints/transports.                             |
| `signatures`           | `AgentCardSignature`      | Cryptographic signature(s) over the card.                     |
| `skills`               | array of `AgentSkill`     | Declared skills.                                              |

> Note: A2A v1.0 expresses endpoints via `preferredTransport` /
> `additionalInterfaces`. Card examples in `DESIGN.md` are illustrative and
> may omit required A2A fields.

## 2. AgentCapabilities

| Field                    | Type                      | Notes                                                         |
| ------------------------ | ------------------------- | ------------------------------------------------------------- |
| `streaming`              | boolean                   | Server supports `SendStreamingMessage` and `SubscribeToTask`. |
| `pushNotifications`      | boolean                   | Server supports webhook-based task updates.                   |
| `stateTransitionHistory` | boolean                   | Task state-transition logs available.                         |
| `extendedAgentCard`      | boolean                   | Server offers an authenticated extended card.                 |
| `extensions`             | array of `AgentExtension` | Extended capabilities beyond core A2A.                        |

## 3. AgentExtension

| Field         | Type    | Notes                                                                                            |
| ------------- | ------- | ------------------------------------------------------------------------------------------------ |
| `uri`         | string  | Unique extension identifier (A2A Events: `https://example.com/a2a-events/extensions/events/v1`). |
| `description` | string  | What the extension does.                                                                         |
| `required`    | boolean | Whether client support is mandatory.                                                             |
| `params`      | object  | Extension-specific configuration. **All A2A Events config lives here.**                          |

## 4. Transports

A2A defines three transport bindings; an agent declares support via
`preferredTransport` and `additionalInterfaces` (`AgentInterface` objects
carry the endpoint URL and binding type):

- `JSONRPC` — JSON-RPC 2.0 over HTTP (and SSE for streaming).
- `GRPC` — Protocol Buffers over gRPC.
- `HTTP+JSON` — RESTful HTTP with JSON payloads.

## 5. Extension activation header

Clients activate extensions with the `A2A-Extensions` request parameter
(HTTP header or query parameter): a comma-separated list of extension URIs
the client wants to use for the request.

Example: `A2A-Extensions: https://example.com/a2a-events/extensions/events/v1`

## 6. Message and Part

`Message`:

| Field              | Type              | Notes                                                        |
| ------------------ | ----------------- | ------------------------------------------------------------ |
| `messageId`        | string            | Unique message id.                                           |
| `contextId`        | string (optional) | Conversation context grouping.                               |
| `taskId`           | string (optional) | Associated task.                                             |
| `role`             | `Role`            | `ROLE_USER` (client→server) or `ROLE_AGENT` (server→client). |
| `parts`            | array of `Part`   | Message content.                                             |
| `referenceTaskIds` | array             | Related task ids.                                            |

`Part` (exactly one content field):

- `TextPart` — `text` (string)
- `FilePart` — `url` (remote reference) or `raw` (embedded bytes), plus `mediaType` / `filename`
- `DataPart` — `data` (structured JSON)

A2A Events' A2A-message delivery uses a `Message` with `role: ROLE_AGENT`
and a `DataPart` carrying the CloudEvent.

## 7. AgentCardSignature

A2A v1.0 signs AgentCards using **JWS (RFC 7515)** computed over a
**JCS-canonicalized (RFC 8785)** form of the card, so signatures are stable
across serializers. A2A Events reuses this for card authenticity and does
**not** define its own card-signing scheme. (A2A Events' event-payload
signatures are a separate addition — A2A signs cards, not events — but
mirror the same JCS canonicalization for consistency.)

## 8. Push notifications (task-scoped)

`PushNotificationConfig` / `TaskPushNotificationConfig`:

| Field            | Type                 | Notes                       |
| ---------------- | -------------------- | --------------------------- |
| `id`             | string               | Config id.                  |
| `taskId`         | string               | Associated task.            |
| `url`            | string               | Webhook endpoint.           |
| `token`          | string (optional)    | Auth token for the webhook. |
| `authentication` | `AuthenticationInfo` | Delivery auth credentials.  |

A2A push notifications are **task-scoped**. A2A Events is the separate,
durable, topic-scoped subscription layer and does not replace them.

## 9. Core RPC methods (for orientation)

A2A defines a set of JSON-RPC methods, including `SendMessage`,
`SendStreamingMessage`, `GetTask`, `SubscribeToTask`,
`CreateTaskPushNotificationConfig`, and related task/config operations.
A2A Events operations (subscribe / renew / delete / list / replay / receive /
ack) are **new** operations the extension adds; they do not exist in A2A
core and are layered on the A2A transports above.
