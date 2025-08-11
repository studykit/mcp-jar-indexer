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
from .tools.index_artifact import INDEX_ARTIFACT_TOOL, handle_index_artifact
from .tools.list_artifacts import LIST_ARTIFACTS_TOOL, handle_list_artifacts
from .tools.list_folder_tree import LIST_FOLDER_TREE_TOOL, handle_list_folder_tree
from .tools.get_file import GET_FILE_TOOL, handle_get_file
from .tools.search_file_names import SEARCH_FILE_NAMES_TOOL, handle_search_file_names
from .tools.search_file_content import (
  SEARCH_FILE_CONTENT_TOOL,
  handle_search_file_content,
)

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
    return [
      REGISTER_SOURCE_TOOL,
      INDEX_ARTIFACT_TOOL,
      LIST_ARTIFACTS_TOOL,
      LIST_FOLDER_TREE_TOOL,
      GET_FILE_TOOL,
      SEARCH_FILE_NAMES_TOOL,
      SEARCH_FILE_CONTENT_TOOL,
    ]

  @server.call_tool()
  async def handle_call_tool(  # type: ignore[misc]
    name: str, arguments: dict[str, Any] | None
  ) -> list[types.TextContent]:
    """Handle tool calls."""
    if name == "register_source":
      return await handle_register_source(arguments or {})
    elif name == "index_artifact":
      return await handle_index_artifact(arguments or {})
    elif name == "list_artifacts":
      return await handle_list_artifacts(arguments or {})
    elif name == "list_folder_tree":
      return await handle_list_folder_tree(arguments or {})
    elif name == "get_file":
      return await handle_get_file(arguments or {})
    elif name == "search_file_names":
      return await handle_search_file_names(arguments or {})
    elif name == "search_file_content":
      return await handle_search_file_content(arguments or {})
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
    instructions="""Use JAR Indexer MCP when working with Java/Kotlin projects and need to:

1. **Explore Library Source Code**: When you need to understand how third-party libraries work internally
   - Analyze implementation details of Spring, Apache Commons, Jackson, etc.
   - Find specific method implementations or class structures
   - Understand dependency relationships and package hierarchies

**Getting Started:**
1. Use `list_artifacts` to check if the library you need is already indexed
2. If not available, use `register_source` to index JAR files or Git repositories
3. Then explore using search and navigation tools to analyze the source code.""",
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
