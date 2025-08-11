"""Tests for search_file_names MCP tool."""

import json
import tempfile
from pathlib import Path
from typing import Any, Dict, Generator
from unittest.mock import MagicMock, patch

import pytest

from src.tools.search_file_names import handle_search_file_names, search_file_names


class TestSearchFileNames:
  """Test cases for search_file_names functionality."""

  @pytest.fixture
  def temp_storage(self) -> Generator[Path, None, None]:
    """Create temporary storage directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
      yield Path(temp_dir)

  @pytest.fixture
  def mock_search_result(self) -> Dict[str, Any]:
    """Mock search_files_by_pattern result."""
    return {
      "files": [
        {
          "name": "TestClass.java",
          "path": "src/main/java/TestClass.java",
          "size": "2KB",
          "line_count": 50,
        },
        {
          "name": "TestUtil.java",
          "path": "src/main/java/TestUtil.java",
          "size": "1KB",
          "line_count": 25,
        },
      ]
    }

  @pytest.mark.asyncio
  async def test_search_file_names_success(self, temp_storage: Path, mock_search_result: Dict[str, Any]) -> None:
    """Test successful file name search."""
    code_path: Path = temp_storage / "code" / "org" / "example" / "test-lib" / "1.0.0"
    code_path.mkdir(parents=True, exist_ok=True)
    # Create the src directory that the test is looking for
    src_path: Path = code_path / "src"
    src_path.mkdir(exist_ok=True)

    with (
      patch("src.tools.search_file_names.validate_maven_coordinates"),
      patch(
        "src.tools.search_file_names.is_artifact_code_available", return_value=True
      ),
      patch("src.tools.search_file_names.StorageManager") as mock_storage_class,
      patch(
        "src.tools.search_file_names.search_files_by_pattern",
        return_value=mock_search_result,
      ),
      patch("src.tools.search_file_names.normalize_path", return_value="src"),
    ):
      mock_storage = MagicMock()
      mock_storage.get_code_path = MagicMock(return_value=code_path)
      mock_storage_class.return_value = mock_storage

      result = await search_file_names(
        "org.example", "test-lib", "1.0.0", "Test*.java", "glob", "src", 10
      )

      assert result["status"] == "success"
      assert len(result["files"]) == 2
      assert result["search_config"]["pattern"] == "Test*.java"
      assert result["files"][0]["name"] == "TestClass.java"

  @pytest.mark.asyncio
  async def test_search_file_names_invalid_pattern_type(self) -> None:
    """Test invalid pattern type case."""
    with patch("src.tools.search_file_names.validate_maven_coordinates"):
      result = await search_file_names(
        "org.example", "test-lib", "1.0.0", "*.java", "invalid_type"
      )

      assert result["status"] == "invalid_pattern_type"
      assert result["files"] == []

  @pytest.mark.asyncio
  async def test_search_file_names_not_indexed(self) -> None:
    """Test artifact not indexed case."""
    with (
      patch("src.tools.search_file_names.validate_maven_coordinates"),
      patch(
        "src.tools.search_file_names.is_artifact_code_available", return_value=False
      ),
    ):
      result = await search_file_names("org.example", "test-lib", "1.0.0", "*.java")

      assert result["status"] == "not_available"
      assert result["files"] == []

  @pytest.mark.asyncio
  async def test_search_file_names_not_found(self) -> None:
    """Test artifact code directory not found."""
    with (
      patch("src.tools.search_file_names.validate_maven_coordinates"),
      patch(
        "src.tools.search_file_names.is_artifact_code_available", return_value=True
      ),
      patch("src.tools.search_file_names.StorageManager") as mock_storage_class,
    ):
      mock_storage = MagicMock()
      mock_storage.get_code_path = MagicMock(return_value=Path("/nonexistent"))
      mock_storage_class.return_value = mock_storage

      result = await search_file_names("org.example", "test-lib", "1.0.0", "*.java")

      assert result["status"] == "not_found"

  @pytest.mark.asyncio
  async def test_search_file_names_start_path_not_found(self, temp_storage: Path) -> None:
    """Test start path not found."""
    code_path: Path = temp_storage / "code" / "org" / "example" / "test-lib" / "1.0.0"
    code_path.mkdir(parents=True, exist_ok=True)

    with (
      patch("src.tools.search_file_names.validate_maven_coordinates"),
      patch(
        "src.tools.search_file_names.is_artifact_code_available", return_value=True
      ),
      patch("src.tools.search_file_names.StorageManager") as mock_storage_class,
      patch("src.tools.search_file_names.normalize_path", return_value="nonexistent"),
    ):
      mock_storage = MagicMock()
      mock_storage.get_code_path = MagicMock(return_value=code_path)
      mock_storage_class.return_value = mock_storage

      result = await search_file_names(
        "org.example", "test-lib", "1.0.0", "*.java", "glob", "nonexistent"
      )

      assert result["status"] == "start_path_not_found"

  @pytest.mark.asyncio
  async def test_search_file_names_start_path_not_directory(self, temp_storage: Path) -> None:
    """Test start path is not a directory."""
    code_path: Path = temp_storage / "code" / "org" / "example" / "test-lib" / "1.0.0"
    code_path.mkdir(parents=True, exist_ok=True)
    file_path: Path = code_path / "test.txt"
    file_path.write_text("test content")

    with (
      patch("src.tools.search_file_names.validate_maven_coordinates"),
      patch(
        "src.tools.search_file_names.is_artifact_code_available", return_value=True
      ),
      patch("src.tools.search_file_names.StorageManager") as mock_storage_class,
      patch("src.tools.search_file_names.normalize_path", return_value="test.txt"),
    ):
      mock_storage = MagicMock()
      mock_storage.get_code_path = MagicMock(return_value=code_path)
      mock_storage_class.return_value = mock_storage

      result = await search_file_names(
        "org.example", "test-lib", "1.0.0", "*.java", "glob", "test.txt"
      )

      assert result["status"] == "start_path_not_directory"

  @pytest.mark.asyncio
  async def test_handle_search_file_names_success(self, mock_search_result: Dict[str, Any]) -> None:
    """Test handle_search_file_names success case."""
    mock_result: Dict[str, Any] = {
      "status": "success",
      "search_config": {
        "start_path": "src",
        "max_depth": 10,
        "pattern": "*.java",
      },
      "files": mock_search_result["files"],
    }

    with patch(
      "src.tools.search_file_names.search_file_names", return_value=mock_result
    ):
      arguments = {
        "group_id": "org.example",
        "artifact_id": "test-lib",
        "version": "1.0.0",
        "pattern": "*.java",
        "pattern_type": "glob",
        "start_path": "src",
        "max_depth": 10,
      }

      result = await handle_search_file_names(arguments)

      assert len(result) == 1
      response_data = json.loads(result[0].text)
      assert response_data["status"] == "success"
      assert len(response_data["files"]) == 2

  @pytest.mark.asyncio
  async def test_handle_search_file_names_exception(self) -> None:
    """Test handle_search_file_names exception handling."""
    with patch(
      "src.tools.search_file_names.search_file_names",
      side_effect=Exception("Test error"),
    ):
      arguments = {
        "group_id": "org.example",
        "artifact_id": "test-lib",
        "version": "1.0.0",
        "pattern": "*.java",
      }

      result = await handle_search_file_names(arguments)

      assert len(result) == 1
      response_data = json.loads(result[0].text)
      assert response_data["status"] == "internal_error"
