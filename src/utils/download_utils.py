"""Download and validation utilities for JAR files."""

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
