"""Test artifact utilities."""

import os
import json
from pathlib import Path
from unittest.mock import patch
import pytest

from src.utils.artifact_utils import (
  get_artifact_code_path,
  is_artifact_code_available,
  is_artifact_code_indexed,
  get_registered_source_info,
)


class TestGetArtifactCodePath:
  """Test get_artifact_code_path function."""

  def test_get_artifact_code_path_basic(self) -> None:
    """Test basic artifact code path generation."""
    path = get_artifact_code_path("org.springframework", "spring-core", "5.3.21")
    expected = "org/springframework/spring-core/5.3.21"
    assert path == expected

  def test_get_artifact_code_path_complex_group(self) -> None:
    """Test with complex group ID."""
    path = get_artifact_code_path(
      "com.fasterxml.jackson.core", "jackson-core", "2.13.0"
    )
    expected = "com/fasterxml/jackson/core/jackson-core/2.13.0"
    assert path == expected

  def test_get_artifact_code_path_simple_group(self) -> None:
    """Test with simple group ID."""
    path = get_artifact_code_path("junit", "junit", "4.13.2")
    expected = "junit/junit/4.13.2"
    assert path == expected

  def test_get_artifact_code_path_invalid_coordinates(self) -> None:
    """Test with invalid Maven coordinates."""
    with pytest.raises(ValueError):
      get_artifact_code_path("", "spring-core", "5.3.21")

    with pytest.raises(ValueError):
      get_artifact_code_path("org.springframework", "", "5.3.21")

    with pytest.raises(ValueError):
      get_artifact_code_path("org.springframework", "spring-core", "")


class TestIsArtifactCodeAvailable:
  """Test is_artifact_code_available function."""

  @pytest.fixture
  def temp_jar_indexer_home(self, tmp_path: Path) -> Path:
    """Create temporary JAR indexer home directory."""
    jar_indexer_home = tmp_path / "jar-indexer"
    jar_indexer_home.mkdir()
    return jar_indexer_home

  @patch.dict(os.environ, {}, clear=True)
  @patch("os.path.expanduser")
  def test_is_artifact_code_available_default_home(
    self, mock_expanduser, temp_jar_indexer_home: Path
  ) -> None:
    """Test with default JAR_INDEXER_HOME."""
    mock_expanduser.return_value = str(temp_jar_indexer_home)

    # Create code directory with content
    code_dir = (
      temp_jar_indexer_home
      / "code"
      / "org"
      / "springframework"
      / "spring-core"
      / "5.3.21"
    )
    code_dir.mkdir(parents=True)
    (code_dir / "Test.java").write_text("public class Test {}")

    result = is_artifact_code_available("org.springframework", "spring-core", "5.3.21")
    assert result is True

  def test_is_artifact_code_available_custom_home(
    self, temp_jar_indexer_home: Path
  ) -> None:
    """Test with custom JAR_INDEXER_HOME environment variable."""
    with patch.dict(os.environ, {"JAR_INDEXER_HOME": str(temp_jar_indexer_home)}):
      # Create code directory with content
      code_dir = (
        temp_jar_indexer_home
        / "code"
        / "org"
        / "springframework"
        / "spring-core"
        / "5.3.21"
      )
      code_dir.mkdir(parents=True)
      (code_dir / "Test.java").write_text("public class Test {}")

      result = is_artifact_code_available(
        "org.springframework", "spring-core", "5.3.21"
      )
      assert result is True

  def test_is_artifact_code_available_no_directory(
    self, temp_jar_indexer_home: Path
  ) -> None:
    """Test with nonexistent code directory."""
    with patch.dict(os.environ, {"JAR_INDEXER_HOME": str(temp_jar_indexer_home)}):
      result = is_artifact_code_available(
        "org.springframework", "spring-core", "5.3.21"
      )
      assert result is False

  def test_is_artifact_code_available_empty_directory(
    self, temp_jar_indexer_home: Path
  ) -> None:
    """Test with empty code directory."""
    with patch.dict(os.environ, {"JAR_INDEXER_HOME": str(temp_jar_indexer_home)}):
      # Create empty code directory
      code_dir = (
        temp_jar_indexer_home
        / "code"
        / "org"
        / "springframework"
        / "spring-core"
        / "5.3.21"
      )
      code_dir.mkdir(parents=True)

      result = is_artifact_code_available(
        "org.springframework", "spring-core", "5.3.21"
      )
      assert result is False

  def test_is_artifact_code_available_file_not_directory(
    self, temp_jar_indexer_home: Path
  ) -> None:
    """Test when path exists but is a file, not directory."""
    with patch.dict(os.environ, {"JAR_INDEXER_HOME": str(temp_jar_indexer_home)}):
      # Create file instead of directory
      code_path = (
        temp_jar_indexer_home
        / "code"
        / "org"
        / "springframework"
        / "spring-core"
        / "5.3.21"
      )
      code_path.parent.mkdir(parents=True)
      code_path.write_text("not a directory")

      result = is_artifact_code_available(
        "org.springframework", "spring-core", "5.3.21"
      )
      assert result is False


