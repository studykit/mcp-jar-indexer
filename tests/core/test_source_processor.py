# pyright: reportTypedDictNotRequiredAccess=false
"""Tests for source_processor module."""


import shutil
import tempfile
from pathlib import Path
from typing import Generator
from unittest.mock import Mock, patch, mock_open
import pytest
import requests

from src.core.source_processor import SourceProcessor
from src.core.storage import StorageManager


class TestSourceProcessor:
    """Test suite for SourceProcessor class."""
    
    @pytest.fixture
    def temp_dir(self) -> Generator[Path, None, None]:
        """Create a temporary directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def storage_manager(self, temp_dir: Path) -> StorageManager:
        """Create a storage manager with temporary directory."""
        return StorageManager(str(temp_dir))
    
    @pytest.fixture
    def source_processor(self, storage_manager: StorageManager) -> SourceProcessor:
        """Create a source processor instance."""
        return SourceProcessor(storage_manager)
    
    @pytest.fixture
    def sample_jar_file(self, temp_dir: Path) -> Path:
        """Create a sample JAR file for testing."""
        jar_path = temp_dir / "sample.jar"
        jar_path.write_text("fake jar content")
        return jar_path
    
    @pytest.fixture
    def sample_directory(self, temp_dir: Path) -> Path:
        """Create a sample directory for testing."""
        dir_path = temp_dir / "sample_project"
        dir_path.mkdir()
        (dir_path / "src").mkdir()
        (dir_path / "src" / "Main.java").write_text("public class Main {}")
        return dir_path
    
    def test_init(self, storage_manager: StorageManager) -> None:
        """Test SourceProcessor initialization."""
        processor = SourceProcessor(storage_manager)
        assert processor.storage == storage_manager
    
    def test_parse_file_jar_uri(self, source_processor: SourceProcessor, sample_jar_file: Path) -> None:
        """Test parsing file:// URI for JAR file."""
        uri = f"file://{sample_jar_file}"
        uri_type, parsed_info = source_processor.parse_uri(uri)
        
        assert uri_type == "file"
        assert parsed_info["type"] == "jar"
        assert parsed_info["path"] == sample_jar_file
        assert parsed_info["is_local"] is True
    
    def test_parse_file_directory_uri(self, source_processor: SourceProcessor, sample_directory: Path) -> None:
        """Test parsing file:// URI for directory."""
        uri = f"file://{sample_directory}"
        uri_type, parsed_info = source_processor.parse_uri(uri)
        
        assert uri_type == "file"
        assert parsed_info["type"] == "directory"
        assert parsed_info["path"] == sample_directory
        assert parsed_info["is_local"] is True
    
    def test_parse_https_jar_uri(self, source_processor: SourceProcessor) -> None:
        """Test parsing https:// URI for JAR file."""
        uri = "https://example.com/library-1.0.0-sources.jar"
        uri_type, parsed_info = source_processor.parse_uri(uri)
        
        assert uri_type == "http"
        assert parsed_info["type"] == "jar"
        assert parsed_info["url"] == uri
        assert parsed_info["is_local"] is False
    
    def test_parse_https_git_uri(self, source_processor: SourceProcessor) -> None:
        """Test parsing https:// URI for Git repository."""
        uri = "https://github.com/user/repo.git"
        uri_type, parsed_info = source_processor.parse_uri(uri)
        
        assert uri_type == "git"
        assert parsed_info["type"] == "repository"
        assert parsed_info["url"] == uri
        assert parsed_info["is_local"] is False
    
    def test_parse_ssh_git_uri(self, source_processor: SourceProcessor) -> None:
        """Test parsing SSH Git URI."""
        uri = "git@github.com:user/repo"
        uri_type, parsed_info = source_processor.parse_uri(uri)
        
        assert uri_type == "git"
        assert parsed_info["type"] == "repository"
        assert parsed_info["url"] == "git@github.com:user/repo"
        assert parsed_info["host"] == "github.com"
        assert parsed_info["repo_path"] == "user/repo"
        assert parsed_info["is_local"] is False
        assert parsed_info["is_ssh"] is True
    
    def test_parse_empty_uri(self, source_processor: SourceProcessor) -> None:
        """Test parsing empty URI raises ValueError."""
        with pytest.raises(ValueError, match="Source URI cannot be empty"):
            source_processor.parse_uri("")
    
    def test_parse_unsupported_scheme(self, source_processor: SourceProcessor) -> None:
        """Test parsing unsupported URI scheme raises ValueError."""
        with pytest.raises(ValueError, match="Unsupported URI scheme"):
            source_processor.parse_uri("ftp://example.com/file.jar")
    
    def test_parse_nonexistent_file(self, source_processor: SourceProcessor) -> None:
        """Test parsing non-existent file raises ValueError."""
        with pytest.raises(ValueError, match="File or directory does not exist"):
            source_processor.parse_uri("file:///nonexistent/path")
    
    def test_parse_unsupported_file_type(self, source_processor: SourceProcessor, temp_dir: Path) -> None:
        """Test parsing unsupported file type raises ValueError."""
        txt_file = temp_dir / "test.txt"
        txt_file.write_text("test content")
        
        with pytest.raises(ValueError, match="Unsupported file type"):
            source_processor.parse_uri(f"file://{txt_file}")
    
    def test_parse_https_uri_invalid_suffix(self, source_processor: SourceProcessor) -> None:
        """Test parsing HTTPS URI with invalid suffix raises ValueError."""
        with pytest.raises(ValueError, match=r"HTTPS/HTTP URIs must end with \.jar.*or \.git"):
            source_processor.parse_uri("https://example.com/file.txt")
    
    @patch('src.core.source_processor.requests.head')
    def test_validate_http_uri_accessible(self, mock_head: Mock, source_processor: SourceProcessor) -> None:
        """Test validating accessible HTTP URI."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_head.return_value = mock_response
        
        uri = "https://example.com/library-sources.jar"
        assert source_processor.validate_uri(uri) is True
    
    @patch('src.core.source_processor.requests.head')
    def test_validate_http_uri_not_accessible(self, mock_head: Mock, source_processor: SourceProcessor) -> None:
        """Test validating inaccessible HTTP URI."""
        mock_head.side_effect = requests.RequestException()
        
        uri = "https://example.com/library-sources.jar"
        assert source_processor.validate_uri(uri) is False
    
    def test_validate_file_uri(self, source_processor: SourceProcessor, sample_jar_file: Path) -> None:
        """Test validating file URI."""
        uri = f"file://{sample_jar_file}"
        assert source_processor.validate_uri(uri) is True
    
    def test_validate_git_https_uri(self, source_processor: SourceProcessor) -> None:
        """Test validating HTTPS Git URI."""
        uri = "https://github.com/user/repo.git"
        assert source_processor.validate_uri(uri) is True
    
    def test_validate_git_ssh_uri(self, source_processor: SourceProcessor) -> None:
        """Test validating SSH Git URI."""
        uri = "git@github.com:user/repo"
        assert source_processor.validate_uri(uri) is True
    
    def test_validate_invalid_uri(self, source_processor: SourceProcessor) -> None:
        """Test validating invalid URI."""
        assert source_processor.validate_uri("invalid://uri") is False
    
    def test_process_file_jar_source(self, source_processor: SourceProcessor, sample_jar_file: Path) -> None:
        """Test processing local JAR file source."""
        result = source_processor.process_source(
            "com.example", "library", "1.0.0", f"file://{sample_jar_file}"
        )
        
        assert result["status"] == "success"
        assert result["source_type"] == "jar"
        assert result["processing_method"] == "copy"
        assert "source_location" in result
        
        # Verify the JAR was copied
        target_path = Path(result["source_location"])
        assert target_path.exists()
        assert target_path.read_text() == "fake jar content"
    
    def test_process_file_directory_source(self, source_processor: SourceProcessor, sample_directory: Path) -> None:
        """Test processing local directory source."""
        result = source_processor.process_source(
            "com.example", "library", "1.0.0", f"file://{sample_directory}"
        )
        
        assert result["status"] == "success"
        assert result["source_type"] == "directory"
        assert result["processing_method"] in ["symlink", "copy"]
        assert "source_location" in result
        
        # Verify the directory was linked or copied
        target_path = Path(result["source_location"])
        assert target_path.exists()
        assert (target_path / "src" / "Main.java").exists()
    
    @patch('src.core.source_processor.requests.get')
    def test_process_http_source(self, mock_get: Mock, source_processor: SourceProcessor) -> None:
        """Test processing HTTP JAR source."""
        mock_response = Mock()
        mock_response.iter_content.return_value = [b"jar content chunk"]
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        with patch("builtins.open", mock_open()):
            result = source_processor.process_source(
                "com.example", "library", "1.0.0", 
                "https://example.com/library-sources.jar"
            )
        
        assert result["status"] == "success"
        assert result["source_type"] == "jar"
        assert result["processing_method"] == "download"
        assert result["download_url"] == "https://example.com/library-sources.jar"
    
    @patch('src.core.source_processor.requests.get')
    def test_process_http_source_download_failure(self, mock_get: Mock, source_processor: SourceProcessor) -> None:
        """Test processing HTTP source with download failure."""
        mock_get.side_effect = requests.RequestException("Network error")
        
        with pytest.raises(ValueError, match="Failed to download JAR"):
            source_processor.process_source(
                "com.example", "library", "1.0.0",
                "https://example.com/library-sources.jar"
            )
    
    def test_process_git_https_source(self, source_processor: SourceProcessor) -> None:
        """Test processing HTTPS Git repository source."""
        result = source_processor.process_source(
            "com.example", "library", "1.0.0",
            "https://github.com/user/repo.git",
            git_ref="v1.0.0"
        )
        
        assert result["status"] == "prepared"
        assert result["source_type"] == "git"
        assert result["git_url"] == "https://github.com/user/repo.git"
        assert result["git_ref"] == "v1.0.0"
        assert result["processing_method"] == "git_clone_worktree"
        assert "bare_repo_path" in result
        assert "worktree_path" in result
        assert "is_ssh" not in result  # HTTPS Git should not have SSH info
    
    def test_process_git_ssh_source(self, source_processor: SourceProcessor) -> None:
        """Test processing SSH Git repository source."""
        result = source_processor.process_source(
            "com.example", "library", "1.0.0",
            "git@github.com:user/repo",
            git_ref="v1.0.0"
        )
        
        assert result["status"] == "prepared"
        assert result["source_type"] == "git"
        assert result["git_url"] == "git@github.com:user/repo"
        assert result["git_ref"] == "v1.0.0"
        assert result["processing_method"] == "git_clone_worktree"
        assert "bare_repo_path" in result
        assert "worktree_path" in result
        assert result["is_ssh"] is True
        assert result["host"] == "github.com"
        assert result["repo_path"] == "user/repo"
    
    def test_process_git_source_missing_ref(self, source_processor: SourceProcessor) -> None:
        """Test processing Git source without git_ref raises ValueError."""
        with pytest.raises(ValueError, match="git_ref is required"):
            source_processor.process_source(
                "com.example", "library", "1.0.0",
                "https://github.com/user/repo.git"
            )
    
    def test_parse_ssh_git_uri_invalid_format(self, source_processor: SourceProcessor) -> None:
        """Test parsing invalid SSH Git URI formats."""
        invalid_uris = [
            "git@invalid-format",  # No colon
            "git@",  # Empty after @
            "git@github.com",  # Missing colon and repo path
        ]
        
        for uri in invalid_uris:
            with pytest.raises(ValueError, match="Invalid SSH Git URI format"):
                source_processor.parse_uri(uri)
    
    def test_parse_invalid_git_like_uri(self, source_processor: SourceProcessor) -> None:
        """Test parsing git-like URI without @ raises unsupported scheme error."""
        with pytest.raises(ValueError, match="Unsupported URI scheme"):
            source_processor.parse_uri("gitgithub.com:user/repo")
    
    def test_process_git_ssh_source_missing_ref(self, source_processor: SourceProcessor) -> None:
        """Test processing SSH Git source without git_ref raises ValueError."""
        with pytest.raises(ValueError, match="git_ref is required"):
            source_processor.process_source(
                "com.example", "library", "1.0.0",
                "git@github.com:user/repo"
            )
    
    def test_cleanup_failed_processing_jar(self, source_processor: SourceProcessor, temp_dir: Path) -> None:
        """Test cleanup for failed JAR processing."""
        # Create some directories to clean up
        target_dir = source_processor.storage.get_source_jar_path(
            "com.example", "library", "1.0.0"
        )
        target_dir.mkdir(parents=True)
        (target_dir / "test.jar").write_text("test")
        
        source_processor.cleanup_failed_processing(
            "com.example", "library", "1.0.0", "jar"
        )
        
        assert not target_dir.exists()
    
    def test_cleanup_failed_processing_directory(self, source_processor: SourceProcessor, temp_dir: Path) -> None:
        """Test cleanup for failed directory processing."""
        # Create code directory to clean up
        target_dir = source_processor.storage.get_code_path(
            "com.example", "library", "1.0.0"
        )
        target_dir.mkdir(parents=True)
        (target_dir / "src").mkdir()
        
        source_processor.cleanup_failed_processing(
            "com.example", "library", "1.0.0", "directory"
        )
        
        assert not target_dir.exists()
    
    def test_cleanup_failed_processing_symlink(self, source_processor: SourceProcessor, sample_directory: Path) -> None:
        """Test cleanup for failed symlink processing."""
        target_dir = source_processor.storage.get_code_path(
            "com.example", "library", "1.0.0"
        )
        target_dir.parent.mkdir(parents=True)
        
        # Create a symlink
        target_dir.symlink_to(sample_directory)
        assert target_dir.is_symlink()
        
        source_processor.cleanup_failed_processing(
            "com.example", "library", "1.0.0", "git"
        )
        
        assert not target_dir.exists()
        # Original directory should still exist
        assert sample_directory.exists()