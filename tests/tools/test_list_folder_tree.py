"""Tests for list_folder_tree MCP tool."""

import json
import tempfile
from pathlib import Path
from typing import Any, Dict, Generator
from unittest.mock import MagicMock, patch

import pytest

from src.tools.list_folder_tree import handle_list_folder_tree, list_folder_tree


class TestListFolderTree:
  """Test cases for list_folder_tree functionality."""

  @pytest.fixture
  def temp_storage(self) -> Generator[Path, None, None]:
    """Create temporary storage directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
      yield Path(temp_dir)

  @pytest.fixture
  def mock_directory_tree_result(self) -> Dict[str, Any]:
    """Mock list_directory_tree result."""
    return {
      "path": "src",
      "max_depth": 3,
      "folders": [
        {
          "name": "main",
          "file_count": 2,
          "files": [],
          "folders": [],
        }
      ],
      "files": [
        {
          "name": "README.md",
          "size": "1KB",
          "line_count": 25,
        }
      ],
    }

  @pytest.mark.asyncio
  async def test_list_folder_tree_success(
    self, temp_storage: Path, mock_directory_tree_result: Dict[str, Any]
  ) -> None:
    """Test successful folder tree listing."""
    code_path: Path = temp_storage / "code" / "org" / "example" / "test-lib" / "1.0.0"
    code_path.mkdir(parents=True, exist_ok=True)
    # Create the src directory that the test is looking for
    src_path: Path = code_path / "src"
    src_path.mkdir(exist_ok=True)

    with (
      patch("src.tools.list_folder_tree.validate_maven_coordinates"),
      patch("src.tools.list_folder_tree.is_artifact_code_available", return_value=True),
      patch("src.tools.list_folder_tree.StorageManager") as mock_storage_class,
      patch(
        "src.tools.list_folder_tree.list_directory_tree",
        return_value=mock_directory_tree_result,
      ),
      patch("src.tools.list_folder_tree.normalize_path", return_value="src"),
    ):
      mock_storage = MagicMock()
      mock_storage.get_code_path = MagicMock(return_value=code_path)
      mock_storage_class.return_value = mock_storage

      result = await list_folder_tree(
        "org.example", "test-lib", "1.0.0", "src", include_files=True, max_depth=3
      )

      assert result["status"] == "success"
      assert result["path"] == "src"
      assert result["max_depth"] == 3
      assert len(result["folders"]) == 1
      assert len(result["files"]) == 1

  @pytest.mark.asyncio
  async def test_list_folder_tree_not_indexed(self) -> None:
    """Test artifact not indexed case."""
    with (
      patch("src.tools.list_folder_tree.validate_maven_coordinates"),
      patch(
        "src.tools.list_folder_tree.is_artifact_code_available", return_value=False
      ),
    ):
      result = await list_folder_tree("org.example", "test-lib", "1.0.0")

      assert result["status"] == "not_available"
      assert result["folders"] == []
      assert result["files"] == []

  @pytest.mark.asyncio
  async def test_list_folder_tree_not_found(self) -> None:
    """Test artifact code directory not found."""
    with (
      patch("src.tools.list_folder_tree.validate_maven_coordinates"),
      patch("src.tools.list_folder_tree.is_artifact_code_available", return_value=True),
      patch("src.tools.list_folder_tree.StorageManager") as mock_storage_class,
    ):
      mock_storage = MagicMock()
      mock_storage.get_code_path = MagicMock(return_value=Path("/nonexistent"))
      mock_storage_class.return_value = mock_storage

      result = await list_folder_tree("org.example", "test-lib", "1.0.0")

      assert result["status"] == "not_found"

  @pytest.mark.asyncio
  async def test_list_folder_tree_path_not_found(self, temp_storage: Path) -> None:
    """Test requested path not found."""
    code_path: Path = temp_storage / "code" / "org" / "example" / "test-lib" / "1.0.0"
    code_path.mkdir(parents=True, exist_ok=True)

    with (
      patch("src.tools.list_folder_tree.validate_maven_coordinates"),
      patch("src.tools.list_folder_tree.is_artifact_code_available", return_value=True),
      patch("src.tools.list_folder_tree.StorageManager") as mock_storage_class,
      patch("src.tools.list_folder_tree.normalize_path", return_value="nonexistent"),
    ):
      mock_storage = MagicMock()
      mock_storage.get_code_path = MagicMock(return_value=code_path)
      mock_storage_class.return_value = mock_storage

      result = await list_folder_tree("org.example", "test-lib", "1.0.0", "nonexistent")

      assert result["status"] == "path_not_found"

  @pytest.mark.asyncio
  async def test_list_folder_tree_not_directory(self, temp_storage: Path) -> None:
    """Test requested path is not a directory."""
    code_path: Path = temp_storage / "code" / "org" / "example" / "test-lib" / "1.0.0"
    code_path.mkdir(parents=True, exist_ok=True)
    file_path: Path = code_path / "test.txt"
    file_path.write_text("test content")

    with (
      patch("src.tools.list_folder_tree.validate_maven_coordinates"),
      patch("src.tools.list_folder_tree.is_artifact_code_available", return_value=True),
      patch("src.tools.list_folder_tree.StorageManager") as mock_storage_class,
      patch("src.tools.list_folder_tree.normalize_path", return_value="test.txt"),
    ):
      mock_storage = MagicMock()
      mock_storage.get_code_path = MagicMock(return_value=code_path)
      mock_storage_class.return_value = mock_storage

      result = await list_folder_tree("org.example", "test-lib", "1.0.0", "test.txt")

      assert result["status"] == "not_directory"

  @pytest.mark.asyncio
  async def test_handle_list_folder_tree_success(self, mock_directory_tree_result: Dict[str, Any]) -> None:
    """Test handle_list_folder_tree success case."""
    mock_result: Dict[str, Any] = {
      "status": "success",
      "path": "src",
      "max_depth": 3,
      "folders": mock_directory_tree_result["folders"],
      "files": mock_directory_tree_result["files"],
    }

    with patch("src.tools.list_folder_tree.list_folder_tree", return_value=mock_result):
      arguments = {
        "group_id": "org.example",
        "artifact_id": "test-lib",
        "version": "1.0.0",
        "path": "src",
        "include_files": True,
        "max_depth": 3,
      }

      result = await handle_list_folder_tree(arguments)

      assert len(result) == 1
      response_data = json.loads(result[0].text)
      assert response_data["status"] == "success"
      assert response_data["path"] == "src"

  @pytest.mark.asyncio
  async def test_handle_list_folder_tree_exception(self) -> None:
    """Test handle_list_folder_tree exception handling."""
    with patch(
      "src.tools.list_folder_tree.list_folder_tree", side_effect=Exception("Test error")
    ):
      arguments = {
        "group_id": "org.example",
        "artifact_id": "test-lib",
        "version": "1.0.0",
      }

      result = await handle_list_folder_tree(arguments)

      assert len(result) == 1
      response_data = json.loads(result[0].text)
      assert response_data["status"] == "internal_error"
