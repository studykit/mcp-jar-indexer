"""File utility functions for JAR indexer.

This module provides utility functions for file operations including
downloading files, validating JAR files, and handling file system operations.
"""

import os
import shutil
import zipfile
from pathlib import Path
from typing import Dict, Any, TypedDict
from urllib.parse import urlparse
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Import validation function
from .validation import validate_maven_coordinates


class FileInfo(TypedDict):
  """File metadata information"""

  name: str  # File name
  size: str  # File size (e.g., "1KB", "2.5MB")
  line_count: int  # Number of lines in text file


class RegisteredSourceInfo(TypedDict):
  """Registered artifact source information"""

  group_id: str  # Maven group ID
  artifact_id: str  # Maven artifact ID
  version: str  # Maven version
  source_uri: str  # Original source URI (for reference)
  git_ref: str | None  # Git reference (for Git sources)
  source_type: str  # "jar", "directory", "git"
  local_path: str  # Intermediate storage relative path (from base directory)


def download_file(
  url: str,
  target_path: Path,
  chunk_size: int = 8192,
  timeout: int = 30,
  max_retries: int = 3,
) -> Dict[str, Any]:
  """Download a file from URL to target path with retry logic.

  Args:
    url: URL to download from
    target_path: Local path to save the file
    chunk_size: Size of chunks to read/write in bytes
    timeout: Request timeout in seconds
    max_retries: Maximum number of retry attempts

  Returns:
    Dictionary containing download result information

  Raises:
    ValueError: If URL is invalid or target path is invalid
    requests.RequestException: If download fails after retries
    OSError: If file writing fails
  """
  if not url or not url.strip():
    raise ValueError("URL cannot be empty")

  # Validate URL format
  parsed = urlparse(url)
  if not parsed.scheme or not parsed.netloc:
    raise ValueError(f"Invalid URL format: {url}")

  if not target_path.parent.exists():
    raise ValueError(f"Target directory does not exist: {target_path.parent}")

  # Set up session with retry strategy
  session = requests.Session()
  retry_strategy = Retry(
    total=max_retries,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["HEAD", "GET", "OPTIONS"],
  )
  adapter = HTTPAdapter(max_retries=retry_strategy)
  session.mount("http://", adapter)
  session.mount("https://", adapter)

  try:
    response = session.get(url, stream=True, timeout=timeout)
    response.raise_for_status()

    # Get content length if available
    content_length = response.headers.get("Content-Length")
    total_size = int(content_length) if content_length else None

    downloaded_size = 0

    with open(target_path, "wb") as f:
      for chunk in response.iter_content(chunk_size=chunk_size):
        if chunk:  # Filter out keep-alive chunks
          f.write(chunk)
          downloaded_size += len(chunk)

    return {
      "status": "success",
      "url": url,
      "target_path": str(target_path),
      "downloaded_size": downloaded_size,
      "total_size": total_size,
      "content_type": response.headers.get("Content-Type", "unknown"),
    }

  except requests.RequestException as e:
    # Clean up partial download
    if target_path.exists():
      target_path.unlink()
    raise requests.RequestException(f"Failed to download {url}: {str(e)}") from e
  except OSError as e:
    # Clean up partial download
    if target_path.exists():
      target_path.unlink()
    raise OSError(f"Failed to write file {target_path}: {str(e)}") from e
  finally:
    session.close()


