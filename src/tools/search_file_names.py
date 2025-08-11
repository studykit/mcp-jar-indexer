"""MCP Tool for searching file names in indexed artifacts."""

import logging
from typing import Any, Dict

from mcp.types import TextContent, Tool

from ..core.storage import StorageManager
from ..jartype.core_types import SearchFileNamesResult
from ..utils.artifact_utils import is_artifact_code_available
from ..utils.filesystem_exploration import search_files_by_pattern
from ..utils.path_utils import normalize_path
from ..utils.validation import validate_maven_coordinates

logger = logging.getLogger(__name__)


class SearchFileNamesError(Exception):
  """Base exception for search_file_names tool errors."""

  pass


class ArtifactNotIndexedError(SearchFileNamesError):
  """Raised when artifact is not indexed."""

  pass


async def search_file_names(
  group_id: str,
  artifact_id: str,
  version: str,
  pattern: str,
  pattern_type: str = "glob",
  start_path: str = "",
  max_depth: int = 10,
) -> SearchFileNamesResult:
  """Search for files by filename pattern (recursively) in an indexed artifact.

  This function searches through all subdirectories under the start_path and
  matches files by filename only. The pattern should not include path separators.

  Args:
    group_id: Maven group ID (e.g., 'org.springframework')
    artifact_id: Maven artifact ID (e.g., 'spring-core')
    version: Maven version (e.g., '5.3.21')
    pattern: Filename pattern only. Glob: '*.java', 'Test*.class'. Regex: '.*\\.java$', '^Test.*'
    pattern_type: Pattern type ("glob" for wildcards or "regex" for regular expressions)
    start_path: Relative path to start recursive search from (default: root)
    max_depth: Maximum depth to search (default: 10)

  Returns:
    SearchFileNamesResult containing search results

  Raises:
    SearchFileNamesError: For various search failures
  """
  try:
    # Validate parameters
    validate_maven_coordinates(group_id, artifact_id, version)

    if pattern_type not in ("regex", "glob"):
      return SearchFileNamesResult(
        status="invalid_pattern_type",
        search_config={
          "start_path": start_path,
          "max_depth": max_depth,
          "pattern": pattern,
        },
        files=[],
      )

    # Check if artifact code is available
    if not is_artifact_code_available(group_id, artifact_id, version):
      return SearchFileNamesResult(
        status="not_available",
        search_config={
          "start_path": start_path,
          "max_depth": max_depth,
          "pattern": pattern,
        },
        files=[],
      )

    # Get artifact code directory
    storage_manager = StorageManager()
    base_path = storage_manager.get_code_path(group_id, artifact_id, version)

    if not base_path.exists():
      return SearchFileNamesResult(
        status="not_found",
        search_config={
          "start_path": start_path,
          "max_depth": max_depth,
          "pattern": pattern,
        },
        files=[],
      )

    # Normalize start path
    normalized_start_path = normalize_path(start_path) if start_path else ""
    full_start_path = (
      base_path / normalized_start_path if normalized_start_path else base_path
    )

    if not full_start_path.exists():
      return SearchFileNamesResult(
        status="start_path_not_found",
        search_config={
          "start_path": start_path,
          "max_depth": max_depth,
          "pattern": pattern,
        },
        files=[],
      )

    if not full_start_path.is_dir():
      return SearchFileNamesResult(
        status="start_path_not_directory",
        search_config={
          "start_path": start_path,
          "max_depth": max_depth,
          "pattern": pattern,
        },
        files=[],
      )

    # Search for files
    result = search_files_by_pattern(
      base_path=str(base_path),
      pattern=pattern,
      pattern_type=pattern_type,
      start_path=normalized_start_path,
      max_depth=max_depth,
    )

    return SearchFileNamesResult(
      status="success",
      search_config={
        "start_path": start_path,
        "max_depth": max_depth,
        "pattern": pattern,
      },
      files=result["files"],
    )

  except Exception as e:
    logger.error(f"Error in search_file_names: {e}")
    return SearchFileNamesResult(
      status="internal_error",
      search_config={
        "start_path": start_path,
        "max_depth": max_depth,
        "pattern": pattern,
      },
      files=[],
    )


# MCP Tool definition
SEARCH_FILE_NAMES_TOOL = Tool(
  name="search_file_names",
  description="Search for files by filename pattern (recursively) in an indexed artifact",
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
      "pattern": {
        "type": "string",
        "description": "Filename pattern only (no path separators). Glob examples: '*.java', 'Test*.class'. Regex examples: '.*\\.java$', '^Test.*'",
      },
      "pattern_type": {
        "type": "string",
        "description": "Pattern type: 'glob' for shell wildcards (*.java, Test*.class) or 'regex' for regular expressions (.*\\.java$, ^Test.*)",
        "enum": ["glob", "regex"],
        "default": "glob",
      },
      "start_path": {
        "type": "string",
        "description": "Relative path to start recursive search from (default: root)",
        "default": "",
      },
      "max_depth": {
        "type": "integer",
        "description": "Maximum depth to search (default: 10)",
        "default": 10,
        "minimum": 1,
        "maximum": 20,
      },
    },
    "required": ["group_id", "artifact_id", "version", "pattern"],
  },
)


async def handle_search_file_names(arguments: Dict[str, Any]) -> list[TextContent]:
  """Handle search_file_names MCP tool call."""
  try:
    result = await search_file_names(
      group_id=arguments["group_id"],
      artifact_id=arguments["artifact_id"],
      version=arguments["version"],
      pattern=arguments["pattern"],
      pattern_type=arguments.get("pattern_type", "glob"),
      start_path=arguments.get("start_path", ""),
      max_depth=arguments.get("max_depth", 10),
    )

    import json

    return [
      TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False))
    ]

  except Exception as e:
    logger.error(f"Error in handle_search_file_names: {e}")
    error_result: Dict[str, Any] = {
      "status": "internal_error",
      "search_config": {
        "start_path": arguments.get("start_path", ""),
        "max_depth": arguments.get("max_depth", 10),
        "pattern": arguments.get("pattern", ""),
      },
      "files": [],
    }
    import json

    return [
      TextContent(
        type="text", text=json.dumps(error_result, indent=2, ensure_ascii=False)
      )
    ]
