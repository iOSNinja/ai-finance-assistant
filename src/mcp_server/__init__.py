"""src/mcp_server — Finnie's MCP server.

Exposes Finnie's 9 educational-finance tools and 2 prompt templates
via the Model Context Protocol. Same FastMCP instance is served over
either stdio (Claude Desktop) or HTTP (SSE / Streamable HTTP).
"""
