"""
Shared fixtures for LLM gateway integration tests.

Assumes the Nasiko local stack is running (see HOW_TO_RUN_AGENT.md or
`make compose-up`). Tests that need specific services will skip if those
services aren't reachable, with a message pointing at the setup step.
"""
from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path
from typing import Iterator

import pytest
import requests

REPO_ROOT = Path(__file__).resolve().parents[2]

GATEWAY_HOST_URL = os.getenv("GATEWAY_HOST_URL", "http://localhost:4500")
PHOENIX_HOST_URL = os.getenv("PHOENIX_HOST_URL", "http://localhost:6006")
KONG_URL = os.getenv("KONG_URL", "http://localhost:9100")
REDIS_CONTAINER = os.getenv("REDIS_CONTAINER", "redis")

DEMO_AGENT_NAME = "a2a-gateway-demo"
CONFIG_PATH = REPO_ROOT / "llm-gateway" / "config.yaml"


def _http_alive(url: str, timeout: float = 2.0) -> bool:
    try:
        r = requests.get(url, timeout=timeout)
        return r.status_code < 500
    except requests.RequestException:
        return False


@pytest.fixture(scope="session")
def gateway_url() -> str:
    if not _http_alive(f"{GATEWAY_HOST_URL}/health/liveliness"):
        pytest.skip(
            f"LLM gateway not reachable at {GATEWAY_HOST_URL}. "
            "Run `make compose-up` first."
        )
    return GATEWAY_HOST_URL


@pytest.fixture(scope="session")
def phoenix_url() -> str:
    if not _http_alive(f"{PHOENIX_HOST_URL}/"):
        pytest.skip(f"Phoenix not reachable at {PHOENIX_HOST_URL}.")
    return PHOENIX_HOST_URL


@pytest.fixture(scope="session")
def kong_url() -> str:
    if not _http_alive(f"{KONG_URL}/"):
        pytest.skip(f"Kong not reachable at {KONG_URL}.")
    return KONG_URL


def redis_xadd_deploy(agent_name: str, agent_path: str) -> None:
    """Publish a deploy command to the redis stream the listener watches."""
    subprocess.run(
        [
            "docker",
            "exec",
            REDIS_CONTAINER,
            "redis-cli",
            "XADD",
            "orchestration:commands",
            "*",
            "command",
            "deploy_agent",
            "agent_name",
            agent_name,
            "agent_path",
            agent_path,
            "base_url",
            "http://nasiko-backend:8000",
            "upload_type",
            "directory",
        ],
        check=True,
    )


def wait_for_container(name: str, timeout: int = 180) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        result = subprocess.run(
            ["docker", "ps", "--filter", f"name={name}", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
        )
        if name in result.stdout:
            return True
        time.sleep(2)
    return False


@pytest.fixture(scope="session")
def demo_agent_deployed(gateway_url: str) -> Iterator[str]:
    """Deploy a2a-gateway-demo once per test session and yield its name."""
    agent_path = f"/app/agents/{DEMO_AGENT_NAME}"
    redis_xadd_deploy(DEMO_AGENT_NAME, agent_path)
    if not wait_for_container(DEMO_AGENT_NAME, timeout=240):
        pytest.skip(
            f"Agent container {DEMO_AGENT_NAME} did not start in time. "
            "Check `docker logs nasiko-redis-listener`."
        )
    # Small buffer for the agent process to finish booting inside the container.
    time.sleep(5)
    yield DEMO_AGENT_NAME
