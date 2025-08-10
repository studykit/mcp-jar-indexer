"""MCP Tool for registering source JAR files or directories."""

import logging
from pathlib import Path
from typing import Any, Dict, Optional

from mcp.types import TextContent, Tool

from ..core.git_handler import (
  GitAuthenticationError,
  GitCloneFailedError,
  GitError,
  GitHandler,
  GitRefNotFoundError,
)
from ..core.source_processor import SourceProcessor
from ..core.storage import StorageManager
from ..utils.file_utils import download_file, validate_jar_file, safe_copy_tree
from ..utils.validation import validate_maven_coordinates, validate_uri_format

logger = logging.getLogger(__name__)


class RegisterSourceError(Exception):
  """Base exception for register_source tool errors."""

  pass


class ResourceNotFoundError(RegisterSourceError):
  """Raised when the source resource cannot be found."""

  pass


class DownloadFailedError(RegisterSourceError):
  """Raised when remote source download fails."""

  pass


class InvalidSourceError(RegisterSourceError):
  """Raised when the source is invalid or corrupted."""

  pass


class UnsupportedSourceTypeError(RegisterSourceError):
  """Raised when the source type is not supported."""

  pass


async def register_source(
  group_id: str,
  artifact_id: str,
  version: str,
  source_uri: str,
  auto_index: bool = True,
  git_ref: Optional[str] = None,
) -> Dict[str, Any]:
  """Register a source JAR file or directory.

  Args:
      group_id: Maven group ID (e.g., 'org.springframework')
      artifact_id: Maven artifact ID (e.g., 'spring-core')
      version: Maven version (e.g., '5.3.21')
      source_uri: URI to the source (JAR file, directory, or Git repository)
      auto_index: Whether to automatically index after registration
      git_ref: Git reference (branch/tag/commit) for Git repositories

  Returns:
      Dict containing registration status and details

  Raises:
      RegisterSourceError: For various registration failures
  """
  try:
    # Validate parameters
    validate_maven_coordinates(group_id, artifact_id, version)
    validate_uri_format(source_uri)

    # Initialize managers
    storage_manager = StorageManager()
    source_processor = SourceProcessor(storage_manager)

    # Ensure storage directories exist
    storage_manager.ensure_directories()
    if not storage_manager.validate_directory_permissions():
      raise RegisterSourceError("Storage directories are not accessible")

    # Parse source URI to determine type and details
    try:
      uri_type, parsed_info = source_processor.parse_uri(source_uri)
      logger.info(f"Parsed URI type: {uri_type} for URI: {source_uri}")
    except ValueError as e:
      raise UnsupportedSourceTypeError(f"URI parsing failed: {str(e)}")

    # Handle different source types based on parsed information
    if uri_type == "file":
      if parsed_info["type"] == "jar":
        await _handle_local_jar_file(
          storage_manager, parsed_info, group_id, artifact_id, version
        )
      elif parsed_info["type"] == "directory":
        await _handle_local_directory(
          storage_manager, parsed_info, group_id, artifact_id, version
        )
      else:
        raise UnsupportedSourceTypeError(f"Unsupported file type: {parsed_info['type']}")
    elif uri_type == "http":
      if parsed_info["type"] == "jar":
        await _handle_remote_jar_file(
          storage_manager, parsed_info, group_id, artifact_id, version
        )
      else:
        raise UnsupportedSourceTypeError(f"Unsupported HTTP type: {parsed_info['type']}")
    elif uri_type == "git":
      if git_ref is None:
        git_ref = "main"  # Default to main branch
      await _handle_git_repository(
        storage_manager, parsed_info, git_ref, group_id, artifact_id, version
      )
    else:
      raise UnsupportedSourceTypeError(f"Unsupported URI type: {uri_type}")

    # TODO: Implement auto_index functionality when index_artifact tool is ready
    if auto_index:
      # For now, just return registered_only until indexing is implemented
      indexed = False
      status = "registered_only"
      message = "Source registered successfully. Use index_artifact tool to perform indexing."
    else:
      indexed = False
      status = "registered_only"
      message = "Source registered successfully. Use index_artifact tool to perform indexing."

    return {
      "group_id": group_id,
      "artifact_id": artifact_id,
      "version": version,
      "status": status,
      "indexed": indexed,
      "message": message,
    }

  except GitCloneFailedError as e:
    logger.error(f"Git clone failed: {e}")
    return {
      "status": "git_clone_failed",
      "message": f"Failed to clone Git repository: {str(e)}",
    }
  except GitRefNotFoundError as e:
    logger.error(f"Git ref not found: {e}")
    return {
      "status": "git_ref_not_found",
      "message": f"Git reference not found: {str(e)}",
    }
  except GitAuthenticationError as e:
    logger.error(f"Git authentication failed: {e}")
    return {
      "status": "git_authentication_failed",
      "message": f"Git authentication failed: {str(e)}",
    }
  except ResourceNotFoundError as e:
    logger.error(f"Resource not found: {e}")
    return {"status": "resource_not_found", "message": str(e)}
  except DownloadFailedError as e:
    logger.error(f"Download failed: {e}")
    return {"status": "download_failed", "message": str(e)}
  except InvalidSourceError as e:
    logger.error(f"Invalid source: {e}")
    return {"status": "invalid_source", "message": str(e)}
  except UnsupportedSourceTypeError as e:
    logger.error(f"Unsupported source type: {e}")
    return {"status": "unsupported_source_type", "message": str(e)}
  except Exception as e:
    logger.error(f"Unexpected error in register_source: {e}")
    return {
      "status": "internal_error",
      "message": f"Internal error occurred: {str(e)}",
    }


