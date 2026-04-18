"""
Integration tests for Track 2 (LLM gateway).

Each test maps 1:1 to an acceptance criterion from the hackathon spec:

  1. test_gateway_health              -> §2.4 #1  gateway up after start-nasiko
  2. test_agent_keyless_completion    -> §2.4 #2  no provider key in agent src,
                                                  LLM call succeeds via gateway
  3. test_provider_rotation           -> §2.4 #3  flip config.yaml, no agent
                                                  code change, calls still work
  4. test_span_correlation            -> §2.4 #4  gateway span linked to agent
                                                  trace in Phoenix

A fifth test (test_legacy_agents_unchanged) guards against regressions in the
existing agent paths (spec §2.4 "existing agents continue to work").

Run with:
    cd nasiko
    uv run pytest tests/integration/test_llm_gateway.py -v
"""
from __future__ import annotations

import json
import re
import subprocess
import time
import uuid
from pathlib import Path

import pytest
import requests

from conftest import (  # type: ignore[import-not-found]
    CONFIG_PATH,
    DEMO_AGENT_NAME,
    REPO_ROOT,
)

MOCK_RESPONSE_SENTINEL = "MOCK_LLM_RESPONSE::ok"


# ---------------------------------------------------------------------------
# Test 1 — Gateway is up after `make compose-up`.
# ---------------------------------------------------------------------------
def test_gateway_health(gateway_url: str) -> None:
    r = requests.get(f"{gateway_url}/health/liveliness", timeout=5)
    assert r.status_code == 200, f"gateway liveliness check failed: {r.status_code}"


# ---------------------------------------------------------------------------
# Test 2 — Sample agent with no provider key completes an LLM call.
# ---------------------------------------------------------------------------
PROVIDER_KEY_NAMES = (
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "OPENROUTER_API_KEY",
    "MINIMAX_API_KEY",
)


def test_demo_agent_source_has_no_provider_keys() -> None:
    agent_src = REPO_ROOT / "agents" / DEMO_AGENT_NAME / "src"
    offending: list[str] = []
    for py_file in agent_src.rglob("*.py"):
        text = py_file.read_text(encoding="utf-8")
        for key in PROVIDER_KEY_NAMES:
            if key in text:
                offending.append(f"{py_file.name}: {key}")
    assert not offending, (
        "a2a-gateway-demo must not reference any provider API key env var. "
        f"Found: {offending}"
    )


def _invoke_agent_via_kong(kong_url: str, agent_name: str, query: str) -> dict:
    url = f"{kong_url}/agents/{agent_name}/"
    payload = {
        "jsonrpc": "2.0",
        "id": str(uuid.uuid4()),
        "method": "message/send",
        "params": {
            "message": {
                "role": "user",
                "parts": [{"kind": "text", "text": query}],
                "messageId": str(uuid.uuid4()),
            }
        },
    }
    r = requests.post(url, json=payload, timeout=60)
    r.raise_for_status()
    return r.json()


def test_agent_keyless_completion(
    kong_url: str, demo_agent_deployed: str
) -> None:
    resp = _invoke_agent_via_kong(
        kong_url, demo_agent_deployed, "Say the word hello in one sentence."
    )
    body = json.dumps(resp)
    assert "result" in resp or "artifacts" in body, (
        f"Unexpected agent response shape: {body[:500]}"
    )
    # Non-empty text artifact proves the gateway → provider round-trip worked.
    assert re.search(r'"text"\s*:\s*"[^"]+', body), (
        f"No non-empty text artifact in response: {body[:500]}"
    )


