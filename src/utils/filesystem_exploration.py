"""File system exploration utilities."""

import re
from pathlib import Path
from typing import Dict

from ..types.core_types import (
  FileInfo,
  FolderInfo,
  ListDirectoryTreeResult,
  GetFileContentResult,
  FileContent,
  SearchFilesByPatternResult,
  FileSearchResult,
  SearchFileContentsResult,
  SearchConfig,
  SearchMatch,
)


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


def list_directory_tree(
  base_path: str, start_path: str = "", max_depth: int = 1, include_files: bool = True
) -> ListDirectoryTreeResult:
  """Explore directory tree structure from specified path and return hierarchical information.

  Args:
    base_path: Artifact root directory absolute path
    start_path: Exploration start path (relative to base_path)
    max_depth: Maximum exploration depth
    include_files: Whether to include file information

  Returns:
    ListDirectoryTreeResult containing directory structure
  """
  base = Path(base_path)
  start = base / start_path if start_path else base

  if not start.exists():
    raise ValueError(f"Start path does not exist: {start}")

  if not start.is_dir():
    raise ValueError(f"Start path is not a directory: {start}")

  def _build_folder_info(path: Path, current_depth: int) -> FolderInfo:
    """Build folder information recursively."""
    files = []
    folders = []

    if include_files:
      # Get files in current directory
      for item in path.iterdir():
        if item.is_file():
          try:
            file_info = get_file_info(str(item))
            files.append(file_info)
          except ValueError:
            # Skip files that can't be read
            pass

    # Get subdirectories if we haven't reached max depth
    if current_depth < max_depth:
      for item in path.iterdir():
        if item.is_dir():
          try:
            folder_info = _build_folder_info(item, current_depth + 1)
            folders.append(folder_info)
          except (PermissionError, OSError):
            # Skip directories that can't be accessed
            pass

    # Count files in directory
    file_count = len([item for item in path.iterdir() if item.is_file()])

    return FolderInfo(
      name=path.name, file_count=file_count, files=files, folders=folders
    )

  # Build root level structure
  root_files = []
  root_folders = []

  if include_files:
    for item in start.iterdir():
      if item.is_file():
        try:
          file_info = get_file_info(str(item))
          root_files.append(file_info)
        except ValueError:
          pass

  # Get subdirectories
  for item in start.iterdir():
    if item.is_dir():
      try:
        folder_info = _build_folder_info(item, 1)
        root_folders.append(folder_info)
      except (PermissionError, OSError):
        pass

  return ListDirectoryTreeResult(
    path=str(start.relative_to(base)) if start != base else "",
    max_depth=max_depth,
    folders=root_folders,
    files=root_files,
  )


def get_file_content(
  base_path: str,
  file_path: str,
  start_line: int | None = None,
  end_line: int | None = None,
) -> GetFileContentResult:
  """Read file content and return it. Optionally specify line range.

  Args:
    base_path: Artifact root directory absolute path
    file_path: Path to file to read (relative to base_path)
    start_line: Start line number (1-based, optional)
    end_line: End line number (1-based, optional)

  Returns:
    GetFileContentResult containing file information and content

  Raises:
    FileNotFoundError: If file doesn't exist
    PermissionError: If file read permission is missing
  """
  base = Path(base_path)
  full_path = base / file_path

  if not full_path.exists():
    raise FileNotFoundError(f"File does not exist: {file_path}")

  if not full_path.is_file():
    raise ValueError(f"Path is not a file: {file_path}")

  # Get file info
  file_info = get_file_info(str(full_path))

  # Read file content
  try:
    with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
      lines = f.readlines()
  except (UnicodeDecodeError, OSError) as e:
    raise PermissionError(f"Cannot read file {file_path}: {str(e)}") from e

  # Apply line range if specified
  if start_line is not None or end_line is not None:
    start_idx = (start_line - 1) if start_line is not None else 0
    end_idx = end_line if end_line is not None else len(lines)

    # Ensure valid range
    start_idx = max(0, start_idx)
    end_idx = min(len(lines), end_idx)

    selected_lines = lines[start_idx:end_idx]
    actual_start = start_idx + 1
    actual_end = end_idx
  else:
    selected_lines = lines
    actual_start = 1
    actual_end = len(lines)

  content = "".join(selected_lines)

  return GetFileContentResult(
    file_info=file_info,
    content=FileContent(
      start_line=actual_start, end_line=actual_end, source_code=content
    ),
  )


