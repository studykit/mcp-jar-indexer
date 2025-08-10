"""Unit tests for register_source MCP tool."""

import json
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.git_handler import (
  GitAuthenticationError,
  GitCloneFailedError,
  GitRefNotFoundError,
)
from src.tools.register_source import (
  DownloadFailedError,
  InvalidSourceError,
  RegisterSourceError,
  ResourceNotFoundError,
  UnsupportedSourceTypeError,
  _handle_git_repository,  # type: ignore[attr-defined]
  _handle_local_directory,  # type: ignore[attr-defined]
  _handle_local_jar_file,  # type: ignore[attr-defined]
  _handle_remote_jar_file,  # type: ignore[attr-defined]
  handle_register_source,
  register_source,
)


class TestRegisterSource:
  """Test cases for register_source function."""

  @pytest.fixture
  def mock_storage_manager(self) -> MagicMock:
    """Mock StorageManager for tests."""
    mock = MagicMock()
    mock.ensure_directories.return_value = None
    mock.validate_directory_permissions.return_value = True
    mock.get_source_jar_path.return_value = Path(
      "/tmp/test/source-jar/org.springframework/spring-core/5.3.21"
    )
    mock.get_code_path.return_value = Path(
      "/tmp/test/code/org.springframework/spring-core/5.3.21"
    )
    mock.get_git_bare_path.return_value = Path(
      "/tmp/test/git-bare/org.springframework/spring-core"
    )
    return mock

  @pytest.fixture
  def mock_source_processor(self) -> MagicMock:
    """Mock SourceProcessor for tests."""
    mock = MagicMock()
    mock.parse_uri.return_value = ("file", {"type": "jar", "path": "/path/to/file.jar"})
    return mock

  @pytest.fixture
  def valid_params(self) -> Dict[str, Any]:
    """Valid parameters for register_source function."""
    return {
      "group_id": "org.springframework",
      "artifact_id": "spring-core",
      "version": "5.3.21",
      "source_uri": "file:///path/to/spring-core-5.3.21-sources.jar",
    }

  @pytest.mark.asyncio
  async def test_register_source_success_jar_auto_index_false(
    self, mock_storage_manager: MagicMock, mock_source_processor: MagicMock, valid_params: Dict[str, Any]
  ) -> None:
    """Test successful registration of JAR file with auto_index=False."""
    with (
      patch("src.tools.register_source.validate_maven_coordinates"),
      patch("src.tools.register_source.validate_uri_format"),
      patch(
        "src.tools.register_source.StorageManager", return_value=mock_storage_manager
      ),
      patch(
        "src.tools.register_source.SourceProcessor", return_value=mock_source_processor
      ),
      patch(
        "src.tools.register_source._handle_local_jar_file", new_callable=AsyncMock
      ) as mock_handle_jar,
    ):
      result = await register_source(**valid_params, auto_index=False)

      assert result["group_id"] == "org.springframework"
      assert result["artifact_id"] == "spring-core"
      assert result["version"] == "5.3.21"
      assert result["status"] == "registered_only"
      assert result["indexed"] is False
      assert "registered successfully" in result["message"]
      mock_handle_jar.assert_called_once()

  @pytest.mark.asyncio
  async def test_register_source_success_jar_auto_index_true(
    self, mock_storage_manager: MagicMock, mock_source_processor: MagicMock, valid_params: Dict[str, Any]
  ) -> None:
    """Test successful registration of JAR file with auto_index=True (default)."""
    with (
      patch("src.tools.register_source.validate_maven_coordinates"),
      patch("src.tools.register_source.validate_uri_format"),
      patch(
        "src.tools.register_source.StorageManager", return_value=mock_storage_manager
      ),
      patch(
        "src.tools.register_source.SourceProcessor", return_value=mock_source_processor
      ),
      patch(
        "src.tools.register_source._handle_local_jar_file", new_callable=AsyncMock
      ) as mock_handle_jar,
    ):
      result = await register_source(**valid_params)  # auto_index=True by default

      assert (
        result["status"] == "registered_only"
      )  # TODO: Will be "registered_and_indexed" when indexing is implemented
      assert (
        result["indexed"] is False
      )  # TODO: Will be True when indexing is implemented
      mock_handle_jar.assert_called_once()

  @pytest.mark.asyncio
  async def test_register_source_directory_type(
    self, mock_storage_manager: MagicMock, valid_params: Dict[str, Any]
  ) -> None:
    """Test registration of directory type."""
    mock_source_processor = MagicMock()
    mock_source_processor.parse_uri.return_value = (
      "file",
      {"type": "directory", "path": "/path/to/sources"},
    )

    with (
      patch("src.tools.register_source.validate_maven_coordinates"),
      patch("src.tools.register_source.validate_uri_format"),
      patch(
        "src.tools.register_source.StorageManager", return_value=mock_storage_manager
      ),
      patch(
        "src.tools.register_source.SourceProcessor", return_value=mock_source_processor
      ),
      patch(
        "src.tools.register_source._handle_local_directory", new_callable=AsyncMock
      ) as mock_handle_dir,
    ):
      result = await register_source(**valid_params)

      assert result["status"] == "registered_only"
      mock_handle_dir.assert_called_once()

  @pytest.mark.asyncio
  async def test_register_source_http_jar(
    self, mock_storage_manager: MagicMock, valid_params: Dict[str, Any]
  ) -> None:
    """Test registration of HTTP JAR file."""
    mock_source_processor = MagicMock()
    mock_source_processor.parse_uri.return_value = (
      "http",
      {"type": "jar", "url": "https://example.com/file.jar"},
    )

    valid_params["source_uri"] = "https://example.com/spring-core-5.3.21-sources.jar"

    with (
      patch("src.tools.register_source.validate_maven_coordinates"),
      patch("src.tools.register_source.validate_uri_format"),
      patch(
        "src.tools.register_source.StorageManager", return_value=mock_storage_manager
      ),
      patch(
        "src.tools.register_source.SourceProcessor", return_value=mock_source_processor
      ),
      patch(
        "src.tools.register_source._handle_remote_jar_file", new_callable=AsyncMock
      ) as mock_handle_remote,
    ):
      result = await register_source(**valid_params)

      assert result["status"] == "registered_only"
      mock_handle_remote.assert_called_once()

  @pytest.mark.asyncio
  async def test_register_source_git_repository(
    self, mock_storage_manager: MagicMock, valid_params: Dict[str, Any]
  ) -> None:
    """Test registration of Git repository."""
    mock_source_processor = MagicMock()
    mock_source_processor.parse_uri.return_value = (
      "git",
      {"url": "https://github.com/spring-projects/spring-framework.git"},
    )

    valid_params["source_uri"] = (
      "https://github.com/spring-projects/spring-framework.git"
    )
    valid_params["git_ref"] = "v5.3.21"

    with (
      patch("src.tools.register_source.validate_maven_coordinates"),
      patch("src.tools.register_source.validate_uri_format"),
      patch(
        "src.tools.register_source.StorageManager", return_value=mock_storage_manager
      ),
      patch(
        "src.tools.register_source.SourceProcessor", return_value=mock_source_processor
      ),
      patch(
        "src.tools.register_source._handle_git_repository", new_callable=AsyncMock
      ) as mock_handle_git,
    ):
      result = await register_source(**valid_params)

      assert result["status"] == "registered_only"
      mock_handle_git.assert_called_once_with(
        mock_storage_manager,
        {"url": "https://github.com/spring-projects/spring-framework.git"},
        "v5.3.21",
        "org.springframework",
        "spring-core",
        "5.3.21",
      )

  @pytest.mark.asyncio
  async def test_register_source_git_repository_default_ref(
    self, mock_storage_manager: MagicMock, valid_params: Dict[str, Any]
  ) -> None:
    """Test registration of Git repository with default git_ref."""
    mock_source_processor = MagicMock()
    mock_source_processor.parse_uri.return_value = (
      "git",
      {"url": "https://github.com/spring-projects/spring-framework.git"},
    )

    valid_params["source_uri"] = (
      "https://github.com/spring-projects/spring-framework.git"
    )

    with (
      patch("src.tools.register_source.validate_maven_coordinates"),
      patch("src.tools.register_source.validate_uri_format"),
      patch(
        "src.tools.register_source.StorageManager", return_value=mock_storage_manager
      ),
      patch(
        "src.tools.register_source.SourceProcessor", return_value=mock_source_processor
      ),
      patch(
        "src.tools.register_source._handle_git_repository", new_callable=AsyncMock
      ) as mock_handle_git,
    ):
      await register_source(**valid_params)

      mock_handle_git.assert_called_once_with(
        mock_storage_manager,
        {"url": "https://github.com/spring-projects/spring-framework.git"},
        "main",  # Default git_ref
        "org.springframework",
        "spring-core",
        "5.3.21",
      )

  @pytest.mark.asyncio
  async def test_register_source_validation_error(self, valid_params: Dict[str, Any]) -> None:
    """Test register_source with validation error."""
    with patch(
      "src.tools.register_source.validate_maven_coordinates",
      side_effect=ValueError("Invalid group_id"),
    ):
      result = await register_source(**valid_params)

      assert result["status"] == "internal_error"
      assert "Invalid group_id" in result["message"]

  @pytest.mark.asyncio
  async def test_register_source_storage_permission_error(
    self, mock_source_processor: MagicMock, valid_params: Dict[str, Any]
  ) -> None:
    """Test register_source with storage permission error."""
    mock_storage_manager = MagicMock()
    mock_storage_manager.ensure_directories.return_value = None
    mock_storage_manager.validate_directory_permissions.return_value = False

    with (
      patch("src.tools.register_source.validate_maven_coordinates"),
      patch("src.tools.register_source.validate_uri_format"),
      patch(
        "src.tools.register_source.StorageManager", return_value=mock_storage_manager
      ),
      patch(
        "src.tools.register_source.SourceProcessor", return_value=mock_source_processor
      ),
    ):
      result = await register_source(**valid_params)

      assert result["status"] == "internal_error"
      assert "Storage directories are not accessible" in result["message"]

  @pytest.mark.asyncio
  async def test_register_source_uri_parsing_error(
    self, mock_storage_manager: MagicMock, valid_params: Dict[str, Any]
  ) -> None:
    """Test register_source with URI parsing error."""
    mock_source_processor = MagicMock()
    mock_source_processor.parse_uri.side_effect = ValueError("Invalid URI format")

    with (
      patch("src.tools.register_source.validate_maven_coordinates"),
      patch("src.tools.register_source.validate_uri_format"),
      patch(
        "src.tools.register_source.StorageManager", return_value=mock_storage_manager
      ),
      patch(
        "src.tools.register_source.SourceProcessor", return_value=mock_source_processor
      ),
    ):
      result = await register_source(**valid_params)

      assert result["status"] == "unsupported_source_type"
      assert "URI parsing failed" in result["message"]

  @pytest.mark.asyncio
  async def test_register_source_unsupported_file_type(
    self, mock_storage_manager: MagicMock, valid_params: Dict[str, Any]
  ) -> None:
    """Test register_source with unsupported file type."""
    mock_source_processor = MagicMock()
    mock_source_processor.parse_uri.return_value = ("file", {"type": "zip"})

    with (
      patch("src.tools.register_source.validate_maven_coordinates"),
      patch("src.tools.register_source.validate_uri_format"),
      patch(
        "src.tools.register_source.StorageManager", return_value=mock_storage_manager
      ),
      patch(
        "src.tools.register_source.SourceProcessor", return_value=mock_source_processor
      ),
    ):
      result = await register_source(**valid_params)

      assert result["status"] == "unsupported_source_type"
      assert "Unsupported file type: zip" in result["message"]

  @pytest.mark.asyncio
  async def test_register_source_unsupported_http_type(
    self, mock_storage_manager: MagicMock, valid_params: Dict[str, Any]
  ) -> None:
    """Test register_source with unsupported HTTP type."""
    mock_source_processor = MagicMock()
    mock_source_processor.parse_uri.return_value = ("http", {"type": "zip"})

    with (
      patch("src.tools.register_source.validate_maven_coordinates"),
      patch("src.tools.register_source.validate_uri_format"),
      patch(
        "src.tools.register_source.StorageManager", return_value=mock_storage_manager
      ),
      patch(
        "src.tools.register_source.SourceProcessor", return_value=mock_source_processor
      ),
    ):
      result = await register_source(**valid_params)

      assert result["status"] == "unsupported_source_type"
      assert "Unsupported HTTP type: zip" in result["message"]

  @pytest.mark.asyncio
  async def test_register_source_unsupported_uri_type(
    self, mock_storage_manager: MagicMock, valid_params: Dict[str, Any]
  ) -> None:
    """Test register_source with unsupported URI type."""
    mock_source_processor = MagicMock()
    mock_source_processor.parse_uri.return_value = (
      "ftp",
      {"url": "ftp://example.com/file.jar"},
    )

    with (
      patch("src.tools.register_source.validate_maven_coordinates"),
      patch("src.tools.register_source.validate_uri_format"),
      patch(
        "src.tools.register_source.StorageManager", return_value=mock_storage_manager
      ),
      patch(
        "src.tools.register_source.SourceProcessor", return_value=mock_source_processor
      ),
    ):
      result = await register_source(**valid_params)

      assert result["status"] == "unsupported_source_type"
      assert "Unsupported URI type: ftp" in result["message"]


