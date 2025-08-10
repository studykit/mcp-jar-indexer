# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

JAR Indexer is an MCP (Model Context Protocol) server that enables Claude Code to access and analyze Java/Kotlin library source code by indexing JAR files and Git repositories. It provides 14 MCP tools for exploring external library implementations, method signatures, and package structures.

For detailed project background, problem statement, and Claude Code integration scenarios, refer to `spec/01_overview.md`.

## Essential Development Commands

### Quick Start
```bash
# Install dependencies and run tests
uv sync && uv run pytest

# Code quality check
uv run ruff check && uv run ruff format

# Run application
uv run python -m src.main
```

For complete development command reference, consult Serena's `tech_stack` memory which contains comprehensive uv commands for testing, formatting, and dependency management.

## When to Reference Documentation

### Specification Documents
- **Project Understanding**: `spec/01_overview.md` - business context, problem definition, and use case scenarios
- **System Design**: `spec/02_architecture.md` - component diagrams, data flow, and storage layout understanding
- **Technology Decisions**: `spec/03_tech_stach.md` - supported environments, library choices, and version constraints
- **MCP Tool Implementation**: `spec/04_mcp_tool_specification.md` - complete list of MCP tools to implement
- **Implementation Details**: `spec/dev/` - specific tool specifications and development workflows

### Guide Documents
- **Code Standards**: `guide/code_style_guide.md` - formatting rules, type annotations, naming conventions, and best practices

### Serena Memory Files
For comprehensive project information during development, consult Serena's memory files:

- **Codebase Structure**: `.serena/memories/codebase_structure.md` - complete directory layout, component organization, implementation status, and Maven coordinate patterns
- **Technology Stack**: `.serena/memories/tech_stack.md` - dependencies, development commands, build configuration, and utility function details  
- **Code Style Conventions**: `.serena/memories/code_style_conventions.md` - formatting standards, naming conventions, documentation requirements, and when to reference style guides

**When to consult Serena memories:**
- Understanding project architecture and current implementation status
- Getting comprehensive lists of development commands and dependencies
- Learning about file organization patterns and coding conventions
- Planning new features or understanding existing component relationships

## Configuration Highlights

Key project settings managed in configuration files:
- Base storage: `~/.jar-indexer/` directory with Maven coordinate structure
- Code style: 2-space indentation, explicit type annotations required  
- Build system: uv package manager with hatchling backend
