# JAR Indexer Specification Documents

This document provides an overview of the specification folder structure and its contents for the JAR Indexer MCP server project.

## Folder Structure

```
spec/
├── CLAUDE.md                           # This overview document
├── 01_overview.md                      # Project overview and business context
├── 02_architecture.md                  # System architecture and data flow
├── 03_mcp_tool_specification.md        # Complete MCP tools specification
└── dev/                               # Development specifications
    ├── index_artifact/                # index_artifact tool implementation specs
    │   ├── overview.md                # 3-phase implementation plan
    │   └── phase_1/                   # Phase 1 detailed specifications
    │       ├── TODO.md                # TODO list (empty placeholder)
    │       └── design_spec.md         # Core function specifications for phase 1
    └── register_source/               # register_source tool implementation specs
        ├── TODO.md                    # Implementation progress tracking
        └── design_spec.md             # Complete implementation design
```

## Document Purposes

### Core Specification Documents

#### 01_overview.md
**When to Reference**: Understanding project goals, business context, problem definition, and use case scenarios.

**Content Overview**:
- Project overview and problem definition (in Korean)
- Claude Code integration challenges with external library source code access
- JAR Indexer solution and integration scenarios
- Real-world examples with Spring Framework, Jackson libraries

**Key Usage**: Essential for understanding why this project exists and what problems it solves.

#### 02_architecture.md
**When to Reference**: Working with component interactions, storage paths, error handling flows, or understanding data flow between MCP tools and storage layers.

**Content Overview**:
- System component diagrams
- Storage layer directory structure (`~/.jar-indexer/`)
- Data flow diagrams (Claude Code → MCP Tools → Storage)
- Error handling and indexing workflows

**Key Usage**: Critical for structural changes, debugging, and understanding how components interact.

#### 03_mcp_tool_specification.md
**When to Reference**: Implementing new MCP tools, understanding tool schemas, or checking complete tool requirements.

**Content Overview**:
- Complete specification for all 14 MCP tools (in English)
- Tool parameters, return values, and error response formats
- Usage examples and workflows
- Common response status codes and error handling

**Key Usage**: The definitive reference for MCP tool implementation and API contracts.

### Development Specifications (`dev/` folder)

#### dev/register_source/design_spec.md
**When to Reference**: Implementing or modifying the `register_source` MCP tool.

**Content Overview**:
- 6-phase implementation plan (Phase 1-6)
- Git repository, JAR file, and local directory processing logic
- Storage management, error handling, and auto-indexing features
- Technical considerations for concurrency, security, performance

**Key Usage**: Step-by-step implementation guide with detailed architecture decisions.

#### dev/register_source/TODO.md
**When to Reference**: Tracking implementation progress for the `register_source` tool.

**Key Usage**: Progress tracking and identifying remaining work for register_source implementation.

#### dev/index_artifact/overview.md
**When to Reference**: Understanding the 3-phase implementation strategy for `index_artifact`.

**Content Overview**:
- 3-phase implementation strategy:
  - Phase 1: Basic file operations and source storage
  - Phase 2: Universal Ctags indexing
  - Phase 3: AST parsing and detailed analysis
- Goals, implementation details, and characteristics for each phase
- Implementation priorities and incremental development approach

**Key Usage**: Understanding the overall strategy and development roadmap for index_artifact.

#### dev/index_artifact/phase_1/design_spec.md
**When to Reference**: Implementing the core functions for `index_artifact` Phase 1.

**Content Overview**:
- Detailed specifications for 32 core functions
- Source extraction/copying functions (JAR, Git, directory)
- File system exploration functions
- Utility and MCP tool functions
- Precise function signatures, parameters, return values, and exception handling

**Key Usage**: The definitive reference for implementing Phase 1 core functionality with exact function specifications.

#### dev/index_artifact/phase_1/TODO.md
**When to Reference**: This file exists but is currently empty (placeholder).

**Content Overview**: Empty placeholder file

**Key Usage**: Not currently used - likely intended for Phase 1 specific TODO tracking.

## Document Relationships

1. **Hierarchy**: `01_overview.md` → `02_architecture.md` → `03_mcp_tool_specification.md`
2. **Implementation Flow**: `03_mcp_tool_specification.md` → `dev/*/design_spec.md` → specific function implementation
3. **Progress Tracking**: `dev/*/TODO.md` files track implementation status
4. **Phase Dependencies**: `dev/index_artifact/overview.md` → `dev/index_artifact/phase_1/design_spec.md`

## How to Use These Documents

1. **Start with Overview**: Read `01_overview.md` to understand the business context
2. **Understand Architecture**: Review `02_architecture.md` for system design
3. **Check API Contracts**: Use `03_mcp_tool_specification.md` for exact MCP tool requirements
4. **Follow Implementation Plans**: Use `dev/*/design_spec.md` for step-by-step implementation guidance
5. **Track Progress**: Check `dev/*/TODO.md` files for current implementation status
6. **Reference Function Specs**: Use `phase_1/design_spec.md` for precise function implementations

These specifications provide comprehensive guidance for developing, maintaining, and extending the JAR Indexer MCP server, with clear tracking of implementation progress and detailed technical specifications.
