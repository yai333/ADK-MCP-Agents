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


async def initialize_mcp_tools():
    """Initialize all MCP tool sessions before agent uses them"""
    print("\n[Direct Agent] Pre-initializing MCP tools...")
    for toolset in mcp_toolsets:
        try:
            # Create a session to initialize the MCP connection
            session = await toolset._mcp_session_manager.create_session()
            tools_list = await session.list_tools()
            prefix = toolset.tool_name_prefix.rstrip('_')
            print(f"  ✓ {prefix}: {len(tools_list.tools)} tools loaded")
        except Exception as e:
            print(f"  ✗ Failed to initialize {toolset.tool_name_prefix}: {e}")
    print("[Direct Agent] MCP tools ready\n")


direct_agent = Agent(
    name="direct_mcp_agent",
    model="gemini-2.5-flash",
    description="Agent with MCP tools",
    instruction="You are a helpful assistant. Use the available tools to accomplish user requests.",
    tools=mcp_toolsets,
)
