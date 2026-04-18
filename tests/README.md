# Nasiko Integration Tests

## Track 2 — LLM Gateway

Integration tests for the platform LLM gateway live in
[`integration/test_llm_gateway.py`](integration/test_llm_gateway.py).

### Prerequisites

- Docker Desktop running
- `.nasiko-local.env` populated (at minimum `ANTHROPIC_API_KEY` and `LITELLM_MASTER_KEY`)
- Stack up: `make compose-up`

### Run

```bash
cd nasiko
uv run pytest tests/integration/test_llm_gateway.py -v
```

### What each test covers

| Test | Acceptance criterion (spec §2.4) |
|---|---|
| `test_gateway_health` | #1 gateway up after `make start-nasiko` |
| `test_demo_agent_source_has_no_provider_keys` | #2 zero provider keys in agent source |
| `test_agent_keyless_completion` | #2 sample agent completes an LLM call via gateway |
| `test_provider_rotation` | #3 flip config, no agent code change |
| `test_span_correlation` | #4 gateway span linked to agent trace in Phoenix |
| `test_legacy_agents_unchanged` | regression guard — existing agents untouched |

Tests skip (don't fail) if the stack isn't running, with a message pointing at the setup step.
