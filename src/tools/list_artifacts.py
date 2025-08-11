"""MCP Tool for listing all artifacts and their status."""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from packaging import version as packaging_version

from mcp.types import TextContent, Tool

from ..core.storage import StorageManager

logger = logging.getLogger(__name__)


class ListArtifactsError(Exception):
  """Base exception for list_artifacts tool errors."""

  pass


def parse_version_filter(version_filter: str) -> List[tuple[str, str]]:
  """Parse version filter string into list of constraints.

  Args:
    version_filter: Version constraint string like "5.3.21", ">=5.3.0", "<6.0.0", ">=5.0.0,<6.0.0"

  Returns:
    List of (operator, version) tuples

  Raises:
    ValueError: If version filter format is invalid
  """
  constraints: List[tuple[str, str]] = []

  # Split by comma for multiple constraints
  parts = version_filter.split(",")

  for part in parts:
    part = part.strip()
    if not part:
      continue

    # Check for operators
    if part.startswith(">="):
      constraints.append((">=", part[2:].strip()))
    elif part.startswith("<="):
      constraints.append(("<=", part[2:].strip()))
    elif part.startswith(">"):
      constraints.append((">", part[1:].strip()))
    elif part.startswith("<"):
      constraints.append(("<", part[1:].strip()))
    elif part.startswith("="):
      constraints.append(("==", part[1:].strip()))
    else:
      # No operator means exact match
      constraints.append(("==", part))

  return constraints


def check_version_constraint(
  artifact_version: str, constraints: List[tuple[str, str]]
) -> bool:
  """Check if version satisfies all constraints.

  Args:
    artifact_version: Version to check
    constraints: List of (operator, version) tuples

  Returns:
    True if version satisfies all constraints
  """
  try:
    parsed_version = packaging_version.parse(artifact_version)

    for operator, constraint_version in constraints:
      parsed_constraint = packaging_version.parse(constraint_version)

      if operator == "==":
        if parsed_version != parsed_constraint:
          return False
      elif operator == ">":
        if parsed_version <= parsed_constraint:
          return False
      elif operator == ">=":
        if parsed_version < parsed_constraint:
          return False
      elif operator == "<":
        if parsed_version >= parsed_constraint:
          return False
      elif operator == "<=":
        if parsed_version > parsed_constraint:
          return False

    return True
  except Exception:
    # If version parsing fails, fall back to string comparison
    for operator, constraint_version in constraints:
      if operator == "==":
        if artifact_version != constraint_version:
          return False
    return True


def get_artifact_status(
  storage_manager: StorageManager, group_id: str, artifact_id: str, version: str
) -> str:
  """Get status string for an artifact.

  Args:
    storage_manager: Storage manager instance
    group_id: Maven group ID
    artifact_id: Maven artifact ID
    version: Maven version

  Returns:
    Comma-separated status string (e.g., "source-jar,index,file-searchable")
  """
  status_parts: List[str] = []

  # Check source types separately
  source_jar_path = storage_manager.get_source_jar_path(group_id, artifact_id, version)
  git_bare_path = storage_manager.get_git_bare_path(group_id, artifact_id)
  code_path = storage_manager.get_code_path(group_id, artifact_id, version)

  # Check for JAR source
  if source_jar_path.exists() and any(source_jar_path.glob("*.jar")):
    status_parts.append("source-jar")

  # Check for Git source (bare repository)
  if git_bare_path.exists() and git_bare_path.is_dir():
    status_parts.append("source-git")

  # Check for directory source (in code directory without JAR or Git)
  if code_path.exists() and code_path.is_dir():
    # Only add source-dir if no JAR or Git source exists
    has_jar = source_jar_path.exists() and any(source_jar_path.glob("*.jar"))
    has_git = git_bare_path.exists() and git_bare_path.is_dir()
    
    if not has_jar and not has_git:
      # Check if it has content
      try:
        contents = list(code_path.iterdir())
        if contents:
          status_parts.append("source-dir")
      except OSError:
        pass

  # Note: Phase 1 implementation does not perform actual indexing
  # The 'index' status will be added in Phase 2-3 when real indexing is implemented

  # Check if file-searchable (code directory has actual source files)
  if code_path.exists() and code_path.is_dir():
    try:
      # Check if directory has source files (not just metadata)
      has_source_files = False
      for item in code_path.iterdir():
        if item.is_file() and not item.name.startswith("."):
          has_source_files = True
          break
        elif item.is_dir() and not item.name.startswith("."):
          # Check if subdirectory has files
          for subitem in item.iterdir():
            if subitem.is_file():
              has_source_files = True
              break
          if has_source_files:
            break

      if has_source_files:
        status_parts.append("file-searchable")
    except OSError:
      pass

  return ",".join(status_parts)


