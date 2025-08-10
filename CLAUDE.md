# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

JAR Indexer is an MCP (Model Context Protocol) server that enables Claude Code to access and analyze Java/Kotlin library source code by indexing JAR files and Git repositories. It provides 14 MCP tools for exploring external library implementations, method signatures, and package structures.

For detailed project background, problem statement, and Claude Code integration scenarios, refer to `spec/01_overview.md`.

## Development Commands

### Testing
```bash
# Run all tests
uv run pytest

# Run tests with verbose output  
uv run pytest -v

# Run specific test module
uv run pytest tests/core/test_source_processor.py -v

# Run single test
uv run pytest tests/core/test_source_processor.py::TestClassName::test_method -v
```

### Code Quality
```bash
# Run linter
uv run ruff check

# Auto-fix linting issues
uv run ruff check --fix

# Format code
uv run ruff format

# Check both lint and format
uv run ruff check && uv run ruff format
```

### Development Environment
```bash
# Install dependencies
uv sync

# Install with dev dependencies
uv sync --group dev

# Add new library (always use uv)
uv add <package-name>

# Add dev dependency
uv add --group dev <package-name>

# Run the main module
uv run python -m src.main
```

## Architecture Overview

### Core Components

- **SourceProcessor** (`src/core/source_processor.py`): Handles different source URI types (file://, https://, git+https://) and processes them for indexing
- **StorageManager** (`src/core/storage.py`): Manages the `~/.jar-indexer/` directory structure with Maven coordinate-based paths
- **MCP Tools** (planned): 14 tools for library exploration including `register_source`, `index_artifact`, `get_type_source`, etc.

For comprehensive architecture diagrams, component relationships, and data flow details, refer to `spec/02_architecture.md`.

### Storage Structure
```
~/.jar-indexer/
├── code/{group_id}/{artifact_id}/{version}/     # Indexed source files
├── source-jar/{group_id}/{artifact_id}/{version}/ # Downloaded JAR files  
└── git-bare/{group_id}/{artifact_id}/           # Git bare repositories
```

### URI Processing Flow

1. **URI Parsing**: `SourceProcessor.parse_uri()` classifies URIs as file, http, or git types
2. **Validation**: `SourceProcessor.validate_uri()` checks accessibility 
3. **Processing**: Type-specific processing methods handle copying, downloading, or Git operations
4. **Storage**: Files organized using Maven coordinates via `StorageManager.create_maven_path()`

## Key Design Patterns

### Maven Coordinate Paths
All storage paths use Maven coordinate format: `{group.id}/{artifact-id}/{version}`
- Example: `org.springframework/spring-core/5.3.21`
- Implemented in `StorageManager.create_maven_path()`

### URI Type Detection
- `file://` - Local JAR files or directories
- `https://` - Remote JAR downloads  
- `git+https://` - Git repository cloning

### Error Recovery
- Failed processing triggers cleanup via `SourceProcessor.cleanup_failed_processing()`
- Storage validation ensures directory permissions

## Testing Strategy

- **Unit Tests**: Core logic in `SourceProcessor` and `StorageManager`
- **Integration Tests**: End-to-end URI processing workflows
- **File System Tests**: Storage path creation and permissions

## Dependencies

- **Python 3.12+** required
- **Core**: `mcp`, `requests`, `aiohttp` for MCP server and HTTP operations
- **Git**: `gitpython` for repository operations
- **Dev**: `ruff` for linting/formatting, `pytest` for testing

For complete dependency list and version requirements, refer to `spec/03_tech_stach.md`.

## When to Reference Spec Documents

- **Project Understanding**: Use `spec/01_overview.md` for business context, problem definition, and use case scenarios
- **System Design**: Use `spec/02_architecture.md` for component diagrams, data flow, and storage layout understanding
- **Technology Decisions**: Use `spec/03_tech_stach.md` for supported environments, library choices, and version constraints
- **MCP Tool Implementation**: Use `spec/04_mcp_tool_specification.md` for the complete list of MCP tools to implement
- **Implementation Details**: Use `spec/dev/` for specific tool specifications and development workflows

## Configuration

- Base storage directory: `~/.jar-indexer/` (configurable via `StorageManager`)
- Ruff configuration: 88 character line length, Python 3.12 target
- Test discovery: `tests/` directory with pytest

## Code Style Guidelines

### Type Annotations
**ALWAYS use explicit type annotations for better IDE support and code clarity:**

```python
# Good - Explicit type annotations
def process_data(items: List[str], count: int) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    return result

def test_method(self, fixture_param: SomeType) -> None:
    # Test implementation
    pass

# Fixtures with proper return types
@pytest.fixture
def sample_data(self) -> Path:
    return Path("/some/path")
```

**Avoid generic or missing annotations:**
```python
# Bad - Generic or missing types
def process_data(items, count):  # No annotations
    result = {}  # Type unclear
    return result

def test_method(self, fixture_param):  # Missing types
    pass
```

### Key Benefits
- **IDE Support**: Better autocomplete, error detection, and refactoring
- **Code Clarity**: Makes function contracts explicit
- **Debugging**: Easier to identify type-related issues
- **Maintenance**: Helps future developers understand expected data types

### TypedDict Usage
When using `TypedDict` with optional fields (`total=False`), add type suppression for test files:
```python
# At the top of test files
# pyright: reportTypedDictNotRequiredAccess=false
```