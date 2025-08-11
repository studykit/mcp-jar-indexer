# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

JAR Indexer is an MCP (Model Context Protocol) server that enables Claude Code to access and analyze Java/Kotlin library source code by indexing JAR files and Git repositories. It provides 14 MCP tools for exploring external library implementations, method signatures, and package structures.

## Essential Development Commands

### Quick Start
```bash
# Install dependencies and run tests
uv sync && uv run pytest

# Code quality check
uv run ruff check && uv run ruff format

# Type checking
uv run pyright

# Run application
uv run python -m src.main
```

For complete development command reference, consult `guide/suggested_commands.md` which contains comprehensive uv commands for testing, formatting, and dependency management.


## Codebase Structure

The JAR Indexer project is organized into several key directories, each with specific responsibilities and documentation:

### Directory Structure Overview

```
jar-indexer/
├── src/                    # Source code implementation
├── spec/                   # Specification and design documents  
├── guide/                  # Development guides and best practices
├── tests/                  # Test suite
└── CLAUDE.md              # This file - root project guidance
```

### Directory-Specific Documentation

For detailed information about each directory structure and contents:

- **Source Code**: `src/CLAUDE.md` - Complete overview of the source code structure, including:
  - Module responsibilities and dependencies
  - Architecture pattern (clean architecture)
  - Key design principles (type safety, error handling, modularity)
  - File-by-file descriptions of core/, tools/, utils/, and jartype/ modules

- **Specifications**: `spec/CLAUDE.md` - Comprehensive guide to specification documents, including:
  - Business context and project goals
  - System architecture and data flow
  - MCP tool API contracts and implementation plans
  - Development phases and progress tracking

### Quick Navigation

When working on specific tasks:
- **Understanding Requirements**: Start with `spec/CLAUDE.md` for context
- **Code Implementation**: Reference `src/CLAUDE.md` for structure guidance  
- **Development Guidelines**: When modifying or writing code in `src/` or `tests/` directories, ALWAYS reference `guide/code_style_guide.md` and `guide/task_completion_checklist.md` for coding standards and mandatory completion steps. Essential for ensuring code quality, testing coverage, and documentation completeness.

## Configuration Highlights

Key project settings managed in configuration files:
- Code style: 2-space indentation, explicit type annotations required  
- Build system: uv package manager with hatchling backend

## Technology Stack

- **Python 3.12+**: Primary language
- **uv**: Package manager and virtual environment
- **hatchling**: Build backend
- **aiohttp**: Async HTTP client
- **mcp**: Model Context Protocol server framework
- **requests**: HTTP library
- **gitpython**: Git repository management
- **pytest**: Testing framework
- **ruff**: Code formatting and linting
