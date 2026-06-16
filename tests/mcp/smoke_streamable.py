"""
tests/mcp/smoke_streamable.py — End-to-end smoke test for Streamable HTTP transport.

PREREQUISITE:
  The HTTP server must be running BEFORE you run this script.
  In one terminal:
    uv run python -m src.mcp_server.run_http --transport streamable-http

  Then in another terminal:
    uv run python -m tests.mcp.smoke_streamable

WHAT THIS PROVES:
  1. The Streamable HTTP endpoint accepts MCP initialize handshakes
  2. Discovery returns the same 9 tools + 2 prompts as stdio / SSE
  3. At least one tool executes end-to-end over Streamable HTTP
  (Same protocol surface as smoke_sse.py — different transport envelope.)
"""

import asyncio
import json
import os
import sys
from typing import Any

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

STREAMABLE_URL = os.environ.get("FINNIE_MCP_STREAMABLE_URL", "http://localhost:8001/mcp")
EXPECTED_TOOLS = 9
EXPECTED_PROMPTS = 2


def _content_text(result: Any) -> str:
    if not result.content:
        return ""
    block = result.content[0]
    return getattr(block, "text", str(block))


def _pretty_print(label: str, raw_text: str, max_chars: int = 600) -> None:
    print(f"    {label}:")
    try:
        text = json.dumps(json.loads(raw_text), indent=2, default=str)
    except (ValueError, TypeError):
        text = raw_text
    if len(text) > max_chars:
        text = text[:max_chars] + f"\n... (truncated; full length: {len(text)} chars)"
    for line in text.splitlines():
        print(f"      {line}")


async def main() -> int:
    print("=" * 70)
    print("Finnie MCP — Streamable HTTP smoke test")
    print("=" * 70)
    print()
    print(f"[1/4] Connecting to Streamable HTTP endpoint: {STREAMABLE_URL}")

    # streamablehttp_client returns a 3-tuple (read, write, get_session_id_callable).
    # The third element is the spec-mandated session-id accessor; we don't need it
    # for the smoke test, so we discard it with `_`.
    async with streamablehttp_client(STREAMABLE_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            print("[2/4] Sending MCP initialize handshake...")
            init_result = await session.initialize()
            print(
                f"      Server:   {init_result.serverInfo.name} v{init_result.serverInfo.version}"
            )
            print(f"      Protocol: {init_result.protocolVersion}")
            print()

            print("[3/4] Discovering tools and prompts...")
            tools_response = await session.list_tools()
            prompts_response = await session.list_prompts()

            tool_names = sorted(t.name for t in tools_response.tools)
            prompt_names = sorted(p.name for p in prompts_response.prompts)

            print(f"      Tools   ({len(tool_names)}): {tool_names}")
            print(f"      Prompts ({len(prompt_names)}): {prompt_names}")

            assert len(tool_names) == EXPECTED_TOOLS, (
                f"Expected {EXPECTED_TOOLS} tools, got {len(tool_names)}"
            )
            assert len(prompt_names) == EXPECTED_PROMPTS, (
                f"Expected {EXPECTED_PROMPTS} prompts, got {len(prompt_names)}"
            )
            print()

            print("[4/4] Calling tool: project_growth($10K start, $500/mo, 25y, 7%)")
            result = await session.call_tool(
                "project_growth",
                {
                    "current_savings": 10_000.0,
                    "monthly_contribution": 500.0,
                    "years": 25,
                    "expected_annual_return_pct": 7.0,
                },
            )
            _pretty_print("result", _content_text(result))
            print()

    print("=" * 70)
    print("✓ Streamable HTTP smoke test PASSED — modern HTTP transport works end-to-end")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
