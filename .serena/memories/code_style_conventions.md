# Code Style and Conventions

## Formatting (Ruff Configuration)
- **Line Length**: 88 characters (Black compatible)
- **Indentation**: 2 spaces (configured in ruff, unusual for Python)
- **Quote Style**: Double quotes for strings
- **Import Style**: Standard Python import organization
- **Line Ending**: Auto-detect

## Code Structure Patterns
- **Class Organization**: Single responsibility classes with clear method grouping
- **Method Naming**: Snake_case with descriptive names
- **Private Methods**: Prefixed with single underscore `_method_name`
- **Type Hints**: Comprehensive type hints throughout codebase
- **Error Handling**: Specific ValueError exceptions with descriptive messages

## Documentation Standards
- **Docstrings**: Google-style docstrings with Args, Returns, and Raises sections
- **Class Docstrings**: Brief purpose description
- **Method Docstrings**: Detailed parameter and return value documentation
- **Inline Comments**: Used sparingly for complex logic explanation

## Testing Conventions
- **Test Structure**: Mirrors source code structure under `tests/` directory
- **Test Files**: Named `test_<module_name>.py`
- **Test Framework**: pytest with standard conventions

## Project Structure Patterns
- **Core Logic**: Located in `src/core/` directory
- **Utilities**: Separate `src/utils/` directory
- **Tools**: MCP tools in `src/tools/` directory
- **Configuration**: Project-level configuration in pyproject.toml
- **Documentation**: Comprehensive spec documents in `spec/` directory

## Maven Coordinate Usage
- **Path Structure**: Uses Maven coordinates for all storage paths
- **Format**: `{group.id}/{artifact-id}/{version}`
- **Example**: `org.springframework/spring-core/5.3.21`
- **Implementation**: Centralized in StorageManager class