# JAR Indexer MCP Server

An MCP (Model Context Protocol) server that enables LLMs to access and analyze Java/Kotlin library source code by indexing JAR files and Git repositories.

## Quick Start

```bash
# Install dependencies
uv sync

# Run the MCP server
uv run python -m src.main
```

## Installation

1. Clone this repository:
```bash
git clone https://github.com/your-username/jar-indexer.git
cd jar-indexer
```

2. Install dependencies:
```bash
uv sync
```

3. Add to Claude Desktop configuration (see below)

### Claude Desktop

Add the following configuration to your Claude Desktop config file:

**Location:**
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

**Configuration:**
```json
{
  "mcpServers": {
    "jar-indexer": {
      "command": "uv",
      "args": ["--directory", "/path/to/jar-indexer", "run", "python", "-m", "src.main"]
    }
  }
}
```

Replace `/path/to/jar-indexer` with the actual path to this project directory.


## Available Tools

Once connected, the server provides these MCP tools:

- **register_source**: Register JAR files, directories, or Git repositories for indexing
- **index_artifact**: Index a specific Maven artifact by downloading its source JAR
- **list_artifacts**: List all registered and indexed artifacts
- **list_folder_tree**: Browse the folder structure of indexed artifacts
- **get_file**: Read the contents of specific files from indexed sources
- **search_file_names**: Search for files by name patterns within indexed sources
- **search_file_content**: Search for content within files using regex patterns

For detailed usage instructions, see the project documentation.
