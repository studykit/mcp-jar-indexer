"""Source URI processing and handling for JAR Indexer MCP Server."""

import shutil
from pathlib import Path
from typing import Any, Dict, Literal, Optional, Tuple, TypedDict
from urllib.parse import ParseResult
from urllib.parse import urlparse
import requests
from .storage import StorageManager


# TypedDict definitions for better type safety
class GitProcessResult(TypedDict, total=False):
  status: str
  source_type: str
  git_url: str
  git_ref: str
  bare_repo_path: str
  worktree_path: str
  processing_method: str
  is_ssh: bool
  host: str
  repo_path: str


class ProcessResult(TypedDict, total=False):
  status: str
  source_type: str
  source_location: str
  processing_method: str
  download_url: str
  git_url: str
  git_ref: str
  bare_repo_path: str
  worktree_path: str
  is_ssh: bool
  host: str
  repo_path: str


class SourceProcessor:
  """Processes different types of source URIs for JAR indexer."""

  def __init__(self, storage_manager: StorageManager):
    """Initialize source processor.

    Args:
        storage_manager: Storage manager instance for path management
    """
    self.storage = storage_manager

  def parse_uri(
    self, source_uri: str
  ) -> Tuple[Literal["file", "http", "git"], Dict[str, Any]]:
    """Parse and classify source URI.

    Args:
        source_uri: Source URI to parse

    Returns:
        Tuple of (uri_type, parsed_info)

    Raises:
        ValueError: If URI format is invalid or unsupported
    """
    if not source_uri:
      raise ValueError("Source URI cannot be empty")

    # Handle SSH Git format: git@host:user/repo
    if source_uri.startswith("git@"):
      return self._parse_ssh_git_uri(source_uri)

    parsed = urlparse(source_uri)

    if parsed.scheme == "file":
      return self._parse_file_uri(parsed)
    elif parsed.scheme == "https" or parsed.scheme == "http":
      # Determine type based on URI suffix
      return self._parse_https_uri(parsed)
    else:
      raise ValueError(f"Unsupported URI scheme: {parsed.scheme}")

  def _parse_file_uri(
    self, parsed: ParseResult
  ) -> Tuple[Literal["file"], Dict[str, Any]]:
    """Parse file:// URI."""
    file_path = Path(parsed.path)

    if not file_path.exists():
      raise ValueError(f"File or directory does not exist: {file_path}")

    if file_path.is_file():
      if file_path.suffix.lower() == ".jar":
        return "file", {"type": "jar", "path": file_path, "is_local": True}
      else:
        raise ValueError(f"Unsupported file type: {file_path.suffix}")
    elif file_path.is_dir():
      return "file", {"type": "directory", "path": file_path, "is_local": True}
    else:
      raise ValueError(f"Path is neither file nor directory: {file_path}")

  def _parse_https_uri(
    self, parsed: ParseResult
  ) -> Tuple[Literal["http", "git"], Dict[str, Any]]:
    """Parse https:// or http:// URI based on suffix."""
    url = parsed.geturl()

    # Check if it's a Git repository (.git suffix)
    if url.lower().endswith(".git"):
      return "git", {"type": "repository", "url": url, "is_local": False}
    # Check if it's a JAR file (.jar suffix)
    elif url.lower().endswith(".jar"):
      return "http", {"type": "jar", "url": url, "is_local": False}
    else:
      raise ValueError(
        "HTTPS/HTTP URIs must end with .jar (JAR file) or .git (Git repository)"
      )

  def _parse_ssh_git_uri(
    self, source_uri: str
  ) -> Tuple[Literal["git"], Dict[str, Any]]:
    """Parse SSH Git URI format: git@host:user/repo"""
    if not source_uri.startswith("git@"):
      raise ValueError("SSH Git URI must start with 'git@'")

    # Extract host and repository path
    # Format: git@github.com:spring-projects/spring-framework
    try:
      at_split = source_uri.split("@", 1)
      if len(at_split) != 2:
        raise ValueError("Invalid SSH Git URI format")

      host_repo = at_split[1]  # github.com:spring-projects/spring-framework
      if ":" not in host_repo:
        raise ValueError("Invalid SSH Git URI format: missing repository path")

      host, repo_path = host_repo.split(":", 1)

      # Convert to standard Git URL format for internal processing
      git_url = f"git@{host}:{repo_path}"

      return "git", {
        "type": "repository",
        "url": git_url,
        "host": host,
        "repo_path": repo_path,
        "is_local": False,
        "is_ssh": True,
      }
    except Exception:
      raise ValueError(f"Invalid SSH Git URI format: {source_uri}")

  def validate_uri(self, source_uri: str) -> bool:
    """Validate if URI is supported and accessible.

    Args:
        source_uri: Source URI to validate

    Returns:
        True if URI is valid and accessible
    """
    try:
      uri_type, parsed_info = self.parse_uri(source_uri)

      if uri_type == "file":
        # File URIs are validated during parsing
        return True
      elif uri_type == "http":
        # Check if remote JAR is accessible
        return self._check_http_accessibility(parsed_info["url"])
      elif uri_type == "git":
        # For now, assume git URIs are valid
        # More sophisticated validation could be added later
        return True

    except ValueError:
      return False

    return False

  def _check_http_accessibility(self, url: str) -> bool:
    """Check if HTTP/HTTPS URL is accessible."""
    try:
      response = requests.head(url, timeout=10)
      return response.status_code == 200
    except requests.RequestException:
      return False

  def process_source(
    self,
    group_id: str,
    artifact_id: str,
    version: str,
    source_uri: str,
    git_ref: Optional[str] = None,
  ) -> ProcessResult:
    """Process source URI and prepare it for indexing.

    Args:
        group_id: Maven group ID
        artifact_id: Maven artifact ID
        version: Maven version
        source_uri: Source URI to process
        git_ref: Git reference (branch/tag/commit) for Git repositories

    Returns:
        Processing result with status and paths

    Raises:
        ValueError: If processing fails
    """
    uri_type, parsed_info = self.parse_uri(source_uri)

    if uri_type == "file":
      return self._process_file_source(group_id, artifact_id, version, parsed_info)
    elif uri_type == "http":
      return self._process_http_source(group_id, artifact_id, version, parsed_info)
    elif uri_type == "git":
      if not git_ref:
        raise ValueError("git_ref is required for Git repository sources")
      return self._process_git_source(
        group_id, artifact_id, version, parsed_info, git_ref
      )
    else:
      raise ValueError(f"Unsupported source type: {uri_type}")

  def _process_file_source(
    self, group_id: str, artifact_id: str, version: str, parsed_info: Dict[str, Any]
  ) -> ProcessResult:
    """Process local file source."""
    source_path = parsed_info["path"]

    if parsed_info["type"] == "jar":
      # Copy JAR to source-jar directory
      target_dir = self.storage.get_source_jar_path(group_id, artifact_id, version)
      target_dir.mkdir(parents=True, exist_ok=True)

      target_file = target_dir / f"{artifact_id}-{version}-sources.jar"
      shutil.copy2(source_path, target_file)

      return {
        "status": "success",
        "source_type": "jar",
        "source_location": str(target_file),
        "processing_method": "copy",
      }

    elif parsed_info["type"] == "directory":
      # Create symbolic link or copy directory to code directory
      target_dir = self.storage.get_code_path(group_id, artifact_id, version)
      target_dir.parent.mkdir(parents=True, exist_ok=True)

      # Try to create symbolic link first, fallback to copy
      try:
        if target_dir.exists():
          if target_dir.is_symlink():
            target_dir.unlink()
          else:
            shutil.rmtree(target_dir)

        target_dir.symlink_to(source_path)
        processing_method = "symlink"
      except OSError:
        # Fallback to copy if symlink fails
        shutil.copytree(source_path, target_dir, dirs_exist_ok=True)
        processing_method = "copy"

      return {
        "status": "success",
        "source_type": "directory",
        "source_location": str(target_dir),
        "processing_method": processing_method,
      }
    else:
      raise ValueError(f"Unsupported parsed_info type: {parsed_info['type']}")

  def _process_http_source(
    self, group_id: str, artifact_id: str, version: str, parsed_info: Dict[str, Any]
  ) -> ProcessResult:
    """Process remote HTTP source."""
    url = parsed_info["url"]

    # Download JAR to source-jar directory
    target_dir = self.storage.get_source_jar_path(group_id, artifact_id, version)
    target_dir.mkdir(parents=True, exist_ok=True)

    target_file = target_dir / f"{artifact_id}-{version}-sources.jar"

    try:
      response = requests.get(url, stream=True, timeout=30)
      response.raise_for_status()

      with open(target_file, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
          f.write(chunk)

      return {
        "status": "success",
        "source_type": "jar",
        "source_location": str(target_file),
        "processing_method": "download",
        "download_url": url,
      }

    except requests.RequestException as e:
      raise ValueError(f"Failed to download JAR from {url}: {str(e)}")

  def _process_git_source(
    self,
    group_id: str,
    artifact_id: str,
    version: str,
    parsed_info: Dict[str, Any],
    git_ref: str,
  ) -> ProcessResult:
    """Process Git repository source.

    Note: This method prepares the parameters for git_handler.
    The actual Git operations should be handled by GitHandler.
    """
    git_url = parsed_info["url"]

    # Prepare paths for Git operations
    bare_repo_path = self.storage.get_git_bare_path(group_id, artifact_id)
    worktree_path = self.storage.get_code_path(group_id, artifact_id, version)

    result: ProcessResult = {
      "status": "prepared",
      "source_type": "git",
      "git_url": git_url,
      "git_ref": git_ref,
      "bare_repo_path": str(bare_repo_path),
      "worktree_path": str(worktree_path),
      "processing_method": "git_clone_worktree",
    }

    # Add SSH-specific information if applicable
    if parsed_info.get("is_ssh", False):
      result.update(
        {
          "is_ssh": True,
          "host": parsed_info["host"],
          "repo_path": parsed_info["repo_path"],
        }
      )

    return result

  def cleanup_failed_processing(
    self, group_id: str, artifact_id: str, version: str, source_type: str
  ) -> None:
    """Clean up artifacts from failed processing.

    Args:
        group_id: Maven group ID
        artifact_id: Maven artifact ID
        version: Maven version
        source_type: Type of source that failed processing
    """
    if source_type in ["jar", "http"]:
      # Clean up source-jar directory
      target_dir = self.storage.get_source_jar_path(group_id, artifact_id, version)
      if target_dir.exists():
        shutil.rmtree(target_dir)

    elif source_type in ["directory", "file", "git"]:
      # Clean up code directory
      target_dir = self.storage.get_code_path(group_id, artifact_id, version)
      if target_dir.exists():
        if target_dir.is_symlink():
          target_dir.unlink()
        else:
          shutil.rmtree(target_dir)
