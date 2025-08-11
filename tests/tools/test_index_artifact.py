"""Tests for index_artifact MCP tool."""

import json
import tempfile
from pathlib import Path
from typing import Generator
from unittest.mock import MagicMock, patch

import pytest

from src.jartype.core_types import IndexArtifactResult, RegisteredSourceInfo
from src.tools.index_artifact import handle_index_artifact, index_artifact


class TestIndexArtifact:
  """Test cases for index_artifact functionality."""

  @pytest.fixture
  def temp_storage(self) -> Generator[Path, None, None]:
    """Create temporary storage directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
      yield Path(temp_dir)

  @pytest.fixture
  def mock_storage_manager(self, temp_storage: Path) -> MagicMock:
    """Mock storage manager with temporary directory."""
    mock_manager = MagicMock()
    mock_manager.base_dir = temp_storage
    mock_manager.ensure_directories = MagicMock()
    mock_manager.validate_directory_permissions = MagicMock(return_value=True)
    mock_manager.get_code_path = MagicMock(
      return_value=temp_storage / "code" / "org" / "example" / "test-lib" / "1.0.0"
    )
    mock_manager.get_git_bare_path = MagicMock(
      return_value=temp_storage / "git" / "org" / "example" / "test-lib"
    )
    return mock_manager

  @pytest.fixture
  def sample_registered_source_info(self) -> RegisteredSourceInfo:
    """Sample registered source info."""
    return RegisteredSourceInfo(
      group_id="org.example",
      artifact_id="test-lib",
      version="1.0.0",
      source_uri="file:///test/source.jar",
      git_ref=None,
      source_type="jar",
      local_path="source-jar/org/example/test-lib/1.0.0",
    )

  @pytest.mark.asyncio
  async def test_index_artifact_success_jar_source(
    self, temp_storage: Path, sample_registered_source_info: RegisteredSourceInfo
  ) -> None:
    """Test successful artifact indexing with JAR source."""
    # Setup
    code_path = temp_storage / "code" / "org" / "example" / "test-lib" / "1.0.0"
    source_jar_path = (
      temp_storage
      / "source-jar"
      / "org"
      / "example"
      / "test-lib"
      / "1.0.0"
      / "test-lib-1.0.0-sources.jar"
    )
    source_jar_path.parent.mkdir(parents=True, exist_ok=True)
    source_jar_path.write_text("mock jar content")

    with (
      patch("src.tools.index_artifact.validate_maven_coordinates"),
      patch("src.tools.index_artifact.StorageManager") as mock_storage_class,
      patch("src.tools.index_artifact.is_artifact_code_available", return_value=False),
      patch(
        "src.tools.index_artifact.get_registered_source_info",
        return_value=sample_registered_source_info,
      ),
      patch("src.tools.index_artifact.extract_jar_source") as mock_extract,
      patch(
        "src.tools.list_artifacts.get_artifact_status",
        return_value="source-jar,file-searchable",
      ),
    ):
      # Create the code path directory
      code_path.mkdir(parents=True, exist_ok=True)

      mock_storage = MagicMock()
      mock_storage.base_path = temp_storage
      mock_storage.ensure_directories = MagicMock()
      mock_storage.get_code_path = MagicMock(return_value=code_path)
      mock_storage_class.return_value = mock_storage

      # Test
      result = await index_artifact("org.example", "test-lib", "1.0.0")

      # Assertions
      assert result.get("status") == "source-jar,file-searchable"
      assert result.get("cache_location") == str(code_path)
      assert "processing_time" in result
      mock_extract.assert_called_once()

  @pytest.mark.asyncio
  async def test_index_artifact_already_available(self) -> None:
    """Test artifact code already available case."""
    with (
      patch("src.tools.index_artifact.validate_maven_coordinates"),
      patch("src.tools.index_artifact.StorageManager") as mock_storage_class,
      patch("src.tools.index_artifact.is_artifact_code_available", return_value=True),
      patch(
        "src.tools.list_artifacts.get_artifact_status",
        return_value="source-jar,file-searchable",
      ),
    ):
      mock_storage = MagicMock()
      mock_storage.ensure_directories = MagicMock()
      mock_storage.get_code_path = MagicMock(return_value=Path("/mock/path"))
      mock_storage_class.return_value = mock_storage

      result = await index_artifact("org.example", "test-lib", "1.0.0")

      assert result.get("status") == "source-jar,file-searchable"
      assert result.get("cache_location") == "/mock/path"

  @pytest.mark.asyncio
  async def test_index_artifact_not_registered(self) -> None:
    """Test artifact not registered case."""
    with (
      patch("src.tools.index_artifact.validate_maven_coordinates"),
      patch("src.tools.index_artifact.StorageManager") as mock_storage_class,
      patch("src.tools.index_artifact.is_artifact_code_available", return_value=False),
      patch("src.tools.index_artifact.get_registered_source_info", return_value=None),
    ):
      mock_storage = MagicMock()
      mock_storage.ensure_directories = MagicMock()
      mock_storage_class.return_value = mock_storage

      result = await index_artifact("org.example", "test-lib", "1.0.0")

      assert result.get("status") == "not_registered"
      assert result.get("cache_location") == ""
      assert "message" in result
      assert "not registered" in result.get("message", "")

  @pytest.mark.asyncio
  async def test_index_artifact_no_jar_files(self, temp_storage: Path) -> None:
    """Test when source directory exists but contains no JAR files."""
    source_info: RegisteredSourceInfo = RegisteredSourceInfo(
      group_id="org.example",
      artifact_id="test-lib",
      version="1.0.0",
      source_uri="file:///test/source.jar",
      git_ref=None,
      source_type="jar",
      local_path="source-jar/org/example/test-lib/1.0.0",
    )

    # Create source directory but no JAR files
    source_dir = temp_storage / "source-jar" / "org" / "example" / "test-lib" / "1.0.0"
    source_dir.mkdir(parents=True, exist_ok=True)
    (source_dir / "README.txt").write_text("No JAR files here")

    with (
      patch("src.tools.index_artifact.validate_maven_coordinates"),
      patch("src.tools.index_artifact.StorageManager") as mock_storage_class,
      patch("src.tools.index_artifact.is_artifact_code_available", return_value=False),
      patch(
        "src.tools.index_artifact.get_registered_source_info", return_value=source_info
      ),
    ):
      mock_storage = MagicMock()
      mock_storage.base_path = temp_storage
      mock_storage.ensure_directories = MagicMock()
      mock_storage.get_code_path = MagicMock(
        return_value=temp_storage / "code" / "org" / "example" / "test-lib" / "1.0.0"
      )
      mock_storage_class.return_value = mock_storage

      result = await index_artifact("org.example", "test-lib", "1.0.0")

      assert result.get("status") == "extraction_failed"
      assert "message" in result
      assert "No JAR files found" in result.get("message", "")

  @pytest.mark.asyncio
  async def test_index_artifact_code_already_available(
    self, temp_storage: Path
  ) -> None:
    """Test artifact code already available case."""
    code_path = temp_storage / "code" / "org" / "example" / "test-lib" / "1.0.0"
    code_path.mkdir(parents=True, exist_ok=True)

    with (
      patch("src.tools.index_artifact.validate_maven_coordinates"),
      patch("src.tools.index_artifact.StorageManager") as mock_storage_class,
      patch("src.tools.index_artifact.is_artifact_code_available", return_value=True),
      patch(
        "src.tools.list_artifacts.get_artifact_status",
        return_value="source-dir,file-searchable",
      ),
    ):
      mock_storage = MagicMock()
      mock_storage.ensure_directories = MagicMock()
      mock_storage.get_code_path = MagicMock(return_value=code_path)
      mock_storage_class.return_value = mock_storage

      result = await index_artifact("org.example", "test-lib", "1.0.0")

      assert result.get("status") == "source-dir,file-searchable"
      assert result.get("cache_location") == str(code_path)

  @pytest.mark.asyncio
  async def test_handle_index_artifact_success(self) -> None:
    """Test handle_index_artifact success case."""
    mock_result: IndexArtifactResult = IndexArtifactResult(
      status="success",
      cache_location="/mock/path",
      processing_time="1.23s",
    )

    with patch("src.tools.index_artifact.index_artifact", return_value=mock_result):
      arguments = {
        "group_id": "org.example",
        "artifact_id": "test-lib",
        "version": "1.0.0",
      }

      result = await handle_index_artifact(arguments)

      assert len(result) == 1
      assert result[0].type == "text"

      response_data = json.loads(result[0].text)
      assert response_data["status"] == "success"
      assert response_data["cache_location"] == "/mock/path"

  @pytest.mark.asyncio
  async def test_handle_index_artifact_exception(self) -> None:
    """Test handle_index_artifact exception handling."""
    with patch(
      "src.tools.index_artifact.index_artifact", side_effect=Exception("Test error")
    ):
      arguments = {
        "group_id": "org.example",
        "artifact_id": "test-lib",
        "version": "1.0.0",
      }

      result = await handle_index_artifact(arguments)

      assert len(result) == 1
      response_data = json.loads(result[0].text)
      assert response_data["status"] == "internal_error"
      assert "message" in response_data
      assert "Handler error" in response_data["message"]
      assert "Test error" in response_data["message"]
