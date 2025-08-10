# Technology Stack and Development Environment

## Python Environment
- **Version**: Python 3.12+ (required)
- **Package Manager**: uv (for dependency management and task running)
- **Virtual Environment**: Managed via uv

## Core Dependencies
- **MCP Framework**: `mcp>=1.12.4` - Model Context Protocol server implementation
- **HTTP Client**: `aiohttp>=3.12.15` - Async HTTP for MCP server operations
- **HTTP Requests**: `requests>=2.32.4` - Synchronous HTTP for downloads
- **Git Operations**: `gitpython>=3.1.0` - Git repository handling
- **Path Handling**: `pathlib>=1.0.0` - Enhanced path operations

## Development Dependencies
- **Code Formatting**: `ruff>=0.12.8` - Fast Python linter and formatter
- **Testing**: `pytest>=8.4.1` - Testing framework
- **Type Checking**: `mypy>=1.17.1` - Static type checker
- **Type Stubs**: `types-requests>=2.32.4.20250809` - Type annotations for requests

## Code Quality Configuration
- **Line Length**: 88 characters (Black compatible)
- **Indentation**: 2 spaces (unusual for Python, configured in pyproject.toml)
- **Target Version**: Python 3.12
- **Linting Rules**: Pyflakes (F) and pycodestyle (E4, E7, E9) enabled
- **Formatting**: Double quotes, space indentation, auto line ending detection

## Development Commands
```bash
# Testing
uv run pytest                                    # Run all tests
uv run pytest -v                               # Verbose output
uv run pytest tests/core/test_source_processor.py -v  # Specific module

# Code Quality  
uv run ruff check                               # Run linter
uv run ruff check --fix                        # Auto-fix issues
uv run ruff format                             # Format code
uv run ruff check && uv run ruff format        # Combined check

# Development Environment
uv sync                                         # Install dependencies
uv sync --group dev                            # Install with dev dependencies
uv add <package-name>                          # Add library
uv add --group dev <package-name>              # Add dev dependency
uv run python -m src.main                     # Run application
```

## Build System
- **Build Backend**: `hatchling` (modern Python packaging)
- **Package Structure**: `src/` layout with wheel packaging
- **Configuration**: All in `pyproject.toml` (modern Python standard)

## IDE Integration
- **Editor Config**: `.editorconfig` for consistent formatting across editors
- **Claude Code Integration**: Configured in `CLAUDE.md` with development commands
- **Permissions**: `.claude/settings.local.json` allows uv pytest and ruff execution

## File Organization Standards
- **Source Code**: `src/` directory with core, tools, utils packages
- **Tests**: `tests/` directory mirroring source structure
- **Documentation**: 
  - Project specs in `spec/` directory
  - Development guides in `guide/` directory
- **Configuration**: Root-level configuration files

## Storage Architecture
- **Base Directory**: `~/.jar-indexer/` (configurable)
- **Structure**:
  - `code/` - Indexed source files by Maven coordinates
  - `source-jar/` - Downloaded JAR files by Maven coordinates  
  - `git-bare/` - Bare Git repositories by Maven coordinates
- **Path Format**: `{group.id}/{artifact-id}/{version}`

## Utility Functions Implementation
- **File Operations**: Download, copy, symlink creation with error handling
- **JAR Validation**: File type verification and integrity checking
- **Directory Management**: Safe directory creation and permission handling
- **File Information**: Size, modification time, and checksum utilities

## MCP Server Features (Planned)
- **14 MCP Tools**: For library exploration and source code access
- **URI Processing**: Support for file://, https://, git+https:// sources
- **Maven Integration**: Coordinate-based organization and path management
- **Git Repository Support**: Bare repositories with worktree management