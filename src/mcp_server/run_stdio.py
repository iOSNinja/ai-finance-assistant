"""
src/mcp_server/run_stdio.py — Run Finnie's MCP server over stdio.
"""

import argparse
import sys

from src.mcp_server.server import mcp
from src.utils.logger import setup_logger

logger = setup_logger("finnie.mcp_server.stdio")


def main() -> int:
    """Parse CLI args, then either print --check report or start the stdio loop."""
    parser = argparse.ArgumentParser(
        description="Finnie MCP server (stdio transport).",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Print registered tools/prompts and exit 0. Validates imports without networking.",
    )
    args = parser.parse_args()

    if args.check:
        tools = sorted(mcp._tool_manager._tools.keys())
        prompts = sorted(mcp._prompt_manager._prompts.keys())
        print(f"finnie MCP server OK  (transport=stdio)")
        print(f"  tools   ({len(tools)}): {tools}")
        print(f"  prompts ({len(prompts)}): {prompts}")
        return 0

    logger.info("Starting Finnie MCP server (transport=stdio)")
    # transport="stdio" is FastMCP's default; we pass it explicitly so the
    # transport is grep-able when debugging later.
    # mcp.run() blocks here until the client disconnects (or Ctrl+C).
    mcp.run(transport="stdio")
    return 0


if __name__ == "__main__":
    sys.exit(main())
