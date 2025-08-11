# JAR Indexer MCP Tools Specification

## Overview
MCP server providing 14 tools to index and explore Java/Kotlin library source code from JAR files, directories, and Git repositories.

## Tool Categories

**Management (3 tools):**
- `register_source` - Register JAR files, directories, or Git repositories
- `index_artifact` - Index registered sources for exploration  
- `list_indexed_artifacts` - List available indexed artifacts

**Package/Type Exploration (3 tools):**
- `list_packages` - Browse package structure hierarchy
- `list_types` - List classes/interfaces in packages
- `get_type_source` - Get complete source code for types

**Member Analysis (4 tools):**
- `list_methods` - List methods with signatures and filtering
- `list_fields` - List fields with signatures and filtering
- `get_method_source` - Get method implementation source
- `get_import_section` - Get import statements for dependency analysis

**File Operations (4 tools):**
- `list_folder_tree` - Browse directory structure
- `search_file_names` - Find files by name patterns (glob/regex)
- `search_file_content` - Search content within files with context
- `get_file` - Get file content with optional line ranges

## Tool Specifications

> **Note:** All tools may return common error responses. See "Common Response Status Codes" section for complete error details.

### Management Tools

#### register_source
Register JAR files, source directories, or Git repositories for indexing.

Supports local/remote JAR files (Maven repositories, file system), local source directories (extracted sources, project directories), and Git repositories (GitHub, GitLab, internal servers with HTTPS/SSH).

**Examples:**
```
# JAR Files
file:///path/to/library-sources.jar
https://repo1.maven.org/maven2/org/example/lib/1.0.0/lib-1.0.0-sources.jar

# Local Directories  
file:///Users/user/project/src/main/java
file:///tmp/extracted-sources

# Git Repositories
https://github.com/user/repo.git
git@github.com:user/repo.git
https://gitlab.com/user/project.git
```

**Parameters:**
- `group_id`, `artifact_id`, `version` - Maven coordinates (required)
- `source_uri` - Source location URI (required)
- `auto_index` - Auto-index after registration (optional, default: true)
- `git_ref` - Git branch/tag/commit (required for Git URIs only, not applicable to JAR files or directories)


**Request:**
```python
register_source(
    group_id: "org.springframework",
    artifact_id: "spring-core",
    version: "5.3.21",
    source_uri: "https://github.com/spring-projects/spring-framework.git",
    auto_index: True,
    git_ref: "v5.3.21"
)
```

**Response:**
```jsonc
{
  "group_id": "org.springframework",
  "artifact_id": "spring-core", 
  "version": "5.3.21",
  "status": "registered_and_indexed", // "registered_only" when auto_index=false
  "indexed": true // false when auto_index=false
}
```


#### index_artifact
Index a registered artifact to enable exploration tools.

**Parameters:**
- `group_id`, `artifact_id`, `version` - Maven coordinates (required)

**Request:**
```python
index_artifact(
    group_id: "org.springframework",
    artifact_id: "spring-core",
    version: "5.3.21"
)
```

**Response (success):**
```json
{
  "status": "success",
  "cache_location": "code/org.springframework/spring-core/5.3.21",
  "processing_time": "2.3s"
}
```


#### list_indexed_artifacts
List all indexed artifacts with optional filtering and pagination.

**Parameters:**
- `page`, `page_size` - Pagination controls (optional)
- `group_filter`, `artifact_filter` - Filter by coordinates (optional)
- `version_filter` - Version constraints: `"5.3.21"`, `">=5.3.0"`, `"<6.0.0"`, `">=5.0.0,<6.0.0"` (optional)

**Request:**
```python
list_indexed_artifacts(
    page: 1,
    page_size: 50,
    group_filter: "org.springframework",
    artifact_filter: "spring-core",
    version_filter: ">=5.3.0"
)
```

**Response (success):**
```json
{
  "status": "success",
  "pagination": {
    "page": 1,
    "total_count": 23,
    "total_pages": 1,
  },
  "artifacts": [
    {
      "group_id": "org.springframework",
      "artifact_id": "spring-core",
      "version": "5.3.21",
      "status": "indexed"
    },
    {
      "group_id": "io.netty",
      "artifact_id": "netty-common",
      "version": "4.1.79.Final",
      "status": "failed"
    }
  ]
}
```


### Package/Type Exploration Tools

#### list_packages
Browse package structure hierarchy within an artifact.

