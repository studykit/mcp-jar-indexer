"""MCP Tool for retrieving file content from indexed artifacts."""

import logging
from typing import Any, Dict, Optional

from mcp.types import TextContent, Tool

from ..core.storage import StorageManager
from ..jartype.core_types import GetFileResult
from ..utils.artifact_utils import is_artifact_code_available
from ..utils.filesystem_exploration import get_file_content
from ..utils.validation import validate_maven_coordinates

logger = logging.getLogger(__name__)


class GetFileError(Exception):
  """Base exception for get_file tool errors."""

  pass


class ArtifactNotIndexedError(GetFileError):
  """Raised when artifact is not indexed."""

  pass


class FileNotFoundError(GetFileError):
  """Raised when file is not found."""

  pass


async def get_file(
  group_id: str,
  artifact_id: str,
  version: str,
  file_path: str,
  start_line: Optional[int] = None,
  end_line: Optional[int] = None,
) -> GetFileResult:
  """Retrieve file content from an indexed artifact.

  Args:
    group_id: Maven group ID (e.g., 'org.springframework')
    artifact_id: Maven artifact ID (e.g., 'spring-core')
    version: Maven version (e.g., '5.3.21')
    file_path: Relative path to file within artifact
    start_line: Start line number (1-based, optional)
    end_line: End line number (1-based, optional)

  Returns:
    GetFileResult containing file information and content

  Raises:
    GetFileError: For various file retrieval failures
  """
  try:
    # Validate parameters
    validate_maven_coordinates(group_id, artifact_id, version)

    # Check if artifact code is available
    if not is_artifact_code_available(group_id, artifact_id, version):
      return GetFileResult(
        status="not_available",
        file_info={"name": "", "size": "", "line_count": 0},
        content={"start_line": 0, "end_line": 0, "source_code": ""},
      )

    # Get artifact code directory
    storage_manager = StorageManager()
    base_path = storage_manager.get_code_path(group_id, artifact_id, version)

    if not base_path.exists():
      return GetFileResult(
        status="not_found",
        file_info={"name": "", "size": "", "line_count": 0},
        content={"start_line": 0, "end_line": 0, "source_code": ""},
      )

    # Use relative file path directly (same approach as search_file_names)
    normalized_file_path = file_path.strip()
    full_file_path = base_path / normalized_file_path

    if not full_file_path.exists():
      return GetFileResult(
        status="file_not_found",
        file_info={"name": "", "size": "", "line_count": 0},
        content={"start_line": 0, "end_line": 0, "source_code": ""},
      )

    if not full_file_path.is_file():
      return GetFileResult(
        status="not_file",
        file_info={"name": "", "size": "", "line_count": 0},
        content={"start_line": 0, "end_line": 0, "source_code": ""},
      )

    # Get file content
    result = get_file_content(
      base_path=str(base_path),
      file_path=normalized_file_path,
      start_line=start_line,
      end_line=end_line,
    )

    return GetFileResult(
      status="success",
      file_info=result["file_info"],
      content=result["content"],
    )

  except Exception as e:
    logger.error(f"Error in get_file: {e}")
    return GetFileResult(
      status="internal_error",
      file_info={"name": "", "size": "", "line_count": 0},
      content={"start_line": 0, "end_line": 0, "source_code": ""},
    )


# MCP Tool definition
GET_FILE_TOOL = Tool(
  name="get_file",
  description="Retrieve file content from an indexed artifact with optional line range",
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
      "file_path": {
        "type": "string",
        "description": "Relative path to file within artifact",
      },
      "start_line": {
        "type": "integer",
        "description": "Start line number (1-based, optional)",
        "minimum": 1,
      },
      "end_line": {
        "type": "integer",
        "description": "End line number (1-based, optional)",
        "minimum": 1,
      },
    },
    "required": ["group_id", "artifact_id", "version", "file_path"],
  },
)


async def handle_get_file(arguments: Dict[str, Any]) -> list[TextContent]:
  """Handle get_file MCP tool call."""
  try:
    result = await get_file(
      group_id=arguments["group_id"],
      artifact_id=arguments["artifact_id"],
      version=arguments["version"],
      file_path=arguments["file_path"],
      start_line=arguments.get("start_line"),
      end_line=arguments.get("end_line"),
    )

    import json

    return [
      TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False))
    ]

  except Exception as e:
    logger.error(f"Error in handle_get_file: {e}")
    error_result = {
      "status": "internal_error",
      "file_info": {"name": "", "size": "", "line_count": 0},
      "content": {"start_line": 0, "end_line": 0, "source_code": ""},
    }
    import json

    return [
      TextContent(
        type="text", text=json.dumps(error_result, indent=2, ensure_ascii=False)
      )
    ]
