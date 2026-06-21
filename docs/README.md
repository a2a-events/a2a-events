# A2A Events Documentation

Introductory documentation for the A2A Events protocol — an
[A2A](https://a2a-protocol.org) extension for durable, AgentCard-native event
subscriptions between agents.

Start here, in order:

1. **[Introduction](introduction.md)** — what A2A Events is, the problem it
   solves, the "subscribe to agents, not URLs" mental model, and how it relates
   to A2A core. Start here.
2. **[Protocol Guide](protocol-guide.md)** — a wire-level tour: discovery, the
   subscription lifecycle, topics & selectors, cursors, the event envelope,
   delivery modes, ack/replay, the method surface, and the security & error
   models.
3. **[Getting Started](getting-started.md)** — run the full flow in code:
   in-memory, then over HTTP, then across containers.
4. **[Scaling and Implementation Notes](scaling.md)** — non-normative guidance
   for building and operating a publisher: where the reference impl stops
   scaling, how to scale fan-out, and operational recommendations.

## Reference material

- [`DESIGN.md`](../DESIGN.md) — the normative specification (the source of truth).
- [`docs/a2a-reference.md`](a2a-reference.md) — a non-authoritative snapshot of
  the A2A v1.0 primitives this extension builds on.
- [`schemas/`](../schemas) — JSON Schemas generated from the models.
- [`conformance/`](../conformance) — conformance vectors.
- [`prior-art.md`](prior-art.md) — prior art and positioning.

These intro docs summarize and link into `DESIGN.md`; where they disagree, the
design wins.
