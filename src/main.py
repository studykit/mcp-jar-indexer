"""JAR Indexer MCP Server - Entry point for the MCP server."""

import asyncio
import logging
from typing import Any

from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.types import ServerCapabilities
import mcp.server.stdio
import mcp.types as types

from .tools.register_source import REGISTER_SOURCE_TOOL, handle_register_source

# Configure logging
logging.basicConfig(
  level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def create_server() -> Server:
  """Create and configure the MCP server."""
  server = Server("jar-indexer")

  @server.list_tools()
  async def handle_list_tools() -> list[types.Tool]:  # type: ignore[misc]
    """List available tools."""
    return [REGISTER_SOURCE_TOOL]

  @server.call_tool()
  async def handle_call_tool(  # type: ignore[misc]
    name: str, arguments: dict[str, Any] | None
  ) -> list[types.TextContent]:
    """Handle tool calls."""
    if name == "register_source":
      return await handle_register_source(arguments or {})
    else:
      raise ValueError(f"Unknown tool: {name}")

  return server


async def main_async():
  """Async main function."""
  logger.info("Starting JAR Indexer MCP Server...")
  server = create_server()

  # Initialize options for the MCP server
  options = InitializationOptions(
    server_name="jar-indexer",
    server_version="0.1.0",
    capabilities=ServerCapabilities(tools={}),  # type: ignore
  )

  async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
    await server.run(read_stream, write_stream, options)


def main():
  """Main entry point."""
  try:
    asyncio.run(main_async())
  except KeyboardInterrupt:
    logger.info("Server stopped by user")
  except Exception as e:
    logger.error(f"Server error: {e}")
    raise


if __name__ == "__main__":
  main()