class TestRegisterSourceErrorHandling:
  """Test error handling for register_source function."""

  @pytest.fixture
  def valid_params(self) -> Dict[str, Any]:
    return {
      "group_id": "org.springframework",
      "artifact_id": "spring-core",
      "version": "5.3.21",
      "source_uri": "https://github.com/spring-projects/spring-framework.git",
      "git_ref": "v5.3.21",
    }

  @pytest.mark.asyncio
  async def test_git_clone_failed_error(self, valid_params: Dict[str, Any]) -> None:
    """Test handling of GitCloneFailedError."""
    with (
      patch("src.tools.register_source.validate_maven_coordinates"),
      patch("src.tools.register_source.validate_uri_format"),
      patch(
        "src.tools.register_source._handle_git_repository",
        new_callable=AsyncMock,
        side_effect=GitCloneFailedError("Clone failed"),
      ),
    ):
      result = await register_source(**valid_params)

      assert result["status"] == "git_clone_failed"
      assert "Failed to clone Git repository" in result["message"]

  @pytest.mark.asyncio
  async def test_git_ref_not_found_error(self, valid_params: Dict[str, Any]) -> None:
    """Test handling of GitRefNotFoundError."""
    with (
      patch("src.tools.register_source.validate_maven_coordinates"),
      patch("src.tools.register_source.validate_uri_format"),
      patch(
        "src.tools.register_source._handle_git_repository",
        new_callable=AsyncMock,
        side_effect=GitRefNotFoundError("Ref not found"),
      ),
    ):
      result = await register_source(**valid_params)

      assert result["status"] == "git_ref_not_found"
      assert "Git reference not found" in result["message"]

  @pytest.mark.asyncio
  async def test_git_authentication_error(self, valid_params: Dict[str, Any]) -> None:
    """Test handling of GitAuthenticationError."""
    with (
      patch("src.tools.register_source.validate_maven_coordinates"),
      patch("src.tools.register_source.validate_uri_format"),
      patch(
        "src.tools.register_source._handle_git_repository",
        new_callable=AsyncMock,
        side_effect=GitAuthenticationError("Auth failed"),
      ),
    ):
      result = await register_source(**valid_params)

      assert result["status"] == "git_authentication_failed"
      assert "Git authentication failed" in result["message"]

  @pytest.mark.asyncio
  async def test_resource_not_found_error(self, valid_params: Dict[str, Any]) -> None:
    """Test handling of ResourceNotFoundError."""
    mock_source_processor = MagicMock()
    mock_source_processor.parse_uri.return_value = (
      "file",
      {"type": "jar", "path": "/path/to/file.jar"},
    )
    mock_storage_manager = MagicMock()
    mock_storage_manager.ensure_directories.return_value = None
    mock_storage_manager.validate_directory_permissions.return_value = True

    with (
      patch("src.tools.register_source.validate_maven_coordinates"),
      patch("src.tools.register_source.validate_uri_format"),
      patch(
        "src.tools.register_source.StorageManager", return_value=mock_storage_manager
      ),
      patch(
        "src.tools.register_source.SourceProcessor", return_value=mock_source_processor
      ),
      patch(
        "src.tools.register_source._handle_local_jar_file",
        new_callable=AsyncMock,
        side_effect=ResourceNotFoundError("File not found"),
      ),
    ):
      result = await register_source(**valid_params)

      assert result["status"] == "resource_not_found"
      assert "File not found" in result["message"]

  @pytest.mark.asyncio
  async def test_download_failed_error(self, valid_params: Dict[str, Any]) -> None:
    """Test handling of DownloadFailedError."""
    mock_source_processor = MagicMock()
    mock_source_processor.parse_uri.return_value = (
      "http",
      {"type": "jar", "url": "https://example.com/file.jar"},
    )
    mock_storage_manager = MagicMock()
    mock_storage_manager.ensure_directories.return_value = None
    mock_storage_manager.validate_directory_permissions.return_value = True

    with (
      patch("src.tools.register_source.validate_maven_coordinates"),
      patch("src.tools.register_source.validate_uri_format"),
      patch(
        "src.tools.register_source.StorageManager", return_value=mock_storage_manager
      ),
      patch(
        "src.tools.register_source.SourceProcessor", return_value=mock_source_processor
      ),
      patch(
        "src.tools.register_source._handle_remote_jar_file",
        new_callable=AsyncMock,
        side_effect=DownloadFailedError("Download failed"),
      ),
    ):
      result = await register_source(**valid_params)

      assert result["status"] == "download_failed"
      assert "Download failed" in result["message"]

  @pytest.mark.asyncio
  async def test_invalid_source_error(self, valid_params: Dict[str, Any]) -> None:
    """Test handling of InvalidSourceError."""
    mock_source_processor = MagicMock()
    mock_source_processor.parse_uri.return_value = (
      "file",
      {"type": "jar", "path": "/path/to/file.jar"},
    )
    mock_storage_manager = MagicMock()
    mock_storage_manager.ensure_directories.return_value = None
    mock_storage_manager.validate_directory_permissions.return_value = True

    with (
      patch("src.tools.register_source.validate_maven_coordinates"),
      patch("src.tools.register_source.validate_uri_format"),
      patch(
        "src.tools.register_source.StorageManager", return_value=mock_storage_manager
      ),
      patch(
        "src.tools.register_source.SourceProcessor", return_value=mock_source_processor
      ),
      patch(
        "src.tools.register_source._handle_local_jar_file",
        new_callable=AsyncMock,
        side_effect=InvalidSourceError("Invalid JAR"),
      ),
    ):
      result = await register_source(**valid_params)

      assert result["status"] == "invalid_source"
      assert "Invalid JAR" in result["message"]

  @pytest.mark.asyncio
  async def test_unsupported_source_type_error(self, valid_params: Dict[str, Any]) -> None:
    """Test handling of UnsupportedSourceTypeError."""
    mock_source_processor = MagicMock()
    mock_source_processor.parse_uri.return_value = (
      "file",
      {"type": "jar", "path": "/path/to/file.jar"},
    )
    mock_storage_manager = MagicMock()
    mock_storage_manager.ensure_directories.return_value = None
    mock_storage_manager.validate_directory_permissions.return_value = True

    with (
      patch("src.tools.register_source.validate_maven_coordinates"),
      patch("src.tools.register_source.validate_uri_format"),
      patch(
        "src.tools.register_source.StorageManager", return_value=mock_storage_manager
      ),
      patch(
        "src.tools.register_source.SourceProcessor", return_value=mock_source_processor
      ),
      patch(
        "src.tools.register_source._handle_local_jar_file",
        new_callable=AsyncMock,
        side_effect=UnsupportedSourceTypeError("Unsupported type"),
      ),
    ):
      result = await register_source(**valid_params)

      assert result["status"] == "unsupported_source_type"
      assert "Unsupported type" in result["message"]


