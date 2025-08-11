"""Source extraction and copying utilities."""

import shutil
import zipfile
from pathlib import Path
from typing import Dict, Any
import git
from git.exc import GitCommandError, InvalidGitRepositoryError, BadName
import py7zr


class GitRefNotFoundError(Exception):
  """Exception raised when Git reference is not found."""

  pass


def extract_jar_source(jar_path: str, target_dir: str) -> None:
  """Extract JAR file to specified directory.

  Args:
    jar_path: Absolute path to JAR file to extract
    target_dir: Target directory path for extraction

  Raises:
    FileNotFoundError: If JAR file doesn't exist
    PermissionError: If target directory write permission is missing
    zipfile.BadZipFile: If invalid JAR file format
  """
  jar_file = Path(jar_path)
  target_path = Path(target_dir)

  if not jar_file.exists():
    raise FileNotFoundError(f"JAR file does not exist: {jar_path}")

  # Ensure target directory exists
  target_path.mkdir(parents=True, exist_ok=True)

  try:
    with zipfile.ZipFile(jar_file, "r") as jar_zip:
      jar_zip.extractall(target_path)
  except zipfile.BadZipFile as e:
    raise zipfile.BadZipFile(f"Invalid JAR file format: {jar_path} - {str(e)}") from e
  except PermissionError as e:
    raise PermissionError(f"Permission denied writing to {target_dir}: {str(e)}") from e


def copy_directory_source(source_dir: str, target_dir: str) -> None:
  """Recursively copy source directory contents to target directory.

  Args:
    source_dir: Absolute path to source directory to copy
    target_dir: Target directory path for copying

  Raises:
    FileNotFoundError: If source directory doesn't exist
    PermissionError: If source read or target write permission is missing
  """
  source_path = Path(source_dir)
  target_path = Path(target_dir)

  if not source_path.exists():
    raise FileNotFoundError(f"Source directory does not exist: {source_dir}")

  if not source_path.is_dir():
    raise FileNotFoundError(f"Source is not a directory: {source_dir}")

  try:
    # Remove target directory if it exists
    if target_path.exists():
      shutil.rmtree(target_path)

    # Copy the entire directory tree
    shutil.copytree(source_path, target_path)
  except PermissionError as e:
    raise PermissionError(f"Permission error during copy: {str(e)}") from e


def compress_directory_to_7z(source_dir: str, target_7z_path: str) -> None:
  """Compress directory to 7z format.

  Args:
    source_dir: Absolute path to source directory to compress
    target_7z_path: Absolute path for 7z file to create

  Raises:
    FileNotFoundError: If source directory doesn't exist
    PermissionError: If source read or target write permission is missing
    RuntimeError: If 7z compression process execution fails
  """
  source_path = Path(source_dir)
  target_path = Path(target_7z_path)

  if not source_path.exists():
    raise FileNotFoundError(f"Source directory does not exist: {source_dir}")

  if not source_path.is_dir():
    raise FileNotFoundError(f"Source is not a directory: {source_dir}")

  # Ensure target parent directory exists
  target_path.parent.mkdir(parents=True, exist_ok=True)

  try:
    # Use py7zr to compress directory
    with py7zr.SevenZipFile(target_path, mode="w") as archive:
      # Add all files and directories recursively
      for item in source_path.rglob("*"):
        if item.is_file():
          # Calculate relative path from source directory
          relative_path = item.relative_to(source_path)
          archive.write(item, str(relative_path))

  except PermissionError as e:
    raise PermissionError(f"Permission error during compression: {str(e)}") from e
  except OSError as e:
    raise RuntimeError(f"7z compression failed: {str(e)}") from e
  except Exception as e:
    raise RuntimeError(f"7z compression process failed: {str(e)}") from e


def extract_7z_source(archive_path: str, target_dir: str) -> None:
  """Extract 7z archive to specified directory.

  Args:
    archive_path: Absolute path to 7z file to extract
    target_dir: Target directory path for extraction

  Raises:
    FileNotFoundError: If 7z file doesn't exist
    PermissionError: If target directory write permission is missing
    RuntimeError: If 7z extraction process execution fails
  """
  archive_file = Path(archive_path)
  target_path = Path(target_dir)

  if not archive_file.exists():
    raise FileNotFoundError(f"7z file does not exist: {archive_path}")

  # Ensure target directory exists
  target_path.mkdir(parents=True, exist_ok=True)

  try:
    # Use py7zr to extract archive
    with py7zr.SevenZipFile(archive_file, mode="r") as archive:
      archive.extractall(path=target_path)

  except PermissionError as e:
    raise PermissionError(f"Permission error during extraction: {str(e)}") from e
  except py7zr.Bad7zFile as e:
    raise RuntimeError(f"Invalid 7z file format: {archive_path} - {str(e)}") from e
  except OSError as e:
    raise RuntimeError(f"7z extraction failed: {str(e)}") from e
  except Exception as e:
    raise RuntimeError(f"7z extraction process failed: {str(e)}") from e


def create_git_worktree(bare_repo_path: str, target_dir: str, git_ref: str) -> None:
  """Create worktree from existing Git bare clone for specific version.

  Args:
    bare_repo_path: Git bare clone directory path (e.g., git-bare/{group_id}/{artifact_id}/bare-repo/)
    target_dir: Target directory path where worktree will be created (e.g., code/{group_id}/{artifact_id}/{version}/)
    git_ref: Branch/tag/commit to checkout (required)

  Raises:
    git.exc.GitCommandError: If Git worktree creation fails
    git.exc.InvalidGitRepositoryError: If invalid bare repository path
    GitRefNotFoundError: If specified git_ref doesn't exist
    PermissionError: If target directory write permission is missing
  """
  bare_path = Path(bare_repo_path)
  target_path = Path(target_dir)

  if not bare_path.exists():
    raise FileNotFoundError(f"Bare repository does not exist: {bare_repo_path}")

  try:
    # Open the bare repository
    repo = git.Repo(bare_path)

    # Check if git_ref exists
    try:
      repo.commit(git_ref)
    except BadName:
      raise GitRefNotFoundError(f"Git reference '{git_ref}' not found in repository")

    # Ensure target parent directory exists
    target_path.parent.mkdir(parents=True, exist_ok=True)

    # Remove target directory if it exists
    if target_path.exists():
      shutil.rmtree(target_path)

    # Create worktree
    repo.git.worktree("add", str(target_path), git_ref)

  except InvalidGitRepositoryError as e:
    raise InvalidGitRepositoryError(
      f"Invalid Git repository: {bare_repo_path} - {str(e)}"
    ) from e
  except GitCommandError as e:
    raise GitCommandError(f"Git worktree creation failed: {str(e)}") from e
  except PermissionError as e:
    raise PermissionError(f"Permission error creating worktree: {str(e)}") from e


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
