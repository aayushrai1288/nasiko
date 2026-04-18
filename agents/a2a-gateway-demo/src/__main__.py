"""
Gateway Demo Agent — proves an agent can complete an LLM call with ZERO
provider API keys in source. All LLM traffic flows through the platform's
LiteLLM gateway. See nasiko/llm-gateway/DECISION.md.
"""
import logging
import os

import click
import uvicorn
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentSkill
from gateway_agent_executor import GatewayAgentExecutor  # type: ignore[import-untyped]
from starlette.applications import Starlette

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@click.command()
@click.option("--host", "host", default="localhost")
@click.option("--port", "port", default=5000)
def main(host: str, port: int) -> None:
    # All three env vars are injected by the orchestrator at deploy time.
    # The agent itself never carries a provider API key.
    gateway_url = os.environ["LLM_GATEWAY_URL"]
    virtual_key = os.environ["LLM_GATEWAY_VIRTUAL_KEY"]
    model = os.getenv("LLM_GATEWAY_MODEL", "nasiko-default")

    logger.info("Gateway demo agent starting. Gateway=%s Model=%s", gateway_url, model)

    skill = AgentSkill(
        id="gateway_demo",
        name="Gateway Demo",
        description="Answers general questions. Proves gateway-routed LLM calls work without provider keys in the agent.",
        tags=["demo", "gateway", "qa"],
        examples=[
            "What is the capital of France?",
            "Explain TCP in one sentence.",
            "Summarize the Pythagorean theorem.",
        ],
    )

    agent_card = AgentCard(
        name="Gateway Demo Agent",
        description="Sample agent that calls the platform LLM gateway. No provider keys in source.",
        url=f"http://{host}:{port}/",
        version="1.0.0",
        default_input_modes=["text"],
        default_output_modes=["text"],
        capabilities=AgentCapabilities(streaming=True),
        skills=[skill],
    )

    executor = GatewayAgentExecutor(
        card=agent_card,
        gateway_url=gateway_url,
        virtual_key=virtual_key,
        model=model,
    )

    handler = DefaultRequestHandler(
        agent_executor=executor, task_store=InMemoryTaskStore()
    )
    a2a_app = A2AStarletteApplication(agent_card=agent_card, http_handler=handler)
    app = Starlette(routes=a2a_app.routes())

    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
