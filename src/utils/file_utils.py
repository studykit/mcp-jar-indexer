"""File utility functions for JAR indexer.

This module provides utility functions for file operations including
downloading files, validating JAR files, and handling file system operations.
"""

import shutil
import zipfile
from pathlib import Path
from typing import Dict, Any
from urllib.parse import urlparse
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


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


def get_file_info(file_path: Path) -> Dict[str, Any]:
  """Get comprehensive information about a file or directory.

  Args:
    file_path: Path to examine

  Returns:
    Dictionary containing file information

  Raises:
    ValueError: If path doesn't exist
  """
  if not file_path.exists():
    raise ValueError(f"Path does not exist: {file_path}")

  stat_info = file_path.stat()

  info = {
    "path": str(file_path),
    "name": file_path.name,
    "exists": True,
    "size": stat_info.st_size,
    "is_file": file_path.is_file(),
    "is_directory": file_path.is_dir(),
    "is_symlink": file_path.is_symlink(),
    "modified_time": stat_info.st_mtime,
    "permissions": oct(stat_info.st_mode)[-3:],
  }

  if file_path.is_file():
    info["suffix"] = file_path.suffix.lower()
    info["stem"] = file_path.stem

    # Add JAR-specific information if it's a JAR file
    if info["suffix"] == ".jar":
      try:
        jar_info = validate_jar_file(file_path)
        info["jar_validation"] = jar_info
      except ValueError as e:
        info["jar_validation"] = {"status": "invalid", "error": str(e)}

  elif file_path.is_dir():
    # Count directory contents
    try:
      contents = list(file_path.iterdir())
      info["contents_count"] = len(contents)
      info["subdirectories"] = sum(1 for p in contents if p.is_dir())
      info["files"] = sum(1 for p in contents if p.is_file())
    except OSError:
      info["contents_count"] = "unknown"
      info["subdirectories"] = "unknown"
      info["files"] = "unknown"

  if file_path.is_symlink():
    try:
      info["symlink_target"] = str(file_path.readlink())
    except OSError:
      info["symlink_target"] = "unknown"

  return info


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