class TestIsArtifactCodeIndexed:
  """Test is_artifact_code_indexed function."""

  @pytest.fixture
  def temp_jar_indexer_home(self, tmp_path: Path) -> Path:
    """Create temporary JAR indexer home directory."""
    jar_indexer_home = tmp_path / "jar-indexer"
    jar_indexer_home.mkdir()
    return jar_indexer_home

  def test_is_artifact_code_indexed_true(self, temp_jar_indexer_home: Path) -> None:
    """Test fully indexed artifact."""
    with patch.dict(os.environ, {"JAR_INDEXER_HOME": str(temp_jar_indexer_home)}):
      # Create code directory with index
      code_dir = (
        temp_jar_indexer_home
        / "code"
        / "org"
        / "springframework"
        / "spring-core"
        / "5.3.21"
      )
      index_dir = code_dir / ".jar-indexer"
      index_dir.mkdir(parents=True)

      # Create valid index.json
      index_file = index_dir / "index.json"
      index_data = {"version": "1.0", "timestamp": "2024-01-01T00:00:00Z", "files": []}
      index_file.write_text(json.dumps(index_data))

      result = is_artifact_code_indexed("org.springframework", "spring-core", "5.3.21")
      assert result is True

  def test_is_artifact_code_indexed_no_index_file(
    self, temp_jar_indexer_home: Path
  ) -> None:
    """Test artifact without index file."""
    with patch.dict(os.environ, {"JAR_INDEXER_HOME": str(temp_jar_indexer_home)}):
      # Create code directory without index
      code_dir = (
        temp_jar_indexer_home
        / "code"
        / "org"
        / "springframework"
        / "spring-core"
        / "5.3.21"
      )
      code_dir.mkdir(parents=True)
      (code_dir / "Test.java").write_text("public class Test {}")

      result = is_artifact_code_indexed("org.springframework", "spring-core", "5.3.21")
      assert result is False

  def test_is_artifact_code_indexed_invalid_json(
    self, temp_jar_indexer_home: Path
  ) -> None:
    """Test artifact with invalid index JSON."""
    with patch.dict(os.environ, {"JAR_INDEXER_HOME": str(temp_jar_indexer_home)}):
      # Create code directory with invalid index
      code_dir = (
        temp_jar_indexer_home
        / "code"
        / "org"
        / "springframework"
        / "spring-core"
        / "5.3.21"
      )
      index_dir = code_dir / ".jar-indexer"
      index_dir.mkdir(parents=True)

      # Create invalid JSON
      index_file = index_dir / "index.json"
      index_file.write_text("invalid json content")

      result = is_artifact_code_indexed("org.springframework", "spring-core", "5.3.21")
      assert result is False

  def test_is_artifact_code_indexed_no_code_directory(
    self, temp_jar_indexer_home: Path
  ) -> None:
    """Test with nonexistent code directory."""
    with patch.dict(os.environ, {"JAR_INDEXER_HOME": str(temp_jar_indexer_home)}):
      result = is_artifact_code_indexed("org.springframework", "spring-core", "5.3.21")
      assert result is False