def scan_all_artifacts(storage_manager: StorageManager) -> List[Dict[str, str]]:
  """Scan storage directories to find all artifacts.

  Args:
    storage_manager: Storage manager instance

  Returns:
    List of artifact dictionaries with group_id, artifact_id, version, and status
  """
  artifacts: List[Dict[str, str]] = []
  seen_artifacts: set[tuple[str, str, str]] = (
    set()
  )  # Track unique (group_id, artifact_id, version) tuples

  # Scan source-jar directory
  source_jar_dir = storage_manager.get_source_jar_dir()
  if source_jar_dir.exists():
    for group_dir in source_jar_dir.iterdir():
      if not group_dir.is_dir():
        continue

      # Traverse group directory structure
      for artifact_path in group_dir.rglob("*"):
        if not artifact_path.is_dir():
          continue

        # Check if this directory contains JAR files
        jar_files = list(artifact_path.glob("*.jar"))
        if not jar_files:
          continue

        # Extract Maven coordinates from path
        try:
          relative_path = artifact_path.relative_to(source_jar_dir)
          path_parts = relative_path.parts

          if len(path_parts) < 3:
            continue

          # Last part is version, second to last is artifact_id
          version = path_parts[-1]
          artifact_id = path_parts[-2]
          # Everything else is group_id
          group_id = ".".join(path_parts[:-2])

          artifact_key = (group_id, artifact_id, version)
          if artifact_key not in seen_artifacts:
            seen_artifacts.add(artifact_key)
            status = get_artifact_status(
              storage_manager, group_id, artifact_id, version
            )
            artifacts.append(
              {
                "group_id": group_id,
                "artifact_id": artifact_id,
                "version": version,
                "status": status,
              }
            )
        except Exception as e:
          logger.warning(f"Failed to parse artifact path {artifact_path}: {e}")

  # Scan git-bare directory for Git sources
  git_bare_dir = storage_manager.get_git_bare_dir()
  if git_bare_dir.exists():
    for group_dir in git_bare_dir.iterdir():
      if not group_dir.is_dir():
        continue

      # Traverse group directory structure
      for artifact_path in group_dir.rglob("*"):
        if not artifact_path.is_dir():
          continue

        # Check if this is a git bare repository
        if not (artifact_path / "HEAD").exists():
          continue

        # Extract Maven coordinates from path (without version for git repos)
        try:
          relative_path = artifact_path.relative_to(git_bare_dir)
          path_parts = relative_path.parts

          if len(path_parts) < 2:
            continue

          # Last part is artifact_id
          artifact_id = path_parts[-1]
          # Everything else is group_id
          group_id = ".".join(path_parts[:-1])

          # Git repos might have multiple versions in code directory
          # Check code directory for versions
          code_base = storage_manager.get_code_dir()
          group_path = group_id.replace(".", "/")
          artifact_code_dir = code_base / group_path / artifact_id

          if artifact_code_dir.exists():
            for version_dir in artifact_code_dir.iterdir():
              if version_dir.is_dir():
                version = version_dir.name
                artifact_key = (group_id, artifact_id, version)
                if artifact_key not in seen_artifacts:
                  seen_artifacts.add(artifact_key)
                  status = get_artifact_status(
                    storage_manager, group_id, artifact_id, version
                  )
                  artifacts.append(
                    {
                      "group_id": group_id,
                      "artifact_id": artifact_id,
                      "version": version,
                      "status": status,
                    }
                  )
        except Exception as e:
          logger.warning(f"Failed to parse git artifact path {artifact_path}: {e}")

  # Scan code directory for any artifacts not found above
  code_dir = storage_manager.get_code_dir()
  if code_dir.exists():
    # We need to find directories that follow the pattern:
    # code_dir/group/path/artifact_id/version/
    # where group/path can have multiple levels (e.g., org/springframework)

    for root, dirs, files in os.walk(code_dir):
      root_path = Path(root)

      # Skip if this directory has no files
      if not files and not dirs:
        continue

      # Check if this looks like a version directory
      # (contains source files, not just subdirectories)
      has_source_files = any(
        f.endswith((".java", ".kt", ".scala", ".groovy", ".class")) for f in files
      )

      if not has_source_files:
        # Check subdirectories for source files
        has_source_in_subdirs = False
        for d in dirs:
          subdir_path = root_path / d
          if subdir_path.is_dir():
            for subfile in subdir_path.glob("*"):
              if subfile.is_file() and subfile.suffix in {
                ".java",
                ".kt",
                ".scala",
                ".groovy",
                ".class",
              }:
                has_source_in_subdirs = True
                break
            if has_source_in_subdirs:
              break

        if not has_source_in_subdirs:
          continue

      # Try to extract Maven coordinates from path
      try:
        relative_path = root_path.relative_to(code_dir)
        path_parts = relative_path.parts

        # Need at least 3 parts: group/artifact/version
        if len(path_parts) < 3:
          continue

        # The last part should be the version
        # The second-to-last should be the artifact ID
        # Everything before that is the group ID
        version = path_parts[-1]
        artifact_id = path_parts[-2]
        group_parts = path_parts[:-2]

        # Reconstruct group_id by joining with dots
        group_id = ".".join(group_parts)

        # Validate that this looks like a proper Maven structure
        # Skip if the version part doesn't look like a version
        if not any(c.isdigit() for c in version):
          continue

        artifact_key = (group_id, artifact_id, version)
        if artifact_key not in seen_artifacts:
          seen_artifacts.add(artifact_key)
          status = get_artifact_status(storage_manager, group_id, artifact_id, version)
          artifacts.append(
            {
              "group_id": group_id,
              "artifact_id": artifact_id,
              "version": version,
              "status": status,
            }
          )
      except Exception as e:
        logger.debug(f"Skipping path {root_path}: {e}")

  return artifacts


