# pyright: reportTypedDictNotRequiredAccess=false

import zipfile
import tempfile
from pathlib import Path
from unittest.mock import patch, Mock
import pytest
import requests

from src.utils.file_utils import (
  download_file,
  validate_jar_file,
  safe_copy_file,
  safe_symlink,
  safe_copy_tree,
  get_file_info,
  ensure_directory,
)


class TestDownloadFile:
  """Test download_file function."""

  @pytest.fixture
  def temp_dir(self) -> Path:
    """Create temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmp_dir:
      yield Path(tmp_dir)

  def test_download_file_success(self, temp_dir: Path) -> None:
    """Test successful file download."""
    target_path = temp_dir / "test.jar"
    test_content = b"test content"

    with patch("requests.Session") as mock_session_class:
      mock_session = Mock()
      mock_session_class.return_value = mock_session

      mock_response = Mock()
      mock_response.iter_content.return_value = [test_content]
      mock_response.headers = {
        "Content-Length": str(len(test_content)),
        "Content-Type": "application/java-archive",
      }
      mock_session.get.return_value = mock_response

      result = download_file("https://example.com/test.jar", target_path)

      assert result["status"] == "success"
      assert result["url"] == "https://example.com/test.jar"
      assert result["downloaded_size"] == len(test_content)
      assert result["total_size"] == len(test_content)
      assert target_path.exists()

  def test_download_file_empty_url(self, temp_dir: Path) -> None:
    """Test download with empty URL."""
    target_path = temp_dir / "test.jar"

    with pytest.raises(ValueError, match="URL cannot be empty"):
      download_file("", target_path)

  def test_download_file_invalid_url(self, temp_dir: Path) -> None:
    """Test download with invalid URL format."""
    target_path = temp_dir / "test.jar"

    with pytest.raises(ValueError, match="Invalid URL format"):
      download_file("not-a-url", target_path)

  def test_download_file_nonexistent_target_dir(self) -> None:
    """Test download to nonexistent directory."""
    target_path = Path("/nonexistent/test.jar")

    with pytest.raises(ValueError, match="Target directory does not exist"):
      download_file("https://example.com/test.jar", target_path)

  def test_download_file_request_failure(self, temp_dir: Path) -> None:
    """Test download with request failure."""
    target_path = temp_dir / "test.jar"

    with patch("requests.Session") as mock_session_class:
      mock_session = Mock()
      mock_session_class.return_value = mock_session
      mock_session.get.side_effect = requests.RequestException("Network error")

      with pytest.raises(requests.RequestException, match="Failed to download"):
        download_file("https://example.com/test.jar", target_path)

      assert not target_path.exists()  # Should clean up partial download


class TestValidateJarFile:
  """Test validate_jar_file function."""

  @pytest.fixture
  def temp_dir(self) -> Path:
    """Create temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmp_dir:
      yield Path(tmp_dir)

  @pytest.fixture
  def valid_jar(self, temp_dir: Path) -> Path:
    """Create a valid JAR file for testing."""
    jar_path = temp_dir / "test.jar"

    with zipfile.ZipFile(jar_path, "w") as jar_zip:
      jar_zip.writestr("META-INF/MANIFEST.MF", "Manifest-Version: 1.0\n")
      jar_zip.writestr(
        "com/example/Test.java", "package com.example;\npublic class Test {}"
      )

    return jar_path

  @pytest.fixture
  def binary_jar(self, temp_dir: Path) -> Path:
    """Create a binary JAR file for testing."""
    jar_path = temp_dir / "binary.jar"

    with zipfile.ZipFile(jar_path, "w") as jar_zip:
      jar_zip.writestr("META-INF/MANIFEST.MF", "Manifest-Version: 1.0\n")
      jar_zip.writestr("com/example/Test.class", "dummy class file content")

    return jar_path

  def test_validate_jar_file_success(self, valid_jar: Path) -> None:
    """Test validation of valid JAR file."""
    result = validate_jar_file(valid_jar)

    assert result["status"] == "valid"
    assert result["jar_path"] == str(valid_jar)
    assert result["total_entries"] == 2
    assert result["java_files"] == 1
    assert result["class_files"] == 0
    assert result["has_manifest"] is True
    assert result["is_source_jar"] is True

  def test_validate_binary_jar(self, binary_jar: Path) -> None:
    """Test validation of binary JAR file."""
    result = validate_jar_file(binary_jar)

    assert result["status"] == "valid"
    assert result["java_files"] == 0
    assert result["class_files"] == 1
    assert result["is_source_jar"] is False

  def test_validate_jar_nonexistent_file(self) -> None:
    """Test validation of nonexistent file."""
    with pytest.raises(ValueError, match="JAR file does not exist"):
      validate_jar_file(Path("/nonexistent.jar"))

  def test_validate_jar_directory(self, temp_dir: Path) -> None:
    """Test validation of directory instead of file."""
    with pytest.raises(ValueError, match="Path is not a file"):
      validate_jar_file(temp_dir)

  def test_validate_jar_empty_file(self, temp_dir: Path) -> None:
    """Test validation of empty file."""
    empty_jar = temp_dir / "empty.jar"
    empty_jar.touch()

    with pytest.raises(ValueError, match="JAR file is empty"):
      validate_jar_file(empty_jar)

  def test_validate_jar_invalid_zip(self, temp_dir: Path) -> None:
    """Test validation of invalid ZIP file."""
    invalid_jar = temp_dir / "invalid.jar"
    invalid_jar.write_text("not a zip file")

    with pytest.raises(ValueError, match="Invalid ZIP/JAR file format"):
      validate_jar_file(invalid_jar)


