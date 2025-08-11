"""Test path utilities."""

import tempfile
from pathlib import Path
from typing import Iterator
import pytest

from src.utils.path_utils import (
  normalize_path,
  calculate_directory_depth,
  ensure_directory,
)


class TestNormalizePath:
  """Test normalize_path function."""

  def test_normalize_path_valid(self) -> None:
    """Test path normalization with valid paths."""
    # Test relative path gets converted to absolute
    result = normalize_path("test/path")
    assert Path(result).is_absolute()
    assert result.endswith("test/path") or result.endswith("test\\path")

  def test_normalize_path_absolute(self) -> None:
    """Test normalization of already absolute path."""
    abs_path = "/usr/local/bin"
    result = normalize_path(abs_path)
    assert Path(result).is_absolute()

  def test_normalize_path_empty(self) -> None:
    """Test normalization with empty string."""
    with pytest.raises(ValueError, match="Path must be a non-empty string"):
      normalize_path("")

  def test_normalize_path_whitespace(self) -> None:
    """Test normalization with whitespace only."""
    with pytest.raises(ValueError, match="Path cannot be empty or whitespace only"):
      normalize_path("   ")

  def test_normalize_path_none(self) -> None:
    """Test normalization with None."""
    with pytest.raises(ValueError, match="Path must be a non-empty string"):
      normalize_path(None)  # type: ignore


class TestCalculateDirectoryDepth:
  """Test calculate_directory_depth function."""

  def test_calculate_directory_depth_same_path(self) -> None:
    """Test depth calculation for same paths."""
    base_path = "/home/user"
    target_path = "/home/user"

    depth = calculate_directory_depth(base_path, target_path)
    assert depth == 0

  def test_calculate_directory_depth_subdirectory(self) -> None:
    """Test depth calculation for subdirectory."""
    base_path = "/home/user"
    target_path = "/home/user/documents/projects"

    depth = calculate_directory_depth(base_path, target_path)
    assert depth == 2

  def test_calculate_directory_depth_single_level(self) -> None:
    """Test depth calculation for single level."""
    base_path = "/home/user"
    target_path = "/home/user/documents"

    depth = calculate_directory_depth(base_path, target_path)
    assert depth == 1

  def test_calculate_directory_depth_not_under_base(self) -> None:
    """Test depth calculation when target is not under base."""
    base_path = "/home/user"
    target_path = "/home/other"

    with pytest.raises(ValueError, match="Target path is not under base path"):
      calculate_directory_depth(base_path, target_path)


class TestEnsureDirectory:
  """Test ensure_directory function."""

  @pytest.fixture
  def temp_dir(self) -> Iterator[Path]:
    """Create temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmp_dir:
      yield Path(tmp_dir)

  def test_ensure_directory_create_new(self, temp_dir: Path) -> None:
    """Test creating a new directory."""
    new_dir = temp_dir / "new_dir"

    result = ensure_directory(new_dir)

    assert result["status"] == "created"
    assert result["created"] is True
    assert new_dir.exists()
    assert new_dir.is_dir()

  def test_ensure_directory_exists(self, temp_dir: Path) -> None:
    """Test with existing directory."""
    existing_dir = temp_dir / "existing"
    existing_dir.mkdir()

    result = ensure_directory(existing_dir)

    assert result["status"] == "exists"
    assert result["created"] is False

  def test_ensure_directory_file_exists(self, temp_dir: Path) -> None:
    """Test with existing file at path."""
    existing_file = temp_dir / "existing_file"
    existing_file.write_text("content")

    with pytest.raises(OSError, match="Path exists but is not a directory"):
      ensure_directory(existing_file)

  def test_ensure_directory_with_parents(self, temp_dir: Path) -> None:
    """Test creating directory with parent directories."""
    nested_dir = temp_dir / "parent" / "child" / "grandchild"

    result = ensure_directory(nested_dir)

    assert result["status"] == "created"
    assert nested_dir.exists()
    assert nested_dir.is_dir()