def validate_jar_file(jar_path: Path) -> Dict[str, Any]:
  """Validate that a file is a valid JAR file.

  Args:
    jar_path: Path to JAR file to validate

  Returns:
    Dictionary containing validation results

  Raises:
    ValueError: If file doesn't exist or is not a valid JAR
  """
  if not jar_path.exists():
    raise ValueError(f"JAR file does not exist: {jar_path}")

  if not jar_path.is_file():
    raise ValueError(f"Path is not a file: {jar_path}")

  if jar_path.stat().st_size == 0:
    raise ValueError(f"JAR file is empty: {jar_path}")

  try:
    with zipfile.ZipFile(jar_path, "r") as jar_zip:
      # Check if it's a valid ZIP file
      zip_info = jar_zip.testzip()
      if zip_info is not None:
        raise ValueError(f"JAR file is corrupted at entry: {zip_info}")

      # Get file list and basic statistics
      file_list = jar_zip.namelist()
      java_files = [f for f in file_list if f.endswith(".java")]
      class_files = [f for f in file_list if f.endswith(".class")]

      # Check for manifest (JAR-specific validation)
      has_manifest = "META-INF/MANIFEST.MF" in file_list

      return {
        "status": "valid",
        "jar_path": str(jar_path),
        "file_size": jar_path.stat().st_size,
        "total_entries": len(file_list),
        "java_files": len(java_files),
        "class_files": len(class_files),
        "has_manifest": has_manifest,
        "is_source_jar": len(java_files) > 0 and len(class_files) == 0,
      }

  except zipfile.BadZipFile as e:
    raise ValueError(f"Invalid ZIP/JAR file format: {jar_path} - {str(e)}") from e
  except Exception as e:
    raise ValueError(f"Failed to validate JAR file {jar_path}: {str(e)}") from e


def safe_copy_file(
  source_path: Path, target_path: Path, overwrite: bool = False
) -> Dict[str, Any]:
  """Safely copy a file with validation and error handling.

  Args:
    source_path: Source file path
    target_path: Target file path
    overwrite: Whether to overwrite existing target file

  Returns:
    Dictionary containing copy operation results

  Raises:
    ValueError: If source doesn't exist or target exists and overwrite is False
    OSError: If copy operation fails
  """
  if not source_path.exists():
    raise ValueError(f"Source file does not exist: {source_path}")

  if not source_path.is_file():
    raise ValueError(f"Source is not a file: {source_path}")

  if target_path.exists() and not overwrite:
    raise ValueError(f"Target file already exists: {target_path}")

  # Ensure target directory exists
  target_path.parent.mkdir(parents=True, exist_ok=True)

  try:
    # Copy file with metadata
    shutil.copy2(source_path, target_path)

    # Verify copy
    source_size = source_path.stat().st_size
    target_size = target_path.stat().st_size

    if source_size != target_size:
      target_path.unlink()  # Clean up corrupted copy
      raise OSError(
        f"Copy verification failed: size mismatch ({source_size} != {target_size})"
      )

    return {
      "status": "success",
      "operation": "copy",
      "source_path": str(source_path),
      "target_path": str(target_path),
      "file_size": source_size,
      "overwritten": target_path.exists(),
    }

  except OSError as e:
    # Clean up partial copy
    if target_path.exists():
      target_path.unlink()
    raise OSError(f"Failed to copy {source_path} to {target_path}: {str(e)}") from e


def safe_symlink(
  source_path: Path, target_path: Path, overwrite: bool = False
) -> Dict[str, Any]:
  """Safely create a symbolic link with validation and error handling.

  Args:
    source_path: Source path to link to
    target_path: Target symbolic link path
    overwrite: Whether to overwrite existing target

  Returns:
    Dictionary containing symlink operation results

  Raises:
    ValueError: If source doesn't exist or target exists and overwrite is False
    OSError: If symlink creation fails
  """
  if not source_path.exists():
    raise ValueError(f"Source path does not exist: {source_path}")

  if target_path.exists() and not overwrite:
    raise ValueError(f"Target path already exists: {target_path}")

  # Ensure target parent directory exists
  target_path.parent.mkdir(parents=True, exist_ok=True)

  # Remove existing target if overwrite is requested
  if target_path.exists() and overwrite:
    if target_path.is_symlink():
      target_path.unlink()
    elif target_path.is_dir():
      shutil.rmtree(target_path)
    else:
      target_path.unlink()

  try:
    target_path.symlink_to(source_path)

    return {
      "status": "success",
      "operation": "symlink",
      "source_path": str(source_path),
      "target_path": str(target_path),
      "is_directory": source_path.is_dir(),
    }

  except OSError as e:
    raise OSError(
      f"Failed to create symlink from {target_path} to {source_path}: {str(e)}"
    ) from e


