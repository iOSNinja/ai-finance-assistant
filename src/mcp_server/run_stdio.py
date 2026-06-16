"""
src/mcp_server/run_stdio.py — Run Finnie's MCP server over stdio.

TRANSPORT: stdio
  Standard input / output. The client (Claude Desktop, an MCP CLI,
  a smoke-test script) spawns THIS file as a subprocess and talks
  to it through stdin/stdout JSON-RPC frames.

WHY STDIO FOR CLAUDE DESKTOP:
  Claude Desktop has no network listener. It always launches MCP
  servers as local subprocesses for two reasons:
    1. Zero firewall / port-conflict pain — no HTTP listener at all
    2. Inherent process isolation — server dies when the client dies

WHY THIS FILE IS TINY:
  All tools, prompts, and instructions live in server.py.
  This file's only job is choosing the transport, optionally printing
  a registration report via --check, AND keeping stdout 100% JSON-RPC.

STDIO STDOUT SAFETY (read this if you're touching the imports below):
  In stdio MCP, the server's stdout IS the JSON-RPC wire — ANY non-JSON
  output corrupts the protocol. Finnie's setup_logger() uses
  StreamHandler(sys.stdout), which means EVERY log line during import
  AND at runtime would normally land on stdout.

  Fix: swap sys.stdout -> sys.stderr BEFORE the server import, so all
  loggers created during imports capture stderr. Restore sys.stdout
  AFTER imports so FastMCP can use it for JSON-RPC. A defensive sweep
  in main() catches any handler that gets lazy-created later.

USAGE:
  # Quick import + registration sanity check (no network, no LLM, exits 0)
  uv run python -m src.mcp_server.run_stdio --check

  # Actually run the stdio loop (blocks on stdin for JSON-RPC frames)
  uv run python -m src.mcp_server.run_stdio
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
    """catch any logger handler still pointing at stdout.

    The pre-import stdout swap should have caught every handler created
    during import. This sweep covers handlers that get lazy-created later
    (e.g., a tool that calls setup_logger() inside its first invocation).

    Returns:
        Number of handlers redirected. Should typically be 0 if the swap
        above worked correctly.
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
        print("finnie MCP server OK  (transport=stdio)")
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
