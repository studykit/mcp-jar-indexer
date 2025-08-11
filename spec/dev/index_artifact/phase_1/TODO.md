# TODO: index_artifact Phase 1 Implementation

Based on `spec/dev/index_artifact/phase_1/design_spec.md`, this TODO organizes implementation tasks considering function dependencies.

## Phase 1: Foundation Layer (Low Dependencies)

### 1.1 Basic Utility Functions
- [x] `validate_maven_coordinates(group_id, artifact_id, version) -> bool`
  - Security validation for file system paths
  - No dependencies
  - **Used by**: All functions handling Maven coordinates
  - **Status**: ✅ Already existed in validation.py

- [x] `normalize_path(path) -> str`
  - Cross-platform path normalization
  - No dependencies
  - **Used by**: All file system operations
  - **Status**: ✅ Implemented in file_utils.py

- [x] `calculate_directory_depth(base_path, target_path) -> int`
  - Directory depth calculation
  - Depends on: `normalize_path`
  - **Used by**: Directory traversal functions
  - **Status**: ✅ Implemented in file_utils.py

## Phase 2: File System Basics

### 2.1 File Information Functions
- [x] `get_file_info(file_path) -> FileInfo`
  - File metadata retrieval
  - Depends on: `normalize_path`
  - **Used by**: Directory listing and file operations
  - **Status**: ✅ Implemented in file_utils.py with proper FileInfo type

- [x] `get_artifact_code_path(group_id, artifact_id, version) -> str`
  - Maven coordinates to path conversion
  - Depends on: `validate_maven_coordinates`
  - **Used by**: All artifact-related functions
  - **Status**: ✅ Implemented in file_utils.py

## Phase 3: Source Extraction Layer

### 3.1 Archive Operations
- [x] `extract_jar_source(jar_path, target_dir) -> None`
  - JAR file extraction
  - Depends on: `normalize_path`
  - **Used by**: `index_artifact` for JAR sources
  - **Status**: ✅ Implemented in source_extraction.py with comprehensive tests

- [x] `compress_directory_to_7z(source_dir, target_7z_path) -> None`
  - Directory compression to 7z
  - Depends on: `normalize_path`
  - **Used by**: Directory source storage
  - **Status**: ✅ Implemented in source_extraction.py with comprehensive tests

- [x] `extract_7z_source(archive_path, target_dir) -> None`
  - 7z archive extraction
  - Depends on: `normalize_path`
  - **Used by**: `index_artifact` for directory sources
  - **Status**: ✅ Implemented in source_extraction.py with comprehensive tests

### 3.2 Directory Operations
- [x] `copy_directory_source(source_dir, target_dir) -> None`
  - Recursive directory copying
  - Depends on: `normalize_path`
  - **Used by**: Directory source processing
  - **Status**: ✅ Implemented in source_extraction.py with comprehensive tests

### 3.3 Git Operations
- [x] `create_git_worktree(bare_repo_path, target_dir, git_ref) -> None`
  - Git worktree creation
  - Depends on: `normalize_path`
  - **Used by**: `index_artifact` for Git sources
  - **Status**: ✅ Implemented in source_extraction.py with comprehensive tests

## Phase 4: Artifact State Management

### 4.1 State Checking Functions
- [x] `is_artifact_code_available(group_id, artifact_id, version) -> bool`
  - Check if code exists in code/ directory
  - Depends on: `validate_maven_coordinates`, `get_artifact_code_path`, `normalize_path`
  - **Used by**: `index_artifact` logic flow
  - **Status**: ✅ Implemented in file_utils.py

- [x] `is_artifact_code_indexed(group_id, artifact_id, version) -> bool`
  - Check if artifact is fully indexed
  - Depends on: `validate_maven_coordinates`, `get_artifact_code_path`, `normalize_path`
  - **Used by**: `index_artifact` logic flow
  - **Status**: ✅ Implemented in file_utils.py

- [x] `get_registered_source_info(group_id, artifact_id, version) -> RegisteredSourceInfo | None`
  - Retrieve source registration info
  - Depends on: `validate_maven_coordinates`
  - **Used by**: `index_artifact` for source extraction
  - **Status**: ✅ Implemented in file_utils.py with RegisteredSourceInfo type

## Phase 5: Core File System Operations

### 5.1 Directory Traversal
- [x] `list_directory_tree(base_path, start_path, max_depth, include_files) -> ListDirectoryTreeResult`
  - Hierarchical directory listing
  - Depends on: `normalize_path`, `get_file_info`, `calculate_directory_depth`
  - **Used by**: `list_folder_tree` MCP tool
  - **Status**: ✅ Implemented in filesystem_exploration.py

