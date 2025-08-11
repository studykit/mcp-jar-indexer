"""Tests for search_file_content MCP tool."""

import json
import tempfile
from pathlib import Path
from typing import Any, Dict, Generator
from unittest.mock import MagicMock, patch

import pytest

from src.tools.search_file_content import (
  handle_search_file_content,
  search_file_content,
)


class TestSearchFileContent:
  """Test cases for search_file_content functionality."""

  @pytest.fixture
  def temp_storage(self) -> Generator[Path, None, None]:
    """Create temporary storage directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
      yield Path(temp_dir)

  @pytest.fixture
  def mock_search_result(self) -> Dict[str, Any]:
    """Mock search_file_contents result."""
    return {
      "search_config": {
        "query": "public class",
        "query_type": "string",
        "start_path": "src",
        "context_before": 2,
        "context_after": 2,
      },
      "matches": {
        "src/main/java/TestClass.java": [
          {
            "content": "package com.example;\n\npublic class TestClass {\n  private String name;\n}",
            "content_range": "1-5",
            "match_lines": "3",
          }
        ],
        "src/main/java/TestUtil.java": [
          {
            "content": "import java.util.*;\n\npublic class TestUtil {\n  public static void test() {\n    // implementation\n  }\n}",
            "content_range": "1-7",
            "match_lines": "3",
          }
        ],
      },
    }

  @pytest.mark.asyncio
  async def test_search_file_content_success(self, temp_storage: Path, mock_search_result: Dict[str, Any]):
    """Test successful file content search."""
    code_path = temp_storage / "code" / "org" / "example" / "test-lib" / "1.0.0"
    code_path.mkdir(parents=True, exist_ok=True)
    # Create the src directory that the test is looking for
    src_path = code_path / "src"
    src_path.mkdir(exist_ok=True)

    with (
      patch("src.tools.search_file_content.validate_maven_coordinates") as _,
      patch(
        "src.tools.search_file_content.is_artifact_code_available", return_value=True
      ) as _,
      patch("src.tools.search_file_content.StorageManager") as mock_storage_class,
      patch(
        "src.tools.search_file_content.search_file_contents",
        return_value=mock_search_result,
      ) as _,
      patch("src.tools.search_file_content.normalize_path", return_value="src") as _,
    ):
      mock_storage = MagicMock()
      mock_storage.get_code_path = MagicMock(return_value=code_path)
      mock_storage_class.return_value = mock_storage

      result = await search_file_content(
        "org.example",
        "test-lib",
        "1.0.0",
        "public class",
        "string",
        "src",
        10,
        2,
        2,
        100,
      )

      assert result["status"] == "success"
      assert result["search_config"]["query"] == "public class"
      assert len(result["matches"]) == 2
      assert "src/main/java/TestClass.java" in result["matches"]

  @pytest.mark.asyncio
  async def test_search_file_content_invalid_query_type(self):
    """Test invalid query type case."""
    with (
      patch("src.tools.search_file_content.validate_maven_coordinates") as _,
    ):
      result = await search_file_content(
        "org.example", "test-lib", "1.0.0", "test", "invalid_type"
      )

      assert result["status"] == "invalid_query_type"
      assert result["matches"] == {}

  @pytest.mark.asyncio
  async def test_search_file_content_not_indexed(self):
    """Test artifact not indexed case."""
    with (
      patch("src.tools.search_file_content.validate_maven_coordinates") as _,
      patch(
        "src.tools.search_file_content.is_artifact_code_available", return_value=False
      ) as _,
    ):
      result = await search_file_content("org.example", "test-lib", "1.0.0", "test")

      assert result["status"] == "not_available"
      assert result["matches"] == {}

  @pytest.mark.asyncio
  async def test_search_file_content_not_found(self):
    """Test artifact code directory not found."""
    with (
      patch("src.tools.search_file_content.validate_maven_coordinates") as _,
      patch(
        "src.tools.search_file_content.is_artifact_code_available", return_value=True
      ) as _,
      patch("src.tools.search_file_content.StorageManager") as mock_storage_class,
    ):
      mock_storage = MagicMock()
      mock_storage.get_code_path = MagicMock(return_value=Path("/nonexistent"))
      mock_storage_class.return_value = mock_storage

      result = await search_file_content("org.example", "test-lib", "1.0.0", "test")

      assert result["status"] == "not_found"

  @pytest.mark.asyncio
  async def test_search_file_content_start_path_not_found(self, temp_storage: Path):
    """Test start path not found."""
    code_path = temp_storage / "code" / "org" / "example" / "test-lib" / "1.0.0"
    code_path.mkdir(parents=True, exist_ok=True)

    with (
      patch("src.tools.search_file_content.validate_maven_coordinates") as _,
      patch(
        "src.tools.search_file_content.is_artifact_code_available", return_value=True
      ) as _,
      patch("src.tools.search_file_content.StorageManager") as mock_storage_class,
      patch("src.tools.search_file_content.normalize_path", return_value="nonexistent") as _,
    ):
      mock_storage = MagicMock()
      mock_storage.get_code_path = MagicMock(return_value=code_path)
      mock_storage_class.return_value = mock_storage

      result = await search_file_content(
        "org.example", "test-lib", "1.0.0", "test", "string", "nonexistent"
      )

      assert result["status"] == "start_path_not_found"

  @pytest.mark.asyncio
  async def test_search_file_content_start_path_not_directory(self, temp_storage: Path):
    """Test start path is not a directory."""
    code_path = temp_storage / "code" / "org" / "example" / "test-lib" / "1.0.0"
    code_path.mkdir(parents=True, exist_ok=True)
    file_path = code_path / "test.txt"
    file_path.write_text("test content")

    with (
      patch("src.tools.search_file_content.validate_maven_coordinates") as _,
      patch(
        "src.tools.search_file_content.is_artifact_code_available", return_value=True
      ) as _,
      patch("src.tools.search_file_content.StorageManager") as mock_storage_class,
      patch("src.tools.search_file_content.normalize_path", return_value="test.txt") as _,
    ):
      mock_storage = MagicMock()
      mock_storage.get_code_path = MagicMock(return_value=code_path)
      mock_storage_class.return_value = mock_storage

      result = await search_file_content(
        "org.example", "test-lib", "1.0.0", "test", "string", "test.txt"
      )

      assert result["status"] == "start_path_not_directory"

  @pytest.mark.asyncio
  async def test_handle_search_file_content_success(self, mock_search_result: Dict[str, Any]):
    """Test handle_search_file_content success case."""
    mock_result: Dict[str, Any] = {
      "status": "success",
      "search_config": mock_search_result["search_config"],
      "matches": mock_search_result["matches"],
    }

    with patch(
      "src.tools.search_file_content.search_file_content", return_value=mock_result
    ):
      arguments = {
        "group_id": "org.example",
        "artifact_id": "test-lib",
        "version": "1.0.0",
        "query": "public class",
        "query_type": "string",
        "start_path": "src",
        "max_depth": 10,
        "context_before": 2,
        "context_after": 2,
        "max_results": 100,
      }

      result = await handle_search_file_content(arguments)

      assert len(result) == 1
      response_data = json.loads(result[0].text)
      assert response_data["status"] == "success"
      assert len(response_data["matches"]) == 2

  @pytest.mark.asyncio
  async def test_handle_search_file_content_exception(self):
    """Test handle_search_file_content exception handling."""
    with patch(
      "src.tools.search_file_content.search_file_content",
      side_effect=Exception("Test error"),
    ):
      arguments = {
        "group_id": "org.example",
        "artifact_id": "test-lib",
        "version": "1.0.0",
        "query": "test",
      }

      result = await handle_search_file_content(arguments)

      assert len(result) == 1
      response_data = json.loads(result[0].text)
      assert response_data["status"] == "internal_error"