**Parameters:**
- `group_id`, `artifact_id`, `version` - Maven coordinates (required)
- `parent_package` - Starting package path (optional, defaults to root)
- `max_depth` - Hierarchy depth to traverse (optional, default: 1)
- `include_description` - Include package descriptions (optional, default: false)

**Request:**
```python
list_packages(
    group_id: "org.springframework",
    artifact_id: "spring-core",
    version: "5.3.21",
    parent_package: "org.springframework.core",
    max_depth: 2,
    include_description: True
)
```

**Response:**
```jsonc
{
  "status": "success",
  "max_depth": 2,
  "packages": [
    {
      "name": "org.springframework.core",
      "description": "Related description", // Only present when include_description=true
      "packages": [
        {
          "name": "annotation",
          "description": "Related description", // Only present when include_description=true
          "packages": [
            {
              "name": "meta",
              "description": "Related description" // Only present when include_description=true
            }
          ]
        },
        {
          "name": "convert",
          "description": "Related description", // Only present when include_description=true
          "packages": [
            {
              "name": "converter",
              "description": "Related description" // Only present when include_description=true
            }
          ]
        }
      ]
    }
  ]
}
```


#### list_types
List classes, interfaces, enums, and annotations within packages.

**Parameters:**
- `group_id`, `artifact_id`, `version` - Maven coordinates (required)
- `package_filter` - Target package (optional)
- `name_filter` - Type name pattern: `"*Utils"`, `"String*"`, `"*Exception*"` (optional)
- `name_filter_type` - Pattern type: "glob" or "regex" (optional, default: "glob")
- `page`, `page_size` - Pagination controls (optional)
- `include_description` - Include type descriptions (optional, default: false)

**Request:**
```python
list_types(
    group_id: "org.springframework",
    artifact_id: "spring-core", 
    version: "5.3.21",
    package_filter: "org.springframework.core",
    name_filter: "*Utils",
    name_filter_type: "glob",
    page: 1,
    page_size: 50,
    include_description: True
)
```

**Response:**
```jsonc
{
  "status": "success",
  "package": "org.springframework.core",
  "pagination": {
    "page": 1,
    "total_count": 247,
    "total_pages": 5,
  },
  "types": [
    {
      "name": "AttributeAccessor",
      "kind": "interface",
      "language": "java",
      "description": "Related description." // Only present when include_description=true
    },
    {
      "name": "AttributeAccessorSupport",
      "kind": "class", 
      "language": "java",
      "description": "Related description." // Only present when include_description=true
    }
  ]
}
```


#### get_type_source
Get complete source code for a specific type.

**Parameters:**
- `group_id`, `artifact_id`, `version` - Maven coordinates (required)
- `type_name` - Fully qualified type name (required)

**Request:**
```python
get_type_source(
    group_id: "org.springframework",
    artifact_id: "spring-core", 
    version: "5.3.21",
    type_name: "org.springframework.core.SpringVersion"
)
```

**Response (success):**
```json
{
  "status": "success",
  "type_info": {
    "name": "org.springframework.core.SpringVersion",
    "kind": "class",
    "language": "java",
    "line_range": {"start": 25, "end": 95},
    "source_code": "Source code content..."
  }
}
```


### Member Analysis Tools

#### list_methods
List all methods of a class or interface with filtering support.

**Parameters:**
- `group_id`, `artifact_id`, `version` - Maven coordinates (required)
- `type_name` - Fully qualified type name (required)
- `include_inherited` - Include inherited methods (optional, default: false)
- `name_filter` - Method name pattern: `"get*"`, `"set*"`, `"*Test"`, `"is*"` (optional)
- `name_filter_type` - Pattern type: "glob" or "regex" (optional, default: "glob")
- `page`, `page_size` - Pagination controls (optional)
- `include_description` - Include method descriptions (optional, default: false)

**Request:**
```python
list_methods(
    group_id: "org.springframework",
    artifact_id: "spring-core", 
    version: "5.3.21",
    type_name: "org.springframework.util.StringUtils",
    include_inherited: False,
    name_filter: "has*",
    name_filter_type: "glob",
    page: 1,
    page_size: 50,
    include_description: True
)
```

**Response:**
```jsonc
{
  "status": "success",
  "type_name": "org.springframework.util.StringUtils",
  "type_kind": "class",
  "language": "java",
  "pagination": {
    "page": 1,
    "total_count": 45,
    "total_pages": 1
  },
  "methods": [
    {
      "signature": "public static boolean hasText(String str)",
      "line_range": {"start": 156, "end": 159},
      "description": "Related description." // Only present when include_description=true
    },
    {
      "signature": "public static boolean hasText(CharSequence str)",
      "line_range": {"start": 171, "end": 174},
      "description": "Related description." // Only present when include_description=true
    }
  ]
}
```


