"""Test source extraction utilities."""

import tempfile
import zipfile
from pathlib import Path
from typing import Iterator
from unittest.mock import patch, Mock, MagicMock
import pytest

from src.utils.source_extraction import (
  extract_jar_source,
  copy_directory_source,
  safe_copy_file,
  safe_symlink,
  safe_copy_tree,
  GitRefNotFoundError,
)


class TestExtractJarSource:
  """Test extract_jar_source function."""

  @pytest.fixture
  def temp_dir(self) -> Iterator[Path]:
    """Create temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmp_dir:
      yield Path(tmp_dir)

  @pytest.fixture
  def source_jar(self, temp_dir: Path) -> Path:
    """Create a source JAR file for testing."""
    jar_path = temp_dir / "source.jar"

    with zipfile.ZipFile(jar_path, "w") as jar_zip:
      jar_zip.writestr("META-INF/MANIFEST.MF", "Manifest-Version: 1.0\n")
      jar_zip.writestr(
        "com/example/Test.java", "package com.example;\npublic class Test {}"
      )
      jar_zip.writestr(
        "com/example/Utils.java", "package com.example;\npublic class Utils {}"
      )

    return jar_path

  def test_extract_jar_source_success(self, temp_dir: Path, source_jar: Path) -> None:
    """Test successful JAR extraction."""
    target_dir = temp_dir / "extracted"

    extract_jar_source(str(source_jar), str(target_dir))

    assert target_dir.exists()
    assert (target_dir / "META-INF" / "MANIFEST.MF").exists()
    assert (target_dir / "com" / "example" / "Test.java").exists()
    assert (target_dir / "com" / "example" / "Utils.java").exists()

  def test_extract_jar_source_nonexistent_jar(self, temp_dir: Path) -> None:
    """Test extraction with nonexistent JAR."""
    nonexistent_jar = temp_dir / "nonexistent.jar"
    target_dir = temp_dir / "extracted"

    with pytest.raises(FileNotFoundError, match="JAR file does not exist"):
      extract_jar_source(str(nonexistent_jar), str(target_dir))

  def test_extract_jar_source_invalid_jar(self, temp_dir: Path) -> None:
    """Test extraction with invalid JAR file."""
    invalid_jar = temp_dir / "invalid.jar"
    invalid_jar.write_text("not a zip file")
    target_dir = temp_dir / "extracted"

    with pytest.raises(zipfile.BadZipFile, match="Invalid JAR file format"):
      extract_jar_source(str(invalid_jar), str(target_dir))


class TestCopyDirectorySource:
  """Test copy_directory_source function."""

  @pytest.fixture
  def temp_dir(self) -> Iterator[Path]:
    """Create temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmp_dir:
      yield Path(tmp_dir)

  def test_copy_directory_source_success(self, temp_dir: Path) -> None:
    """Test successful directory copy."""
    source_dir = temp_dir / "source"
    target_dir = temp_dir / "target"

    # Create source structure
    source_dir.mkdir()
    (source_dir / "file1.txt").write_text("content1")
    (source_dir / "subdir").mkdir()
    (source_dir / "subdir" / "file2.txt").write_text("content2")

    copy_directory_source(str(source_dir), str(target_dir))

    assert target_dir.exists()
    assert (target_dir / "file1.txt").read_text() == "content1"
    assert (target_dir / "subdir" / "file2.txt").read_text() == "content2"

  def test_copy_directory_source_nonexistent(self, temp_dir: Path) -> None:
    """Test copy with nonexistent source directory."""
    nonexistent_dir = temp_dir / "nonexistent"
    target_dir = temp_dir / "target"

    with pytest.raises(FileNotFoundError, match="Source directory does not exist"):
      copy_directory_source(str(nonexistent_dir), str(target_dir))

  def test_copy_directory_source_not_directory(self, temp_dir: Path) -> None:
    """Test copy with source being a file."""
    source_file = temp_dir / "source.txt"
    source_file.write_text("content")
    target_dir = temp_dir / "target"

    with pytest.raises(FileNotFoundError, match="Source is not a directory"):
      copy_directory_source(str(source_file), str(target_dir))


