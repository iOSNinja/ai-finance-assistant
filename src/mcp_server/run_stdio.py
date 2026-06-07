"""
src/mcp_server/run_stdio.py — Run Finnie's MCP server over stdio.
"""
import sys

# stdio safety part 1: swap stdout -> stderr for the import phase
# This MUST run before any Finnie module is imported. Finnie's setup_logger()
# captures sys.stdout AT THE MOMENT of handler creation — by swapping first,
# every StreamHandler(sys.stdout) in the import chain actually captures stderr.
# Restored to the real stdout below so FastMCP can use it for JSON-RPC.
_real_stdout = sys.stdout
sys.stdout = sys.stderr

import argparse
import logging

from src.mcp_server.server import mcp
from src.utils.logger import setup_logger

# Creating THIS module's logger while stdout is still swapped so its handler
# also captures stderr instead of stdout.
logger = setup_logger("finnie.mcp_server.stdio")

# stdio safety part 2: restore real stdout for the MCP JSON-RPC wire
sys.stdout = _real_stdout


def _redirect_stdout_loggers_to_stderr() -> int:
    """Belt-and-suspenders: catch any logger handler still pointing at stdout.
    """
    all_loggers = [logging.getLogger()] + [
        logging.getLogger(name) for name in logging.root.manager.loggerDict
    ]
    redirected = 0
    for log in all_loggers:
        for handler in log.handlers:
            if isinstance(handler, logging.StreamHandler) and handler.stream is sys.stdout:
                handler.stream = sys.stderr
                redirected += 1
    return redirected


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

    # Defensive sweep — most/all handlers should already be on stderr from
    # the import-time stdout swap. This catches anything that snuck in.
    redirected = _redirect_stdout_loggers_to_stderr()

    logger.info(
        "Starting Finnie MCP server (transport=stdio)",
        extra={"defensive_redirects": redirected},
    )
    # transport="stdio" is FastMCP's default; we pass it explicitly so the
    # transport is grep-able when debugging later.
    # mcp.run() blocks here until the client disconnects (or Ctrl+C).
    mcp.run(transport="stdio")
    return 0


if __name__ == "__main__":
    sys.exit(main())