def safe_copy_tree(
  source_dir: Path, target_dir: Path, overwrite: bool = False
) -> Dict[str, Any]:
  """Safely copy a directory tree with validation and error handling.

  Args:
    source_dir: Source directory path
    target_dir: Target directory path
    overwrite: Whether to overwrite existing target directory

  Returns:
    Dictionary containing copy operation results

  Raises:
    ValueError: If source doesn't exist or target exists and overwrite is False
    OSError: If copy operation fails
  """
  if not source_dir.exists():
    raise ValueError(f"Source directory does not exist: {source_dir}")

  if not source_dir.is_dir():
    raise ValueError(f"Source is not a directory: {source_dir}")

  if target_dir.exists() and not overwrite:
    raise ValueError(f"Target directory already exists: {target_dir}")

  # Remove existing target if overwrite is requested
  if target_dir.exists() and overwrite:
    shutil.rmtree(target_dir)

  try:
    shutil.copytree(source_dir, target_dir, dirs_exist_ok=False)

    # Count copied items
    copied_files = sum(1 for _ in target_dir.rglob("*") if _.is_file())
    copied_dirs = sum(1 for _ in target_dir.rglob("*") if _.is_dir())

    return {
      "status": "success",
      "operation": "copy_tree",
      "source_dir": str(source_dir),
      "target_dir": str(target_dir),
      "copied_files": copied_files,
      "copied_directories": copied_dirs,
    }

  except OSError as e:
    # Clean up partial copy
    if target_dir.exists():
      shutil.rmtree(target_dir, ignore_errors=True)
    raise OSError(
      f"Failed to copy directory {source_dir} to {target_dir}: {str(e)}"
    ) from e


def get_file_info(file_path: str) -> FileInfo:
  """Get file metadata information.

  Args:
    file_path: Path to file to examine

  Returns:
    FileInfo containing file metadata

  Raises:
    ValueError: If path doesn't exist or is not a file
  """
  path_obj = Path(file_path)

  if not path_obj.exists():
    raise ValueError(f"Path does not exist: {file_path}")

  if not path_obj.is_file():
    raise ValueError(f"Path is not a file: {file_path}")

  stat_info = path_obj.stat()
  file_size = stat_info.st_size

  # Format file size in human-readable format
  def format_file_size(size_bytes: int) -> str:
    """Convert bytes to human readable format"""
    if size_bytes == 0:
      return "0B"

    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(size_bytes)
    unit_index = 0

    while size >= 1024.0 and unit_index < len(units) - 1:
      size /= 1024.0
      unit_index += 1

    if unit_index == 0:
      return f"{int(size)}{units[unit_index]}"
    else:
      return f"{size:.1f}{units[unit_index]}"

  # Count lines for text files
  line_count = 0
  try:
    # Check if file appears to be binary by reading first 1024 bytes
    with open(path_obj, "rb") as f:
      chunk = f.read(1024)
      # If chunk contains null bytes, treat as binary
      if b"\x00" in chunk:
        line_count = 0
      else:
        # Try to read as text file to count lines
        with open(path_obj, "r", encoding="utf-8", errors="ignore") as text_f:
          line_count = sum(1 for _ in text_f)
  except (UnicodeDecodeError, OSError):
    # If it's a binary file or can't be read, set line_count to 0
    line_count = 0

  return FileInfo(
    name=path_obj.name, size=format_file_size(file_size), line_count=line_count
  )


def ensure_directory(dir_path: Path, mode: int = 0o755) -> Dict[str, Any]:
  """Ensure a directory exists with proper permissions.

  Args:
    dir_path: Directory path to create
    mode: Permission mode for the directory

  Returns:
    Dictionary containing operation results

  Raises:
    OSError: If directory creation fails
  """
  try:
    if dir_path.exists():
      if not dir_path.is_dir():
        raise OSError(f"Path exists but is not a directory: {dir_path}")

      return {"status": "exists", "path": str(dir_path), "created": False}

    # Create directory with parents
    dir_path.mkdir(mode=mode, parents=True, exist_ok=True)

    return {
      "status": "created",
      "path": str(dir_path),
      "created": True,
      "mode": oct(mode),
    }

  except OSError as e:
    raise OSError(f"Failed to create directory {dir_path}: {str(e)}") from e