# ---------------------------------------------------------------------------
# Test 3 — Provider rotation without agent code change.
# ---------------------------------------------------------------------------
def _record_agent_image_sha(agent_name: str) -> str:
    result = subprocess.run(
        ["docker", "image", "inspect", f"{agent_name}_instrumented", "--format", "{{.Id}}"],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def _restart_gateway() -> None:
    subprocess.run(
        [
            "docker",
            "compose",
            "--env-file",
            str(REPO_ROOT / ".nasiko-local.env"),
            "-f",
            str(REPO_ROOT / "docker-compose.local.yml"),
            "up",
            "-d",
            "--force-recreate",
            "llm-gateway",
        ],
        check=True,
    )
    # Wait for the gateway to come back.
    for _ in range(30):
        try:
            r = requests.get("http://localhost:4500/health/liveliness", timeout=2)
            if r.status_code == 200:
                return
        except requests.RequestException:
            pass
        time.sleep(2)
    raise RuntimeError("gateway did not return after restart")


def test_provider_rotation(
    kong_url: str, demo_agent_deployed: str
) -> None:
    """Flip config.yaml primary from anthropic -> mock, restart gateway,
    verify same agent (same image SHA) now gets the mock's canned response."""
    original = CONFIG_PATH.read_text(encoding="utf-8")
    sha_before = _record_agent_image_sha(demo_agent_deployed)

    try:
        # Swap: the first model_name:nasiko-default entry is the primary.
        # Replace it wholesale with the mock-backed block.
        rotated = re.sub(
            r"(- model_name: nasiko-default\s*\n\s*litellm_params:\s*\n\s*model:) anthropic/[^\n]+\n(\s*api_key: os\.environ/ANTHROPIC_API_KEY)",
            r"\1 openai/mock-model\n      api_base: http://mock-llm:8080/v1\n      api_key: sk-mock",
            original,
            count=1,
        )
        assert rotated != original, "rotation regex did not match config.yaml"
        CONFIG_PATH.write_text(rotated, encoding="utf-8")
        _restart_gateway()

        resp = _invoke_agent_via_kong(
            kong_url, demo_agent_deployed, "Any question at all."
        )
        body = json.dumps(resp)
        assert MOCK_RESPONSE_SENTINEL in body, (
            f"Expected mock sentinel in response after rotation, got: {body[:500]}"
        )

        sha_after = _record_agent_image_sha(demo_agent_deployed)
        assert sha_before == sha_after, (
            "Agent image SHA changed — rotation should not rebuild the agent"
        )
    finally:
        CONFIG_PATH.write_text(original, encoding="utf-8")
        _restart_gateway()


# ---------------------------------------------------------------------------
# Test 4 — Gateway request produces a span linked to the calling agent's trace.
# ---------------------------------------------------------------------------
def test_span_correlation(
    kong_url: str, phoenix_url: str, demo_agent_deployed: str
) -> None:
    marker = f"trace-probe-{uuid.uuid4().hex[:8]}"
    _invoke_agent_via_kong(kong_url, demo_agent_deployed, f"marker={marker} say hi")

    # Phoenix needs a moment to ingest.
    time.sleep(8)

    # Phoenix exposes a GraphQL endpoint; query projects/spans for recent traces
    # and check at least one trace has both agent and gateway service names.
    query = {
        "query": """
        query recentSpans {
          projects {
            edges {
              node {
                name
                spans(first: 50, sort: {col: startTime, dir: desc}) {
                  edges {
                    node {
                      spanId
                      traceId
                      parentId
                      name
                      attributes
                    }
                  }
                }
              }
            }
          }
        }
        """
    }
    r = requests.post(f"{phoenix_url}/graphql", json=query, timeout=15)
    r.raise_for_status()
    data = r.json()

    # Walk response, group spans by trace_id, check at least one trace has
    # both an agent-origin span and a gateway-origin span.
    traces: dict[str, list[dict]] = {}
    for project in data.get("data", {}).get("projects", {}).get("edges", []):
        for span_edge in (
            project.get("node", {}).get("spans", {}).get("edges", [])
        ):
            s = span_edge["node"]
            traces.setdefault(s["traceId"], []).append(s)

    correlated = False
    for trace_id, spans in traces.items():
        names = " ".join(s.get("name", "").lower() for s in spans)
        attrs = json.dumps([s.get("attributes") for s in spans]).lower()
        has_agent = "agent" in names or DEMO_AGENT_NAME in attrs
        has_gateway = "litellm" in names or "litellm" in attrs or "llm-gateway" in attrs
        if has_agent and has_gateway:
            # Also verify parent/child relationship: some gateway span must have
            # a parent_id that matches another span in the same trace.
            span_ids = {s["spanId"] for s in spans}
            for s in spans:
                if s.get("parentId") in span_ids:
                    correlated = True
                    break
        if correlated:
            break

    assert correlated, (
        "No trace found in Phoenix with correlated agent + gateway spans. "
        "Check OTEL export on the gateway and the observability injector."
    )


# ---------------------------------------------------------------------------
# Regression guard — existing agents must still work unchanged.
# ---------------------------------------------------------------------------
LEGACY_AGENTS = ("a2a-translator", "a2a-github-agent", "a2a-compliance-checker")


@pytest.mark.parametrize("agent_name", LEGACY_AGENTS)
def test_legacy_agents_unchanged(agent_name: str) -> None:
    """Source files of pre-existing agents must be byte-identical to the pre-change
    baseline (no files we added/edited there as part of Track 2)."""
    agent_dir = REPO_ROOT / "agents" / agent_name
    assert agent_dir.is_dir(), f"legacy agent missing: {agent_name}"
    # Verify git thinks these files are unchanged vs. main.
    result = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "diff", "--name-only", "main", "--", f"agents/{agent_name}/"],
        capture_output=True,
        text=True,
    )
    changed = [line for line in result.stdout.splitlines() if line.strip()]
    assert not changed, (
        f"Legacy agent {agent_name} has modifications vs main: {changed}. "
        "Track 2 must not edit legacy agent files."
    )
