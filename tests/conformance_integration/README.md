# Cross-language conformance integration

This directory holds tests that run the conformance vectors against
multiple language implementations (Python, TypeScript, etc.) to ensure
they all correctly implement the A2A Events protocol.

The actual conformance fixtures live in [`../../conformance/`](../../conformance)
at the root of this (spec) repo, the source of truth.

## Running

```bash
# Run against Python implementation
pytest tests/conformance_integration/ --lang python

# Run against TypeScript implementation (when available)
pytest tests/conformance_integration/ --lang typescript
```

## Purpose

This (spec) repo — [`a2a-events`](https://github.com/a2a-events/a2a-events) — is
the home for cross-language conformance testing. Language implementations such as
[`a2a-events-python`](https://github.com/a2a-events/a2a-events-python) live in
their own repos and vendor the fixtures from here; this directory drives those
implementations against the canonical vectors.
