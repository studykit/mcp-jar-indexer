"""MCP Tool for indexing artifact source code."""

import logging
import time
from typing import Any, Dict

from mcp.types import TextContent, Tool

from ..core.storage import StorageManager
from ..jartype.core_types import IndexArtifactResult, RegisteredSourceInfo
from ..utils.artifact_utils import (
  get_registered_source_info,
  is_artifact_code_available,
)
from ..utils.source_extraction import (
  copy_directory_source,
  create_git_worktree,
  extract_jar_source,
)
from ..utils.validation import validate_maven_coordinates

logger = logging.getLogger(__name__)


class IndexArtifactError(Exception):
  """Base exception for index_artifact tool errors."""

  pass


class ArtifactNotRegisteredError(IndexArtifactError):
  """Raised when artifact is not registered."""

  pass


class ExtractionFailedError(IndexArtifactError):
  """Raised when source extraction fails."""

  pass


async def index_artifact(
  group_id: str, artifact_id: str, version: str
) -> IndexArtifactResult:
  """Index an artifact by extracting its source code.

  Args:
    group_id: Maven group ID (e.g., 'org.springframework')
    artifact_id: Maven artifact ID (e.g., 'spring-core')
    version: Maven version (e.g., '5.3.21')

  Returns:
    IndexArtifactResult containing status and details

  Raises:
    IndexArtifactError: For various indexing failures
  """
  start_time = time.time()

  try:
    # Validate parameters
    validate_maven_coordinates(group_id, artifact_id, version)

    # Initialize storage manager
    storage_manager = StorageManager()
    storage_manager.ensure_directories()

    # Check if source code is already available
    if is_artifact_code_available(group_id, artifact_id, version):
      cache_location = storage_manager.get_code_path(group_id, artifact_id, version)
      processing_time = f"{time.time() - start_time:.2f}s"
      
      # Get current artifact status
      from .list_artifacts import get_artifact_status
      current_status = get_artifact_status(storage_manager, group_id, artifact_id, version)
      
      return IndexArtifactResult(
        status=current_status,
        cache_location=str(cache_location),
        processing_time=processing_time,
      )


    # Get registered source info
    source_info = get_registered_source_info(group_id, artifact_id, version)
    if source_info is None:
      raise ArtifactNotRegisteredError(
        f"Artifact {group_id}:{artifact_id}:{version} is not registered. "
        + "Use register_source tool first."
      )

    # Extract source based on type
    await _extract_source_to_code_directory(storage_manager, source_info)

    # Source extraction completed - get current status
    cache_location = storage_manager.get_code_path(group_id, artifact_id, version)
    processing_time = f"{time.time() - start_time:.2f}s"
    
    # Get current artifact status
    from .list_artifacts import get_artifact_status
    current_status = get_artifact_status(storage_manager, group_id, artifact_id, version)
    
    return IndexArtifactResult(
      status=current_status,
      cache_location=str(cache_location),
      processing_time=processing_time,
    )

  except ArtifactNotRegisteredError as e:
    processing_time = f"{time.time() - start_time:.2f}s"
    return IndexArtifactResult(
      status="not_registered",
      cache_location="",
      processing_time=processing_time,
      message=str(e),
    )
  except ExtractionFailedError as e:
    processing_time = f"{time.time() - start_time:.2f}s"
    return IndexArtifactResult(
      status="extraction_failed",
      cache_location="",
      processing_time=processing_time,
      message=str(e),
    )
  except Exception as e:
    logger.error(f"Unexpected error in index_artifact: {e}")
    processing_time = f"{time.time() - start_time:.2f}s"
    return IndexArtifactResult(
      status="internal_error",
      cache_location="",
      processing_time=processing_time,
      message=f"Internal error: {str(e)}",
    )


async def _extract_source_to_code_directory(
  storage_manager: StorageManager, source_info: RegisteredSourceInfo
) -> None:
  """Extract source code to the code directory based on source type."""
  try:
    group_id = source_info["group_id"]
    artifact_id = source_info["artifact_id"]
    version = source_info["version"]
    source_type = source_info["source_type"]
    local_path = source_info["local_path"]

    target_dir = storage_manager.get_code_path(group_id, artifact_id, version)

    # Remove existing target directory if it exists
    if target_dir.exists():
      import shutil

      shutil.rmtree(target_dir)

    # Ensure the target directory exists
    target_dir.mkdir(parents=True, exist_ok=True)

    if source_type == "jar":
      # Extract JAR file from source-jar directory
      source_jar_dir = storage_manager.base_path / local_path
      if not source_jar_dir.exists():
        raise ExtractionFailedError(f"Source JAR directory not found: {source_jar_dir}")

      # Find the actual JAR file in the directory
      jar_files = list(source_jar_dir.glob("*.jar"))
      if not jar_files:
        raise ExtractionFailedError(
          f"No JAR files found in directory: {source_jar_dir}"
        )

      if len(jar_files) > 1:
        logger.warning(
          f"Multiple JAR files found in {source_jar_dir}, using first one: {jar_files[0]}"
        )

      source_jar_path = jar_files[0]
      extract_jar_source(str(source_jar_path), str(target_dir))
      logger.info(f"Extracted JAR source from {source_jar_path} to: {target_dir}")

    elif source_type == "directory":
      # The directory source should already be in the code directory
      # This case should not occur in normal flow, but handle it
      source_dir = storage_manager.base_path / local_path
      if not source_dir.exists():
        raise ExtractionFailedError(f"Source directory not found: {source_dir}")

      copy_directory_source(str(source_dir), str(target_dir))
      logger.info(f"Copied directory source to: {target_dir}")

    elif source_type == "git":
      # Extract from Git worktree
      git_ref = source_info["git_ref"]
      if git_ref is None:
        git_ref = "main"

      # Get bare repo path and create worktree
      bare_repo_path = storage_manager.get_git_bare_path(group_id, artifact_id)
      if not bare_repo_path.exists():
        raise ExtractionFailedError(f"Git bare repository not found: {bare_repo_path}")

      create_git_worktree(str(bare_repo_path), str(target_dir), git_ref)
      logger.info(f"Created Git worktree at: {target_dir}")

    else:
      raise ExtractionFailedError(f"Unsupported source type: {source_type}")

  except Exception as e:
    logger.error(f"Source extraction failed: {e}")
    raise ExtractionFailedError(f"Failed to extract source: {str(e)}")


# MCP Tool definition
INDEX_ARTIFACT_TOOL = Tool(
  name="index_artifact",
  description="Index an artifact by extracting its registered source code for browsing and searching",
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
    },
    "required": ["group_id", "artifact_id", "version"],
  },
)


async def handle_index_artifact(arguments: Dict[str, Any]) -> list[TextContent]:
  """Handle index_artifact MCP tool call."""
  try:
    result = await index_artifact(
      group_id=arguments["group_id"],
      artifact_id=arguments["artifact_id"],
      version=arguments["version"],
    )

    import json

    return [
      TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False))
    ]

  except Exception as e:
    logger.error(f"Error in handle_index_artifact: {e}")
    error_result = {
      "status": "internal_error",
      "cache_location": "",
      "processing_time": "0s",
      "message": f"Handler error: {str(e)}",
    }
    import json

    return [
      TextContent(
        type="text", text=json.dumps(error_result, indent=2, ensure_ascii=False)
      )
    ]
