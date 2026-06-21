# Getting Started

This page runs the A2A Events flow end to end — declare a topic, subscribe with
a selector, publish events, observe signed delivery and implicit ack, then
replay. It starts fully in-memory (no network, no database) so you can see the
whole protocol in one file, then points at the HTTP and multi-container setups.

If you haven't yet, read the [Introduction](introduction.md) for the mental
model and the [Protocol Guide](protocol-guide.md) for the wire details.

---

## Install

The Python reference implementation lives in its own repository,
[`a2a-events-python`](https://github.com/a2a-events/a2a-events-python). It uses
[uv](https://docs.astral.sh/uv/). For local development:

```bash
git clone https://github.com/a2a-events/a2a-events-python
cd a2a-events-python
uv sync --extra dev
uv run pytest        # the full test suite
```

Optional extras pull in the transports/backends you need:

- `server` / `client` — the FastAPI publisher & subscriber apps and the httpx transport.
- `postgres` — the durable Postgres event/subscription stores and retry queue.
- `grpc` — the gRPC binding.

## The 60-second in-memory tour

The reference runtime has an `InMemoryTransport` that wires a publisher and
subscriber together with no network, so the entire lifecycle fits in one script.
This is [`examples/quickstart.py`](https://github.com/a2a-events/a2a-events-python/blob/main/examples/quickstart.py)
in the `a2a-events-python` repo — run it with
`uv run python examples/quickstart.py` from that repo's root:

```python
import asyncio

from a2a_events import (
    A2AEventsPublisher,
    InMemorySubscriber,
    InMemoryTransport,
    PublisherConfig,
    SigningKey,
    Topic,
)
from a2a_events.jsonrpc import handle

PUBLISHER_CARD = "https://agent-b.example.com/.well-known/agent-card.json"
SUBSCRIBER_CARD = "https://agent-a.example.com/.well-known/agent-card.json"
TOPIC = "agent_card.discovered"


async def main() -> None:
    transport = InMemoryTransport()
    key = SigningKey.generate("key_2026_06")

    # The subscriber half: registers receive endpoints on the transport and
    # exposes a card the publisher can "discover".
    subscriber = InMemorySubscriber(
        card_url=SUBSCRIBER_CARD,
        transport=transport,
        key_resolver=lambda _kid: key.public_key,   # verify signatures
    )

    # The publisher half: signs events, resolves the subscriber's card.
    publisher = A2AEventsPublisher(
        agent_card_url=PUBLISHER_CARD,
        transport=transport,
        signing_key=key,
        config=PublisherConfig(card_resolver=lambda _url: subscriber.card()),
    )
    publisher.declare_topic(
        Topic(name=TOPIC, filterableFields=["data.cardUrl", "data.capabilities"])
    )

    # Subscribe over the canonical JSON-RPC surface: only streaming-capable
    # cards, delivered as A2A messages.
    sub = await handle(
        publisher,
        {
            "jsonrpc": "2.0",
            "id": "1",
            "method": "a2a.events.Subscribe",
            "params": {
                "subscriberCardUrl": SUBSCRIBER_CARD,
                "topics": [TOPIC],
                "selector": {
                    "type": "field_filter",
                    "where": {"data.capabilities": ["streaming"]},
                },
                "delivery": {"mode": "a2a-message"},
                "fromCursor": "latest",
                "leaseSeconds": 3600,
            },
        },
    )
    sub_id = sub["result"]["subscriptionId"]

    # Publish: one event matches the selector, one does not.
    await publisher.publish(TOPIC, "discovered.v1", {"cardUrl": "https://x", "capabilities": ["streaming"]})
    await publisher.publish(TOPIC, "discovered.v1", {"cardUrl": "https://y", "capabilities": ["batch"]})

    print(f"delivered {len(subscriber.received)} event(s)")   # -> 1, the selector filtered the other

    # Replay the topic from the start of retention.
    replay = await handle(
        publisher,
        {
            "jsonrpc": "2.0",
            "id": "2",
            "method": "a2a.events.Replay",
            "params": {"subscriptionId": sub_id, "fromCursor": "earliest"},
        },
    )
    print(f"replay returned {len(replay['result']['events'])} matching event(s)")


if __name__ == "__main__":
    asyncio.run(main())
```

What this exercises, mapped to the [Protocol Guide](protocol-guide.md):

| Step                        | Protocol concept                                         |
| --------------------------- | -------------------------------------------------------- |
| `declare_topic(...)`        | Topic declaration (§2)                                   |
| `card_resolver`             | AgentCard discovery (§1)                                 |
| `a2a.events.Subscribe`      | Subscription lifecycle + lease (§3)                      |
| `selector: field_filter`    | Server-side filtering within a topic (§2)                |
| `publish(...)` → `received` | Signed A2A-message delivery (§5, §6) + implicit ack (§7) |
| `a2a.events.Replay`         | Replay from a cursor (§7)                                |

Notice you never wrote a delivery URL: the publisher got it from the
subscriber's card via `card_resolver`. Over the network that resolver is an
`AgentCardResolver` that fetches and trust-checks the real card.

## Going over HTTP

Swap the in-memory pieces for the FastAPI apps (needs the `server`/`client`
extras). The shapes are identical — same JSON-RPC methods, same envelope:

```python
from a2a_events.server import create_publisher_app, create_subscriber_app
```

- `create_publisher_app(publisher)` serves the canonical JSON-RPC endpoint
  (`POST /a2a-events/jsonrpc`), the JWKS endpoint (`GET /a2a-events/keys`), and
  the optional HTTP+JSON binding (the `GET/POST/DELETE /a2a-events/...` routes
  from the method-surface table).
- `create_subscriber_app(receiver)` serves the A2A endpoint (`POST /a2a/v1`) and
  the webhook receive endpoint (`POST /a2a-events/receive`).

On the publisher you opt into the production features by passing collaborators to
`A2AEventsPublisher` — a Postgres `store`/`subscription_store`, a `retry_queue`
(plus a `RetryWorker`), an `authorizer`, a `delivery_token_issuer`, a `metrics`
sink, `page_size`, and so on. Each is independent; you add only what you need.
The subscriber verifies signatures via a `JwksKeyResolver` pointed at the
publisher's `/a2a-events/keys`.

## See it across containers

The most complete example is the multi-container end-to-end suite. It builds an
image, brings up Postgres + a publisher service + a subscriber service on a
private Docker network, and runs a host driver that exercises **every** feature
over the real network — discovery + trust, signed delivery with JWKS, delivery
tokens, topic authorization, durable retry, pagination, retention compaction,
observability, timestamp-skew rejection, auto lease renewal, and durable
subscriptions surviving a publisher restart:

```bash
./e2e/run.sh        # from the a2a-events-python repo root
```

The service wiring in
[`e2e/publisher_service.py`](https://github.com/a2a-events/a2a-events-python/blob/main/e2e/publisher_service.py) and
[`e2e/subscriber_service.py`](https://github.com/a2a-events/a2a-events-python/blob/main/e2e/subscriber_service.py) is a
good reference for a production-shaped deployment, and
[`e2e/driver.py`](https://github.com/a2a-events/a2a-events-python/blob/main/e2e/driver.py) shows each feature being driven
over HTTP.

## Where to go next

- [Protocol Guide](protocol-guide.md) — the wire protocol in depth.
- [the specification](https://a2a-events.github.io/a2a-events/specification/) — the normative specification.
- [`schemas/`](https://github.com/a2a-events/a2a-events/tree/main/schemas) — JSON Schemas generated from the models.
- [`conformance/`](https://github.com/a2a-events/a2a-events/tree/main/conformance) — conformance vectors.