async def _handle_local_jar_file(
  storage_manager: StorageManager,
  parsed_info: Dict[str, Any],
  group_id: str,
  artifact_id: str,
  version: str,
) -> None:
  """Handle local JAR file source registration."""
  try:
    local_path = Path(parsed_info["path"])
    if not local_path.exists():
      raise ResourceNotFoundError(
        f"Local JAR file not found: {local_path}"
      )
    if not validate_jar_file(local_path):
      raise InvalidSourceError(f"Invalid JAR file: {local_path}")

    # Copy JAR to source-jar directory
    target_dir = storage_manager.get_source_jar_path(group_id, artifact_id, version)
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / f"{artifact_id}-{version}-sources.jar"

    import shutil
    shutil.copy2(local_path, target_path)
    logger.info(f"Copied JAR file to: {target_path}")

  except Exception as e:
    if isinstance(e, RegisterSourceError):
      raise
    raise RegisterSourceError(f"Error processing local JAR file: {str(e)}")


async def _handle_remote_jar_file(
  storage_manager: StorageManager,
  parsed_info: Dict[str, Any],
  group_id: str,
  artifact_id: str,
  version: str,
) -> None:
  """Handle remote JAR file source registration."""
  try:
    url = parsed_info["url"]
    target_dir = storage_manager.get_source_jar_path(group_id, artifact_id, version)
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / f"{artifact_id}-{version}-sources.jar"

    try:
      download_file(url, target_path)
      if not validate_jar_file(target_path):
        target_path.unlink()  # Clean up invalid file
        raise InvalidSourceError(f"Downloaded file is not a valid JAR file: {url}")
      logger.info(f"Downloaded JAR file to: {target_path}")
    except Exception as e:
      raise DownloadFailedError(f"Failed to download JAR file: {url} - {str(e)}")

  except Exception as e:
    if isinstance(e, RegisterSourceError):
      raise
    raise RegisterSourceError(f"Error processing remote JAR file: {str(e)}")


