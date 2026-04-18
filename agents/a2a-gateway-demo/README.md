# a2a-gateway-demo

Sample agent demonstrating the Nasiko LLM gateway pattern (Track 2).

## What's special about it

`grep -r "OPENAI_API_KEY\|ANTHROPIC_API_KEY\|OPENROUTER_API_KEY" src/` returns **nothing**.
The agent holds no provider credentials. All LLM traffic is routed through the platform's LiteLLM gateway.

## How it works

At deploy time the orchestrator injects two env vars into the container:

- `LLM_GATEWAY_URL` — e.g. `http://llm-gateway:4000/v1`
- `LLM_GATEWAY_VIRTUAL_KEY` — e.g. `sk-nasiko-virtual`

The agent's `GatewayAgentExecutor` constructs a stock `openai.AsyncOpenAI` client pointed at the gateway URL with the virtual key. The gateway resolves the virtual model alias (`nasiko-default`) to the real provider (Anthropic, OpenAI, …) and attaches the real API key server-side.

Provider rotation is a YAML edit on the gateway — no change to this agent.

See:
- `nasiko/llm-gateway/config.yaml` — model aliases and provider keys
- `nasiko/llm-gateway/DECISION.md` — why LiteLLM
- `nasiko/docs/llm-gateway.md` — developer guide
