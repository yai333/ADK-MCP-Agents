import asyncio
from google.adk.agents import Agent
from google.adk.tools.mcp_tool import StdioConnectionParams
from mcp import StdioServerParameters
import mcp_config
from schema_fixer import SchemaFixingMcpToolset


mcp_toolsets = []
for server_name, config in mcp_config.MCP_SERVERS.items():
    toolset = SchemaFixingMcpToolset(
        connection_params=StdioConnectionParams(
            server_params=StdioServerParameters(
                command=config['command'],
                args=config['args'],
                env=config.get('env')
            ),
            timeout=30.0
        ),
        tool_name_prefix=f'{server_name}_'
    )
    mcp_toolsets.append(toolset)

direct_agent = Agent(
    name="direct_mcp_agent",
    model="gemini-2.5-flash",
    description="Agent with MCP tools",
    instruction="You are a helpful assistant. Use the available tools to accomplish user requests.",
    tools=mcp_toolsets,
)