def normalize_path(path: str) -> str:
  """Cross-platform path normalization.

  Args:
    path: Path string to normalize

  Returns:
    Normalized absolute path

  Raises:
    ValueError: If path is empty or invalid
  """
  if not path or not isinstance(path, str):
    raise ValueError("Path must be a non-empty string")

  path = path.strip()
  if not path:
    raise ValueError("Path cannot be empty or whitespace only")

  # Normalize path using os.path.normpath and convert to absolute path
  normalized = os.path.normpath(os.path.abspath(path))
  return normalized


def calculate_directory_depth(base_path: str, target_path: str) -> int:
  """Calculate directory depth between base and target paths.

  Args:
    base_path: Base directory path
    target_path: Target path to calculate depth for

  Returns:
    Directory depth (0 if target is same as base, positive for subdirectories)

  Raises:
    ValueError: If paths are invalid or target is not under base
  """
  normalized_base = normalize_path(base_path)
  normalized_target = normalize_path(target_path)

  # Check if target path is under base path
  try:
    relative_path = os.path.relpath(normalized_target, normalized_base)
  except ValueError as e:
    raise ValueError(f"Cannot calculate relative path: {e}") from e

  # If relative path starts with '..', target is not under base
  if relative_path.startswith(".."):
    raise ValueError(
      f"Target path is not under base path: {target_path} not under {base_path}"
    )

  # If paths are the same, depth is 0
  if relative_path == ".":
    return 0

  # Count path components to determine depth
  path_parts = Path(relative_path).parts
  return len(path_parts)


def get_artifact_code_path(group_id: str, artifact_id: str, version: str) -> str:
  """Convert Maven coordinates to artifact code directory path.

  Args:
    group_id: Maven group ID (e.g., 'org.springframework')
    artifact_id: Maven artifact ID (e.g., 'spring-core')
    version: Maven version (e.g., '5.3.21')

  Returns:
    Relative path to artifact code directory

  Raises:
    ValueError: If Maven coordinates are invalid
  """
  # Validate Maven coordinates
  validate_maven_coordinates(group_id, artifact_id, version)

  # Convert group_id dots to path separators (org.springframework -> org/springframework)
  group_path = group_id.replace(".", "/")

  # Construct path: group_path/artifact_id/version
  artifact_path = f"{group_path}/{artifact_id}/{version}"

  return artifact_path


def is_artifact_code_available(group_id: str, artifact_id: str, version: str) -> bool:
  """Check if artifact source code exists in code/ directory.

  Args:
    group_id: Maven group ID
    artifact_id: Maven artifact ID
    version: Maven version

  Returns:
    True if code directory exists and contains sources

  Raises:
    ValueError: If Maven coordinates are invalid
  """
  # Get the artifact code path
  artifact_path = get_artifact_code_path(group_id, artifact_id, version)

  # Get the base directory from environment or use default ~/.jar-indexer
  base_dir = os.path.expanduser(os.environ.get("JAR_INDEXER_HOME", "~/.jar-indexer"))
  code_dir = os.path.join(base_dir, "code", artifact_path)

  # Check if the code directory exists and has content
  code_path = Path(code_dir)
  if not code_path.exists():
    return False

  if not code_path.is_dir():
    return False

  # Check if directory has any content (should have sources/ subdirectory)
  try:
    contents = list(code_path.iterdir())
    return len(contents) > 0
  except OSError:
    return False


