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

## System Commands (Darwin/macOS)
```bash
# List files (standard Unix)
ls -la

# Change directory
cd <directory>

# Search in files (use ripgrep if available)
grep -r "pattern" .

# Find files
find . -name "*.py"

# Git operations
git status
git add .
git commit -m "message"
```

## Project-Specific Storage
- **Base Directory**: `~/.jar-indexer/`
- **Code Storage**: `~/.jar-indexer/code/{group_id}/{artifact_id}/{version}/`
- **Source JARs**: `~/.jar-indexer/source-jar/{group_id}/{artifact_id}/{version}/`
- **Git Repos**: `~/.jar-indexer/git-bare/{group_id}/{artifact_id}/`