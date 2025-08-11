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

## When to Reference Documentation

### Specification Documents
For comprehensive guidance on when and how to use specification documents, see **`spec/CLAUDE.md`** which provides:
- Detailed descriptions of each specification document's purpose
- When to reference specific files for different types of work
- Document relationships and dependencies
- Current implementation status and progress tracking
- Complete folder structure and content overviews

**Quick Reference**:
- `spec/01_overview.md` - Business context and project goals
- `spec/02_architecture.md` - System design and data flow
- `spec/03_mcp_tool_specification.md` - Complete MCP tool API contracts
- `spec/dev/` - Implementation plans and detailed technical specifications

### Guide Documents
- **Code Standards**: `guide/code_style_guide.md` - Reference when writing new code, implementing functions, or making code quality improvements. Essential for indentation standards (2-space rule), type annotation requirements (always explicit), naming conventions, docstring formatting, error handling patterns, and testing standards.
- **Codebase Structure**: `guide/codebase.md` - Reference when navigating the project, adding new modules, understanding file organization, or determining where to place new functionality. Critical for understanding the clean architecture pattern, module responsibilities, and test structure organization.
- **Task Completion Checklist**: `guide/task_completion_checklist.md` - Reference for the mandatory steps and best practices to follow when completing development tasks. Essential for ensuring code quality, testing coverage, and documentation completeness.

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
