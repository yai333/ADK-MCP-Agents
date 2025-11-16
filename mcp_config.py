import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

AGENT_DIR = os.path.dirname(os.path.dirname(__file__))

MCP_SERVERS = {
    # Pre-built MCP servers
    "filesystem": {
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-filesystem", AGENT_DIR]
    },
    "pdf": {
        "command": "npx",
        "args": ["-y", "@mcp-z/mcp-pdf"]
    },
    # docs_fetch has initialization timeout issues with ADK - commented out for now
    # "docs_fetch": {
    #     "command": "npx",
    #     "args": ["-y", "@iflow-mcp/docs-fetch-mcp"]
    # },
    # Local custom MCP server (using FastMCP)
    "calculator": {
        "command": "python",
        "args": ["-m", "adk_mcp_agent.servers.calculator.mcp_server"],
        "env": {"PYTHONPATH": AGENT_DIR}
    },
    # BigQuery MCP server
    "bigquery": {
        "command": "npx",
        "args": [
            "-y",
            "@ergut/mcp-bigquery-server",
            "--project-id",
            os.getenv("BIGQUERY_PROJECT", "lively-metrics-295911"),
            "--location",
            "australia-southeast1"
        ]
    }
}
