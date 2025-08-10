"""Tests for register_source MCP tool."""

import asyncio
import json
import shutil
import tempfile
import zipfile
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.core.git_handler import (
  GitAuthenticationError,
  GitCloneFailedError,
  GitRefNotFoundError,
)
# Note: SourceType enum not available, using strings directly
from src.tools.register_source import (
  DownloadFailedError,
  InvalidSourceError,
  REGISTER_SOURCE_TOOL,
  RegisterSourceError,
  ResourceNotFoundError,
  UnsupportedSourceTypeError,
  handle_register_source,
  register_source,
)


class TestRegisterSource:
  """Test cases for register_source function."""

  @pytest.fixture
  def temp_dir(self):
    """Create temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmp_dir:
      yield Path(tmp_dir)

  @pytest.fixture
  def mock_jar_file(self, temp_dir):
    """Create a mock JAR file for testing."""
    jar_path = temp_dir / "test-sources.jar"
    # Create a simple ZIP file (JAR is basically a ZIP)
    with zipfile.ZipFile(jar_path, "w") as zf:
      zf.writestr("META-INF/MANIFEST.MF", "Manifest-Version: 1.0\n")
      zf.writestr("com/example/Test.java", "public class Test {}")
    return jar_path

  @pytest.fixture
  def mock_source_dir(self, temp_dir):
    """Create a mock source directory for testing."""
    source_dir = temp_dir / "sources"
    source_dir.mkdir()
    (source_dir / "com").mkdir()
    (source_dir / "com" / "example").mkdir(parents=True)
    (source_dir / "com" / "example" / "Test.java").write_text("public class Test {}")
    return source_dir

  def test_register_source_tool_schema(self):
    """Test that REGISTER_SOURCE_TOOL has correct schema."""
    assert REGISTER_SOURCE_TOOL.name == "register_source"
    assert REGISTER_SOURCE_TOOL.description is not None
    
    schema = REGISTER_SOURCE_TOOL.inputSchema
    assert schema["type"] == "object"
    assert "group_id" in schema["properties"]
    assert "artifact_id" in schema["properties"] 
    assert "version" in schema["properties"]
    assert "source_uri" in schema["properties"]
    assert "auto_index" in schema["properties"]
    assert "git_ref" in schema["properties"]
    
    required = schema["required"]
    assert "group_id" in required
    assert "artifact_id" in required
    assert "version" in required
    assert "source_uri" in required

  @pytest.mark.asyncio
  async def test_register_source_validation_error(self):
    """Test register_source with invalid parameters."""
    with patch("src.tools.register_source.validate_maven_coordinates") as mock_validate:
      mock_validate.side_effect = ValueError("Invalid group_id")
      
      result = await register_source(
        group_id="invalid..group",
        artifact_id="test",
        version="1.0.0",
        source_uri="file:///test.jar"
      )
      
      assert result["status"] == "internal_error"
      assert "Invalid group_id" in result["message"]

  @pytest.mark.asyncio
  async def test_register_source_storage_error(self):
    """Test register_source with storage validation error."""
    with patch("src.tools.register_source.validate_maven_coordinates"), \
         patch("src.tools.register_source.validate_uri_format"), \
         patch("src.tools.register_source.StorageManager") as mock_storage:
      
      mock_storage_instance = Mock()
      mock_storage_instance.validate_directory_permissions.return_value = False
      mock_storage.return_value = mock_storage_instance
      
      result = await register_source(
        group_id="com.example",
        artifact_id="test",
        version="1.0.0",
        source_uri="file:///test.jar"
      )
      
      assert result["status"] == "internal_error"
      assert "Storage directories are not accessible" in result["message"]

  @pytest.mark.asyncio
  async def test_register_source_local_jar_success(self, mock_jar_file, temp_dir):
    """Test successful registration of local JAR file."""
    with patch("src.tools.register_source.validate_maven_coordinates"), \
         patch("src.tools.register_source.validate_uri_format"), \
         patch("src.tools.register_source.StorageManager") as mock_storage, \
         patch("src.tools.register_source.SourceProcessor") as mock_processor:
      
      # Setup mocks
      mock_storage_instance = Mock()
      mock_storage_instance.validate_directory_permissions.return_value = True
      target_dir = temp_dir / "target"
      target_dir.mkdir()
      mock_storage_instance.get_source_jar_path.return_value = target_dir
      mock_storage.return_value = mock_storage_instance
      
      mock_processor_instance = Mock()
      mock_processor_instance.parse_uri.return_value = ("file", {
        "type": "jar",
        "path": str(mock_jar_file)
      })
      mock_processor.return_value = mock_processor_instance
      
      with patch("src.tools.register_source.validate_jar_file", return_value=True):
        result = await register_source(
          group_id="com.example",
          artifact_id="test",
          version="1.0.0",
          source_uri=f"file://{mock_jar_file}",
          auto_index=False
        )
      
      assert result["group_id"] == "com.example"
      assert result["artifact_id"] == "test"
      assert result["version"] == "1.0.0"
      assert result["status"] == "registered_only"
      assert not result["indexed"]

  @pytest.mark.asyncio
  async def test_register_source_local_jar_not_found(self):
    """Test registration of non-existent local JAR file."""
    with patch("src.tools.register_source.validate_maven_coordinates"), \
         patch("src.tools.register_source.validate_uri_format"), \
         patch("src.tools.register_source.StorageManager") as mock_storage, \
         patch("src.tools.register_source.SourceProcessor") as mock_processor:
      
      # Setup mocks
      mock_storage_instance = Mock()
      mock_storage_instance.validate_directory_permissions.return_value = True
      mock_storage.return_value = mock_storage_instance
      
      mock_processor_instance = Mock()
      mock_processor_instance.parse_uri.return_value = ("file", {"type": "jar", "path": "/non/existent/file.jar"})
      mock_processor.return_value = mock_processor_instance
      
      result = await register_source(
        group_id="com.example",
        artifact_id="test",
        version="1.0.0",
        source_uri="file:///non/existent/file.jar"
      )
      
      assert result["status"] == "resource_not_found"
      assert "Local JAR file not found" in result["message"]

  @pytest.mark.asyncio
  async def test_register_source_remote_jar_success(self, temp_dir):
    """Test successful registration of remote JAR file."""
    with patch("src.tools.register_source.validate_maven_coordinates"), \
         patch("src.tools.register_source.validate_uri_format"), \
         patch("src.tools.register_source.StorageManager") as mock_storage, \
         patch("src.tools.register_source.SourceProcessor") as mock_processor, \
         patch("src.tools.register_source.download_file") as mock_download, \
         patch("src.tools.register_source.is_jar_file", return_value=True):
      
      # Setup mocks
      mock_storage_instance = Mock()
      mock_storage_instance.validate_directory_permissions.return_value = True
      target_dir = temp_dir / "target"
      target_dir.mkdir()
      mock_storage_instance.get_source_jar_path.return_value = target_dir
      mock_storage.return_value = mock_storage_instance
      
      mock_processor_instance = Mock()
      mock_processor_instance.parse_uri.return_value = ("file", {"type": "jar", "path": "/non/existent/file.jar"})
      mock_processor_instance.parse_uri.return_value = {
        "scheme": "https",
        "path": "/test.jar"
      }
      mock_processor.return_value = mock_processor_instance
      
      result = await register_source(
        group_id="com.example",
        artifact_id="test",
        version="1.0.0",
        source_uri="https://example.com/test.jar",
        auto_index=False
      )
      
      assert result["status"] == "registered_only"
      mock_download.assert_called_once()

  @pytest.mark.asyncio
  async def test_register_source_remote_jar_download_failed(self, temp_dir):
    """Test registration of remote JAR file with download failure."""
    with patch("src.tools.register_source.validate_maven_coordinates"), \
         patch("src.tools.register_source.validate_uri_format"), \
         patch("src.tools.register_source.StorageManager") as mock_storage, \
         patch("src.tools.register_source.SourceProcessor") as mock_processor, \
         patch("src.tools.register_source.download_file") as mock_download:
      
      # Setup mocks
      mock_storage_instance = Mock()
      mock_storage_instance.validate_directory_permissions.return_value = True
      target_dir = temp_dir / "target"
      target_dir.mkdir()
      mock_storage_instance.get_source_jar_path.return_value = target_dir
      mock_storage.return_value = mock_storage_instance
      
      mock_processor_instance = Mock()
      mock_processor_instance.parse_uri.return_value = ("file", {"type": "jar", "path": "/non/existent/file.jar"})
      mock_processor_instance.parse_uri.return_value = {
        "scheme": "https",
        "path": "/test.jar"
      }
      mock_processor.return_value = mock_processor_instance
      
      mock_download.side_effect = Exception("Connection failed")
      
      result = await register_source(
        group_id="com.example",
        artifact_id="test",
        version="1.0.0",
        source_uri="https://example.com/test.jar"
      )
      
      assert result["status"] == "download_failed"
      assert "Failed to download JAR file" in result["message"]

  @pytest.mark.asyncio
  async def test_register_source_local_directory_success(self, mock_source_dir, temp_dir):
    """Test successful registration of local directory."""
    with patch("src.tools.register_source.validate_maven_coordinates"), \
         patch("src.tools.register_source.validate_uri_format"), \
         patch("src.tools.register_source.StorageManager") as mock_storage, \
         patch("src.tools.register_source.SourceProcessor") as mock_processor, \
         patch("src.tools.register_source.GitHandler") as mock_git_handler, \
         patch("src.tools.register_source.copy_or_link_directory") as mock_copy:
      
      # Setup mocks
      mock_storage_instance = Mock()
      mock_storage_instance.validate_directory_permissions.return_value = True
      target_dir = temp_dir / "target"
      target_dir.mkdir()
      mock_storage_instance.get_code_path.return_value = target_dir
      mock_storage.return_value = mock_storage_instance
      
      mock_processor_instance = Mock()
      mock_processor_instance.parse_uri.return_value = ("file", {"type": "directory", "path": "/non/existent/directory"})
      mock_processor_instance.parse_uri.return_value = {
        "scheme": "file",
        "path": str(mock_source_dir)
      }
      mock_processor.return_value = mock_processor_instance
      
      mock_git_instance = Mock()
      mock_git_instance.is_git_repository.return_value = False
      mock_git_handler.return_value = mock_git_instance
      
      result = await register_source(
        group_id="com.example",
        artifact_id="test",
        version="1.0.0",
        source_uri=f"file://{mock_source_dir}",
        auto_index=False
      )
      
      assert result["status"] == "registered_only"
      mock_copy.assert_called_once()

  @pytest.mark.asyncio
  async def test_register_source_local_directory_not_found(self):
    """Test registration of non-existent local directory."""
    with patch("src.tools.register_source.validate_maven_coordinates"), \
         patch("src.tools.register_source.validate_uri_format"), \
         patch("src.tools.register_source.StorageManager") as mock_storage, \
         patch("src.tools.register_source.SourceProcessor") as mock_processor:
      
      # Setup mocks
      mock_storage_instance = Mock()
      mock_storage_instance.validate_directory_permissions.return_value = True
      mock_storage.return_value = mock_storage_instance
      
      mock_processor_instance = Mock()
      mock_processor_instance.parse_uri.return_value = ("file", {"type": "directory", "path": "/non/existent/directory"})
      mock_processor.return_value = mock_processor_instance
      
      result = await register_source(
        group_id="com.example",
        artifact_id="test",
        version="1.0.0",
        source_uri="file:///non/existent/directory"
      )
      
      assert result["status"] == "resource_not_found"
      assert "Local directory not found" in result["message"]

  @pytest.mark.asyncio
  async def test_register_source_git_repository_success(self, temp_dir):
    """Test successful registration of Git repository."""
    with patch("src.tools.register_source.validate_maven_coordinates"), \
         patch("src.tools.register_source.validate_uri_format"), \
         patch("src.tools.register_source.StorageManager") as mock_storage, \
         patch("src.tools.register_source.SourceProcessor") as mock_processor, \
         patch("src.tools.register_source.GitHandler") as mock_git_handler:
      
      # Setup mocks
      mock_storage_instance = Mock()
      mock_storage_instance.validate_directory_permissions.return_value = True
      bare_dir = temp_dir / "bare"
      code_dir = temp_dir / "code"
      mock_storage_instance.get_git_bare_path.return_value = bare_dir
      mock_storage_instance.get_code_path.return_value = code_dir
      mock_storage.return_value = mock_storage_instance
      
      mock_processor_instance = Mock()
      mock_processor_instance.parse_uri.return_value = ("git", {"url": "https://github.com/example/test.git"})
      mock_processor.return_value = mock_processor_instance
      
      mock_git_instance = Mock()
      mock_git_instance.create_bare_clone = AsyncMock()
      mock_git_instance.verify_git_ref.return_value = True
      mock_git_instance.create_worktree = Mock()
      mock_git_handler.return_value = mock_git_instance
      
      result = await register_source(
        group_id="com.example",
        artifact_id="test",
        version="1.0.0",
        source_uri="https://github.com/example/test.git",
        git_ref="v1.0.0",
        auto_index=False
      )
      
      assert result["status"] == "registered_only"
      mock_git_instance.create_bare_clone.assert_called_once()
      mock_git_instance.create_worktree.assert_called_once()

  @pytest.mark.asyncio
  async def test_register_source_git_repository_clone_failed(self):
    """Test Git repository registration with clone failure."""
    with patch("src.tools.register_source.validate_maven_coordinates"), \
         patch("src.tools.register_source.validate_uri_format"), \
         patch("src.tools.register_source.StorageManager") as mock_storage, \
         patch("src.tools.register_source.SourceProcessor") as mock_processor, \
         patch("src.tools.register_source.GitHandler") as mock_git_handler:
      
      # Setup mocks
      mock_storage_instance = Mock()
      mock_storage_instance.validate_directory_permissions.return_value = True
      mock_storage_instance.get_git_bare_path.return_value = Path("/tmp/bare")
      mock_storage.return_value = mock_storage_instance
      
      mock_processor_instance = Mock()
      mock_processor_instance.parse_uri.return_value = ("git", {"url": "https://github.com/example/test.git"})
      mock_processor.return_value = mock_processor_instance
      
      mock_git_instance = Mock()
      mock_git_instance.create_bare_clone = AsyncMock(side_effect=GitCloneFailedError("Clone failed"))
      mock_git_handler.return_value = mock_git_instance
      
      result = await register_source(
        group_id="com.example",
        artifact_id="test",
        version="1.0.0",
        source_uri="https://github.com/example/test.git",
        git_ref="v1.0.0"
      )
      
      assert result["status"] == "git_clone_failed"
      assert "Failed to clone Git repository" in result["message"]

  @pytest.mark.asyncio
  async def test_register_source_git_ref_not_found(self):
    """Test Git repository registration with invalid ref."""
    with patch("src.tools.register_source.validate_maven_coordinates"), \
         patch("src.tools.register_source.validate_uri_format"), \
         patch("src.tools.register_source.StorageManager") as mock_storage, \
         patch("src.tools.register_source.SourceProcessor") as mock_processor, \
         patch("src.tools.register_source.GitHandler") as mock_git_handler:
      
      # Setup mocks
      mock_storage_instance = Mock()
      mock_storage_instance.validate_directory_permissions.return_value = True
      bare_dir = Path("/tmp/bare")
      mock_storage_instance.get_git_bare_path.return_value = bare_dir
      mock_storage.return_value = mock_storage_instance
      
      mock_processor_instance = Mock()
      mock_processor_instance.parse_uri.return_value = ("git", {"url": "https://github.com/example/test.git"})
      mock_processor.return_value = mock_processor_instance
      
      mock_git_instance = Mock()
      mock_git_instance.create_bare_clone = AsyncMock()
      mock_git_instance.verify_git_ref.return_value = False
      mock_git_handler.return_value = mock_git_instance
      
      result = await register_source(
        group_id="com.example",
        artifact_id="test",
        version="1.0.0",
        source_uri="https://github.com/example/test.git",
        git_ref="invalid-ref"
      )
      
      assert result["status"] == "git_ref_not_found"
      assert "Git reference not found" in result["message"]

  @pytest.mark.asyncio
  async def test_register_source_git_auth_failed(self):
    """Test Git repository registration with authentication failure."""
    with patch("src.tools.register_source.validate_maven_coordinates"), \
         patch("src.tools.register_source.validate_uri_format"), \
         patch("src.tools.register_source.StorageManager") as mock_storage, \
         patch("src.tools.register_source.SourceProcessor") as mock_processor, \
         patch("src.tools.register_source.GitHandler") as mock_git_handler:
      
      # Setup mocks
      mock_storage_instance = Mock()
      mock_storage_instance.validate_directory_permissions.return_value = True
      mock_storage_instance.get_git_bare_path.return_value = Path("/tmp/bare")
      mock_storage.return_value = mock_storage_instance
      
      mock_processor_instance = Mock()
      mock_processor_instance.parse_uri.return_value = ("git", {"url": "https://github.com/example/test.git"})
      mock_processor.return_value = mock_processor_instance
      
      mock_git_instance = Mock()
      mock_git_instance.create_bare_clone = AsyncMock(side_effect=GitAuthenticationError("Auth failed"))
      mock_git_handler.return_value = mock_git_instance
      
      result = await register_source(
        group_id="com.example",
        artifact_id="test",
        version="1.0.0",
        source_uri="git@github.com:private/repo.git",
        git_ref="main"
      )
      
      assert result["status"] == "git_authentication_failed"
      assert "Git authentication failed" in result["message"]

  @pytest.mark.asyncio
  async def test_register_source_unsupported_type(self):
    """Test register_source with unsupported source type."""
    with patch("src.tools.register_source.validate_maven_coordinates"), \
         patch("src.tools.register_source.validate_uri_format"), \
         patch("src.tools.register_source.StorageManager") as mock_storage, \
         patch("src.tools.register_source.SourceProcessor") as mock_processor:
      
      # Setup mocks
      mock_storage_instance = Mock()
      mock_storage_instance.validate_directory_permissions.return_value = True
      mock_storage.return_value = mock_storage_instance
      
      mock_processor_instance = Mock()
      mock_processor_instance.parse_uri.return_value = ("unknown", {"type": "unknown"})
      mock_processor.return_value = mock_processor_instance
      
      result = await register_source(
        group_id="com.example",
        artifact_id="test",
        version="1.0.0",
        source_uri="unknown://example.com/test"
      )
      
      assert result["status"] == "unsupported_source_type"
      assert "Unsupported source type" in result["message"]

  @pytest.mark.asyncio
  async def test_handle_register_source_success(self):
    """Test handle_register_source function with successful call."""
    arguments = {
      "group_id": "com.example",
      "artifact_id": "test",
      "version": "1.0.0",
      "source_uri": "file:///test.jar",
      "auto_index": False
    }
    
    with patch("src.tools.register_source.register_source") as mock_register:
      mock_register.return_value = {
        "group_id": "com.example",
        "artifact_id": "test",
        "version": "1.0.0",
        "status": "registered_only",
        "indexed": False
      }
      
      result = await handle_register_source(arguments)
      
      assert len(result) == 1
      assert result[0].type == "text"
      response_data = json.loads(result[0].text)
      assert response_data["status"] == "registered_only"

  @pytest.mark.asyncio
  async def test_handle_register_source_error(self):
    """Test handle_register_source function with error."""
    arguments = {
      "group_id": "com.example",
      "artifact_id": "test",
      "version": "1.0.0",
      "source_uri": "file:///test.jar"
    }
    
    with patch("src.tools.register_source.register_source") as mock_register:
      mock_register.side_effect = Exception("Test error")
      
      result = await handle_register_source(arguments)
      
      assert len(result) == 1
      assert result[0].type == "text"
      response_data = json.loads(result[0].text)
      assert response_data["status"] == "internal_error"
      assert "Test error" in response_data["message"]


class TestRegisterSourceExceptions:
  """Test custom exception classes."""

  def test_register_source_error(self):
    """Test RegisterSourceError exception."""
    error = RegisterSourceError("Test error")
    assert str(error) == "Test error"
    assert isinstance(error, Exception)

  def test_resource_not_found_error(self):
    """Test ResourceNotFoundError exception."""
    error = ResourceNotFoundError("Resource not found")
    assert str(error) == "Resource not found"
    assert isinstance(error, RegisterSourceError)

  def test_download_failed_error(self):
    """Test DownloadFailedError exception."""
    error = DownloadFailedError("Download failed")
    assert str(error) == "Download failed"
    assert isinstance(error, RegisterSourceError)

  def test_invalid_source_error(self):
    """Test InvalidSourceError exception."""
    error = InvalidSourceError("Invalid source")
    assert str(error) == "Invalid source"
    assert isinstance(error, RegisterSourceError)

  def test_unsupported_source_type_error(self):
    """Test UnsupportedSourceTypeError exception."""
    error = UnsupportedSourceTypeError("Unsupported type")
    assert str(error) == "Unsupported type"
    assert isinstance(error, RegisterSourceError)