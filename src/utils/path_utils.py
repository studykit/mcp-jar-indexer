"""Path manipulation and validation utilities."""

import os
from pathlib import Path
from typing import Dict, Any


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
