# JAR Indexer MCP Server

An MCP (Model Context Protocol) server that enables LLMs to access and analyze Java/Kotlin library source code by indexing JAR files and Git repositories.

## Quick Start

```bash
# Install dependencies
uv sync

# Run the MCP server
uv run python -m src.main
```

## Adding to LLMs

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
      "args": ["run", "python", "-m", "src.main"],
      "cwd": "/path/to/jar-indexer"
    }
  }
}
```

Replace `/path/to/jar-indexer` with the actual path to this project directory.

### Continue VSCode Extension

Add to your Continue config file (`~/.continue/config.json`):

```json
{
  "mcpServers": [
    {
      "name": "jar-indexer",
      "command": "uv",
      "args": ["run", "python", "-m", "src.main"],
      "cwd": "/path/to/jar-indexer"
    }
  ]
}
```

### Cline VSCode Extension

Add to Cline's MCP settings in VSCode:

1. Open VSCode Settings
2. Search for "Cline MCP"
3. Add server configuration:
   - **Name:** `jar-indexer`
   - **Command:** `uv`
   - **Args:** `["run", "python", "-m", "src.main"]`
   - **Working Directory:** `/path/to/jar-indexer`

### OpenAI API with MCP

If using MCP with OpenAI API, configure in your MCP client:

```python
import mcp

client = mcp.Client()
await client.add_server(
    name="jar-indexer",
    command=["uv", "run", "python", "-m", "src.main"],
    cwd="/path/to/jar-indexer"
)
```

### Generic MCP Client

For any MCP-compatible client, use these connection parameters:

- **Protocol:** stdio
- **Command:** `uv run python -m src.main`
- **Working Directory:** Project root directory
- **Environment:** Ensure `uv` is in PATH

## Verification

After adding the server to your LLM client:

1. Restart the LLM application
2. The JAR Indexer should appear in available MCP servers
3. Test with a simple command like asking about available tools
4. You should see the `register_source` tool available

## Troubleshooting

**Server not connecting:**
- Ensure `uv` is installed and in PATH
- Check that the working directory path is correct
- Verify all dependencies are installed with `uv sync`

**Permission errors:**
- Ensure the LLM client has read access to the project directory
- Check that `uv` has execution permissions

**Tool not appearing:**
- Restart the LLM client completely
- Check the MCP server logs for connection errors
- Verify the JSON configuration syntax is valid

## Available Tools

Once connected, the server provides these MCP tools:

- **register_source**: Register JAR files or Git repositories for indexing

For detailed usage instructions, see the project documentation.