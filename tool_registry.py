from typing import Any, List


class ToolRegistry:
    """Registry that exposes MCP tools for code execution."""

    def __init__(self):
        self._mcp_toolsets = {}
        self._tools_cache = {}  # tool_name -> tool info dict
        self._sessions_cache = {}  # tool_name -> MCP session

    def register_mcp_toolset(self, name: str, toolset):
        """Register an MCP toolset."""
        self._mcp_toolsets[name] = toolset

    async def _ensure_tools_loaded(self):
        """Load tools from all registered MCP toolsets."""
        if self._tools_cache:
            return

        for name, toolset in self._mcp_toolsets.items():
            # Get MCP session
            session = await toolset._mcp_session_manager.create_session()

            # Fetch tools from MCP server
            tools_response = await session.list_tools()

            for raw_tool in tools_response.tools:
                # Apply prefix
                tool_name = raw_tool.name
                if toolset.tool_name_prefix:
                    tool_name = f"{toolset.tool_name_prefix}{raw_tool.name}"

                # Store tool info and session
                self._tools_cache[tool_name] = {
                    'name': tool_name,
                    'raw_name': raw_tool.name,  # Original name without prefix
                    'description': raw_tool.description,
                    'inputSchema': raw_tool.inputSchema
                }
                self._sessions_cache[tool_name] = session

    async def list_tools(self, include_schemas: bool = False) -> List[dict]:
        """List all available tools.

        Args:
            include_schemas: If True, include full parameter schemas.
                           If False, only return names and descriptions (lighter weight).
        """
        await self._ensure_tools_loaded()

        tools_info = []
        for tool_name, tool_info in self._tools_cache.items():
            if include_schemas:
                # Full schema (heavy - use sparingly)
                tools_info.append({
                    "name": tool_info['name'],
                    "description": tool_info['description'],
                    "parameters": tool_info['inputSchema']
                })
            else:
                # Lightweight - just name and description
                tools_info.append({
                    "name": tool_info['name'],
                    "description": tool_info['description']
                })

        return tools_info

    async def get_tool_schema(self, tool_name: str) -> dict:
        """Get the full schema for a specific tool.

        Use this for lazy loading - only fetch schemas for tools you actually need.
        Handles underscore→hyphen conversion for tools with hyphens in their names.
        """
        await self._ensure_tools_loaded()

        # First try the exact name
        if tool_name in self._tools_cache:
            tool_info = self._tools_cache[tool_name]
            return {
                "name": tool_info['name'],
                "description": tool_info['description'],
                "parameters": tool_info['inputSchema']
            }

        # If not found, try converting underscores to hyphens after the prefix
        if '_' in tool_name:
            parts = tool_name.split('_', 1)
            prefix = parts[0]
            rest = parts[1] if len(parts) > 1 else ''

            if '_' in rest:
                name_with_hyphens = f"{prefix}_{rest.replace('_', '-')}"
                if name_with_hyphens in self._tools_cache:
                    tool_info = self._tools_cache[name_with_hyphens]
                    return {
                        "name": tool_info['name'],
                        "description": tool_info['description'],
                        "parameters": tool_info['inputSchema']
                    }

        # Neither version found
        available = list(self._tools_cache.keys())
        raise ValueError(f"Tool '{tool_name}' not found. Available tools: {available}")

    async def call_tool(self, tool_name: str, **kwargs) -> Any:
        """Call a tool by name with arguments."""
        await self._ensure_tools_loaded()

        if tool_name not in self._tools_cache:
            raise ValueError(f"Tool '{tool_name}' not found")

        # Get tool info and session
        tool_info = self._tools_cache[tool_name]
        session = self._sessions_cache[tool_name]

        # Call MCP tool directly using the session
        # Use the raw tool name (without prefix) for the MCP call
        result = await session.call_tool(tool_info['raw_name'], arguments=kwargs)

        # Extract clean result from MCP response
        if hasattr(result, 'content') and result.content:
            # Content is a list of TextContent objects
            content_items = result.content
            if len(content_items) == 1:
                # Single item - extract text
                text_result = content_items[0].text

                # If result is JSON with a "result" field, extract it automatically
                # This handles calculator tools that return {"operation": "add", "result": 8}
                try:
                    import json
                    parsed = json.loads(text_result)
                    if isinstance(parsed, dict) and 'result' in parsed:
                        return parsed['result']
                except (json.JSONDecodeError, TypeError):
                    pass

                return text_result
            else:
                # Multiple items - return list of texts
                return [item.text for item in content_items]

        return result

    def __getattr__(self, name: str):
        """Allow tools.tool_name() syntax.

        Handles underscore→hyphen conversion for tools with hyphens in their names.
        Example: tools.pdf_create_simple_pdf() → calls tool "pdf_create-simple-pdf"

        The conversion preserves the prefix (e.g., "pdf_", "filesystem_") and only
        converts underscores to hyphens in the tool name part.
        """
        async def call_wrapper(**kwargs):
            # First try the exact name
            try:
                return await self.call_tool(name, **kwargs)
            except ValueError as original_error:
                # If not found, try converting underscores to hyphens after the prefix
                # Tool names like "pdf_create-simple-pdf" are called as "pdf_create_simple_pdf" in Python
                # We need to preserve the prefix underscore and convert the rest

                # Find the prefix (text before first underscore)
                if '_' in name:
                    # Split only on first underscore
                    parts = name.split('_', 1)
                    prefix = parts[0]
                    rest = parts[1] if len(parts) > 1 else ''

                    # Try converting underscores to hyphens in the rest
                    if '_' in rest:
                        name_with_hyphens = f"{prefix}_{rest.replace('_', '-')}"
                        try:
                            return await self.call_tool(name_with_hyphens, **kwargs)
                        except ValueError:
                            # Both attempts failed
                            available = list(self._tools_cache.keys())
                            raise ValueError(
                                f"Tool '{name}' not found. Also tried '{name_with_hyphens}'. "
                                f"Available tools: {available}"
                            )

                # Re-raise original error with available tools list
                available = list(self._tools_cache.keys())
                raise ValueError(f"Tool '{name}' not found. Available tools: {available}")
        return call_wrapper


# Global registry instance for code execution
_global_registry = ToolRegistry()


def get_registry() -> ToolRegistry:
    """Get the global tool registry."""
    return _global_registry
