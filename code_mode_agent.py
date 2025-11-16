import json
import asyncio
from google.adk.agents import Agent
from google.adk.tools.tool_context import ToolContext
from google.adk.tools.mcp_tool import StdioConnectionParams
from mcp import StdioServerParameters
import code_executor
import tool_registry
import mcp_config
from schema_fixer import SchemaFixingMcpToolset


async def list_mcp_tools(tool_context: ToolContext, include_schemas: bool = False) -> str:
    """List all available MCP tools.

    Args:
        include_schemas: If False (default), returns only names and descriptions (lightweight).
                        If True, includes full parameter schemas (heavier, use sparingly).

    For 50+ tools, use False to avoid context bloat, then call get_tool_schema() for specific tools.
    """
    registry = tool_registry.get_registry()
    tools = await registry.list_tools(include_schemas=include_schemas)
    return json.dumps({"available_tools": tools}, indent=2)


async def get_tool_schema(tool_name: str, tool_context: ToolContext) -> str:
    """Get the full schema for a specific tool.

    Use this for lazy loading when you have many tools - only fetch schemas you need.
    """
    registry = tool_registry.get_registry()
    schema = await registry.get_tool_schema(tool_name)
    return json.dumps(schema, indent=2)


def execute_python_code(code: str, tool_context: ToolContext) -> str:
    """Execute Python code with sandboxing. A 'tools' object is available to call MCP tools."""
    # Log the generated code
    print("\n" + "="*80)
    print("GENERATED CODE:")
    print("="*80)
    print(code)
    print("="*80 + "\n")

    registry = tool_registry.get_registry()
    globals_dict = {'tools': registry}

    # Execute with 30 second timeout and allow imports for MCP tools
    result = code_executor.execute_code(
        code,
        capture_output=True,
        globals_dict=globals_dict,
        timeout=30,
        allow_imports=True
    )

    # Check if variables contain coroutines (forgot to await)
    variables = result.get('variables', {})
    if variables:
        for key, value in variables.items():
            if hasattr(value, '__name__') and 'coroutine' in str(type(value)):
                result['success'] = False
                result['error'] = f"Variable '{key}' is a coroutine - you forgot to use 'await' when calling async tools. All MCP tool calls MUST use 'await'."
                variables = {}
                break

    filtered_result = {
        'success': result['success'],
        'stdout': result['stdout'][:1000] if result['stdout'] else '',
        'stderr': result['stderr'][:500] if result['stderr'] else '',
        # Convert to string to avoid JSON serialization issues
        'variables': str(variables) if variables else {},
        'error': result.get('error')
    }
    return json.dumps(filtered_result, indent=2)


# Register MCP toolsets
# Using SchemaFixingMcpToolset for all servers to handle tuple validation schemas
# that crash Gemini's schema converter. Clean schemas pass through unchanged.
registry = tool_registry.get_registry()
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
    registry.register_mcp_toolset(server_name, toolset)


code_mode_agent = Agent(
    name="code_mode_agent",
    model="gemini-2.5-flash",
    description="Agent that executes Python code with MCP tools",
    instruction="""Code execution assistant. You have 3 functions available to call directly:
1. list_mcp_tools() - discover MCP tools
2. get_tool_schema(tool_name) - get schema for an MCP tool
3. execute_python_code(code="...") - execute Python code

MCP tools (like calculator_add, pdf_create-simple-pdf) are NOT called directly.
They are ONLY accessible inside Python code via the 'tools' object.

YOUR WORKFLOW for every request:
Step 1: Call list_mcp_tools() directly
Step 2: Call get_tool_schema(tool_name) directly for tools you need
Step 3: Call execute_python_code(code="...") with Python code that uses tools.tool_name()

Example:
User: "Calculate 5 + 3"
You call: list_mcp_tools() → see calculator_add exists
You call: get_tool_schema("calculator_add") → see it needs params a, b
You call: execute_python_code(code="result = await tools.calculator_add(a=5, b=3)")

CRITICAL:
- MCP tools go INSIDE execute_python_code, not called directly
- Use await for all tools.* calls in Python
- Tool responses can be numbers, strings, or dicts - use them directly
- When tools return file paths (e.g., "Output: /path/to/file"), report the ACTUAL path, not the requested filename
- Store answer in 'result' variable
- Complete all 3 steps, don't ask permission
""",
    tools=[list_mcp_tools, get_tool_schema, execute_python_code],
)