class TestSafeCopyFile:
  """Test safe_copy_file function."""

  @pytest.fixture
  def temp_dir(self) -> Iterator[Path]:
    """Create temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmp_dir:
      yield Path(tmp_dir)

  def test_safe_copy_file_success(self, temp_dir: Path) -> None:
    """Test successful file copy."""
    source_file = temp_dir / "source.txt"
    target_file = temp_dir / "target.txt"
    test_content = "test content"

    source_file.write_text(test_content)

    result = safe_copy_file(source_file, target_file)

    assert result["status"] == "success"
    assert result["operation"] == "copy"
    assert target_file.exists()
    assert target_file.read_text() == test_content

  def test_safe_copy_file_nonexistent_source(self, temp_dir: Path) -> None:
    """Test copy with nonexistent source file."""
    source_file = temp_dir / "nonexistent.txt"
    target_file = temp_dir / "target.txt"

    with pytest.raises(ValueError, match="Source file does not exist"):
      safe_copy_file(source_file, target_file)

  def test_safe_copy_file_source_is_directory(self, temp_dir: Path) -> None:
    """Test copy with source being a directory."""
    source_dir = temp_dir / "source_dir"
    source_dir.mkdir()
    target_file = temp_dir / "target.txt"

    with pytest.raises(ValueError, match="Source is not a file"):
      safe_copy_file(source_dir, target_file)

  def test_safe_copy_file_target_exists_no_overwrite(self, temp_dir: Path) -> None:
    """Test copy with existing target and overwrite=False."""
    source_file = temp_dir / "source.txt"
    target_file = temp_dir / "target.txt"

    source_file.write_text("source")
    target_file.write_text("target")

    with pytest.raises(ValueError, match="Target file already exists"):
      safe_copy_file(source_file, target_file, overwrite=False)

  def test_safe_copy_file_target_exists_overwrite(self, temp_dir: Path) -> None:
    """Test copy with existing target and overwrite=True."""
    source_file = temp_dir / "source.txt"
    target_file = temp_dir / "target.txt"

    source_file.write_text("source content")
    target_file.write_text("target content")

    result = safe_copy_file(source_file, target_file, overwrite=True)

    assert result["status"] == "success"
    assert target_file.read_text() == "source content"


class TestSafeSymlink:
  """Test safe_symlink function."""

  @pytest.fixture
  def temp_dir(self) -> Iterator[Path]:
    """Create temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmp_dir:
      yield Path(tmp_dir)

  def test_safe_symlink_success(self, temp_dir: Path) -> None:
    """Test successful symlink creation."""
    source_file = temp_dir / "source.txt"
    target_link = temp_dir / "target_link"

    source_file.write_text("test content")

    result = safe_symlink(source_file, target_link)

    assert result["status"] == "success"
    assert result["operation"] == "symlink"
    assert target_link.is_symlink()
    assert target_link.readlink() == source_file

  def test_safe_symlink_directory(self, temp_dir: Path) -> None:
    """Test symlink creation for directory."""
    source_dir = temp_dir / "source_dir"
    target_link = temp_dir / "target_link"

    source_dir.mkdir()

    result = safe_symlink(source_dir, target_link)

    assert result["status"] == "success"
    assert result["is_directory"] is True
    assert target_link.is_symlink()

  def test_safe_symlink_nonexistent_source(self, temp_dir: Path) -> None:
    """Test symlink with nonexistent source."""
    source_file = temp_dir / "nonexistent.txt"
    target_link = temp_dir / "target_link"

    with pytest.raises(ValueError, match="Source path does not exist"):
      safe_symlink(source_file, target_link)

  def test_safe_symlink_target_exists_no_overwrite(self, temp_dir: Path) -> None:
    """Test symlink with existing target and overwrite=False."""
    source_file = temp_dir / "source.txt"
    target_link = temp_dir / "target_link"

    source_file.write_text("source")
    target_link.write_text("existing")

    with pytest.raises(ValueError, match="Target path already exists"):
      safe_symlink(source_file, target_link, overwrite=False)


