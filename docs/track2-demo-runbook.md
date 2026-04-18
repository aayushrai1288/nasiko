# Track 2 — Demo Video Runbook

Target length: 4–6 minutes. Three segments.

## Pre-recording checklist

- [ ] `.nasiko-local.env` populated with a real `ANTHROPIC_API_KEY`.
- [ ] Docker Desktop running; `docker info` works.
- [ ] Terminal pane + browser (Phoenix at `http://localhost:6006`) visible side by side.
- [ ] `make start-nasiko` finished; `docker compose -f docker-compose.local.yml ps` shows `llm-gateway`, `mock-llm`, `phoenix-observability`, `nasiko-redis-listener` all `healthy`.
- [ ] Demo agent NOT yet deployed (we deploy it on camera).

## Segment 1 — Working product (≈ 3 min)

### 1.1 Gateway is up

```bash
curl -s http://localhost:4500/health/liveliness
# {"status":"healthy"}
```

Narrate: *"Gateway booted via `make start-nasiko`, zero manual install."*

### 1.2 Sample agent has no provider keys

```bash
grep -rn "OPENAI_API_KEY\|ANTHROPIC_API_KEY\|OPENROUTER_API_KEY\|MINIMAX_API_KEY" \
  agents/a2a-gateway-demo/src/
# (empty)
```

Open [agents/a2a-gateway-demo/src/gateway_agent_executor.py:30-33](../agents/a2a-gateway-demo/src/gateway_agent_executor.py#L30-L33). Narrate: *"OpenAI SDK pointed at the gateway URL, authenticated with a virtual key. No provider credential anywhere in this agent."*

### 1.3 Deploy the agent (via redis stream — same path every agent uses)

```bash
docker exec redis redis-cli XADD orchestration:commands '*' \
  command deploy_agent \
  agent_name a2a-gateway-demo \
  agent_path /app/agents/a2a-gateway-demo \
  base_url http://nasiko-backend:8000 \
  upload_type directory

docker logs nasiko-redis-listener -f
# ... watch for "Successfully deployed agent: a2a-gateway-demo"
```

### 1.4 Invoke the agent through Kong

```bash
curl -s -X POST http://localhost:9100/agents/a2a-gateway-demo/ \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":"demo-1","method":"message/send",
       "params":{"message":{"role":"user",
         "parts":[{"kind":"text","text":"Say hello in one sentence."}],
         "messageId":"m1"}}}' | jq .
```

Point at the text artifact. Narrate: *"Real Anthropic response round-tripped through the gateway. Agent never saw an Anthropic key."*

### 1.5 Trace correlation in Phoenix

Switch to `http://localhost:6006`, pick the most recent trace. Expand — show:
- Agent-origin span (project name `a2a-gateway-demo`).
- Gateway-origin span (service `llm-gateway`).
- Same `traceId`; gateway span's `parentId` = agent span's `spanId`.

Narrate: *"One trace, end-to-end. OTEL callbacks on the gateway plus `traceparent` propagation from the OpenAI SDK."*

### 1.6 Provider rotation (no agent rebuild)

Capture the agent image SHA:

```bash
docker inspect a2a-gateway-demo_instrumented --format '{{.Id}}' > /tmp/sha_before
```

Edit [llm-gateway/config.yaml](../llm-gateway/config.yaml) — swap the first `nasiko-default` block to:

```yaml
- model_name: nasiko-default
  litellm_params:
    model: openai/mock-model
    api_base: http://mock-llm:8080/v1
    api_key: sk-mock
```

Restart the gateway only:

```bash
make gateway-restart
```

Re-invoke the same agent (same `curl` as 1.4). Response now contains `MOCK_LLM_RESPONSE::ok`. Re-capture SHA:

```bash
docker inspect a2a-gateway-demo_instrumented --format '{{.Id}}' > /tmp/sha_after
diff /tmp/sha_before /tmp/sha_after   # empty = identical
```

Narrate: *"Provider rotated from Anthropic to a mock — one yaml edit, zero agent changes, byte-identical agent image."*

Revert `config.yaml` and `make gateway-restart` before moving on.

## Segment 2 — Technical details (≈ 1.5 min)

Three things only — no deeper than the narration below.

1. **LiteLLM vs Portkey** ([llm-gateway/DECISION.md](../llm-gateway/DECISION.md)): self-hosted OSS, config-as-code, OpenAI-compatible in, any-provider out, native OTEL. Portkey's OSS gateway is narrower and its full product is SaaS-first — wrong fit for a 48h sprint.
2. **Env injection** ([orchestrator/agent_builder.py:427-461](../orchestrator/agent_builder.py#L427-L461)): right before `docker compose up`, the orchestrator merges `LLM_GATEWAY_URL=http://llm-gateway:4000` and `LLM_GATEWAY_VIRTUAL_KEY=<master>` into every agent's compose file. No agent code change needed; every deployed agent becomes gateway-capable.
3. **Trace correlation**: Phoenix OTEL auto-instruments the OpenAI SDK, which emits `traceparent` on the outgoing HTTP call. LiteLLM's `callbacks: ["otel"]` ([llm-gateway/config.yaml:28-34](../llm-gateway/config.yaml#L28-L34)) receives that header and emits a child span to the same Phoenix OTLP endpoint. Result: one trace, three spans (agent, gateway, provider).

## Segment 3 — Acceptance criteria coverage (≈ 1 min)

Put this table on-screen. Walk through it row by row.

| # | Criterion | Status | File:line |
|---|---|---|---|
| 1 | Gateway auto-deploys with `make start-nasiko` | ✅ | [Makefile:69-88](../Makefile#L69-L88) |
| 2 | Sample agent, no provider key, LLM call works | ✅ | [a2a-gateway-demo/src/\_\_main\_\_.py:28-29](../agents/a2a-gateway-demo/src/__main__.py#L28-L29) |
| 3 | Provider rotation = config-only, same agent image | ✅ | [test_llm_gateway.py:151-186](../tests/integration/test_llm_gateway.py#L151-L186) |
| 4 | Existing agents unchanged | ✅ | [test_llm_gateway.py:267-286](../tests/integration/test_llm_gateway.py#L267-L286) |
| 5 | Deployed via infra flow, in docker-compose.local.yml | ✅ | [docker-compose.local.yml:293-322](../docker-compose.local.yml#L293-L322) |
| 6 | Agents get gateway URL + virtual key auto-injected | ✅ | [agent_builder.py:427-461](../orchestrator/agent_builder.py#L427-L461) |
| 7 | Gateway spans correlate with agent trace in Phoenix | ✅ | [config.yaml:28-34](../llm-gateway/config.yaml#L28-L34) + Phoenix demo above |
| 8 | Docs: gateway guide + "do not hardcode keys" note | ✅ | [docs/llm-gateway.md](llm-gateway.md) + [HOW_TO_RUN_AGENT.md:115](../HOW_TO_RUN_AGENT.md#L115) |
| 9 | At least one sample agent using the gateway | ✅ | [agents/a2a-gateway-demo/](../agents/a2a-gateway-demo/) |
| 10 | Integration tests in CI | ✅ | [.github/workflows/ci.yml](../.github/workflows/ci.yml) `integration` job |

**Honest non-goals, to call out:**
- Per-agent virtual keys with spend limits — using a single master key; adequate for hackathon, noted as future work.
- OAuth-protected providers and credential rotation UI — out of scope.
- Full stack in free-tier GitHub runners without the `ANTHROPIC_API_KEY` secret — CI falls back to static tests on fork PRs (no real LLM call). Documented in [tests/README.md](../tests/README.md).

End.
