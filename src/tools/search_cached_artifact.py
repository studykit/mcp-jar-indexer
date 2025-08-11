"""MCP tool for searching cached artifact files in Maven/Gradle local repositories."""

import json
import logging
from typing import Any, Dict

from mcp.types import TextContent, Tool

from ..jartype.core_types import SearchCachedArtifactResult
from ..utils.cache_utils import search_cached_artifacts
from ..utils.validation import validate_maven_coordinates

logger = logging.getLogger(__name__)

SEARCH_CACHED_ARTIFACT_TOOL = Tool(
  name="search_cached_artifact",
  description="Search for source JAR files in Maven/Gradle local repository caches",
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
      "version_filter": {"type": "string", "description": "Version constraints (e.g., '5.3.21', '>=5.3.0', '<6.0.0', '>=5.0.0,<6.0.0')"},
      "cache": {
        "type": "string",
        "description": "Cache types to search: 'maven', 'gradle', or 'maven,gradle' (default: 'maven,gradle')",
        "default": "maven,gradle",
      },
    },
    "required": ["group_id", "artifact_id"],
  },
)


async def search_cached_artifact_impl(
  group_id: str, artifact_id: str, version_filter: str | None = None, cache: str = "maven,gradle"
) -> SearchCachedArtifactResult:
  """
  Search for source JAR files in Maven/Gradle local repository caches.

  Args:
    group_id: Maven group ID
    artifact_id: Maven artifact ID
    version_filter: Optional version filter (if None, searches all versions)
    cache: Cache types to search ("maven", "gradle", "maven,gradle")

  Returns:
    Dictionary with status and paths information
  """
  try:
    # Validate Maven coordinates
    if version_filter:
      validate_maven_coordinates(group_id, artifact_id, version_filter)
    else:
      # Validate group_id and artifact_id only
      if not group_id or not group_id.strip():
        raise ValueError("group_id is required and cannot be empty")
      if not artifact_id or not artifact_id.strip():
        raise ValueError("artifact_id is required and cannot be empty")

    # Search for cached source JARs
    source_jar_paths = search_cached_artifacts(group_id, artifact_id, version_filter, cache)

    if source_jar_paths:
      return SearchCachedArtifactResult(status="success", paths=source_jar_paths)
    else:
      version_info = f":{version_filter}" if version_filter else " (all versions)"
      return SearchCachedArtifactResult(
        status="not_found",
        paths=[],
        message=f"No source JAR files found for {group_id}:{artifact_id}{version_info}",
      )

  except ValueError as e:
    logger.warning(f"Invalid Maven coordinates: {e}")
    return SearchCachedArtifactResult(
      status="invalid_coordinates", paths=[], message=str(e)
    )
  except Exception as e:
    logger.error(f"Error searching cached source JAR: {e}")
    return SearchCachedArtifactResult(
      status="internal_error", paths=[], message=f"Internal error: {e}"
    )


async def handle_search_cached_artifact(arguments: Dict[str, Any]) -> list[TextContent]:
  """Handle search_cached_artifact MCP tool request."""
  try:
    # Extract arguments with defaults
    group_id = arguments["group_id"]
    artifact_id = arguments["artifact_id"]
    version_filter = arguments.get("version_filter")
    cache = arguments.get("cache", "maven,gradle")

    # Execute search
    result = await search_cached_artifact_impl(group_id, artifact_id, version_filter, cache)

    # Return formatted response
    return [TextContent(type="text", text=json.dumps(result, indent=2))]

  except Exception as e:
    logger.error(f"Error in handle_search_cached_artifact: {e}")
    error_response = SearchCachedArtifactResult(
      status="internal_error",
      paths=[],
      message=f"Failed to search cached source JAR: {e}",
    )
    return [TextContent(type="text", text=json.dumps(error_response, indent=2))]