async def _handle_local_directory(
  storage_manager: StorageManager,
  parsed_info: Dict[str, Any],
  group_id: str,
  artifact_id: str,
  version: str,
) -> None:
  """Handle local directory source registration."""
  try:
    source_path = Path(parsed_info["path"])
    if not source_path.exists():
      raise ResourceNotFoundError(f"Local directory not found: {source_path}")
    if not source_path.is_dir():
      raise InvalidSourceError(f"Path is not a directory: {source_path}")

    # Check if it's a Git repository
    git_handler = GitHandler(storage_manager)
    if git_handler.is_git_repository(str(source_path)):
      raise UnsupportedSourceTypeError(
        f"Git repository directory must be registered with git_ref parameter: {source_path}"
      )

    # Copy directory to code directory
    target_path = storage_manager.get_code_path(group_id, artifact_id, version)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Remove existing directory if it exists
    if target_path.exists():
      import shutil
      shutil.rmtree(target_path)

    safe_copy_tree(source_path, target_path)
    logger.info(f"Copied directory to: {target_path}")

  except Exception as e:
    if isinstance(e, RegisterSourceError):
      raise
    raise RegisterSourceError(f"Error processing local directory: {str(e)}")


async def _handle_git_repository(
  storage_manager: StorageManager,
  parsed_info: Dict[str, Any],
  git_ref: str,
  group_id: str,
  artifact_id: str,
  version: str,
) -> None:
  """Handle Git repository source registration."""
  try:
    git_handler = GitHandler(storage_manager)
    git_url = parsed_info["url"]

    # Get paths for bare repo and worktree
    bare_repo_path = storage_manager.get_git_bare_path(group_id, artifact_id)
    worktree_path = storage_manager.get_code_path(group_id, artifact_id, version)

    # Clone or update bare repository
    if bare_repo_path.exists():
      # Update existing repo
      git_handler.update_repository(group_id, artifact_id)
      logger.info(f"Updated existing bare repository: {bare_repo_path}")
    else:
      # Clone new repo
      git_handler.clone_bare_repository(git_url, group_id, artifact_id)
      logger.info(f"Created bare repository: {bare_repo_path}")

    # Create worktree for specific version (this will validate the git_ref internally)
    if worktree_path.exists():
      # Remove existing worktree
      git_handler.remove_worktree(group_id, artifact_id, version)

    # The create_worktree method will validate the git_ref internally and raise GitRefNotFoundError if not found
    git_handler.create_worktree(group_id, artifact_id, version, git_ref)
    logger.info(f"Created worktree: {worktree_path} for ref: {git_ref}")

  except GitError:
    # Re-raise Git errors to be handled by the main function
    raise
  except Exception as e:
    raise RegisterSourceError(f"Error processing Git repository: {str(e)}")


# MCP Tool definition
REGISTER_SOURCE_TOOL = Tool(
  name="register_source",
  description="Register a source JAR file, directory, or Git repository for indexing",
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
      "source_uri": {
        "type": "string",
        "description": "URI to the source (JAR file, directory, or Git repository)",
      },
      "auto_index": {
        "type": "boolean",
        "description": "Whether to automatically index after registration",
        "default": True,
      },
      "git_ref": {
        "type": "string",
        "description": "Git reference (branch/tag/commit) for Git repositories",
        "default": None,
      },
    },
    "required": ["group_id", "artifact_id", "version", "source_uri"],
  },
)


async def handle_register_source(arguments: Dict[str, Any]) -> list[TextContent]:
  """Handle register_source MCP tool call."""
  try:
    result = await register_source(
      group_id=arguments["group_id"],
      artifact_id=arguments["artifact_id"],
      version=arguments["version"],
      source_uri=arguments["source_uri"],
      auto_index=arguments.get("auto_index", True),
      git_ref=arguments.get("git_ref"),
    )

    import json

    return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False))]

  except Exception as e:
    logger.error(f"Error in handle_register_source: {e}")
    error_result = {
      "status": "internal_error",
      "message": f"Internal error occurred: {str(e)}",
    }
    import json

    return [TextContent(type="text", text=json.dumps(error_result, indent=2, ensure_ascii=False))]