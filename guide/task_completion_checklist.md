# Task Completion Checklist

## Required Steps When Completing Development Tasks

### 1. Code Quality Checks (MANDATORY)
```bash
# Always run both linting and formatting
uv run ruff check
uv run ruff format
```
- Fix any linting errors before considering task complete
- Ensure code follows project formatting standards

### 2. Testing Requirements
```bash
# Run all tests to ensure nothing is broken
uv run pytest

# For new features, run specific test modules
uv run pytest tests/core/ -v
```
- All tests must pass before completion
- Write new tests for new functionality
- Ensure test coverage for edge cases

### 3. Code Review Self-Check
- Verify type hints are comprehensive
- Check docstring completeness (Args, Returns, Raises)
- Ensure error handling with descriptive messages
- Use appropriate access modifiers (private methods with `_` prefix)

### 4. Documentation Updates
- Update relevant spec documents if architecture changes
- Ensure CLAUDE.md is updated with new commands or conventions
- Add or update docstrings for new/modified code

### 5. Pre-commit Validation
- Run the combined quality check: `uv run ruff check && uv run ruff format`
- Verify tests pass: `uv run pytest`
- Check git status for untracked files that should be committed

### 6. Storage and Path Validation
- Ensure new code follows Maven coordinate storage patterns
- Validate storage paths use StorageManager methods
- Check file permissions and directory creation logic

## Never Skip These Steps
1. Linting and formatting checks
2. Full test suite execution  
3. Type hint validation
4. Error handling verification
5. Documentation completeness