class TestHandleLocalJarFile:
  """Test cases for _handle_local_jar_file function."""

  @pytest.fixture
  def mock_storage_manager(self) -> MagicMock:
    mock = MagicMock()
    mock.get_source_jar_path.return_value = Path(
      "/tmp/test/source-jar/org.springframework/spring-core/5.3.21"
    )
    return mock

  @pytest.fixture
  def temp_jar_file(self) -> Generator[Path, None, None]:
    """Create a temporary JAR file for testing."""
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".jar")
    temp_file.write(b"PK\x03\x04")  # JAR file magic bytes
    temp_file.close()
    yield Path(temp_file.name)
    Path(temp_file.name).unlink(missing_ok=True)

  @pytest.mark.asyncio
  async def test_handle_local_jar_file_success(
    self, mock_storage_manager: MagicMock, temp_jar_file: Path
  ) -> None:
    """Test successful handling of local JAR file."""
    parsed_info = {"path": str(temp_jar_file)}

    with (
      patch("src.tools.register_source.validate_jar_file", return_value=True),
      patch("pathlib.Path.mkdir") as mock_mkdir,
      patch("shutil.copy2") as mock_copy,
    ):
      await _handle_local_jar_file(
        mock_storage_manager,
        parsed_info,
        "org.springframework",
        "spring-core",
        "5.3.21",
      )

      mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
      mock_copy.assert_called_once()

  @pytest.mark.asyncio
  async def test_handle_local_jar_file_not_found(self, mock_storage_manager: MagicMock) -> None:
    """Test handling of non-existent JAR file."""
    parsed_info = {"path": "/nonexistent/file.jar"}

    with pytest.raises(ResourceNotFoundError, match="Local JAR file not found"):
      await _handle_local_jar_file(
        mock_storage_manager,
        parsed_info,
        "org.springframework",
        "spring-core",
        "5.3.21",
      )

  @pytest.mark.asyncio
  async def test_handle_local_jar_file_invalid(
    self, mock_storage_manager: MagicMock, temp_jar_file: Path
  ) -> None:
    """Test handling of invalid JAR file."""
    parsed_info = {"path": str(temp_jar_file)}

    with patch("src.tools.register_source.validate_jar_file", return_value=False):
      with pytest.raises(InvalidSourceError, match="Invalid JAR file"):
        await _handle_local_jar_file(
          mock_storage_manager,
          parsed_info,
          "org.springframework",
          "spring-core",
          "5.3.21",
        )

  @pytest.mark.asyncio
  async def test_handle_local_jar_file_copy_error(
    self, mock_storage_manager: MagicMock, temp_jar_file: Path
  ) -> None:
    """Test handling of file copy error."""
    parsed_info = {"path": str(temp_jar_file)}

    with (
      patch("src.tools.register_source.validate_jar_file", return_value=True),
      patch("pathlib.Path.mkdir"),
      patch("shutil.copy2", side_effect=PermissionError("Permission denied")),
    ):
      with pytest.raises(RegisterSourceError, match="Error processing local JAR file"):
        await _handle_local_jar_file(
          mock_storage_manager,
          parsed_info,
          "org.springframework",
          "spring-core",
          "5.3.21",
        )