#### list_fields
List all fields of a class or interface with filtering support.

**Parameters:**
- `group_id`, `artifact_id`, `version` - Maven coordinates (required)
- `type_name` - Fully qualified type name (required)
- `include_inherited` - Include inherited fields (optional, default: false)
- `name_filter` - Field name pattern: `"*VERSION*"`, `"*CONFIG*"`, `"cache*"`, `"logger"` (optional)
- `name_filter_type` - Pattern type: "glob" or "regex" (optional, default: "glob")
- `page`, `page_size` - Pagination controls (optional)
- `include_description` - Include field descriptions (optional, default: false)

**Request:**
```python
list_fields(
    group_id: "org.springframework",
    artifact_id: "spring-core", 
    version: "5.3.21",
    type_name: "org.springframework.core.SpringVersion",
    include_inherited: False,
    name_filter: "*VERSION*",
    name_filter_type: "glob",
    page: 1,
    page_size: 50,
    include_description: True
)
```

**Response:**
```jsonc
{
  "status": "success",
  "type_name": "org.springframework.core.SpringVersion",
  "type_kind": "class",
  "pagination": {
    "page": 1,
    "total_count": 5,
    "total_pages": 1
  },
  "fields": [
    {
      "signature": "private static final String VERSION",
      "line_range": {"start": 28, "end": 28},
      "description": "Related description." // Only present when include_description=true
    },
    {
      "signature": "private static final Logger logger",
      "line_range": {"start": 32, "end": 32},
      "description": "Related description." // Only present when include_description=true
    }
  ]
}
```


#### get_import_section
Get import statements for a type to analyze dependencies.

**Parameters:**
- `group_id`, `artifact_id`, `version` - Maven coordinates (required)
- `type_name` - Fully qualified type name (required)

**Request:**
```python
get_import_section(
    group_id: "org.springframework",
    artifact_id: "spring-core", 
    version: "5.3.21",
    type_name: "org.springframework.core.SpringVersion"
)
```

**Response:**
```json
{
  "status": "success",
  "type_name": "org.springframework.core.SpringVersion",
  "import_section": {
    "line_range": {"start": 23, "end": 31},
    "source_code": "Import statements..."
  }
}
```


#### get_method_source
Get source code for specific method implementations.

**Parameters:**
- `group_id`, `artifact_id`, `version` - Maven coordinates (required)
- `type_name` - Fully qualified type name (required)
- `method_name` - Method name (required)
- `method_signature` - Method parameter signature for overload disambiguation (optional)

**Request:**
```python
get_method_source(
    group_id: "org.springframework",
    artifact_id: "spring-core", 
    version: "5.3.21",
    type_name: "org.springframework.util.StringUtils",
    method_name: "hasText",
    method_signature: "(String)"
)
```

**Response:**
```json
{
  "status": "success",
  "method_source": [
    {
      "line_range": {"start": 156, "end": 159},
      "source_code": "Method implementation..."
    }
  ]
}
```


### File Operations Tools

#### list_folder_tree
Browse directory structure within an artifact.

**Parameters:**
- `group_id`, `artifact_id`, `version` - Maven coordinates (required)
- `path` - Starting directory path (optional, defaults to root)
- `include_files` - Include files in response (optional, default: true)
- `max_depth` - Directory traversal depth (optional, default: 1)

**Request:**
```python
list_folder_tree(
    group_id: "org.springframework",
    artifact_id: "spring-core",
    version: "5.3.21",
    path: "org/springframework/core",
    include_files: True,
    max_depth: 3
)
```

**Response:**
```jsonc
{
  "status": "success",
  "path": "org/springframework/core",
  "max_depth": 3,
  "folders": [
    {
      "name": "annotation",
      "file_count": 8,
      "files": [{"name": "File.java", "size": "1KB", "line_count": 50}], // Only present when include_files=true
      "folders": [
        {
          "name": "meta",
          "file_count": 5,
          "folders": [{"name": "impl", "file_count": 3}]
        }
      ]
    }
  ],
  "files": [{"name": "File.java", "size": "1KB", "line_count": 50}] // Only present when include_files=true
}
```


#### search_file_names
Find files by name patterns using glob or regex matching.

