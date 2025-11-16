"""Generic schema fixer for MCP tools to ensure Gemini compatibility.

This module provides a wrapper that fixes schema incompatibilities between
MCP tool schemas and Gemini's expected format. This is needed for a small
subset of MCP servers that use JSON Schema features unsupported by Gemini.

WHEN TO USE THIS:
- Most MCP servers work fine with regular McpToolset
- Only use SchemaFixingMcpToolset when you get schema-related crashes
- Testing shows only ~1% of MCP tools need this fix (e.g., @mcp-z/mcp-pdf)

THE ISSUE:
Gemini's schema converter (_sanitize_schema_formats_for_gemini in
_gemini_schema_util.py) expects all nested schema fields to be dicts.
Some MCP servers use lists for tuple validation, which is valid JSON Schema:

    items: [{type: "number"}, {type: "number"}]  # 2-element array

This causes ADK to crash with:
    AttributeError: 'list' object has no attribute 'items' at line 144

COMPATIBILITY NOTE:
Tuple validation is broadly unsupported across all LLM providers:
- Google Gemini: Crashes on tuple schemas
- Anthropic Claude: Rejects with JSON Schema draft 2020-12 validation error
- OpenAI: Limited support, often errors
- Industry research shows only ~1% of MCP tools use tuple validation

See:
- https://github.com/google/adk-python/issues/30 (array type fix)
- https://github.com/anthropics/claude-code/issues/586 (Claude tuple issue)
- https://mastra.ai/blog/mcp-tool-compatibility-layer (cross-provider analysis)
"""

from typing import Any, Dict
from google.adk.tools.mcp_tool import McpToolset


def fix_schema_for_gemini(schema: Any) -> Any:
    """
    Recursively fix MCP tool schemas to be compatible with Gemini's expectations.

    Converts tuple validation (items as list) to single-item array schemas.
    This loses type precision but enables compatibility.

    Args:
        schema: The schema object to fix (can be dict, list, or primitive)

    Returns:
        Fixed schema compatible with Gemini
    """
    # Handle None
    if schema is None:
        return None

    # Handle primitives (str, int, bool, etc.) - pass through unchanged
    if not isinstance(schema, (dict, list)):
        return schema

    # Handle lists - these appear in tuple validation schemas
    if isinstance(schema, list):
        if not schema:
            return None

        # For tuple validation like items: [{type: "number"}, {type: "number"}]
        # Convert to a single schema (use first item as representative)
        if isinstance(schema[0], dict):
            return fix_schema_for_gemini(schema[0])

        # For lists of primitives or mixed types, return None to skip
        return None

    # Handle dicts - recursively fix all values
    if isinstance(schema, dict):
        fixed = {}
        for key, value in schema.items():
            # Special handling for JSON Schema fields that might be lists for tuple validation
            # BUT exclude anyOf, oneOf, allOf which MUST remain as lists
            if key in ['items', 'prefixItems', 'contains', 'additionalItems']:
                # These can be either objects or arrays in JSON Schema
                # Convert tuple validation arrays to single object for Gemini
                if isinstance(value, list):
                    # Tuple validation - use first item if it's a dict
                    if value and isinstance(value[0], dict):
                        fixed[key] = fix_schema_for_gemini(value[0])
                    # else: skip this field entirely
                elif isinstance(value, dict):
                    fixed[key] = fix_schema_for_gemini(value)
                else:
                    # Primitive value - pass through
                    fixed[key] = value
            elif key in ['anyOf', 'oneOf', 'allOf']:
                # These MUST remain as lists, but recursively fix each element
                if isinstance(value, list):
                    fixed[key] = [fix_schema_for_gemini(
                        item) for item in value]
                else:
                    # Shouldn't happen, but handle gracefully
                    fixed[key] = value
            else:
                # Recursively fix other fields
                fixed_value = fix_schema_for_gemini(value)
                # Only include if we got a valid result
                # Skip None results UNLESS the original was None
                if fixed_value is not None:
                    fixed[key] = fixed_value
                elif value is None:
                    fixed[key] = None

        return fixed

    # Fallback - should never reach here
    return schema


class SchemaFixingMcpToolset(McpToolset):
    """
    Wrapper around McpToolset that automatically fixes schema incompatibilities.

    Use this ONLY when regular McpToolset fails with schema errors.
    Testing shows ~99% of MCP servers work fine without this fix.

    Usage:
        # Most servers - use regular McpToolset:
        toolset = McpToolset(connection_params=..., tool_name_prefix="fs_")

        # Problematic servers (e.g., @mcp-z/mcp-pdf) - use this wrapper:
        toolset = SchemaFixingMcpToolset(connection_params=..., tool_name_prefix="pdf_")
    """

    async def get_tools(self, readonly_context=None):
        """Get tools with fixed schemas."""
        from mcp.types import Tool as McpBaseTool
        from google.adk.tools.mcp_tool import MCPTool

        # Get headers if header provider exists
        headers = (
            self._header_provider(readonly_context)
            if self._header_provider and readonly_context
            else None
        )

        # Get session from session manager
        session = await self._mcp_session_manager.create_session(headers=headers)

        # Fetch available tools from the MCP server
        tools_response = await session.list_tools()

        # Fix schemas and create tools
        tools = []
        for raw_tool in tools_response.tools:
            # Fix the schema
            fixed_schema = fix_schema_for_gemini(raw_tool.inputSchema)

            # Create a new tool with the fixed schema
            # IMPORTANT: Keep original name (no prefix) so MCP server recognizes it
            fixed_raw_tool = McpBaseTool(
                name=raw_tool.name,  # Original name without prefix
                description=raw_tool.description,
                inputSchema=fixed_schema
            )

            # Wrap in MCPTool
            mcp_tool = MCPTool(
                mcp_tool=fixed_raw_tool,
                mcp_session_manager=self._mcp_session_manager,
                auth_scheme=self._auth_scheme,
                auth_credential=self._auth_credential,
                require_confirmation=self._require_confirmation,
                header_provider=self._header_provider,
            )

            # Apply prefix to the tool's display name (for agent)
            # but keep the MCP server call using the original name
            if self.tool_name_prefix:
                mcp_tool._name = f"{self.tool_name_prefix}{raw_tool.name}"

            if self._is_tool_selected(mcp_tool, readonly_context):
                tools.append(mcp_tool)

        return tools