async def list_artifacts(
  page: Optional[int] = None,
  page_size: Optional[int] = None,
  group_filter: Optional[str] = None,
  artifact_filter: Optional[str] = None,
  version_filter: Optional[str] = None,
  status_filter: Optional[str] = None,
) -> Dict[str, Any]:
  """List all artifacts and their status.

  Args:
    page: Page number (1-based)
    page_size: Number of items per page
    group_filter: Filter by group ID
    artifact_filter: Filter by artifact ID
    version_filter: Version constraints (e.g., ">=5.3.0", "<6.0.0")
    status_filter: Filter by status components (comma-separated)

  Returns:
    Dictionary with status, pagination info, and artifact list
  """
  try:
    # Initialize storage manager
    storage_manager = StorageManager()
    storage_manager.ensure_directories()

    # Scan all artifacts
    all_artifacts = scan_all_artifacts(storage_manager)

    # Apply filters
    filtered_artifacts: List[Dict[str, str]] = []

    for artifact in all_artifacts:
      # Apply group filter
      if group_filter and not artifact["group_id"].startswith(group_filter):
        continue

      # Apply artifact filter
      if artifact_filter and not artifact["artifact_id"].startswith(artifact_filter):
        continue

      # Apply version filter
      if version_filter:
        try:
          constraints = parse_version_filter(version_filter)
          if not check_version_constraint(artifact["version"], constraints):
            continue
        except Exception as e:
          logger.warning(f"Failed to apply version filter: {e}")

      # Apply status filter
      if status_filter:
        required_statuses = set(s.strip() for s in status_filter.split(","))
        artifact_statuses: set[str] = (
          set(s.strip() for s in artifact["status"].split(","))
          if artifact["status"]
          else set()
        )

        # Check if artifact has all required statuses
        if not required_statuses.issubset(artifact_statuses):
          continue

      filtered_artifacts.append(artifact)

    # Sort artifacts by group_id, artifact_id, version
    filtered_artifacts.sort(
      key=lambda x: (x["group_id"], x["artifact_id"], x["version"])
    )

    # Apply pagination
    total_count = len(filtered_artifacts)

    if page is not None and page_size is not None:
      # Calculate pagination
      start_idx = (page - 1) * page_size
      end_idx = start_idx + page_size
      paginated_artifacts = filtered_artifacts[start_idx:end_idx]
      total_pages = (total_count + page_size - 1) // page_size

      return {
        "status": "success",
        "pagination": {
          "page": page,
          "total_count": total_count,
          "total_pages": total_pages,
        },
        "artifacts": paginated_artifacts,
      }
    else:
      # No pagination, return all
      return {
        "status": "success",
        "pagination": {
          "page": 1,
          "total_count": total_count,
          "total_pages": 1,
        },
        "artifacts": filtered_artifacts,
      }

  except Exception as e:
    logger.error(f"Error in list_artifacts: {e}")
    return {"status": "internal_error", "message": str(e), "artifacts": []}