class TestHandleRemoteJarFile:
  """Test cases for _handle_remote_jar_file function."""

  @pytest.fixture
  def mock_storage_manager(self) -> MagicMock:
    mock = MagicMock()
    mock.get_source_jar_path.return_value = Path(
      "/tmp/test/source-jar/org.springframework/spring-core/5.3.21"
    )
    return mock

  @pytest.mark.asyncio
  async def test_handle_remote_jar_file_success(self, mock_storage_manager: MagicMock) -> None:
    """Test successful handling of remote JAR file."""
    parsed_info = {"url": "https://example.com/spring-core-5.3.21-sources.jar"}

    with (
      patch("src.tools.register_source.download_file") as mock_download,
      patch("src.tools.register_source.validate_jar_file", return_value=True),
      patch("pathlib.Path.mkdir") as mock_mkdir,
    ):
      await _handle_remote_jar_file(
        mock_storage_manager,
        parsed_info,
        "org.springframework",
        "spring-core",
        "5.3.21",
      )

      mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
      mock_download.assert_called_once()

  @pytest.mark.asyncio
  async def test_handle_remote_jar_file_download_failed(self, mock_storage_manager: MagicMock) -> None:
    """Test handling of download failure."""
    parsed_info = {"url": "https://example.com/spring-core-5.3.21-sources.jar"}

    with (
      patch(
        "src.tools.register_source.download_file",
        side_effect=Exception("Network error"),
      ),
      patch("pathlib.Path.mkdir"),
    ):
      with pytest.raises(DownloadFailedError, match="Failed to download JAR file"):
        await _handle_remote_jar_file(
          mock_storage_manager,
          parsed_info,
          "org.springframework",
          "spring-core",
          "5.3.21",
        )

  @pytest.mark.asyncio
  async def test_handle_remote_jar_file_invalid_after_download(
    self, mock_storage_manager: MagicMock
  ) -> None:
    """Test handling of invalid JAR file after download."""
    parsed_info = {"url": "https://example.com/spring-core-5.3.21-sources.jar"}

    # Mock download_file to not raise an exception, but validate_jar_file to return False
    with (
      patch("src.tools.register_source.download_file"),
      patch("src.tools.register_source.validate_jar_file", return_value=False),
      patch("pathlib.Path.mkdir"),
    ):
      # The function should catch the InvalidSourceError and re-raise as DownloadFailedError
      with pytest.raises(DownloadFailedError, match="Failed to download JAR file"):
        await _handle_remote_jar_file(
          mock_storage_manager,
          parsed_info,
          "org.springframework",
          "spring-core",
          "5.3.21",
        )


