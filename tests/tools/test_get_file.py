"""Tests for get_file MCP tool."""

import json
import tempfile
from pathlib import Path
from typing import Any, Dict, Generator
from unittest.mock import MagicMock, patch

import pytest

from src.tools.get_file import handle_get_file, get_file


class TestGetFile:
  """Test cases for get_file functionality."""

  @pytest.fixture
  def temp_storage(self) -> Generator[Path, None, None]:
    """Create temporary storage directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
      yield Path(temp_dir)

  @pytest.fixture
  def mock_file_content_result(self) -> Dict[str, Any]:
    """Mock get_file_content result."""
    return {
      "file_info": {
        "name": "TestClass.java",
        "size": "2KB",
        "line_count": 50,
      },
      "content": {
        "start_line": 1,
        "end_line": 50,
        "source_code": "public class TestClass {\n  // Implementation\n}",
      },
    }

  @pytest.mark.asyncio
  async def test_get_file_success(
    self, temp_storage: Path, mock_file_content_result: Dict[str, Any]
  ) -> None:
    """Test successful file retrieval."""
    code_path = temp_storage / "code" / "org" / "example" / "test-lib" / "1.0.0"
    code_path.mkdir(parents=True, exist_ok=True)
    test_file = code_path / "TestClass.java"
    test_file.write_text("public class TestClass {\n  // Implementation\n}")

    with (
      patch("src.tools.get_file.validate_maven_coordinates"),
      patch("src.tools.get_file.is_artifact_code_available", return_value=True),
      patch("src.tools.get_file.StorageManager") as mock_storage_class,
      patch(
        "src.tools.get_file.get_file_content", return_value=mock_file_content_result
      ),
    ):
      mock_storage = MagicMock()
      mock_storage.get_code_path = MagicMock(return_value=code_path)
      mock_storage_class.return_value = mock_storage

      result = await get_file(
        "org.example", "test-lib", "1.0.0", "TestClass.java", start_line=1, end_line=50
      )

      assert result["status"] == "success"
      assert result["file_info"]["name"] == "TestClass.java"
      assert (
        result["content"]["source_code"]
        == "public class TestClass {\n  // Implementation\n}"
      )

  @pytest.mark.asyncio
  async def test_get_file_not_indexed(self) -> None:
    """Test artifact not indexed case."""
    with (
      patch("src.tools.get_file.validate_maven_coordinates"),
      patch("src.tools.get_file.is_artifact_code_available", return_value=False),
    ):
      result = await get_file("org.example", "test-lib", "1.0.0", "TestClass.java")

      assert result["status"] == "not_available"
      assert result["file_info"]["name"] == ""
      assert result["content"]["source_code"] == ""

  @pytest.mark.asyncio
  async def test_get_file_not_found(self) -> None:
    """Test artifact code directory not found."""
    with (
      patch("src.tools.get_file.validate_maven_coordinates"),
      patch("src.tools.get_file.is_artifact_code_available", return_value=True),
      patch("src.tools.get_file.StorageManager") as mock_storage_class,
    ):
      mock_storage = MagicMock()
      mock_storage.get_code_path = MagicMock(return_value=Path("/nonexistent"))
      mock_storage_class.return_value = mock_storage

      result = await get_file("org.example", "test-lib", "1.0.0", "TestClass.java")

      assert result["status"] == "not_found"

  @pytest.mark.asyncio
  async def test_get_file_file_not_found(self, temp_storage: Path) -> None:
    """Test requested file not found."""
    code_path = temp_storage / "code" / "org" / "example" / "test-lib" / "1.0.0"
    code_path.mkdir(parents=True, exist_ok=True)

    with (
      patch("src.tools.get_file.validate_maven_coordinates"),
      patch("src.tools.get_file.is_artifact_code_available", return_value=True),
      patch("src.tools.get_file.StorageManager") as mock_storage_class,
    ):
      mock_storage = MagicMock()
      mock_storage.get_code_path = MagicMock(return_value=code_path)
      mock_storage_class.return_value = mock_storage

      result = await get_file("org.example", "test-lib", "1.0.0", "NonExistent.java")

      assert result["status"] == "file_not_found"

  @pytest.mark.asyncio
  async def test_get_file_not_file(self, temp_storage: Path) -> None:
    """Test requested path is not a file."""
    code_path = temp_storage / "code" / "org" / "example" / "test-lib" / "1.0.0"
    code_path.mkdir(parents=True, exist_ok=True)
    dir_path = code_path / "src"
    dir_path.mkdir()

    with (
      patch("src.tools.get_file.validate_maven_coordinates"),
      patch("src.tools.get_file.is_artifact_code_available", return_value=True),
      patch("src.tools.get_file.StorageManager") as mock_storage_class,
    ):
      mock_storage = MagicMock()
      mock_storage.get_code_path = MagicMock(return_value=code_path)
      mock_storage_class.return_value = mock_storage

      result = await get_file("org.example", "test-lib", "1.0.0", "src")

      assert result["status"] == "not_file"

  @pytest.mark.asyncio
  async def test_handle_get_file_success(
    self, mock_file_content_result: Dict[str, Any]
  ) -> None:
    """Test handle_get_file success case."""
    mock_result: Dict[str, Any] = {
      "status": "success",
      "file_info": mock_file_content_result["file_info"],
      "content": mock_file_content_result["content"],
    }

    with patch("src.tools.get_file.get_file", return_value=mock_result):
      arguments = {
        "group_id": "org.example",
        "artifact_id": "test-lib",
        "version": "1.0.0",
        "file_path": "TestClass.java",
        "start_line": 1,
        "end_line": 50,
      }

      result = await handle_get_file(arguments)

      assert len(result) == 1
      response_data = json.loads(result[0].text)
      assert response_data["status"] == "success"
      assert response_data["file_info"]["name"] == "TestClass.java"

  @pytest.mark.asyncio
  async def test_handle_get_file_exception(self) -> None:
    """Test handle_get_file exception handling."""
    with patch("src.tools.get_file.get_file", side_effect=Exception("Test error")):
      arguments = {
        "group_id": "org.example",
        "artifact_id": "test-lib",
        "version": "1.0.0",
        "file_path": "TestClass.java",
      }

      result = await handle_get_file(arguments)

      assert len(result) == 1
      response_data = json.loads(result[0].text)
      assert response_data["status"] == "internal_error"