# MCP Tool definition
LIST_ARTIFACTS_TOOL = Tool(
  name="list_artifacts",
  description="List all artifacts and check their status (source-jar/git/dir, index, file-searchable)",
  inputSchema={
    "type": "object",
    "properties": {
      "page": {"type": "integer", "description": "Page number (1-based)", "minimum": 1},
      "page_size": {
        "type": "integer",
        "description": "Number of items per page",
        "minimum": 1,
        "maximum": 100,
      },
      "group_filter": {"type": "string", "description": "Filter by group ID prefix"},
      "artifact_filter": {
        "type": "string",
        "description": "Filter by artifact ID prefix",
      },
      "version_filter": {
        "type": "string",
        "description": "Version constraints (e.g., '5.3.21', '>=5.3.0', '<6.0.0', '>=5.0.0,<6.0.0')",
      },
      "status_filter": {
        "type": "string",
        "description": "Filter by status components (comma-separated: 'source-jar', 'source-git', 'source-dir', 'index', 'file-searchable')",
      },
    },
    "required": [],
  },
)


async def handle_list_artifacts(arguments: Dict[str, Any]) -> list[TextContent]:
  """Handle list_artifacts MCP tool call."""
  try:
    result = await list_artifacts(
      page=arguments.get("page"),
      page_size=arguments.get("page_size"),
      group_filter=arguments.get("group_filter"),
      artifact_filter=arguments.get("artifact_filter"),
      version_filter=arguments.get("version_filter"),
      status_filter=arguments.get("status_filter"),
    )

    return [
      TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False))
    ]

  except Exception as e:
    logger.error(f"Error in handle_list_artifacts: {e}")
    error_result: Dict[str, Any] = {
      "status": "internal_error",
      "message": str(e),
      "artifacts": [],
    }
    return [
      TextContent(
        type="text", text=json.dumps(error_result, indent=2, ensure_ascii=False)
      )
    ]
