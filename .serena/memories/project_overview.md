# JAR Indexer - Project Overview

## Project Purpose
JAR Indexer is an MCP (Model Context Protocol) server that enables Claude Code to access and analyze Java/Kotlin library source code by indexing JAR files and Git repositories. It provides 14 MCP tools for exploring external library implementations, method signatures, and package structures.

## Problem Solved
When Claude Code analyzes Java/Kotlin projects, it often needs to access external library source code (Spring Framework, Jackson, etc.) but cannot directly access JAR file contents. JAR Indexer solves this by:

1. **Source JAR Auto-Discovery**: Finds `-sources.jar` files in Maven/Gradle caches and remote repositories
2. **Full Source Indexing**: Extracts and indexes source code by packages, classes, and methods
3. **MCP Tools**: Provides 14 tools for efficient library source exploration
4. **Smart Caching**: Locally caches indexed libraries for fast reuse

## Core Integration Scenarios
- **Method Analysis**: Get implementation details of library methods
- **Library Structure Exploration**: Browse package structures and class hierarchies
- **Bug Debugging**: Examine library source code to understand exceptions and behavior

## Architecture
- **Core Components**: SourceProcessor, StorageManager, MCP Tools (planned)
- **Storage Structure**: `~/.jar-indexer/` with Maven coordinate-based paths
- **URI Processing**: Handles file://, https://, and git+https:// sources

## Current Implementation Status
- Core source processing logic implemented
- Storage management with Maven coordinate paths
- URI parsing and validation for multiple source types
- Test structure in place
- 14 MCP tools planned but not yet implemented