"""Core type definitions for JAR Indexer."""

from typing import TypedDict


class SearchMatch(TypedDict):
  """Single search match information"""

  content: str  # Matched content (with context lines)
  content_range: str  # Content range (e.g., "10-15")
  match_lines: str  # Actual matched line numbers (e.g., "12,14")


class SearchConfig(TypedDict):
  """Search configuration information"""

  query: str
  query_type: str  # "string" | "regex"
  start_path: str
  context_before: int
  context_after: int


class SearchFileContentsResult(TypedDict):
  """search_file_contents return type"""

  search_config: SearchConfig
  matches: dict[str, list[SearchMatch]]


class RegisteredSourceInfo(TypedDict):
  """Registered artifact source information"""

  group_id: str  # Maven group ID
  artifact_id: str  # Maven artifact ID
  version: str  # Maven version
  source_uri: str  # Original source URI (for reference)
  git_ref: str | None  # Git reference (for Git sources)
  source_type: str  # "jar", "directory", "git"
  local_path: str  # Intermediate storage relative path (from base directory)


class FileInfo(TypedDict):
  """File metadata information"""

  name: str  # File name
  size: str  # File size (e.g., "1KB", "2.5MB")
  line_count: int  # Number of lines in text file


class IndexArtifactResult(TypedDict, total=False):
  """index_artifact MCP tool response"""

  status: str  # "success" or error code
  cache_location: str  # Source code location (on success)
  processing_time: str  # Processing time (on success)
  message: str  # Error message (on error only)


class SearchFileContentMcpResult(TypedDict):
  """search_file_content MCP tool response"""

  status: str  # "success" or error code
  search_config: SearchConfig  # Search configuration (on success)
  matches: dict[str, list[SearchMatch]]  # Search results (on success)


class FolderInfo(TypedDict):
  """Folder information"""

  name: str  # Folder name
  file_count: int  # Number of files
  files: list[FileInfo]  # File list (when include_files=True)
  folders: list["FolderInfo"]  # Subfolder list


class ListFolderTreeResult(TypedDict):
  """list_folder_tree MCP tool response"""

  status: str  # "success" or error code
  path: str  # Explored path
  max_depth: int  # Applied max depth
  folders: list[FolderInfo]  # Subdirectory list
  files: list[FileInfo]  # File list (when include_files=True)


class FileSearchResult(TypedDict):
  """File search result"""

  name: str  # File name
  path: str  # File path
  size: str  # File size (e.g., "1KB")
  line_count: int  # Line count


class FileSearchConfig(TypedDict):
  """File search configuration information"""

  start_path: str  # Search start path
  max_depth: int  # Maximum search depth
  pattern: str  # Search pattern


class SearchFileNamesResult(TypedDict):
  """search_file_names MCP tool response"""

  status: str  # "success" or error code
  search_config: FileSearchConfig  # Search configuration
  files: list[FileSearchResult]  # Found file list


class FileContent(TypedDict):
  """File content information"""

  start_line: int  # Start line
  end_line: int  # End line
  source_code: str  # File content


class GetFileResult(TypedDict):
  """get_file MCP tool response"""

  status: str  # "success" or error code
  file_info: FileInfo  # File information
  content: FileContent  # File content


class ListDirectoryTreeResult(TypedDict):
  """list_directory_tree return type"""

  path: str  # Explored path
  max_depth: int  # Applied max depth
  folders: list[FolderInfo]  # Subdirectory list
  files: list[FileInfo]  # File list


class GetFileContentResult(TypedDict):
  """get_file_content return type"""

  file_info: FileInfo  # File information
  content: FileContent  # File content


class SearchFilesByPatternResult(TypedDict):
  """search_files_by_pattern return type"""

  files: list[FileSearchResult]  # Matched file information list