class TestSafeCopyTree:
  """Test safe_copy_tree function."""

  @pytest.fixture
  def temp_dir(self) -> Iterator[Path]:
    """Create temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmp_dir:
      yield Path(tmp_dir)

  def test_safe_copy_tree_success(self, temp_dir: Path) -> None:
    """Test successful directory tree copy."""
    source_dir = temp_dir / "source"
    target_dir = temp_dir / "target"

    # Create source structure
    source_dir.mkdir()
    (source_dir / "file1.txt").write_text("content1")
    (source_dir / "subdir").mkdir()
    (source_dir / "subdir" / "file2.txt").write_text("content2")

    result = safe_copy_tree(source_dir, target_dir)

    assert result["status"] == "success"
    assert result["operation"] == "copy_tree"
    assert result["copied_files"] == 2
    assert result["copied_directories"] == 1
    assert (target_dir / "file1.txt").read_text() == "content1"
    assert (target_dir / "subdir" / "file2.txt").read_text() == "content2"

  def test_safe_copy_tree_nonexistent_source(self, temp_dir: Path) -> None:
    """Test copy tree with nonexistent source."""
    source_dir = temp_dir / "nonexistent"
    target_dir = temp_dir / "target"

    with pytest.raises(ValueError, match="Source directory does not exist"):
      safe_copy_tree(source_dir, target_dir)

  def test_safe_copy_tree_source_not_directory(self, temp_dir: Path) -> None:
    """Test copy tree with source not being a directory."""
    source_file = temp_dir / "source.txt"
    target_dir = temp_dir / "target"

    source_file.write_text("content")

    with pytest.raises(ValueError, match="Source is not a directory"):
      safe_copy_tree(source_file, target_dir)


# Mock tests for Git-related functions
class TestGitFunctions:
  """Test Git-related functions with mocks."""

  @pytest.fixture
  def temp_dir(self) -> Iterator[Path]:
    """Create temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmp_dir:
      yield Path(tmp_dir)

  def test_compress_directory_to_7z_success(self, temp_dir: Path) -> None:
    """Test 7z compression success."""
    from src.utils.source_extraction import compress_directory_to_7z

    source_dir = temp_dir / "source"
    source_dir.mkdir()
    (source_dir / "file.txt").write_text("test content")
    (source_dir / "subdir").mkdir()
    (source_dir / "subdir" / "nested.txt").write_text("nested content")

    target_7z = temp_dir / "archive.7z"

    compress_directory_to_7z(str(source_dir), str(target_7z))

    # Verify the 7z file was created
    assert target_7z.exists()
    assert target_7z.stat().st_size > 0

  def test_extract_7z_source_success(self, temp_dir: Path) -> None:
    """Test 7z extraction success."""
    from src.utils.source_extraction import compress_directory_to_7z, extract_7z_source

    # First create a test archive
    source_dir = temp_dir / "source"
    source_dir.mkdir()
    (source_dir / "file.txt").write_text("test content")
    (source_dir / "subdir").mkdir()
    (source_dir / "subdir" / "nested.txt").write_text("nested content")

    archive_path = temp_dir / "archive.7z"
    compress_directory_to_7z(str(source_dir), str(archive_path))

    # Now extract it
    target_dir = temp_dir / "extracted"
    extract_7z_source(str(archive_path), str(target_dir))

    # Verify extraction
    assert target_dir.exists()
    assert (target_dir / "file.txt").exists()
    assert (target_dir / "file.txt").read_text() == "test content"
    assert (target_dir / "subdir" / "nested.txt").exists()
    assert (target_dir / "subdir" / "nested.txt").read_text() == "nested content"

  def test_compress_directory_to_7z_nonexistent_source(self, temp_dir: Path) -> None:
    """Test compression with nonexistent source directory."""
    from src.utils.source_extraction import compress_directory_to_7z

    nonexistent_dir = temp_dir / "nonexistent"
    target_7z = temp_dir / "archive.7z"

    with pytest.raises(FileNotFoundError, match="Source directory does not exist"):
      compress_directory_to_7z(str(nonexistent_dir), str(target_7z))

  def test_extract_7z_source_nonexistent_archive(self, temp_dir: Path) -> None:
    """Test extraction with nonexistent archive."""
    from src.utils.source_extraction import extract_7z_source

    nonexistent_archive = temp_dir / "nonexistent.7z"
    target_dir = temp_dir / "extracted"

    with pytest.raises(FileNotFoundError, match="7z file does not exist"):
      extract_7z_source(str(nonexistent_archive), str(target_dir))

  @patch("src.utils.source_extraction.git.Repo")
  def test_create_git_worktree_success(self, mock_repo_class: MagicMock, temp_dir: Path) -> None:
    """Test Git worktree creation success."""
    from src.utils.source_extraction import create_git_worktree

    bare_repo_path = temp_dir / "bare"
    bare_repo_path.mkdir()

    target_dir = temp_dir / "worktree"
    git_ref = "main"

    # Mock Git repo
    mock_repo = Mock()
    mock_repo_class.return_value = mock_repo
    mock_repo.commit.return_value = Mock()  # Mock commit exists

    create_git_worktree(str(bare_repo_path), str(target_dir), git_ref)

    mock_repo.git.worktree.assert_called_once_with("add", str(target_dir), git_ref)

  @patch("src.utils.source_extraction.git.Repo")
  def test_create_git_worktree_ref_not_found(
    self, mock_repo_class: MagicMock, temp_dir: Path
  ) -> None:
    """Test Git worktree creation with invalid ref."""
    from src.utils.source_extraction import create_git_worktree
    from git import exc as git_exc

    bare_repo_path = temp_dir / "bare"
    bare_repo_path.mkdir()

    target_dir = temp_dir / "worktree"
    git_ref = "nonexistent"

    # Mock Git repo with bad name error
    mock_repo = Mock()
    mock_repo_class.return_value = mock_repo
    mock_repo.commit.side_effect = git_exc.BadName()

    with pytest.raises(GitRefNotFoundError):
      create_git_worktree(str(bare_repo_path), str(target_dir), git_ref)
