# Nasiko LLM Gateway

Platform-managed [LiteLLM](https://github.com/BerriAI/litellm) proxy that fronts every LLM provider. Agents call this gateway; real provider keys live only in [`config.yaml`](config.yaml).

See [`DECISION.md`](DECISION.md) for why LiteLLM over Portkey.

## Endpoints

- `http://llm-gateway:4000` — inside the docker network (agents)
- `http://localhost:4500` — from the host (dev, tests)

Both are OpenAI-compatible: `/v1/chat/completions`, `/v1/models`, `/v1/embeddings`.

Liveness: `/health/liveliness`.

## Virtual keys and models

Agents use the master virtual key (`LITELLM_MASTER_KEY`) and ask for the model alias `nasiko-default`. The gateway rewrites the request to the real provider + real key server-side.

## Adding a provider

1. Add an entry to `config.yaml`:
   ```yaml
   - model_name: my-alias
     litellm_params:
       model: openai/gpt-4o-mini
       api_key: os.environ/OPENAI_API_KEY
   ```
2. Add the real key to `.nasiko-local.env`:
   ```
   OPENAI_API_KEY=sk-...
   ```
3. Restart the gateway:
   ```bash
   make gateway-restart
   ```

Agents don't need to know.

## Rotating the primary provider

Swap the first `nasiko-default` entry's `model:` and `api_key:` fields. Restart with `make gateway-restart`. Provider rotation test (`test_provider_rotation`) exercises exactly this path.

## Rotating the virtual key

Change `LITELLM_MASTER_KEY` in `.nasiko-local.env` and restart the gateway **and** the redis listener (so newly deployed agents receive the new key):

```bash
docker compose --env-file .nasiko-local.env -f docker-compose.local.yml \
  up -d --force-recreate llm-gateway nasiko-redis-listener
```

Already-running agents will continue to use the old key until they're redeployed.

## Observability

Gateway spans are exported via OTLP HTTP to Phoenix (`http://phoenix-observability:4318`). Every chat completion produces a span. Because LiteLLM honors the incoming `traceparent` header, the span nests under the agent's root span so a Phoenix trace shows agent → gateway → provider end-to-end.

## Mock provider (for tests)

`mock-llm/` is a tiny FastAPI stub that implements enough of the OpenAI Chat Completions API to act as a rotation target in integration tests. It returns a fixed canned response so tests can pattern-match on it.