**Parameters:**
- `group_id`, `artifact_id`, `version` - Maven coordinates (required)
- `pattern` - Search pattern (required)
- `pattern_type` - Pattern type: "glob" or "regex" (required)
- `start_path` - Starting directory (optional, defaults to root)
- `max_depth` - Search depth limit (optional, default: unlimited)

**Request:**
```python
search_file_names(
    group_id: "org.springframework",
    artifact_id: "spring-core",
    version: "5.3.21",
    pattern: "StringUtils*.java",
    pattern_type: "glob",
    start_path: "org/springframework/util",
    max_depth: 2
)
```

**Response (success):**
```json
{
  "status": "success",
  "search_config": {
    "start_path": "org/springframework/util",
    "max_depth": 2,
    "pattern": "StringUtils*.java"
  },
  "files": [
    {
      "name": "File.java",
      "path": "path/to/File.java",
      "size": "1KB",
      "line_count": 50
    }
  ]
}
```


#### search_file_content
Search for text within file contents with configurable context lines.

**Parameters:**
- `group_id`, `artifact_id`, `version` - Maven coordinates (required)
- `query` - Search query (required)
- `query_type` - Query type: "string" or "regex" (required)
- `start_path` - Starting directory (optional, defaults to root)
- `max_depth` - Search depth limit (optional, default: unlimited)
- `context_before`, `context_after` - Context lines around matches (optional)
- `max_results` - Maximum number of results (optional)

**Request:**
```python
search_file_content(
    group_id: "org.springframework",
    artifact_id: "spring-core",
    version: "5.3.21",
    query: "hasText",
    query_type: "string",
    start_path: "org/springframework/util",
    max_depth: 2,
    context_before: 2,
    context_after: 3,
    max_results: 20
)
```

**Response:**
```json
{
  "status": "success",
  "search_config": {
    "query": "hasText",
    "query_type": "string",
    "start_path": "org/springframework/util",
    "context_before": 2,
    "context_after": 3
  },
  "matches": {
    "File.java": [
      {
        "content": "Matched content...",
        "content_range": "10-15",
        "match_lines": "12"
      }
    ]
  }
}
```


#### get_file
Get file content with optional line range specification.

**Parameters:**
- `group_id`, `artifact_id`, `version` - Maven coordinates (required)
- `file_path` - File path within artifact (required)
- `start_line`, `end_line` - Line range to retrieve (optional, defaults to entire file)

**Request:**
```python
get_file(
    group_id: "org.springframework",
    artifact_id: "spring-core",
    version: "5.3.21",
    file_path: "org/springframework/util/StringUtils.java",
    start_line: 150,
    end_line: 200
)
```

**Response:**
```json
{
  "status": "success",
  "file_info": {
    "name": "File.java",
    "path": "path/to/File.java"
  },
  "content": {
    "start_line": 150,
    "end_line": 200,
    "source_code": "File content..."
  }
}
```


## Common Usage Workflows

**Setup Workflow:**
1. `register_source` - Register JAR/directory/Git repository
2. `index_artifact` - Index the source (if auto_index=false)
3. `list_indexed_artifacts` - Verify indexing completed

**Code Exploration Workflows:**
- **Package Structure**: `list_packages` → `list_types` → `get_type_source`
- **Method Analysis**: `list_methods` → `get_method_source` → `get_import_section`  
- **File Operations**: `list_folder_tree` → `search_file_names` → `get_file`
- **Content Search**: `search_file_content` with context lines

---

## Common Response Status Codes

**Success States:**
- `"success"` - Operation completed successfully
- `"registered_and_indexed"` - Source registered and indexed
- `"registered_only"` - Source registered but not indexed

**Error States:**
- `"source_jar_not_found"` - Source not found, use `register_source`
- `"indexing_required"` - Source exists but needs indexing, use `index_artifact`
- `"internal_error"` - Server-side processing error

**Error States (register_source only):**
- `"resource_not_found"` - Invalid file path or URI
- `"download_failed"` - Remote source download failed
- `"invalid_source"` - Corrupted or unsupported source format
- `"unsupported_source_type"` - Only JAR files, directories, or Git repositories supported
- `"git_clone_failed"` - Git repository access failed (permission denied or not found)
- `"git_ref_not_found"` - Git branch/tag/commit not found

**Error Response Format:**
```json
{
  "status": "error_code",
  "message": "Descriptive error message",
  "suggested_action": "recommended_tool_name"  // when applicable
}
```
