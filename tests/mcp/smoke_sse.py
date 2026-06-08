"""
tests/mcp/smoke_sse.py — End-to-end smoke test for the SSE transport.

PREREQUISITE:
  The HTTP server must be running BEFORE you run this script.
  In one terminal:
    uv run python -m src.mcp_server.run_http --transport sse

  Then in another terminal:
    uv run python -m tests.mcp.smoke_sse

WHAT THIS PROVES:
  1. The SSE endpoint accepts MCP initialize handshakes
  2. Discovery returns the same 9 tools + 2 prompts as stdio
  3. At least one tool executes end-to-end over HTTP
"""
import asyncio
import json
import os
import sys
from typing import Any

from mcp import ClientSession
from mcp.client.sse import sse_client


SSE_URL = os.environ.get("FINNIE_MCP_SSE_URL", "http://localhost:8001/sse")
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
    print("Finnie MCP — SSE smoke test")
    print("=" * 70)
    print()
    print(f"[1/4] Connecting to SSE endpoint: {SSE_URL}")

    async with sse_client(SSE_URL) as (read, write):
        async with ClientSession(read, write) as session:

            print(f"[2/4] Sending MCP initialize handshake...")
            init_result = await session.initialize()
            print(f"      Server:   {init_result.serverInfo.name} "
                  f"v{init_result.serverInfo.version}")
            print(f"      Protocol: {init_result.protocolVersion}")
            print()

            print(f"[3/4] Discovering tools and prompts...")
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

            print(f"[4/4] Calling tool: required_monthly_savings(target=$500K, 20y, 8%)")
            result = await session.call_tool(
                "required_monthly_savings",
                {
                    "target_amount": 500_000.0,
                    "years": 20,
                    "expected_annual_return_pct": 8.0,
                },
            )
            _pretty_print("result", _content_text(result))
            print()

    print("=" * 70)
    print("✓ SSE smoke test PASSED — HTTP transport works end-to-end")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))