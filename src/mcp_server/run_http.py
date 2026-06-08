"""
src/mcp_server/run_http.py — Run Finnie's MCP server over HTTP.

TRANSPORT: SSE  or  Streamable HTTP
  --transport sse              Legacy SSE (two endpoints)
  --transport streamable-http  Spec's modern HTTP transport (single /mcp endpoint)

WHY BOTH?
  - Streamable HTTP is the spec's recommended replacement; SSE is being
    deprecated. Supporting both.

USAGE:
  # Quick import + registration sanity check
  uv run python -m src.mcp_server.run_http --check

  # SSE (default) — listens on http://0.0.0.0:8001/sse
  uv run python -m src.mcp_server.run_http

  # Streamable HTTP — listens on http://0.0.0.0:8001/mcp
  uv run python -m src.mcp_server.run_http --transport streamable-http

  # Custom port / host
  uv run python -m src.mcp_server.run_http --port 9000 --host 127.0.0.1
"""
import argparse
import sys

from src.mcp_server.server import mcp
from src.utils.logger import setup_logger

logger = setup_logger("finnie.mcp_server.http")

VALID_TRANSPORTS = ("sse", "streamable-http")


def main() -> int:
    """Parse CLI args, then either print --check report or start the HTTP server."""
    parser = argparse.ArgumentParser(
        description="Finnie MCP server (HTTP transport — SSE or Streamable HTTP).",
    )
    parser.add_argument(
        "--transport",
        choices=VALID_TRANSPORTS,
        default="sse",
        help="HTTP transport flavor. Default: sse.",
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Bind host. Default: 0.0.0.0 (listen on all interfaces).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8001,
        help="Bind port. Default: 8001.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Print registered tools/prompts and exit 0. Validates imports.",
    )
    args = parser.parse_args()

    if args.check:
        tools = sorted(mcp._tool_manager._tools.keys())
        prompts = sorted(mcp._prompt_manager._prompts.keys())
        print(f"finnie MCP server OK  (transport=http)")
        print(f"  tools   ({len(tools)}): {tools}")
        print(f"  prompts ({len(prompts)}): {prompts}")
        return 0

    # FastMCP reads host/port from its settings object at runtime.
    mcp.settings.host = args.host
    mcp.settings.port = args.port

    # Different transports expose different URL paths.
    if args.transport == "sse":
        endpoint_path = "/sse"
        client_hint = "from mcp.client.sse import sse_client"
    else:  # streamable-http
        endpoint_path = "/mcp"
        client_hint = "from mcp.client.streamable_http import streamablehttp_client"

    endpoint_url = f"http://{args.host}:{args.port}{endpoint_path}"

    logger.info(
        "Starting Finnie MCP server",
        extra={"transport": args.transport, "host": args.host, "port": args.port},
    )

    # Human-friendly startup banner before uvicorn takes over.
    print(f"finnie MCP server  (transport={args.transport})")
    print(f"  Endpoint:   {endpoint_url}")
    print(f"  Client API: {client_hint}")
    print(f"  Press Ctrl+C to stop.")
    print()

    # mcp.run() starts uvicorn/starlette and blocks until Ctrl+C.
    mcp.run(transport=args.transport)
    return 0


if __name__ == "__main__":
    sys.exit(main())