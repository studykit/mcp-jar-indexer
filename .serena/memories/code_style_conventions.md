# Code Style and Conventions

## Project Configuration
- **Documentation Structure**: CLAUDE.md references separate guide files for detailed standards
- **Guide Organization**: Dedicated `guide/` directory for development standards
- **Reference Separation**: 
  - `spec/` documents for project specifications and architecture
  - `guide/` documents for implementation standards and best practices

## Formatting Standards (Updated)
- **Line Length**: 88 characters (Black compatible)
- **Indentation**: 2 spaces (configured in pyproject.toml `indent-width = 2`)
- **Quote Style**: Double quotes for strings
- **Import Style**: PEP 8 import organization (standard library, third-party, local)
- **Line Ending**: Auto-detect
- **Configuration Sources**:
  - `.editorconfig`: `indent_size = 2`, `indent_style = space`
  - `pyproject.toml`: `[tool.ruff.format]` with `indent-style = "space"`
  - Ruff enforces consistent indentation via formatting

## Code Structure Patterns (Refined)
- **Class Organization**: Single responsibility with clear method grouping
- **Method Naming**: snake_case with descriptive names
- **Private Methods**: Prefixed with single underscore `_method_name`
- **Constants**: UPPER_SNAKE_CASE (e.g., `DEFAULT_TIMEOUT`, `MAX_RETRIES`)
- **Classes**: PascalCase (e.g., `SourceProcessor`, `StorageManager`)
- **Type Hints**: Explicit type annotations required for all functions
- **Error Handling**: Specific exception types with contextual error messages

## Documentation Standards (Enhanced)
- **Docstrings**: Google-style docstrings with Args, Returns, and Raises sections
- **Class Docstrings**: Brief purpose description
- **Method Docstrings**: Detailed parameter and return value documentation
- **Inline Comments**: Used sparingly for complex logic, explain "why" not "what"
- **Reference Guide**: Complete standards in `guide/code_style_guide.md`

## Testing Conventions
- **Test Structure**: Mirrors source code structure under `tests/` directory
- **Test Files**: Named `test_<module_name>.py`
- **Test Classes**: Named `Test<ClassName>`
- **Test Methods**: Named `test_<method_name>_<scenario>`
- **Test Framework**: pytest with standard conventions
- **Descriptive Names**: Test method names explain the scenario being tested

## Import Organization (PEP 8)
1. Standard library imports
2. Related third-party library imports  
3. Local application/library imports

```python
# Standard library
import os
from pathlib import Path
from typing import Dict, List, Optional

# Third-party
import requests
from mcp import types

# Local imports
from .storage import StorageManager
from ..utils.validation import validate_maven_coordinates
```

## Project Structure Patterns
- **Core Logic**: Located in `src/core/` directory
- **Utilities**: Separate `src/utils/` directory with file operations and validation
- **Tools**: MCP tools in `src/tools/` directory
- **Guides**: Development standards in `guide/` directory
- **Configuration**: Project-level configuration in pyproject.toml
- **Documentation**: 
  - Specifications in `spec/` directory
  - Implementation guides in `guide/` directory

## Maven Coordinate Usage
- **Path Structure**: Uses Maven coordinates for all storage paths
- **Format**: `{group.id}/{artifact-id}/{version}`
- **Example**: `org.springframework/spring-core/5.3.21`
- **Implementation**: Centralized in StorageManager class

## When to Reference Standards
- **Code Style Guide**: Before writing new code, during reviews, IDE setup, onboarding
- **Key Requirements**: 2-space indentation, explicit type annotations, Google docstrings
- **Enforcement**: Automated via Ruff formatting and linting