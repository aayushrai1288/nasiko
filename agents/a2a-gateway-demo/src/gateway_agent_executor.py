"""Executor for the gateway-demo agent. Routes every chat completion through
the platform LiteLLM gateway via the stock OpenAI Python SDK."""
import logging

from a2a.server.agent_execution import AgentExecutor
from a2a.server.agent_execution.context import RequestContext
from a2a.server.events.event_queue import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import AgentCard, TaskState, TextPart, UnsupportedOperationError
from a2a.utils.errors import ServerError
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a helpful assistant running inside the Nasiko platform. "
    "Answer concisely. You have no external tools."
)


class GatewayAgentExecutor(AgentExecutor):
    def __init__(
        self,
        card: AgentCard,
        gateway_url: str,
        virtual_key: str,
        model: str,
    ) -> None:
        self._card = card
        # OpenAI-compatible client pointed at the LiteLLM gateway. The gateway
        # handles real provider authentication; we only send the virtual key.
        self.client = AsyncOpenAI(api_key=virtual_key, base_url=gateway_url)
        self.model = model

    async def _answer(self, message_text: str, updater: TaskUpdater) -> None:
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": message_text},
                ],
                temperature=0.2,
                max_tokens=1000,
            )
            content = response.choices[0].message.content or ""
            await updater.add_artifact([TextPart(text=content)])
            await updater.complete()
        except Exception as e:
            logger.exception("gateway call failed: %s", e)
            await updater.add_artifact(
                [TextPart(text=f"Gateway call failed: {e!s}")]
            )
            await updater.complete()

    async def execute(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        updater = TaskUpdater(event_queue, context.task_id, context.context_id)
        if not context.current_task:
            await updater.submit()
        await updater.start_work()

        message_text = ""
        for part in context.message.parts:
            if isinstance(part.root, TextPart):
                message_text += part.root.text

        if not message_text.strip():
            await updater.update_status(
                TaskState.failed,
                message=updater.new_agent_message(
                    [TextPart(text="Empty message.")]
                ),
            )
            return

        await self._answer(message_text, updater)

    async def cancel(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        raise ServerError(error=UnsupportedOperationError())
