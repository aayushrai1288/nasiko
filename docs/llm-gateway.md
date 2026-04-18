# Using the Nasiko LLM Gateway

**Do not hardcode model provider API keys in your agent.** Nasiko provides a platform-managed LLM gateway. Your agent calls the gateway and the gateway calls the real provider on your behalf.

## What gets injected into your agent

At deploy time the orchestrator sets these env vars inside your agent container:

| Var | Example | What it is |
|---|---|---|
| `LLM_GATEWAY_URL` | `http://llm-gateway:4000/v1` | OpenAI-compatible base URL |
| `LLM_GATEWAY_VIRTUAL_KEY` | `sk-nasiko-virtual` | Platform virtual key |

You don't set these yourself — the orchestrator injects them. See [`orchestrator/agent_builder.py::_deploy_agent`](../orchestrator/agent_builder.py).

## Calling the gateway

Use any OpenAI-compatible client. Most Python SDKs have a `base_url` parameter.

### openai

```python
import os
from openai import AsyncOpenAI

client = AsyncOpenAI(
    api_key=os.environ["LLM_GATEWAY_VIRTUAL_KEY"],
    base_url=os.environ["LLM_GATEWAY_URL"],
)

response = await client.chat.completions.create(
    model="nasiko-default",           # virtual model alias
    messages=[{"role": "user", "content": "Hello"}],
)
```

### langchain

```python
import os
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    api_key=os.environ["LLM_GATEWAY_VIRTUAL_KEY"],
    base_url=os.environ["LLM_GATEWAY_URL"],
    model="nasiko-default",
)
```

### crewai

```python
import os
from crewai import LLM

llm = LLM(
    model="nasiko-default",
    api_key=os.environ["LLM_GATEWAY_VIRTUAL_KEY"],
    base_url=os.environ["LLM_GATEWAY_URL"],
)
```

## Model aliases

| Alias | Backing model |
|---|---|
| `nasiko-default` | Whatever the platform picks (currently Anthropic Claude Haiku) |
| `claude-haiku` | Anthropic Claude Haiku 4.5 |
| `claude-sonnet` | Anthropic Claude Sonnet 4.5 |

Use `nasiko-default` unless you have a specific reason to pin a model. The platform may rotate the backing model for `nasiko-default` without breaking your agent.

## Tracing

Every gateway request emits an OpenTelemetry span. If your agent has the Phoenix observability injection enabled (the default in Nasiko), the gateway span nests under your agent's root span automatically. Open Phoenix at `http://localhost:6006` to see the full agent → gateway → provider trace.

No code changes needed — the standard OpenTelemetry HTTP instrumentation propagates the `traceparent` header for you.

## Why not use a provider key directly?

- Secrets leak through uploaded `.zip` files.
- Every developer would need to obtain and manage their own provider keys.
- Rotating providers (e.g. OpenAI → Anthropic) would mean editing every agent.
- Usage, cost, and rate-limit tracking would be scattered.

The gateway centralizes all of this. Real provider keys live only in [`llm-gateway/config.yaml`](../llm-gateway/config.yaml) and are loaded from `.nasiko-local.env`.

## Sample agent

[`agents/a2a-gateway-demo`](../agents/a2a-gateway-demo) is the reference implementation. `grep` its source for provider key env vars — you'll find none.

## Further reading

- [`llm-gateway/README.md`](../llm-gateway/README.md) — ops (adding providers, rotating keys)
- [`llm-gateway/DECISION.md`](../llm-gateway/DECISION.md) — why LiteLLM
- [`tests/README.md`](../tests/README.md) — integration tests