class TestGetRegisteredSourceInfo:
  """Test get_registered_source_info function."""

  @pytest.fixture
  def temp_jar_indexer_home(self, tmp_path: Path) -> Path:
    """Create temporary JAR indexer home directory."""
    jar_indexer_home = tmp_path / "jar-indexer"
    jar_indexer_home.mkdir()
    return jar_indexer_home

  def test_get_registered_source_info_jar_source(
    self, temp_jar_indexer_home: Path
  ) -> None:
    """Test getting info for JAR source."""
    with patch.dict(os.environ, {"JAR_INDEXER_HOME": str(temp_jar_indexer_home)}):
      # Create JAR source
      jar_dir = (
        temp_jar_indexer_home
        / "source-jar"
        / "org"
        / "springframework"
        / "spring-core"
        / "5.3.21"
      )
      jar_dir.mkdir(parents=True)
      jar_file = jar_dir / "spring-core-5.3.21-sources.jar"
      jar_file.write_bytes(b"dummy jar content")

      result = get_registered_source_info(
        "org.springframework", "spring-core", "5.3.21"
      )

      assert result is not None
      assert result["group_id"] == "org.springframework"
      assert result["artifact_id"] == "spring-core"
      assert result["version"] == "5.3.21"
      assert result["source_type"] == "jar"
      assert result["git_ref"] is None
      assert "source-jar" in result["local_path"]

  def test_get_registered_source_info_directory_source(
    self, temp_jar_indexer_home: Path
  ) -> None:
    """Test getting info for compressed directory source."""
    with patch.dict(os.environ, {"JAR_INDEXER_HOME": str(temp_jar_indexer_home)}):
      # Create directory source
      source_dir = (
        temp_jar_indexer_home
        / "source-dir"
        / "org"
        / "springframework"
        / "spring-core"
        / "5.3.21"
      )
      source_dir.mkdir(parents=True)
      archive_file = source_dir / "sources.7z"
      archive_file.write_bytes(b"dummy 7z content")

      result = get_registered_source_info(
        "org.springframework", "spring-core", "5.3.21"
      )

      assert result is not None
      assert result["source_type"] == "directory"
      assert result["git_ref"] is None
      assert "source-dir" in result["local_path"]

  def test_get_registered_source_info_git_source(
    self, temp_jar_indexer_home: Path
  ) -> None:
    """Test getting info for Git source."""
    with patch.dict(os.environ, {"JAR_INDEXER_HOME": str(temp_jar_indexer_home)}):
      # Create Git source directories - git-bare path needs to match artifact path structure
      # For org.springframework/spring-core/5.3.21, git-bare path should be org/springframework/spring-core
      git_bare_dir = (
        temp_jar_indexer_home / "git-bare" / "org" / "springframework" / "spring-core"
      )
      git_bare_dir.mkdir(parents=True)

      code_dir = (
        temp_jar_indexer_home
        / "code"
        / "org"
        / "springframework"
        / "spring-core"
        / "5.3.21"
      )
      code_dir.mkdir(parents=True)
      (code_dir / "Test.java").write_text("public class Test {}")

      result = get_registered_source_info(
        "org.springframework", "spring-core", "5.3.21"
      )

      assert result is not None
      assert result["source_type"] == "git"
      assert result["git_ref"] == "main"  # Default git_ref
      assert "code" in result["local_path"]

  def test_get_registered_source_info_git_with_metadata(
    self, temp_jar_indexer_home: Path
  ) -> None:
    """Test getting info for Git source with metadata."""
    with patch.dict(os.environ, {"JAR_INDEXER_HOME": str(temp_jar_indexer_home)}):
      # Create Git source directories - git-bare path needs to match artifact path structure
      git_bare_dir = (
        temp_jar_indexer_home / "git-bare" / "org" / "springframework" / "spring-core"
      )
      git_bare_dir.mkdir(parents=True)

      code_dir = (
        temp_jar_indexer_home
        / "code"
        / "org"
        / "springframework"
        / "spring-core"
        / "5.3.21"
      )
      index_dir = code_dir / ".jar-indexer"
      index_dir.mkdir(parents=True)

      # Create metadata with git_ref
      metadata_file = index_dir / "metadata.json"
      metadata = {"git_ref": "v5.3.21"}
      metadata_file.write_text(json.dumps(metadata))

      result = get_registered_source_info(
        "org.springframework", "spring-core", "5.3.21"
      )

      assert result is not None
      assert result["source_type"] == "git"
      assert result["git_ref"] == "v5.3.21"  # From metadata

  def test_get_registered_source_info_code_only(
    self, temp_jar_indexer_home: Path
  ) -> None:
    """Test getting info for code-only directory (no source registration)."""
    with patch.dict(os.environ, {"JAR_INDEXER_HOME": str(temp_jar_indexer_home)}):
      # Create only code directory
      code_dir = (
        temp_jar_indexer_home
        / "code"
        / "org"
        / "springframework"
        / "spring-core"
        / "5.3.21"
      )
      code_dir.mkdir(parents=True)
      (code_dir / "Test.java").write_text("public class Test {}")

      result = get_registered_source_info(
        "org.springframework", "spring-core", "5.3.21"
      )

      assert result is not None
      assert result["source_type"] == "directory"
      assert result["git_ref"] is None
      assert "code" in result["local_path"]

  def test_get_registered_source_info_not_found(
    self, temp_jar_indexer_home: Path
  ) -> None:
    """Test getting info for non-registered artifact."""
    with patch.dict(os.environ, {"JAR_INDEXER_HOME": str(temp_jar_indexer_home)}):
      result = get_registered_source_info(
        "org.springframework", "spring-core", "5.3.21"
      )
      assert result is None

  def test_get_registered_source_info_invalid_coordinates(self) -> None:
    """Test with invalid Maven coordinates."""
    with pytest.raises(ValueError):
      get_registered_source_info("", "spring-core", "5.3.21")

    with pytest.raises(ValueError):
      get_registered_source_info("org.springframework", "", "5.3.21")

    with pytest.raises(ValueError):
      get_registered_source_info("org.springframework", "spring-core", "")
