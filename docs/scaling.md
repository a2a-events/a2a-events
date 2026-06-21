# Scaling and Implementation Notes

> **Non-normative.** This is implementation guidance for people building or
> operating an A2A Events publisher, not part of the protocol. The wire
> protocol is defined in [`DESIGN.md`](../DESIGN.md); nothing here changes it.
> Where this doc describes the reference implementation, it cites the source so
> you can check it against the code you actually have.

The Python reference implementation (`a2a-events-python/src/a2a_events/`) is a correct,
durable, single-process publisher. It is deliberately simple: it favors obvious
semantics over throughput so it can anchor conformance tests and demonstrate the
protocol. This document explains where that simplicity stops scaling, what to
change as your subscriber count and event rate grow, and a handful of other
recommendations that come up once a deployment is real.

The good news is that the runtime is split along a contract/implementation seam
([`runtime/contracts.py`](https://github.com/a2a-events/a2a-events-python/blob/main/src/a2a_events/runtime/contracts.py): the
`EventStore`, `SubscriptionStore`, `RetryQueue`, and `Transport` Protocols).
Most of what follows can be implemented behind those contracts — a different
backend, a different delivery tier — without touching the protocol or the
publisher's control plane.

---

## 1. How delivery works today

`A2AEventsPublisher.publish()`
([`publisher.py`](https://github.com/a2a-events/a2a-events-python/blob/main/src/a2a_events/runtime/publisher.py)) does this on
every publish:

```python
record = await self._run_store(self.store.append, ...)   # 1. durably append
for sub in await self._run_store(self.subs.list_all):    # 2. scan ALL subs
    ... # topic check, auth, high-water, selector match
    await self._deliver_one(sub, record)                 # 3. deliver, inline, one at a time
```

Three properties of this loop dominate behavior at scale:

- **Fan-out is sequential.** Subscriber *N+1*'s delivery is not started until
  *N*'s `await` returns. With `N` subscribers and per-delivery round-trip `L`, a
  single `publish()` takes ≈ `N × L` of wall-clock and the caller is blocked for
  all of it. At 10k subscribers × 50 ms that is ~500 s for one event.
- **Throughput is capped by serialization, not the network.** Because only one
  delivery is ever in flight, you get at most `1/L` deliveries per second no
  matter how much bandwidth exists. You are starving the link, not saturating
  it. *Network throughput only becomes the bottleneck after you add
  concurrency* — which is why that is the first change to make.
- **Dispatch cost scales with total subscribers, not matches.**
  `subs.list_all()` is scanned and selectors re-evaluated in Python on every
  publish, so CPU grows with the whole subscriber set even if one subscriber
  matches.

The `RetryQueue`/`RetryWorker` path
([`retry_worker.py`](https://github.com/a2a-events/a2a-events-python/blob/main/src/a2a_events/runtime/retry_worker.py)) already
removes retries from the hot path — the first failure enqueues a durable retry
and the loop moves on — but the **first** attempt is still synchronous and
serial. Without a retry queue, the inline exponential backoff sleeps happen
*inside* the fan-out loop (`_deliver_one`), so one slow or dead subscriber
stalls every subscriber behind it (head-of-line blocking).

---

## 2. Scaling fan-out

Roughly in order of value-for-effort.

### 2.1 Concurrent delivery within a publish (smallest change, biggest win)

Replace the serial `for` loop with bounded-concurrency fan-out: `asyncio.gather`
(or a task group) over the matching subscribers, gated by a semaphore that caps
in-flight deliveries (e.g. 200–1000). The bound is what keeps file descriptors,
sockets, and memory finite while still using the link.

This is a contained change in `publish()` and is independent of any backend.
Watch the interaction with **ordering** (§3.3) and with `offload_store` — the
store calls inside the loop (`high_water`, attempt recording, cursor advance)
become concurrent too, so the store must tolerate concurrent access (the pooled
Postgres backends do; the in-memory ones are single-threaded by design).

### 2.2 Decouple publish from delivery (the real fix for huge fan-out)

The durable model the protocol already assumes is a **log-and-pull** one:
*"cursors index the topic log, not the filtered delivery stream"* (DESIGN
§10.9). Lean into it:

1. `publish()` only appends to the `EventStore` and returns. It does **no**
   delivery.
2. A separate pool of **delivery workers** advances each subscription's cursor
   over the topic log, sends, and records acks/dead-letters — exactly the work
   `_deliver_one` does today, just out of band.

Why this matters at scale:

- A slow or dead subscriber falls behind *its own* cursor only. It cannot stall
  the publish path or other subscribers.
- Publish latency becomes O(append), independent of subscriber count.
- You get natural **backpressure** (a lagging subscriber's cursor simply trails)
  and **replay** for free (it is the same cursor read).
- Delivery workers are horizontally scalable (see §2.4).

This is the single most impactful change for large fan-out, and the contracts
already support it — `EventStore.read(topic, from_cursor, ...)` is the pull API.

### 2.3 Index subscriptions by topic

`publish()` (and a pull-based delivery worker) currently pays O(total
subscriptions) to find the matching ones. Add a `subscriptions_for_topic(topic)`
method to the `SubscriptionStore` contract and back it with an index
(`topic -> [subscription_id]`). Dispatch then costs O(matches). In Postgres this
is a `WHERE %s = ANY(topics)` with a GIN index; in memory it is a dict of sets.

### 2.4 Shard the fan-out horizontally

Partition subscriptions across worker instances by `hash(subscription_id) % K`.
Each instance owns a disjoint slice, reads the topic log, and delivers to its
slice. Because subscriptions, cursors, high-water marks, and the retry queue are
all durable behind the stores, instances are stateless and can be added or
restarted freely. This is how you go past one box.

### 2.5 Amortize signing across subscribers

Today each subscriber receives a **distinct** signed envelope: the event embeds
`subscriptionId`, `cursor`, and `deliveryAttempt`
(`publisher.py` `_build_event`), so the Ed25519 signature is computed
per-subscriber-per-event. At a fan-out of 10k that is 10k signatures per event —
a real CPU cost.

If you can make the signed payload **subscription-agnostic** (sign the event
once; carry `subscriptionId`/`cursor`/`attempt` as unsigned delivery metadata or
in a transport header), one signature serves every subscriber on that event.
This is a protocol-level decision about what the signature covers (DESIGN §16,
§21.3) — call it out explicitly rather than changing it silently, because it
changes what a subscriber's verification protects.

### 2.6 Reuse connections and use HTTP/2

For webhook/HTTP delivery, a fresh TCP+TLS handshake per delivery dominates cost
at scale. Use a shared `httpx` client with connection pooling and HTTP/2 so
deliveries to the same host multiplex over kept-alive connections. The
`Transport` contract already lets you supply such a client
([`http_delivery.py`](https://github.com/a2a-events/a2a-events-python/blob/main/src/a2a_events/runtime/http_delivery.py)).

### 2.7 Relay tiers / a real broker substrate

For very large or bursty fan-out, two options open up now that `Transport` and
`EventStore` are pluggable:

- **Relay tree** — intermediate publishers each subscribe and re-fan to a slice,
  turning one 1→N fan-out into a tree of bounded 1→k fan-outs.
- **Broker substrate** — back `EventStore`/`Transport` with Kafka, NATS
  JetStream, or Redis Streams and let the broker do fan-out and retention. The
  A2A Events publisher becomes the control plane (subscriptions, leases, auth,
  signing) over a delivery substrate built for throughput.

---

## 3. Other implementation recommendations

### 3.1 Postgres backend at scale

- **Append contention.** Per-topic append serializes on a transaction-scoped
  advisory lock (`pg_advisory_xact_lock(hashtext(topic))`,
  [`postgres/event_store.py`](https://github.com/a2a-events/a2a-events-python/blob/main/src/a2a_events/runtime/postgres/event_store.py))
  so concurrent publishes never collide on the UNIQUE cursor. This makes a
  single **hot topic** a serialization point. If one topic is very hot, shard it
  into sub-topics, or move cursor allocation to a sequence/identity column and
  drop the lock.
- **Table growth & partitioning.** `a2a_events` grows without bound between
  compactions. Partition by topic (or time) so retention compaction (DESIGN §31)
  becomes a partition drop instead of a bulk `DELETE`, and so per-topic reads hit
  one partition.
- **Indexes.** Reads order by `cursor` within a topic; make sure `(topic,
  cursor)` is indexed. The retry queue already indexes `next_retry_at`.
- **Wakeups.** Delivery workers polling the log add latency and load. Postgres
  `LISTEN/NOTIFY` on append (DESIGN §7.4 lists it) lets workers wake on new
  events instead of polling.
- **Pool sizing & offload.** The pooled backends check out a connection per
  call; with `PublisherConfig(offload_store=True, store_thread_safe=True)`
  blocking calls run in worker threads so they do not stall the event loop. Size `max_size`
  against your concurrency bound (§2.1) — an unbounded fan-out against a small
  pool just moves the queue from the network to the pool.

### 3.2 Retry queue tuning

`RetryWorker` defaults are `poll_interval=1.0s`, `batch=100`, `lease_seconds=60`
([`retry_worker.py`](https://github.com/a2a-events/a2a-events-python/blob/main/src/a2a_events/runtime/retry_worker.py)).

- `poll_interval` trades retry latency against load; pair it with
  `LISTEN/NOTIFY` (§3.1) if you need both low latency and low idle load.
- `lease_seconds` must comfortably exceed your worst-case single-delivery time,
  or a slow delivery's lease expires and a second worker re-attempts it
  (still safe — at-least-once — but wasteful).
- Add **jitter** to the exponential backoff so a broker-wide outage doesn't
  produce a synchronized retry stampede when it recovers (thundering herd).
- Run multiple workers: `claim_due` uses `FOR UPDATE SKIP LOCKED`, so workers
  cooperate without coordination.

### 3.3 Ordering under concurrency

The reference impl delivers a subscription's events in cursor order because it is
serial. **Concurrent fan-out (§2.1) and multiple delivery workers (§2.4) can
reorder deliveries** — across subscribers that is fine, but a single subscriber
generally expects in-order events. Preserve per-subscription ordering by
single-flighting each subscription (one in-flight delivery per
`subscription_id`, concurrency *across* subscriptions) and only advancing the
cursor/high-water on ack. Document the guarantee you actually provide; A2A Events
is at-least-once and explicitly **not** exactly-once (DESIGN §19.1–§19.3).

### 3.4 Receiver-side idempotency

At-least-once means a subscriber **will** occasionally see a duplicate (a
delivery that succeeded but whose ack was lost, a lease re-claim, a retry after a
crash). Receivers should dedupe on the stable event `id` (or `topic`+`cursor`)
and treat delivery as idempotent. This is a property of subscribers, not the
publisher, but it is the most common correctness bug in integrations, so call it
out in your subscriber docs.

### 3.5 Selector evaluation cost

Selectors are evaluated per-subscriber-per-event in Python
([`selectors.py`](https://github.com/a2a-events/a2a-events-python/blob/main/src/a2a_events/selectors.py)). At high fan-out this
is meaningful CPU. Combined with §2.3, evaluate selectors only for subscribers
already indexed to the topic; for very common selector shapes, consider
pre-compiling or grouping subscribers by selector so a match is computed once per
distinct selector rather than once per subscriber.

### 3.6 Observability you will want before you need it

The metrics seam ([`observability.py`](https://github.com/a2a-events/a2a-events-python/blob/main/src/a2a_events/observability.py))
already emits `published_events`, `selector_evaluations`, `delivery_attempts`,
`lease_renewals`, and a `delivery_latency_seconds` histogram. For scale, also
track:

- **Per-subscription lag** — `latest_cursor(topic) − subscription cursor`. This
  is the single best health signal in a pull model; it tells you who is falling
  behind before they dead-letter.
- **Retry queue depth** and oldest `next_retry_at` — backpressure and stuck
  retries.
- **Dead-letter rate** per subscription — a subscriber that is gone.
- **Delivery latency percentiles** (p50/p95/p99), not just a mean — fan-out tail
  latency is what hurts.

### 3.7 Security costs at scale

- **JWKS caching.** Subscribers refetch signing keys by `kid` on cache miss
  (DESIGN §21.3); make sure that cache is warm and bounded, or key rotation
  becomes a fetch storm.
- **SSRF checks.** Endpoint validation runs per delivery
  ([`runtime/ssrf.py`](https://github.com/a2a-events/a2a-events-python/blob/main/src/a2a_events/runtime/ssrf.py)); cache resolved
  decisions per endpoint rather than re-resolving on every send.

---

## 4. A suggested evolution path

You do not need all of this at once. A pragmatic order:

1. **Bounded-concurrency fan-out** (§2.1) — unblocks throughput immediately, one
   localized change.
2. **Topic→subscription index** (§2.3) — stops paying for idle subscribers.
3. **Decouple publish from delivery** (§2.2) — the structural change that makes
   slow subscribers harmless and enables everything below.
4. **Per-subscription lag + retry-depth metrics** (§3.6) — so you can see the
   effect of the above and find the next bottleneck.
5. **Shard delivery workers** (§2.4) and, if needed, **a broker substrate**
   (§2.7) — horizontal scale.

Each step is implementable behind the existing contracts, so you can adopt them
incrementally without a protocol change or a rewrite.
