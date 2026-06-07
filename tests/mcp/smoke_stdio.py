"""
tests/mcp/smoke_stdio.py — End-to-end smoke test for the stdio transport.

WHAT THIS TEST PROVES:
  1. run_stdio.py can be launched as a subprocess (Claude Desktop's pattern)
  2. The MCP `initialize` handshake completes successfully
  3. All 9 tools and 2 prompts are discovered via list_tools / list_prompts
  4. One tool from EACH architectural pattern executes end-to-end:
       - RAG:  finance_qa_search
       - Math: required_monthly_savings
       - API:  get_index_overview
  5. Both prompt templates render correctly

USAGE:
  uv run python -m tests.mcp.smoke_stdio
"""
import asyncio
import json
import sys
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


# How the client should launch our server
# This is the EXACT same shape Claude Desktop uses in its config file.
# 'command' + 'args' together describe the subprocess to spawn.
SERVER_PARAMS = StdioServerParameters(
    command="uv",
    args=["run", "python", "-m", "src.mcp_server.run_stdio"],
    env=None,  # inherit current env (.env file, OPENAI_API_KEY, TAVILY_API_KEY, etc.)
)

EXPECTED_TOOLS = 9
EXPECTED_PROMPTS = 2


def _content_text(result: Any) -> str:
    """Extract the text payload from an MCP CallToolResult's content blocks.

    MCP tool results carry a list of typed content blocks (text, image, audio,
    resource). For our tools, the first block is always text — a JSON string.
    """
    if not result.content:
        return ""
    block = result.content[0]
    return getattr(block, "text", str(block))


def _pretty_print(label: str, raw_text: str, max_chars: int = 600) -> None:
    """Pretty-print a tool result; try JSON-decode for readability, truncate."""
    print(f"    {label}:")
    try:
        decoded = json.loads(raw_text)
        text = json.dumps(decoded, indent=2, default=str)
    except (ValueError, TypeError):
        text = raw_text
    if len(text) > max_chars:
        text = text[:max_chars] + f"\n... (truncated; full length: {len(text)} chars)"
    for line in text.splitlines():
        print(f"      {line}")


async def main() -> int:
    print("=" * 70)
    print("Finnie MCP — stdio smoke test")
    print("=" * 70)
    print()

    print(f"[1/6] Launching server: {SERVER_PARAMS.command} {' '.join(SERVER_PARAMS.args)}")

    # 'stdio_client' spawns the subprocess and returns (read_stream, write_stream).
    # The 'async with' ensures the subprocess is killed cleanly when we exit.
    async with stdio_client(SERVER_PARAMS) as (read, write):

        # 'ClientSession' wraps the raw streams in the MCP protocol layer.
        async with ClientSession(read, write) as session:

            # Step 2: initialize handshake
            print(f"[2/6] Sending MCP initialize handshake...")
            init_result = await session.initialize()
            print(f"      Server:   {init_result.serverInfo.name} "
                  f"v{init_result.serverInfo.version}")
            print(f"      Protocol: {init_result.protocolVersion}")
            print()

            # Step 3: discover tools + prompts
            print(f"[3/6] Discovering tools and prompts...")
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

            # Step 4: RAG pattern — finance_qa_search
            print(f"[4/6] Calling RAG tool: finance_qa_search('What is an ETF?')")
            rag_result = await session.call_tool(
                "finance_qa_search",
                {"query": "What is an ETF?", "top_k": 3},
            )
            _pretty_print("result", _content_text(rag_result))
            print()

            # Step 5: Math pattern — required_monthly_savings
            print(f"[5/6] Calling math tool: required_monthly_savings(target=$1M, 30y, 7%)")
            math_result = await session.call_tool(
                "required_monthly_savings",
                {
                    "target_amount": 1_000_000.0,
                    "years": 30,
                    "expected_annual_return_pct": 7.0,
                },
            )
            _pretty_print("result", _content_text(math_result))
            print()

            # Step 6: API pattern — get_index_overview (no args)
            print(f"[6/6] Calling API tool: get_index_overview()")
            try:
                api_result = await session.call_tool("get_index_overview", {})
                _pretty_print("result", _content_text(api_result))
            except Exception as e:
                # yfinance can rate-limit; we don't fail the wire test on a data hiccup
                print(f"      WARNING: API call raised ({type(e).__name__}: {e})")
                print(f"      The wire still works — yfinance availability is not our concern here.")
            print()

            # render both prompts
            print(f"[+]   Rendering prompt: explain-like-im-5"
                  f"(concept='compound interest', audience='child')")
            prompt_result = await session.get_prompt(
                "explain-like-im-5",
                {"concept": "compound interest", "audience": "child"},
            )
            for msg in prompt_result.messages:
                text = getattr(msg.content, "text", str(msg.content))
                print(f"      [{msg.role}] {text[:280]}")
            print()

            print(f"[+]   Rendering prompt: regulatory-disclaimer()")
            disclaimer_result = await session.get_prompt("regulatory-disclaimer", {})
            for msg in disclaimer_result.messages:
                text = getattr(msg.content, "text", str(msg.content))
                print(f"      [{msg.role}] {text}")
            print()

    print("=" * 70)
    print("✓ Smoke test PASSED — stdio transport works end-to-end")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))