class TestSafeCopyFile:
  """Test safe_copy_file function."""

  @pytest.fixture
  def temp_dir(self) -> Path:
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
  def temp_dir(self) -> Path:
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
  def temp_dir(self) -> Path:
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


class TestGetFileInfo:
  """Test get_file_info function."""

  @pytest.fixture
  def temp_dir(self) -> Path:
    """Create temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmp_dir:
      yield Path(tmp_dir)

  def test_get_file_info_file(self, temp_dir: Path) -> None:
    """Test file info for a regular file."""
    test_file = temp_dir / "test.txt"
    test_file.write_text("test content")

    info = get_file_info(test_file)

    assert info["path"] == str(test_file)
    assert info["name"] == "test.txt"
    assert info["exists"] is True
    assert info["is_file"] is True
    assert info["is_directory"] is False
    assert info["is_symlink"] is False
    assert info["suffix"] == ".txt"
    assert info["stem"] == "test"

  def test_get_file_info_directory(self, temp_dir: Path) -> None:
    """Test file info for a directory."""
    # Create some contents
    (temp_dir / "file1.txt").write_text("content")
    (temp_dir / "subdir").mkdir()

    info = get_file_info(temp_dir)

    assert info["is_directory"] is True
    assert info["is_file"] is False
    assert info["contents_count"] == 2
    assert info["files"] == 1
    assert info["subdirectories"] == 1

  def test_get_file_info_jar(self, temp_dir: Path) -> None:
    """Test file info for a JAR file."""
    jar_path = temp_dir / "test.jar"

    with zipfile.ZipFile(jar_path, "w") as jar_zip:
      jar_zip.writestr("META-INF/MANIFEST.MF", "Manifest-Version: 1.0\n")
      jar_zip.writestr("Test.java", "public class Test {}")

    info = get_file_info(jar_path)

    assert info["suffix"] == ".jar"
    assert "jar_validation" in info
    assert info["jar_validation"]["status"] == "valid"

  def test_get_file_info_nonexistent(self, temp_dir: Path) -> None:
    """Test file info for nonexistent path."""
    nonexistent = temp_dir / "nonexistent.txt"

    with pytest.raises(ValueError, match="Path does not exist"):
      get_file_info(nonexistent)


class TestEnsureDirectory:
  """Test ensure_directory function."""

  @pytest.fixture
  def temp_dir(self) -> Path:
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
