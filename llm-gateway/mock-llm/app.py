"""
Minimal OpenAI-compatible mock provider for integration testing.

Used as the rotation target in the LLM gateway config so the provider-rotation
test (acceptance criterion #3) can succeed without a second real provider key.
Returns a single canned completion that tests can pattern-match on.
"""
import time
import uuid

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="mock-llm")

# Stable sentinel string — integration tests assert on this to confirm the
# request hit the mock and not the real provider.
MOCK_RESPONSE = "MOCK_LLM_RESPONSE::ok"


class ChatMessage(BaseModel):
    role: str
    content: str | None = None


class ChatCompletionRequest(BaseModel):
    model: str
    messages: list[ChatMessage]
    temperature: float | None = 0.2
    max_tokens: int | None = None
    stream: bool | None = False


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/v1/chat/completions")
def chat_completions(req: ChatCompletionRequest) -> dict:
    return {
        "id": f"chatcmpl-mock-{uuid.uuid4().hex[:12]}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": req.model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": MOCK_RESPONSE},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 1,
            "completion_tokens": 1,
            "total_tokens": 2,
        },
    }


@app.get("/v1/models")
def models() -> dict:
    return {
        "object": "list",
        "data": [
            {
                "id": "mock-model",
                "object": "model",
                "created": int(time.time()),
                "owned_by": "nasiko-test",
            }
        ],
    }
