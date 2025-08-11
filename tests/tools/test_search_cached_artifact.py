"""Tests for search_cached_artifact MCP tool."""

import json
import tempfile
from pathlib import Path
from typing import Dict, Any, Iterable
from unittest.mock import patch

import pytest

from src.tools.search_cached_artifact import (
  handle_search_cached_artifact,
  search_cached_artifact_impl,
)


class TestSearchCachedArtifact:
  """Test cases for search_cached_artifact functionality."""

  @pytest.fixture
  def temp_maven_cache(self) -> Iterable[Path]:
    """Create temporary Maven cache directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
      cache_path = Path(temp_dir) / ".m2" / "repository"
      cache_path.mkdir(parents=True, exist_ok=True)
      yield cache_path

  @pytest.fixture
  def temp_gradle_cache(self) -> Iterable[Path]:
    """Create temporary Gradle cache directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
      cache_path = Path(temp_dir) / ".gradle" / "caches"
      cache_path.mkdir(parents=True, exist_ok=True)
      yield cache_path

  @pytest.mark.asyncio
  async def test_search_cached_artifact_success_maven(
    self, temp_maven_cache: Path
  ) -> None:
    """Test successful source JAR search in Maven cache."""
    # Setup Maven cache structure
    group_path = temp_maven_cache / "org" / "springframework" / "spring-core" / "5.3.21"
    group_path.mkdir(parents=True, exist_ok=True)

    source_jar = group_path / "spring-core-5.3.21-sources.jar"
    source_jar.write_text("mock jar content")

    with (
      patch("src.tools.search_cached_artifact.validate_maven_coordinates"),
      patch(
        "src.tools.search_cached_artifact.search_cached_artifacts",
        return_value=[str(source_jar.absolute())],
      ),
    ):
      result = await search_cached_artifact_impl(
        "org.springframework", "spring-core", "5.3.21", "maven"
      )

      assert result.get("status") == "success"
      assert result.get("paths") == [str(source_jar.absolute())]

  @pytest.mark.asyncio
  async def test_search_cached_artifact_not_found(self) -> None:
    """Test source JAR not found case."""
    with (
      patch("src.tools.search_cached_artifact.validate_maven_coordinates"),
      patch(
        "src.tools.search_cached_artifact.search_cached_artifacts", return_value=[]
      ),
    ):
      result = await search_cached_artifact_impl(
        "org.example", "nonexistent", "1.0.0", "maven,gradle"
      )

      assert result.get("status") == "not_found"
      assert result.get("paths") == []
      assert "No source JAR files found" in result.get("message", "")

  @pytest.mark.asyncio
  async def test_search_cached_artifact_invalid_coordinates(self) -> None:
    """Test invalid Maven coordinates."""
    with patch(
      "src.tools.search_cached_artifact.validate_maven_coordinates",
      side_effect=ValueError("Invalid group_id"),
    ):
      result = await search_cached_artifact_impl("", "test-lib", "1.0.0", "maven")

      assert result.get("status") == "invalid_coordinates"
      assert result.get("paths") == []
      assert "Invalid group_id" in result.get("message", "")

  @pytest.mark.asyncio
  async def test_search_cached_artifact_internal_error(self) -> None:
    """Test internal error handling."""
    with (
      patch("src.tools.search_cached_artifact.validate_maven_coordinates"),
      patch(
        "src.tools.search_cached_artifact.search_cached_artifacts",
        side_effect=Exception("Test error"),
      ),
    ):
      result = await search_cached_artifact_impl(
        "org.example", "test-lib", "1.0.0", "maven"
      )

      assert result.get("status") == "internal_error"
      assert result.get("paths") == []
      assert "Test error" in result.get("message", "")

  @pytest.mark.asyncio
  async def test_handle_search_cached_artifact_success(self) -> None:
    """Test handle_search_cached_artifact success case."""
    mock_result: Dict[str, Any] = {
      "status": "success",
      "paths": ["/Users/user/.m2/repository/org/springframework/spring-core/5.3.21/spring-core-5.3.21-sources.jar"],
    }

    with patch(
      "src.tools.search_cached_artifact.search_cached_artifact_impl",
      return_value=mock_result,
    ):
      arguments = {
        "group_id": "org.springframework",
        "artifact_id": "spring-core",
        "version_filter": "5.3.21",
        "cache": "maven,gradle",
      }

      result = await handle_search_cached_artifact(arguments)

      assert len(result) == 1
      response_data = json.loads(result[0].text)
      assert response_data["status"] == "success"
      assert "spring-core-5.3.21-sources.jar" in response_data["paths"][0]

  @pytest.mark.asyncio
  async def test_handle_search_cached_artifact_default_cache(self) -> None:
    """Test handle_search_cached_artifact with default cache parameter."""
    mock_result: Dict[str, Any] = {
      "status": "success",
      "paths": ["/Users/user/.m2/repository/org/springframework/spring-core/5.3.21/spring-core-5.3.21-sources.jar"],
    }

    with patch(
      "src.tools.search_cached_artifact.search_cached_artifact_impl",
      return_value=mock_result,
    ) as mock_impl:
      arguments = {
        "group_id": "org.springframework",
        "artifact_id": "spring-core",
        "version_filter": "5.3.21",
        # cache parameter omitted - should default to "maven,gradle"
      }

      await handle_search_cached_artifact(arguments)

      # Verify default cache parameter was used
      mock_impl.assert_called_once_with(
        "org.springframework", "spring-core", "5.3.21", "maven,gradle"
      )

  @pytest.mark.asyncio
  async def test_handle_search_cached_artifact_exception(self) -> None:
    """Test handle_search_cached_artifact exception handling."""
    with patch(
      "src.tools.search_cached_artifact.search_cached_artifact_impl",
      side_effect=Exception("Test error"),
    ):
      arguments = {
        "group_id": "org.springframework",
        "artifact_id": "spring-core",
        "version_filter": "5.3.21",
      }

      response = await handle_search_cached_artifact(arguments)

      assert len(response) == 1
      response_data = json.loads(response[0].text)
      assert response_data["status"] == "internal_error"
      assert "Test error" in response_data["message"]
