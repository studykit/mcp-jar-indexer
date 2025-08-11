"""MCP Tool for searching file content in indexed artifacts."""

import logging
from typing import Any, Dict

from mcp.types import TextContent, Tool

from ..core.storage import StorageManager
from ..jartype.core_types import SearchFileContentMcpResult
from ..utils.artifact_utils import is_artifact_code_available
from ..utils.filesystem_exploration import search_file_contents
from ..utils.path_utils import normalize_path
from ..utils.validation import validate_maven_coordinates

logger = logging.getLogger(__name__)


class SearchFileContentError(Exception):
  """Base exception for search_file_content tool errors."""

  pass


class ArtifactNotIndexedError(SearchFileContentError):
  """Raised when artifact is not indexed."""

  pass


async def search_file_content(
  group_id: str,
  artifact_id: str,
  version: str,
  query: str,
  query_type: str = "string",
  start_path: str = "",
  max_depth: int = 10,
  context_before: int = 2,
  context_after: int = 2,
  max_results: int = 100,
) -> SearchFileContentMcpResult:
  """Search for content within files of an indexed artifact.

  Args:
    group_id: Maven group ID (e.g., 'org.springframework')
    artifact_id: Maven artifact ID (e.g., 'spring-core')
    version: Maven version (e.g., '5.3.21')
    query: Search query for file content
    query_type: Query type ("string" or "regex")
    start_path: Relative path to start search from (default: root)
    max_depth: Maximum depth to search (default: 10)
    context_before: Number of context lines before match (default: 2)
    context_after: Number of context lines after match (default: 2)
    max_results: Maximum number of results per file (default: 100)

  Returns:
    SearchFileContentMcpResult containing search results

  Raises:
    SearchFileContentError: For various search failures
  """
  try:
    # Validate parameters
    validate_maven_coordinates(group_id, artifact_id, version)

    if query_type not in ("string", "regex"):
      return SearchFileContentMcpResult(
        status="invalid_query_type",
        search_config={
          "query": query,
          "query_type": query_type,
          "start_path": start_path,
          "context_before": context_before,
          "context_after": context_after,
        },
        matches={},
      )

    # Check if artifact code is available
    if not is_artifact_code_available(group_id, artifact_id, version):
      return SearchFileContentMcpResult(
        status="not_available",
        search_config={
          "query": query,
          "query_type": query_type,
          "start_path": start_path,
          "context_before": context_before,
          "context_after": context_after,
        },
        matches={},
      )

    # Get artifact code directory
    storage_manager = StorageManager()
    base_path = storage_manager.get_code_path(group_id, artifact_id, version)

    if not base_path.exists():
      return SearchFileContentMcpResult(
        status="not_found",
        search_config={
          "query": query,
          "query_type": query_type,
          "start_path": start_path,
          "context_before": context_before,
          "context_after": context_after,
        },
        matches={},
      )

    # Normalize start path
    normalized_start_path = normalize_path(start_path) if start_path else ""
    full_start_path = (
      base_path / normalized_start_path if normalized_start_path else base_path
    )

    if not full_start_path.exists():
      return SearchFileContentMcpResult(
        status="start_path_not_found",
        search_config={
          "query": query,
          "query_type": query_type,
          "start_path": start_path,
          "context_before": context_before,
          "context_after": context_after,
        },
        matches={},
      )

    if not full_start_path.is_dir():
      return SearchFileContentMcpResult(
        status="start_path_not_directory",
        search_config={
          "query": query,
          "query_type": query_type,
          "start_path": start_path,
          "context_before": context_before,
          "context_after": context_after,
        },
        matches={},
      )

    # Search file contents
    result = search_file_contents(
      base_path=str(base_path),
      query=query,
      query_type=query_type,
      start_path=normalized_start_path,
      max_depth=max_depth,
      context_before=context_before,
      context_after=context_after,
      max_results=max_results,
    )

    return SearchFileContentMcpResult(
      status="success",
      search_config=result["search_config"],
      matches=result["matches"],
    )

  except Exception as e:
    logger.error(f"Error in search_file_content: {e}")
    return SearchFileContentMcpResult(
      status="internal_error",
      search_config={
        "query": query,
        "query_type": query_type,
        "start_path": start_path,
        "context_before": context_before,
        "context_after": context_after,
      },
      matches={},
    )


# MCP Tool definition
SEARCH_FILE_CONTENT_TOOL = Tool(
  name="search_file_content",
  description="Search for content within files of an indexed artifact",
  inputSchema={
    "type": "object",
    "properties": {
      "group_id": {
        "type": "string",
        "description": "Maven group ID (e.g., 'org.springframework')",
      },
      "artifact_id": {
        "type": "string",
        "description": "Maven artifact ID (e.g., 'spring-core')",
      },
      "version": {
        "type": "string",
        "description": "Maven version (e.g., '5.3.21')",
      },
      "query": {
        "type": "string",
        "description": "Search query for file content",
      },
      "query_type": {
        "type": "string",
        "description": "Query type ('string' or 'regex')",
        "enum": ["string", "regex"],
        "default": "string",
      },
      "start_path": {
        "type": "string",
        "description": "Relative path to start search from (default: root)",
        "default": "",
      },
      "max_depth": {
        "type": "integer",
        "description": "Maximum depth to search (default: 10)",
        "default": 10,
        "minimum": 1,
        "maximum": 20,
      },
      "context_before": {
        "type": "integer",
        "description": "Number of context lines before match (default: 2)",
        "default": 2,
        "minimum": 0,
        "maximum": 10,
      },
      "context_after": {
        "type": "integer",
        "description": "Number of context lines after match (default: 2)",
        "default": 2,
        "minimum": 0,
        "maximum": 10,
      },
      "max_results": {
        "type": "integer",
        "description": "Maximum number of results per file (default: 100)",
        "default": 100,
        "minimum": 1,
        "maximum": 1000,
      },
    },
    "required": ["group_id", "artifact_id", "version", "query"],
  },
)


async def handle_search_file_content(arguments: Dict[str, Any]) -> list[TextContent]:
  """Handle search_file_content MCP tool call."""
  try:
    result = await search_file_content(
      group_id=arguments["group_id"],
      artifact_id=arguments["artifact_id"],
      version=arguments["version"],
      query=arguments["query"],
      query_type=arguments.get("query_type", "string"),
      start_path=arguments.get("start_path", ""),
      max_depth=arguments.get("max_depth", 10),
      context_before=arguments.get("context_before", 2),
      context_after=arguments.get("context_after", 2),
      max_results=arguments.get("max_results", 100),
    )

    import json

    return [
      TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False))
    ]

  except Exception as e:
    logger.error(f"Error in handle_search_file_content: {e}")
    error_result = {
      "status": "internal_error",
      "search_config": {
        "query": arguments.get("query", ""),
        "query_type": arguments.get("query_type", "string"),
        "start_path": arguments.get("start_path", ""),
        "context_before": arguments.get("context_before", 2),
        "context_after": arguments.get("context_after", 2),
      },
      "matches": {},
    }
    import json

    return [
      TextContent(
        type="text", text=json.dumps(error_result, indent=2, ensure_ascii=False)
      )
    ]