def is_artifact_code_indexed(group_id: str, artifact_id: str, version: str) -> bool:
  """Check if artifact is fully indexed (has metadata and index files).

  Args:
    group_id: Maven group ID
    artifact_id: Maven artifact ID
    version: Maven version

  Returns:
    True if artifact is fully indexed

  Raises:
    ValueError: If Maven coordinates are invalid
  """
  # Get the artifact code path
  artifact_path = get_artifact_code_path(group_id, artifact_id, version)

  # Get the base directory from environment or use default ~/.jar-indexer
  base_dir = os.path.expanduser(os.environ.get("JAR_INDEXER_HOME", "~/.jar-indexer"))
  code_dir = os.path.join(base_dir, "code", artifact_path)

  code_path = Path(code_dir)
  if not code_path.exists() or not code_path.is_dir():
    return False

  # Check for required index files
  required_files = ["metadata.json", "index.json", "packages.json"]

  for required_file in required_files:
    file_path = code_path / required_file
    if not file_path.exists() or not file_path.is_file():
      return False

  # Check if sources directory exists
  sources_dir = code_path / "sources"
  if not sources_dir.exists() or not sources_dir.is_dir():
    return False

  return True


def get_registered_source_info(
  group_id: str, artifact_id: str, version: str
) -> RegisteredSourceInfo | None:
  """Retrieve registered source information for an artifact.

  Args:
    group_id: Maven group ID
    artifact_id: Maven artifact ID
    version: Maven version

  Returns:
    RegisteredSourceInfo if source is registered, None otherwise

  Raises:
    ValueError: If Maven coordinates are invalid
  """
  # Get the artifact path
  artifact_path = get_artifact_code_path(group_id, artifact_id, version)

  # Get the base directory from environment or use default ~/.jar-indexer
  base_dir = os.path.expanduser(os.environ.get("JAR_INDEXER_HOME", "~/.jar-indexer"))
  base_path = Path(base_dir)

  # Check different source types to determine what's registered

  # 1. Check for JAR source in source-jar/ directory
  jar_dir = base_path / "source-jar" / artifact_path
  if jar_dir.exists() and jar_dir.is_dir():
    # Look for JAR files
    jar_files = list(jar_dir.glob("*.jar"))
    if jar_files:
      jar_file = jar_files[0]  # Take the first JAR file found
      return RegisteredSourceInfo(
        group_id=group_id,
        artifact_id=artifact_id,
        version=version,
        source_uri=f"file://{jar_file.absolute()}",  # Reconstruct likely source URI
        git_ref=None,
        source_type="jar",
        local_path=f"source-jar/{artifact_path}",
      )

  # 2. Check for Git source by looking for git-bare and code directories
  git_bare_path = artifact_path.rsplit("/", 1)[0]  # Remove version for git-bare path
  git_bare_dir = base_path / "git-bare" / git_bare_path
  code_dir = base_path / "code" / artifact_path

  if git_bare_dir.exists() and code_dir.exists():
    # This is likely a Git source
    # Try to determine git_ref by checking if there's a metadata file or other indicators
    git_ref = None

    # Check if there's a metadata file that might contain git_ref info
    metadata_file = code_dir / "metadata.json"
    if metadata_file.exists():
      try:
        import json

        with open(metadata_file, "r") as f:
          metadata = json.load(f)
          git_ref = metadata.get("git_ref")
      except (json.JSONDecodeError, OSError):
        pass

    # If no git_ref found in metadata, use default 'main'
    if git_ref is None:
      git_ref = "main"

    return RegisteredSourceInfo(
      group_id=group_id,
      artifact_id=artifact_id,
      version=version,
      source_uri="git://unknown",  # Cannot reliably reconstruct original Git URI
      git_ref=git_ref,
      source_type="git",
      local_path=f"code/{artifact_path}",
    )

  # 3. Check for directory source (code directory exists but no git-bare)
  if code_dir.exists() and code_dir.is_dir():
    return RegisteredSourceInfo(
      group_id=group_id,
      artifact_id=artifact_id,
      version=version,
      source_uri=f"file://{code_dir.absolute()}",  # Use current code directory path
      git_ref=None,
      source_type="directory",
      local_path=f"code/{artifact_path}",
    )

  # No registered source found
  return None
