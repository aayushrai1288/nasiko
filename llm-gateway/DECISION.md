# Gateway Choice: LiteLLM

## Decision
LiteLLM Proxy (`ghcr.io/berriai/litellm:main-stable`) as the platform LLM gateway.

## Alternatives considered
Portkey (self-hosted open-source gateway).

## Rationale
- **Single container deploy** — drops into `docker-compose.local.yml` next to Phoenix/Kong with no extra services. Portkey's self-hosted path needs a control plane plus worker.
- **OpenAI-compatible endpoint** — agents keep using the `openai` Python SDK pointed at `http://llm-gateway:4000/v1`. Zero SDK rewrites.
- **Provider routing via YAML** — `config.yaml` lists model aliases and provider credentials. Rotation is an edit + container restart.
- **OTEL export is one env flag** — `litellm_settings.callbacks: ["otel"]` emits spans to the OTLP endpoint Phoenix already listens on. No custom instrumentation code.
- **MIT licensed** — no SaaS dependency, survives offline demo.

## Not chosen because
Portkey's full product is SaaS-first; the OSS gateway is narrower and heavier to self-host for a 48h sprint. If Nasiko later needs guardrails / prompt firewall, revisit.
