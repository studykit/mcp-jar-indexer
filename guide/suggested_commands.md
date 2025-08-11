# Essential Development Commands

## Dependency Management
```bash
# Install dependencies
uv sync

# Install with dev dependencies
uv sync --group dev

# Add new library (always use uv)
uv add <package-name>

# Add dev dependency
uv add --group dev <package-name>
```

## Type Checking Commands
```bash
# Run pyright type checking on entire project
uv run pyright

# Run pyright on specific file or directory
uv run pyright src/types/
uv run pyright src/utils/validation.py

# Run pyright with different output formats
uv run pyright --outputjson    # JSON output for tools
uv run pyright --stats         # Show type checking statistics
```

## Testing Commands
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

## Code Quality Commands
```bash
# Run linter
uv run ruff check

# Auto-fix linting issues
uv run ruff check --fix

# Format code
uv run ruff format

# Check both lint and format (combined)
uv run ruff check && uv run ruff format
```

## Running the Application
```bash
# Run the main module
uv run python -m src.main
```
