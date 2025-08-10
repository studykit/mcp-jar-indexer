# Code Style Guide

This document defines the coding standards and style guidelines for the JAR Indexer project.

## Indentation Standards

**Follow project-wide indentation configuration:**

- **Python Files**: 2 spaces (configured in `pyproject.toml` - `indent-width = 2`)
- **All Files**: Use spaces, not tabs (`.editorconfig` - `indent_style = space`)
- **General**: 2 spaces for most file types (JSON, YAML, JS/TS, HTML/CSS)
- **Exception**: Makefiles use tabs as required by Make

```python
# Good - 2 space indentation
def example_function(param: str) -> None:
  if param:
    result = process_data(param)
    return result
  return None

class ExampleClass:
  def __init__(self, value: int) -> None:
    self.value = value
    
  def method(self) -> str:
    return f"Value: {self.value}"
```

**Configuration Sources:**
- `.editorconfig`: `indent_size = 2`, `indent_style = space`
- `pyproject.toml`: `[tool.ruff.format]` `indent-style = "space"`
- Ruff enforces consistent indentation via formatting

## Type Annotations

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

## Import Organization

Follow PEP 8 import ordering:
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

## Naming Conventions

- **Classes**: PascalCase (e.g., `SourceProcessor`, `StorageManager`)
- **Functions and variables**: snake_case (e.g., `parse_uri`, `group_id`)
- **Constants**: UPPER_SNAKE_CASE (e.g., `DEFAULT_TIMEOUT`, `MAX_RETRIES`)
- **Private members**: Leading underscore (e.g., `_parse_file_uri`)

## Documentation

### Docstrings
Use Google-style docstrings for all public functions and classes:

```python
def process_source(
  self,
  group_id: str,
  artifact_id: str,
  version: str,
  source_uri: str,
  git_ref: Optional[str] = None,
) -> ProcessResult:
  """Process source URI and prepare it for indexing.

  Args:
      group_id: Maven group ID
      artifact_id: Maven artifact ID
      version: Maven version
      source_uri: Source URI to process
      git_ref: Git reference (branch/tag/commit) for Git repositories

  Returns:
      Processing result with status and paths

  Raises:
      ValueError: If processing fails
  """
```

### Comments
- Use comments sparingly for complex logic
- Prefer self-documenting code over comments
- When needed, explain "why" not "what"

## Error Handling

- Use specific exception types when possible
- Include helpful error messages with context
- Clean up resources in finally blocks or use context managers

```python
try:
  response = requests.get(url, stream=True, timeout=30)
  response.raise_for_status()
except requests.RequestException as e:
  raise ValueError(f"Failed to download JAR from {url}: {str(e)}")
```

## Testing Standards

- Test file names: `test_<module_name>.py`
- Test class names: `Test<ClassName>`
- Test method names: `test_<method_name>_<scenario>`
- Use descriptive test method names that explain the scenario

```python
def test_parse_uri_with_valid_jar_file_returns_file_type(self):
  """Test that parsing a valid JAR file URI returns file type."""
```

## File Structure

- Keep modules focused on single responsibilities
- Use `__init__.py` for package initialization only
- Organize related functionality into packages
- Separate concerns (core logic, utilities, tools)