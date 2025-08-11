# src/ Directory Structure

This document outlines the codebase structure for the JAR Indexer MCP Server source code.

## Directory Overview

```
src/
├── main.py                    # Entry point and MCP server setup
├── core/                      # Core business logic
│   ├── __init__.py
│   ├── git_handler.py         # Git repository management
│   ├── source_processor.py    # Source code processing and indexing
│   └── storage.py             # Storage directory management
├── jartype/                   # Type definitions
│   ├── __init__.py
│   └── core_types.py          # Core type definitions and TypedDict classes
├── tools/                     # MCP tool implementations
│   ├── __init__.py
│   └── register_source.py     # register_source MCP tool
└── utils/                     # Utility modules
    ├── __init__.py
    ├── artifact_utils.py      # Maven artifact handling utilities
    ├── download_utils.py      # File download and validation
    ├── filesystem_exploration.py  # File system exploration utilities
    ├── path_utils.py          # Path manipulation utilities
    ├── source_extraction.py   # Source extraction and copying
    └── validation.py          # Input validation utilities
```

## Module Responsibilities

### `main.py`
- **Purpose**: MCP server entry point and configuration
- **Key Functions**: Server creation, tool registration, async main loop
- **Dependencies**: MCP framework, tools module

### `core/` - Core Business Logic
- **`git_handler.py`**: Git repository cloning, authentication, and management
- **`source_processor.py`**: Source code indexing and processing logic  
- **`storage.py`**: Storage directory structure and path management

### `jartype/` - Type Definitions
- **`core_types.py`**: TypedDict classes for search matches, configurations, and data structures

### `tools/` - MCP Tool Implementations
- **`register_source.py`**: Implementation of the `register_source` MCP tool for registering JAR files, directories, and Git repositories

### `utils/` - Utility Modules
- **`artifact_utils.py`**: Maven coordinate handling and artifact utilities
- **`download_utils.py`**: HTTP file downloading and JAR validation
- **`filesystem_exploration.py`**: Directory traversal and file system exploration
- **`path_utils.py`**: Path manipulation and normalization utilities
- **`source_extraction.py`**: Safe file copying and source extraction
- **`validation.py`**: Input validation for URIs and Maven coordinates

## Architecture Pattern

The codebase follows a clean architecture pattern with clear separation of concerns:
- **Entry Point**: `main.py` handles MCP server setup
- **Tools Layer**: MCP tool implementations in `tools/`
- **Core Layer**: Business logic in `core/`
- **Utilities Layer**: Reusable utilities in `utils/`
- **Types Layer**: Type definitions in `jartype/`

## Key Design Principles

1. **Type Safety**: All modules use explicit type annotations and TypedDict classes
2. **Error Handling**: Comprehensive error handling with custom exception classes
3. **Modularity**: Clear module boundaries with single responsibilities  
4. **Async Support**: Async/await patterns for I/O operations
5. **Clean Architecture**: Dependencies flow inward from tools → core → utils