def search_files_by_pattern(
  base_path: str,
  pattern: str,
  pattern_type: str,
  start_path: str = "",
  max_depth: int | None = None,
) -> SearchFilesByPatternResult:
  """Search files by specified pattern.

  Args:
    base_path: Artifact root directory absolute path
    pattern: Search pattern
    pattern_type: Pattern type ("glob" or "regex")
    start_path: Search start path (relative to base_path)
    max_depth: Maximum search depth (None for unlimited)

  Returns:
    SearchFilesByPatternResult containing matched files
  """
  base = Path(base_path)
  start = base / start_path if start_path else base

  if not start.exists():
    raise ValueError(f"Start path does not exist: {start}")

  if not start.is_dir():
    raise ValueError(f"Start path is not a directory: {start}")

  matched_files: list[FileSearchResult] = []

  def _search_directory(path: Path, current_depth: int):
    """Search directory recursively."""
    if max_depth is not None and current_depth > max_depth:
      return

    try:
      for item in path.iterdir():
        if item.is_file():
          # Check if file matches pattern
          relative_path = item.relative_to(base)

          if pattern_type == "glob":
            if item.match(pattern):
              try:
                file_info = get_file_info(str(item))
                matched_files.append(
                  FileSearchResult(
                    name=item.name,
                    path=str(relative_path),
                    size=file_info["size"],
                    line_count=file_info["line_count"],
                  )
                )
              except ValueError:
                pass
          elif pattern_type == "regex":
            if re.search(pattern, item.name):
              try:
                file_info = get_file_info(str(item))
                matched_files.append(
                  FileSearchResult(
                    name=item.name,
                    path=str(relative_path),
                    size=file_info["size"],
                    line_count=file_info["line_count"],
                  )
                )
              except ValueError:
                pass
        elif item.is_dir():
          _search_directory(item, current_depth + 1)
    except (PermissionError, OSError):
      # Skip directories that can't be accessed
      pass

  _search_directory(start, 0)

  return SearchFilesByPatternResult(files=matched_files)


def search_file_contents(
  base_path: str,
  query: str,
  query_type: str,
  start_path: str = "",
  max_depth: int | None = None,
  context_before: int = 0,
  context_after: int = 0,
  max_results: int | None = None,
) -> SearchFileContentsResult:
  """Search specified query in file contents and return with context.

  Args:
    base_path: Artifact root directory absolute path
    query: Search query
    query_type: Query type ("string" or "regex")
    start_path: Search start path (relative to base_path)
    max_depth: Maximum search depth (None for unlimited)
    context_before: Number of context lines before match
    context_after: Number of context lines after match
    max_results: Maximum number of results (None for unlimited)

  Returns:
    SearchFileContentsResult containing search results
  """
  base = Path(base_path)
  start = base / start_path if start_path else base

  if not start.exists():
    raise ValueError(f"Start path does not exist: {start}")

  if not start.is_dir():
    raise ValueError(f"Start path is not a directory: {start}")

  matches: Dict[str, list[SearchMatch]] = {}
  total_results = 0

  def _search_file_content(file_path: Path):
    """Search content in a single file."""
    nonlocal total_results

    if max_results is not None and total_results >= max_results:
      return

    try:
      with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()
    except (UnicodeDecodeError, OSError):
      return

    file_matches = []

    for line_num, line in enumerate(lines, 1):
      if max_results is not None and total_results >= max_results:
        break

      # Check if line matches query
      if query_type == "string":
        if query in line:
          match_found = True
        else:
          match_found = False
      elif query_type == "regex":
        try:
          if re.search(query, line):
            match_found = True
          else:
            match_found = False
        except re.error:
          continue
      else:
        continue

      if match_found:
        # Calculate context range
        start_line = max(1, line_num - context_before)
        end_line = min(len(lines), line_num + context_after)

        # Get context lines
        context_lines = []
        for i in range(start_line - 1, end_line):
          context_lines.append(f"{i + 1:4d}: {lines[i]}")

        content = "".join(context_lines)

        match = SearchMatch(
          content=content.rstrip(),
          content_range=f"{start_line}-{end_line}",
          match_lines=str(line_num),
        )

        file_matches.append(match)
        total_results += 1

    if file_matches:
      relative_path = str(file_path.relative_to(base))
      matches[relative_path] = file_matches

  def _search_directory(path: Path, current_depth: int):
    """Search directory recursively."""
    if max_depth is not None and current_depth > max_depth:
      return

    if max_results is not None and total_results >= max_results:
      return

    try:
      for item in path.iterdir():
        if max_results is not None and total_results >= max_results:
          break

        if item.is_file():
          _search_file_content(item)
        elif item.is_dir():
          _search_directory(item, current_depth + 1)
    except (PermissionError, OSError):
      pass

  _search_directory(start, 0)

  search_config = SearchConfig(
    query=query,
    query_type=query_type,
    start_path=start_path,
    context_before=context_before,
    context_after=context_after,
  )

  return SearchFileContentsResult(search_config=search_config, matches=matches)
