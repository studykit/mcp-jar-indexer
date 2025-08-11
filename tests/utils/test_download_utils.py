# pyright: reportTypedDictNotRequiredAccess=false

import zipfile
import tempfile
from pathlib import Path
from typing import Iterator
from unittest.mock import patch, Mock
import pytest
import requests

from src.utils.download_utils import (
  download_file,
  validate_jar_file,
)


class TestDownloadFile:
  """Test download_file function."""

  @pytest.fixture
  def temp_dir(self) -> Iterator[Path]:
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
  def temp_dir(self) -> Iterator[Path]:
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