class TestHandleLocalDirectory:
  """Test cases for _handle_local_directory function."""

  @pytest.fixture
  def mock_storage_manager(self) -> MagicMock:
    mock = MagicMock()
    mock.get_code_path.return_value = Path(
      "/tmp/test/code/org.springframework/spring-core/5.3.21"
    )
    return mock

  @pytest.fixture
  def temp_directory(self) -> Generator[Path, None, None]:
    """Create a temporary directory for testing."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir, ignore_errors=True)

  @pytest.mark.asyncio
  async def test_handle_local_directory_success(
    self, mock_storage_manager: MagicMock, temp_directory: Path
  ) -> None:
    """Test successful handling of local directory."""
    parsed_info = {"path": str(temp_directory)}
    target_path = Path("/tmp/test/code/org.springframework/spring-core/5.3.21")

    # Since the actual temp_directory exists, we'll test the successful path
    with (
      patch("src.tools.register_source.GitHandler") as mock_git_handler_class,
      patch("src.tools.register_source.safe_copy_tree") as mock_copy,
      patch("pathlib.Path.mkdir"),
    ):
      mock_git_handler = MagicMock()
      mock_git_handler.is_git_repository.return_value = False
      mock_git_handler_class.return_value = mock_git_handler

      await _handle_local_directory(
        mock_storage_manager,
        parsed_info,
        "org.springframework",
        "spring-core",
        "5.3.21",
      )

      mock_copy.assert_called_once_with(temp_directory, target_path)

  @pytest.mark.asyncio
  async def test_handle_local_directory_not_found(self, mock_storage_manager: MagicMock) -> None:
    """Test handling of non-existent directory."""
    parsed_info = {"path": "/nonexistent/directory"}

    with pytest.raises(ResourceNotFoundError, match="Local directory not found"):
      await _handle_local_directory(
        mock_storage_manager,
        parsed_info,
        "org.springframework",
        "spring-core",
        "5.3.21",
      )

  @pytest.mark.asyncio
  async def test_handle_local_directory_not_directory(
    self, mock_storage_manager: MagicMock, temp_directory: Path
  ) -> None:
    """Test handling when path is not a directory."""
    # Create a file instead of directory
    test_file = temp_directory / "test.txt"
    test_file.write_text("test")

    parsed_info = {"path": str(test_file)}

    with pytest.raises(InvalidSourceError, match="Path is not a directory"):
      await _handle_local_directory(
        mock_storage_manager,
        parsed_info,
        "org.springframework",
        "spring-core",
        "5.3.21",
      )

  @pytest.mark.asyncio
  async def test_handle_local_directory_git_repo_without_ref(
    self, mock_storage_manager: MagicMock, temp_directory: Path
  ) -> None:
    """Test handling of Git repository directory without git_ref parameter."""
    parsed_info = {"path": str(temp_directory)}

    with patch("src.tools.register_source.GitHandler") as mock_git_handler_class:
      mock_git_handler = MagicMock()
      mock_git_handler.is_git_repository.return_value = True
      mock_git_handler_class.return_value = mock_git_handler

      with pytest.raises(
        UnsupportedSourceTypeError,
        match="Git repository directory must be registered with git_ref parameter",
      ):
        await _handle_local_directory(
          mock_storage_manager,
          parsed_info,
          "org.springframework",
          "spring-core",
          "5.3.21",
        )

  @pytest.mark.asyncio
  async def test_handle_local_directory_existing_target(
    self, mock_storage_manager: MagicMock, temp_directory: Path
  ) -> None:
    """Test handling when target directory already exists."""
    parsed_info = {"path": str(temp_directory)}

    with (
      patch("src.tools.register_source.GitHandler") as mock_git_handler_class,
      patch("src.tools.register_source.safe_copy_tree") as mock_copy,
      patch("pathlib.Path.mkdir"),
      patch("pathlib.Path.exists", return_value=True),
      patch("shutil.rmtree") as mock_rmtree,
    ):
      mock_git_handler = MagicMock()
      mock_git_handler.is_git_repository.return_value = False
      mock_git_handler_class.return_value = mock_git_handler

      await _handle_local_directory(
        mock_storage_manager,
        parsed_info,
        "org.springframework",
        "spring-core",
        "5.3.21",
      )

      mock_rmtree.assert_called_once()
      mock_copy.assert_called_once()


class TestHandleGitRepository:
  """Test cases for _handle_git_repository function."""

  @pytest.fixture
  def mock_storage_manager(self) -> MagicMock:
    mock = MagicMock()
    mock.get_git_bare_path.return_value = Path(
      "/tmp/test/git-bare/org.springframework/spring-core"
    )
    mock.get_code_path.return_value = Path(
      "/tmp/test/code/org.springframework/spring-core/5.3.21"
    )
    return mock

  @pytest.fixture
  def mock_git_handler(self) -> MagicMock:
    return MagicMock()

  @pytest.mark.asyncio
  async def test_handle_git_repository_new_repo(
    self, mock_storage_manager: MagicMock, mock_git_handler: MagicMock
  ) -> None:
    """Test handling of new Git repository."""
    parsed_info = {"url": "https://github.com/spring-projects/spring-framework.git"}

    with (
      patch("src.tools.register_source.GitHandler", return_value=mock_git_handler),
      patch("pathlib.Path.exists", return_value=False),
    ):
      await _handle_git_repository(
        mock_storage_manager,
        parsed_info,
        "v5.3.21",
        "org.springframework",
        "spring-core",
        "5.3.21",
      )

      mock_git_handler.clone_bare_repository.assert_called_once_with(
        "https://github.com/spring-projects/spring-framework.git",
        "org.springframework",
        "spring-core",
      )
      mock_git_handler.create_worktree.assert_called_once_with(
        "org.springframework", "spring-core", "5.3.21", "v5.3.21"
      )

  @pytest.mark.asyncio
  async def test_handle_git_repository_existing_repo(
    self, mock_storage_manager: MagicMock, mock_git_handler: MagicMock
  ) -> None:
    """Test handling of existing Git repository."""
    parsed_info = {"url": "https://github.com/spring-projects/spring-framework.git"}

    with (
      patch("src.tools.register_source.GitHandler", return_value=mock_git_handler),
      patch("pathlib.Path.exists", side_effect=[True, False]),
    ):  # bare_repo_path exists, worktree_path doesn't
      await _handle_git_repository(
        mock_storage_manager,
        parsed_info,
        "v5.3.21",
        "org.springframework",
        "spring-core",
        "5.3.21",
      )

      mock_git_handler.update_repository.assert_called_once_with(
        "org.springframework", "spring-core"
      )
      mock_git_handler.create_worktree.assert_called_once_with(
        "org.springframework", "spring-core", "5.3.21", "v5.3.21"
      )

  @pytest.mark.asyncio
  async def test_handle_git_repository_existing_worktree(
    self, mock_storage_manager: MagicMock, mock_git_handler: MagicMock
  ) -> None:
    """Test handling when worktree already exists."""
    parsed_info = {"url": "https://github.com/spring-projects/spring-framework.git"}

    with (
      patch("src.tools.register_source.GitHandler", return_value=mock_git_handler),
      patch("pathlib.Path.exists", return_value=True),
    ):
      await _handle_git_repository(
        mock_storage_manager,
        parsed_info,
        "v5.3.21",
        "org.springframework",
        "spring-core",
        "5.3.21",
      )

      mock_git_handler.remove_worktree.assert_called_once_with(
        "org.springframework", "spring-core", "5.3.21"
      )
      mock_git_handler.create_worktree.assert_called_once()

  @pytest.mark.asyncio
  async def test_handle_git_repository_git_error_passthrough(
    self, mock_storage_manager: MagicMock, mock_git_handler: MagicMock
  ) -> None:
    """Test that Git errors are passed through."""
    parsed_info = {"url": "https://github.com/spring-projects/spring-framework.git"}

    mock_git_handler.clone_bare_repository.side_effect = GitCloneFailedError(
      "Clone failed"
    )

    with (
      patch("src.tools.register_source.GitHandler", return_value=mock_git_handler),
      patch("pathlib.Path.exists", return_value=False),
    ):
      with pytest.raises(GitCloneFailedError):
        await _handle_git_repository(
          mock_storage_manager,
          parsed_info,
          "v5.3.21",
          "org.springframework",
          "spring-core",
          "5.3.21",
        )

  @pytest.mark.asyncio
  async def test_handle_git_repository_general_error(
    self, mock_storage_manager: MagicMock, mock_git_handler: MagicMock
  ) -> None:
    """Test handling of general errors."""
    parsed_info = {"url": "https://github.com/spring-projects/spring-framework.git"}

    mock_git_handler.clone_bare_repository.side_effect = Exception("Unexpected error")

    with (
      patch("src.tools.register_source.GitHandler", return_value=mock_git_handler),
      patch("pathlib.Path.exists", return_value=False),
    ):
      with pytest.raises(RegisterSourceError, match="Error processing Git repository"):
        await _handle_git_repository(
          mock_storage_manager,
          parsed_info,
          "v5.3.21",
          "org.springframework",
          "spring-core",
          "5.3.21",
        )


class TestHandleRegisterSource:
  """Test cases for handle_register_source MCP tool handler."""

  @pytest.fixture
  def valid_arguments(self) -> Dict[str, Any]:
    return {
      "group_id": "org.springframework",
      "artifact_id": "spring-core",
      "version": "5.3.21",
      "source_uri": "file:///path/to/spring-core-5.3.21-sources.jar",
      "auto_index": True,
      "git_ref": "v5.3.21",
    }

  @pytest.mark.asyncio
  async def test_handle_register_source_success(self, valid_arguments: Dict[str, Any]) -> None:
    """Test successful MCP tool handler."""
    mock_result: Dict[str, Any] = {
      "group_id": "org.springframework",
      "artifact_id": "spring-core",
      "version": "5.3.21",
      "status": "registered_only",
      "indexed": False,
      "message": "Source registered successfully.",
    }

    with patch(
      "src.tools.register_source.register_source",
      new_callable=AsyncMock,
      return_value=mock_result,
    ):
      result = await handle_register_source(valid_arguments)

      assert len(result) == 1
      assert result[0].type == "text"

      response_data = json.loads(result[0].text)
      assert response_data["group_id"] == "org.springframework"
      assert response_data["status"] == "registered_only"

  @pytest.mark.asyncio
  async def test_handle_register_source_with_defaults(self) -> None:
    """Test MCP tool handler with default values."""
    arguments = {
      "group_id": "org.springframework",
      "artifact_id": "spring-core",
      "version": "5.3.21",
      "source_uri": "file:///path/to/spring-core-5.3.21-sources.jar",
    }

    mock_result = {"status": "registered_only"}

    with patch(
      "src.tools.register_source.register_source",
      new_callable=AsyncMock,
      return_value=mock_result,
    ) as mock_register:
      await handle_register_source(arguments)

      mock_register.assert_called_once_with(
        group_id="org.springframework",
        artifact_id="spring-core",
        version="5.3.21",
        source_uri="file:///path/to/spring-core-5.3.21-sources.jar",
        auto_index=True,  # Default value
        git_ref=None,  # Default value
      )

  @pytest.mark.asyncio
  async def test_handle_register_source_exception(self, valid_arguments: Dict[str, Any]) -> None:
    """Test MCP tool handler with exception."""
    with patch(
      "src.tools.register_source.register_source",
      new_callable=AsyncMock,
      side_effect=Exception("Unexpected error"),
    ):
      result = await handle_register_source(valid_arguments)

      assert len(result) == 1
      assert result[0].type == "text"

      response_data = json.loads(result[0].text)
      assert response_data["status"] == "internal_error"
      assert "Unexpected error" in response_data["message"]


class TestRegisterSourceExceptionClasses:
  """Test cases for custom exception classes."""

  def test_register_source_error(self) -> None:
    """Test RegisterSourceError base class."""
    error = RegisterSourceError("Test error")
    assert str(error) == "Test error"
    assert isinstance(error, Exception)

  def test_resource_not_found_error(self) -> None:
    """Test ResourceNotFoundError."""
    error = ResourceNotFoundError("File not found")
    assert str(error) == "File not found"
    assert isinstance(error, RegisterSourceError)

  def test_download_failed_error(self) -> None:
    """Test DownloadFailedError."""
    error = DownloadFailedError("Download failed")
    assert str(error) == "Download failed"
    assert isinstance(error, RegisterSourceError)

  def test_invalid_source_error(self) -> None:
    """Test InvalidSourceError."""
    error = InvalidSourceError("Invalid source")
    assert str(error) == "Invalid source"
    assert isinstance(error, RegisterSourceError)

  def test_unsupported_source_type_error(self) -> None:
    """Test UnsupportedSourceTypeError."""
    error = UnsupportedSourceTypeError("Unsupported type")
    assert str(error) == "Unsupported type"
    assert isinstance(error, RegisterSourceError)
