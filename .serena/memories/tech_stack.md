# Tech Stack and Dependencies

## Python Version
- **Required**: Python 3.12+
- **Target**: Python 3.12 (configured in ruff)

## Core Dependencies
- **mcp**: >=1.12.4 - Model Context Protocol implementation
- **aiohttp**: >=3.12.15 - Async HTTP client/server
- **requests**: >=2.32.4 - HTTP library for sync operations
- **gitpython**: >=3.1.0 - Git operations and repository handling
- **pathlib**: >=1.0.0 - Path operations

## Development Dependencies
- **ruff**: >=0.8.12 - Linting and code formatting
- **pytest**: >=8.0.0 - Testing framework

## Build System
- **hatchling** - Modern Python packaging build backend
- **uv** - Fast Python package installer and dependency manager

## System Requirements
- **Platform**: Supports Darwin (macOS), likely Linux/Windows compatible
- **Git**: Required for Git repository operations
- **Storage**: Uses `~/.jar-indexer/` directory for local caching

## Removed Dependencies
- **tree-sitter libraries**: Removed tree-sitter, tree-sitter-java, and tree-sitter-kotlin (no longer used for parsing)