### 5.2 File Content Operations
- [x] `get_file_content(base_path, file_path, start_line, end_line) -> GetFileContentResult`
  - Read file content with optional line range
  - Depends on: `normalize_path`, `get_file_info`
  - **Used by**: `get_file` MCP tool
  - **Status**: ✅ Implemented in filesystem_exploration.py

### 5.3 Search Operations
- [x] `search_files_by_pattern(base_path, pattern, pattern_type, start_path, max_depth) -> SearchFilesByPatternResult`
  - File name pattern search
  - Depends on: `normalize_path`, `get_file_info`, `calculate_directory_depth`
  - **Used by**: `search_file_names` MCP tool
  - **Status**: ✅ Implemented in filesystem_exploration.py

- [x] `search_file_contents(base_path, query, query_type, start_path, max_depth, context_before, context_after, max_results) -> SearchFileContentsResult`
  - File content search with context
  - Depends on: `normalize_path`, `calculate_directory_depth`
  - **Used by**: `search_file_content` MCP tool
  - **Status**: ✅ Implemented in filesystem_exploration.py

## Phase 6: MCP Tool Layer

### 6.1 Primary MCP Tools
- [x] `index_artifact(group_id, artifact_id, version) -> IndexArtifactResult`
  - Main artifact indexing tool
  - Depends on: Most functions from phases 1-4
  - **Complex logic**: Check indexed → Check available → Extract source → Create index
  - **Status**: ✅ Implemented in tools/index_artifact.py with comprehensive tests

### 6.2 Browse MCP Tools
- [x] `list_folder_tree(group_id, artifact_id, version, path, include_files, max_depth) -> ListFolderTreeResult`
  - Directory structure exploration
  - Depends on: `validate_maven_coordinates`, `list_directory_tree`
  - **Status**: ✅ Implemented in tools/list_folder_tree.py with comprehensive tests

- [x] `get_file(group_id, artifact_id, version, file_path, start_line, end_line) -> GetFileResult`
  - File content retrieval
  - Depends on: `validate_maven_coordinates`, `get_file_content`
  - **Status**: ✅ Implemented in tools/get_file.py with comprehensive tests

### 6.3 Search MCP Tools
- [x] `search_file_names(group_id, artifact_id, version, pattern, pattern_type, start_path, max_depth) -> SearchFileNamesResult`
  - File name search tool
  - Depends on: `validate_maven_coordinates`, `search_files_by_pattern`
  - **Status**: ✅ Implemented in tools/search_file_names.py with comprehensive tests

- [x] `search_file_content(group_id, artifact_id, version, query, query_type, start_path, max_depth, context_before, context_after, max_results) -> SearchFileContentMcpResult`
  - File content search tool
  - Depends on: `validate_maven_coordinates`, `search_file_contents`
  - **Status**: ✅ Implemented in tools/search_file_content.py with comprehensive tests

## Implementation Status

### ✅ COMPLETED (22/22 functions)
**High Priority (Core Dependencies):**
1. ✅ **Phase 1: Foundation utilities** (3/3 functions completed)
   - `validate_maven_coordinates` ✅
   - `normalize_path` ✅ 
   - `calculate_directory_depth` ✅
   
2. ✅ **Phase 2: File system basics** (2/2 functions completed)
   - `get_file_info` ✅
   - `get_artifact_code_path` ✅

3. ✅ **Phase 3: Source extraction** (5/5 functions completed)
   - `extract_jar_source` ✅
   - `compress_directory_to_7z` ✅
   - `extract_7z_source` ✅
   - `copy_directory_source` ✅
   - `create_git_worktree` ✅
   
4. ✅ **Phase 4: Artifact state management** (3/3 functions completed)
   - `is_artifact_code_available` ✅
   - `is_artifact_code_indexed` ✅
   - `get_registered_source_info` ✅
   
5. ✅ **Phase 5: Core file operations** (4/4 functions completed)
   - `list_directory_tree` ✅
   - `get_file_content` ✅
   - `search_files_by_pattern` ✅
   - `search_file_contents` ✅

### ✅ COMPLETED (22/22 functions)
**Final Priority (Interface Layer):**
6. ✅ **Phase 6: MCP tools** (5/5 functions completed)

## Implementation Priority

## Key Dependencies Summary

- **`validate_maven_coordinates`**: Required by all Maven coordinate handling
- **`normalize_path`**: Required by all file system operations
- **`get_artifact_code_path`**: Required by all artifact-specific operations
- **`is_artifact_code_*`**: Critical for `index_artifact` logic flow
- **File system operations**: Dependencies for MCP tool implementations

## Testing Strategy

- Test each phase in dependency order
- Unit test low-dependency functions first
- Integration test MCP tools last
- Mock file system operations for testing