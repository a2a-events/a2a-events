# A2A Events Conformance Suite

Language-agnostic test vectors that any A2A Events implementation can run to
check it matches the spec (spec §33). This repo is the source of truth for
these fixtures. The reference Python runner is
[`tests/test_conformance.py`](https://github.com/a2a-events/a2a-events-python/blob/main/tests/test_conformance.py)
in the [`a2a-events-python`](https://github.com/a2a-events/a2a-events-python)
repo, which vendors a copy of these fixtures (kept in sync via its
`scripts/sync_spec.py`); other SDKs should consume these same JSON fixtures.

## Fixtures

### `fixtures/selectors.json`
Selector-matching vectors for the normative algebra (spec §10.4). A shared
`event` plus `cases`, each with a `selector` and either:
- `match` (boolean) — the expected match result, or
- `error` (symbolic code, e.g. `INVALID_SELECTOR`) — the matcher must reject it.

Optional `default_search_fields` supplies a topic's default `keyword_search`
fields when the selector omits `fields`.

### `fixtures/cursors.json`
Cursor-ordering vectors (spec §10.9). `ordered` is a list of reference
cursors already in ascending order; a conformant byte-wise lexicographic sort
must leave it unchanged, and that order must equal event order.

### `fixtures/errors.json`
Error-code mapping (spec §30). Each symbolic code maps to a JSON-RPC
numeric `code` (in the `-32000..-32099` server-error range) and an HTTP status
for the HTTP+JSON binding.

## Published schemas

The JSON Schemas under [`../schemas/`](../schemas) are the published contract,
generated from the reference models (`a2a-events-python`'s
`scripts/export_schemas.py`). The runner checks its vendored copy for drift and
validates sample instances against them.

## §33 behavioral cases → coverage

| §33 case                                          | Covered by                                                          |
| ------------------------------------------------- | ------------------------------------------------------------------- |
| valid minimal subscription is accepted            | `test_end_to_end::test_subscribe_deliver_ack`                       |
| unknown topic is rejected                         | `test_end_to_end::test_unknown_topic_rejected`                      |
| invalid selector is rejected                      | `fixtures/selectors.json` (`INVALID_SELECTOR`)                      |
| unsupported delivery mode is rejected             | publisher guard (`DELIVERY_MODE_NOT_SUPPORTED`)                     |
| subscription expires without renewal              | `test_end_to_end::test_lease_expiry_stops_delivery`                 |
| renew extends lease                               | `test_end_to_end::test_renew_and_delete`                            |
| event with invalid signature is rejected          | `receiver` (bad-signature → no-retry)                               |
| duplicate eventId is deduplicated                 | `test_end_to_end::test_duplicate_delivery_is_deduplicated`          |
| replay from valid cursor returns matching events  | `test_end_to_end::test_replay_returns_matching_events`              |
| replay from expired cursor returns CURSOR_EXPIRED | store retention check (§31)                                         |
| publisher refuses undeclared callback URL         | `DELIVERY_ENDPOINT_NOT_DECLARED` guard                              |
| activation handshake echoes extension             | `test_http_integration::test_activation_handshake_echoes_extension` |

## Running

From the [`a2a-events-python`](https://github.com/a2a-events/a2a-events-python)
repo:

```bash
uv run pytest tests/test_conformance.py
```
