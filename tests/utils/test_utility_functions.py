"""Tests for utility functions from path_utils, artifact_utils, and filesystem_exploration modules."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from src.utils.path_utils import calculate_directory_depth, normalize_path
from src.utils.artifact_utils import (
  get_artifact_code_path,
  get_registered_source_info,
  is_artifact_code_available,
  is_artifact_code_indexed,
)
from src.utils.filesystem_exploration import get_file_info


class TestNormalizePath:
  """Test normalize_path function."""

  def test_normalize_path_basic(self) -> None:
    """Test basic path normalization."""
    path = normalize_path("./test/path")
    assert os.path.isabs(path)
    assert "test" in path
    assert "path" in path

  def test_normalize_path_empty(self) -> None:
    """Test empty path raises error."""
    with pytest.raises(ValueError, match="Path must be a non-empty string"):
      normalize_path("")

  def test_normalize_path_whitespace(self) -> None:
    """Test whitespace-only path raises error."""
    with pytest.raises(ValueError, match="Path cannot be empty or whitespace only"):
      normalize_path("   ")

  def test_normalize_path_not_string(self) -> None:
    """Test non-string path raises error."""
    with pytest.raises(ValueError, match="Path must be a non-empty string"):
      normalize_path(None)  # type: ignore


class TestCalculateDirectoryDepth:
  """Test calculate_directory_depth function."""

  def test_calculate_directory_depth_same(self) -> None:
    """Test depth calculation for same directory."""
    base = "/home/user"
    target = "/home/user"
    depth = calculate_directory_depth(base, target)
    assert depth == 0

  def test_calculate_directory_depth_subdirectory(self) -> None:
    """Test depth calculation for subdirectory."""
    base = "/home/user"
    target = "/home/user/project/src"
    depth = calculate_directory_depth(base, target)
    assert depth == 2

  def test_calculate_directory_depth_not_under_base(self) -> None:
    """Test error when target is not under base."""
    base = "/home/user/project"
    target = "/home/other"
    with pytest.raises(ValueError, match="Target path is not under base path"):
      calculate_directory_depth(base, target)


class TestGetArtifactCodePath:
  """Test get_artifact_code_path function."""

  def test_get_artifact_code_path_basic(self) -> None:
    """Test basic Maven coordinate to path conversion."""
    path = get_artifact_code_path("org.springframework", "spring-core", "5.3.21")
    assert path == "org/springframework/spring-core/5.3.21"

  def test_get_artifact_code_path_complex_group(self) -> None:
    """Test complex group ID conversion."""
    path = get_artifact_code_path(
      "com.fasterxml.jackson.core", "jackson-core", "2.13.3"
    )
    assert path == "com/fasterxml/jackson/core/jackson-core/2.13.3"

  def test_get_artifact_code_path_invalid_coordinates(self) -> None:
    """Test invalid coordinates raise error."""
    with pytest.raises(ValueError):
      get_artifact_code_path("", "spring-core", "5.3.21")


class TestGetFileInfo:
  """Test get_file_info function."""

  def test_get_file_info_text_file(self) -> None:
    """Test file info for text file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
      f.write("line 1\nline 2\nline 3")
      f.flush()

      try:
        info = get_file_info(f.name)

        assert isinstance(info, dict)
        assert info["name"] == Path(f.name).name
        assert info["line_count"] == 3
        assert "B" in info["size"] or "KB" in info["size"]
      finally:
        os.unlink(f.name)

  def test_get_file_info_binary_file(self) -> None:
    """Test file info for binary file."""
    with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as f:
      f.write(b"\x00\x01\x02\x03")
      f.flush()

      try:
        info = get_file_info(f.name)

        assert isinstance(info, dict)
        assert info["name"] == Path(f.name).name
        assert info["line_count"] == 0  # Binary file should have 0 lines
        assert info["size"] == "4B"
      finally:
        os.unlink(f.name)

  def test_get_file_info_nonexistent(self) -> None:
    """Test file info for nonexistent file."""
    with pytest.raises(ValueError, match="Path does not exist"):
      get_file_info("/nonexistent/file.txt")

  def test_get_file_info_directory(self) -> None:
    """Test file info raises error for directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
      with pytest.raises(ValueError, match="Path is not a file"):
        get_file_info(temp_dir)


class TestArtifactStateFunctions:
  """Test artifact state management functions."""

  @patch.dict(os.environ, {"JAR_INDEXER_HOME": "/test/home"})
  def test_is_artifact_code_available_false(self) -> None:
    """Test is_artifact_code_available returns False for non-existent code."""
    result = is_artifact_code_available("org.test", "test-lib", "1.0.0")
    assert result is False

  @patch.dict(os.environ, {"JAR_INDEXER_HOME": "/test/home"})
  def test_is_artifact_code_indexed_false(self) -> None:
    """Test is_artifact_code_indexed returns False for non-indexed artifact."""
    result = is_artifact_code_indexed("org.test", "test-lib", "1.0.0")
    assert result is False

  @patch.dict(os.environ, {"JAR_INDEXER_HOME": "/test/home"})
  def test_get_registered_source_info_none(self) -> None:
    """Test get_registered_source_info returns None for unregistered artifact."""
    result = get_registered_source_info("org.test", "test-lib", "1.0.0")
    assert result is None
