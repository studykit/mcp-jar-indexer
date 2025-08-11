"""MCP Tool for exploring artifact directory structure."""

import logging
from typing import Any, Dict

from mcp.types import TextContent, Tool

from ..core.storage import StorageManager
from ..jartype.core_types import ListFolderTreeResult
from ..utils.artifact_utils import is_artifact_code_available
from ..utils.filesystem_exploration import list_directory_tree
from ..utils.path_utils import normalize_path
from ..utils.validation import validate_maven_coordinates

logger = logging.getLogger(__name__)


class ListFolderTreeError(Exception):
  """Base exception for list_folder_tree tool errors."""

  pass


class ArtifactNotIndexedError(ListFolderTreeError):
  """Raised when artifact is not indexed."""

  pass


async def list_folder_tree(
  group_id: str,
  artifact_id: str,
  version: str,
  path: str = "",
  include_files: bool = False,
  max_depth: int = 3,
) -> ListFolderTreeResult:
  """Explore directory structure of an indexed artifact.

  Args:
    group_id: Maven group ID (e.g., 'org.springframework')
    artifact_id: Maven artifact ID (e.g., 'spring-core')
    version: Maven version (e.g., '5.3.21')
    path: Relative path within artifact to explore (default: root)
    include_files: Whether to include files in the listing
    max_depth: Maximum depth to explore (default: 3)

  Returns:
    ListFolderTreeResult containing directory structure

  Raises:
    ListFolderTreeError: For various listing failures
  """
  try:
    # Validate parameters
    validate_maven_coordinates(group_id, artifact_id, version)

    # Check if artifact code is available
    if not is_artifact_code_available(group_id, artifact_id, version):
      return ListFolderTreeResult(
        status="not_available",
        path=path,
        max_depth=max_depth,
        folders=[],
        files=[],
      )

    # Get artifact code directory
    storage_manager = StorageManager()
    base_path = storage_manager.get_code_path(group_id, artifact_id, version)

    if not base_path.exists():
      return ListFolderTreeResult(
        status="not_found",
        path=path,
        max_depth=max_depth,
        folders=[],
        files=[],
      )

    # Normalize and validate the requested path
    start_path = normalize_path(path) if path else ""
    full_start_path = base_path / start_path if start_path else base_path

    if not full_start_path.exists():
      return ListFolderTreeResult(
        status="path_not_found",
        path=path,
        max_depth=max_depth,
        folders=[],
        files=[],
      )

    if not full_start_path.is_dir():
      return ListFolderTreeResult(
        status="not_directory",
        path=path,
        max_depth=max_depth,
        folders=[],
        files=[],
      )

    # List directory tree
    result = list_directory_tree(
      base_path=str(base_path),
      start_path=start_path,
      max_depth=max_depth,
      include_files=include_files,
    )

    return ListFolderTreeResult(
      status="success",
      path=result["path"],
      max_depth=result["max_depth"],
      folders=result["folders"],
      files=result["files"],
    )

  except Exception as e:
    logger.error(f"Error in list_folder_tree: {e}")
    return ListFolderTreeResult(
      status="internal_error",
      path=path,
      max_depth=max_depth,
      folders=[],
      files=[],
    )


# MCP Tool definition
LIST_FOLDER_TREE_TOOL = Tool(
  name="list_folder_tree",
  description="Explore the directory structure of an indexed artifact",
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
      "path": {
        "type": "string",
        "description": "Relative path within artifact to explore (default: root)",
        "default": "",
      },
      "include_files": {
        "type": "boolean",
        "description": "Whether to include files in the listing",
        "default": False,
      },
      "max_depth": {
        "type": "integer",
        "description": "Maximum depth to explore (default: 3)",
        "default": 3,
        "minimum": 1,
        "maximum": 10,
      },
    },
    "required": ["group_id", "artifact_id", "version"],
  },
)


async def handle_list_folder_tree(arguments: Dict[str, Any]) -> list[TextContent]:
  """Handle list_folder_tree MCP tool call."""
  try:
    result = await list_folder_tree(
      group_id=arguments["group_id"],
      artifact_id=arguments["artifact_id"],
      version=arguments["version"],
      path=arguments.get("path", ""),
      include_files=arguments.get("include_files", False),
      max_depth=arguments.get("max_depth", 3),
    )

    import json

    return [
      TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False))
    ]

  except Exception as e:
    logger.error(f"Error in handle_list_folder_tree: {e}")
    error_result: ListFolderTreeResult = {
      "status": "internal_error",
      "path": arguments.get("path", ""),
      "max_depth": arguments.get("max_depth", 3),
      "folders": [],
      "files": [],
    }
    import json

    return [
      TextContent(
        type="text", text=json.dumps(error_result, indent=2, ensure_ascii=False)
      )
    ]
