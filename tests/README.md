# Nasiko Integration Tests

## Track 2 — LLM Gateway

Integration tests for the platform LLM gateway live in
[`integration/test_llm_gateway.py`](integration/test_llm_gateway.py). They map 1:1
to the hackathon acceptance criteria (spec §2.4) plus a regression guard.

### Two tiers

| Tier | What runs | Needs Docker? | Needs provider key? |
|---|---|---|---|
| **Static** | `test_demo_agent_source_has_no_provider_keys`, `test_legacy_agents_unchanged` | no | no |
| **Full stack** | everything above + `test_gateway_health`, `test_agent_keyless_completion`, `test_provider_rotation`, `test_span_correlation` | yes (`make compose-up`) | yes (`ANTHROPIC_API_KEY`) |

The tier is chosen automatically: fixtures at `integration/conftest.py` probe each
service (gateway, Phoenix, Kong) and **skip** (not fail) tests that depend on a
service that isn't up. So the static tier falls out of running pytest without
the stack.

### Local run — full stack

```bash
cd nasiko
cp .nasiko-local.env.example .nasiko-local.env   # set ANTHROPIC_API_KEY
make start-nasiko                                 # boots the whole stack
pytest tests/integration/ -v
```

### Local run — static only (no Docker)

```bash
pytest tests/integration/ -v \
  -k "test_demo_agent_source_has_no_provider_keys or test_legacy_agents_unchanged"
```

### CI

[`.github/workflows/ci.yml`](../.github/workflows/ci.yml)'s `integration` job
runs the full tier when the repo has an `ANTHROPIC_API_KEY` secret, and falls
back to the static tier on fork PRs (no secrets exposed). Add the secret under
Settings → Secrets and variables → Actions.

### What each test covers

| Test | Acceptance criterion (spec §2.4) |
|---|---|
| `test_gateway_health` | #1 gateway up after `make start-nasiko` |
| `test_demo_agent_source_has_no_provider_keys` | #2 zero provider keys in agent source |
| `test_agent_keyless_completion` | #2 sample agent completes an LLM call via gateway |
| `test_provider_rotation` | #3 flip config, no agent code change (same image SHA) |
| `test_span_correlation` | #4 gateway span linked to agent trace in Phoenix |
| `test_legacy_agents_unchanged` | regression guard — existing agents untouched vs `main` |
