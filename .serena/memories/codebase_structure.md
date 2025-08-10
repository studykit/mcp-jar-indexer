# Codebase Structure and Organization

## Directory Layout
```
jar-indexer/
├── src/                          # Source code
│   ├── core/                     # Core business logic
│   │   ├── source_processor.py   # URI processing and source handling
│   │   ├── storage.py             # Storage management with Maven paths
│   │   └── __init__.py
│   ├── tools/                    # MCP tools (planned, 14 total)
│   │   └── __init__.py
│   ├── utils/                    # Utility functions
│   │   └── __init__.py
│   └── main.py                   # Application entry point
├── tests/                        # Test suite
│   ├── core/                     # Core logic tests
│   │   ├── test_source_processor.py
│   │   ├── test_storage.py
│   │   └── __init__.py
│   └── __init__.py
├── spec/                         # Project documentation
│   ├── 01_overview.md            # Project purpose and problem definition
│   ├── 02_architecture.md        # System architecture and components
│   ├── 03_tech_stach.md          # Technology stack details
│   ├── 04_mcp_tool_specification.md  # MCP tools specification
│   └── dev/                      # Development-specific docs
│       └── 02_register_source.md # Source registration specification
├── pyproject.toml                # Project configuration and dependencies
├── CLAUDE.md                     # Claude Code integration instructions
└── README.md                     # Project documentation
```

## Key Components

### Core Classes
- **SourceProcessor**: Handles different URI types (file://, https://, git+https://)
- **StorageManager**: Manages `~/.jar-indexer/` directory with Maven coordinate paths

### Storage Organization
- **Base Path**: `~/.jar-indexer/`
- **Code Storage**: Indexed source files organized by Maven coordinates
- **Source JARs**: Downloaded/copied JAR files
- **Git Bare**: Git repositories for source access

### URI Processing Flow
1. **URI Parsing**: Classifies URIs by type (file, http, git)
2. **Validation**: Checks accessibility and format
3. **Processing**: Type-specific handling (copy, download, clone)
4. **Storage**: Organized using Maven coordinate paths

### Maven Coordinate Pattern
- **Format**: `{group.id}/{artifact-id}/{version}`
- **Example**: `org.springframework/spring-core/5.3.21`
- **Usage**: All storage paths follow this convention

## Implementation Status
- ✅ Core source processing logic
- ✅ Storage management system
- ✅ URI parsing and validation
- ✅ Test structure established
- ⏳ MCP tools (14 planned, not yet implemented)
- ⏳ Git repository handling
- ⏳ JAR indexing and extraction