# ADK MCP Agents

Two ADK agents demonstrating MCP patterns with code mode.

## Quick Start

```bash
uv sync

cp .env.example .env

# Run all examples
uv run python example.py

./test.sh direct   # Test direct agent
./test.sh code     # Test code mode agent


# Or run tests directly (includes verbose warnings)
uv run python test_direct_agent.py
uv run python test_code_mode_agent.py
```

## Two Agents

### 1. Direct Agent
Traditional MCP tool calling - agent calls tools directly.

```python
from adk_mcp_agent.direct_agent import direct_agent
from google.adk.runners import Runner

runner = Runner(agent=direct_agent)
response = runner.run("Calculate 5 + 3")
```

### 2. Code Mode Agent
Cloudflare code mode pattern - agent generates Python code that executes with tools.

```python
from adk_mcp_agent.code_mode_agent import code_mode_agent
from google.adk.runners import Runner

runner = Runner(agent=code_mode_agent)
response = runner.run("Calculate sum of squares from 1 to 10")
```

## Example MCP Servers

Configured in `mcp_config.py`:

- **calculator** (custom) - Arithmetic operations using FastMCP
- **filesystem** (pre-built) - File operations in /tmp
- **pdf** (pre-built) - PDF text extraction


## Adding Custom MCP Servers

1. Create server in `servers/your_server/mcp_server.py`:

```python
from fastmcp import FastMCP

mcp = FastMCP(name="your_server")

@mcp.tool
async def your_tool(param: str) -> dict:
    return {"result": param}

if __name__ == "__main__":
    mcp.run()
```

2. Add to `mcp_config.py`:

```python
"your_server": {
    "command": "python",
    "args": ["-m", "adk_mcp_agent.servers.your_server.mcp_server"],
    "env": {"PYTHONPATH": AGENT_DIR}
}
```

## Known Issues

## Schema Compatibility Issue

### The Problem

Some pre-built MCP servers use **tuple validation** in their JSON schemas, which is valid JSON Schema but unsupported by most LLM providers:

```json
"items": [{"type": "number"}, {"type": "number"}]  // 2-element tuple
```

This causes Google ADK/Gemini to crash with:
```
AttributeError: 'list' object has no attribute 'items'
```

### Impact

- **~1% of MCP tools** are affected (based on testing 84+ tools)
- **Affected server**: `@mcp-z/mcp-pdf` (in the `create-pdf` tool)
- **Clean servers**: filesystem, playwright, memory, github, everything, etc.

### Cross-Provider Compatibility

Tuple validation is broadly unsupported:
- **Google Gemini**: Runtime crash in schema converter
