"""Calculator MCP Server using FastMCP"""

from fastmcp import FastMCP
from . import calculator

# Create FastMCP server
mcp = FastMCP(name="calculator")


@mcp.tool
async def add(a: float, b: float) -> dict:
    """Add two numbers.

    Args:
        a: First number
        b: Second number

    Returns:
        Dictionary with result
    """
    result = calculator.add(a, b)
    return {"operation": "add", "a": a, "b": b, "result": result}


@mcp.tool
async def subtract(a: float, b: float) -> dict:
    """Subtract b from a.

    Args:
        a: First number
        b: Number to subtract

    Returns:
        Dictionary with result
    """
    result = calculator.subtract(a, b)
    return {"operation": "subtract", "a": a, "b": b, "result": result}


@mcp.tool
async def multiply(a: float, b: float) -> dict:
    """Multiply two numbers.

    Args:
        a: First number
        b: Second number

    Returns:
        Dictionary with result
    """
    result = calculator.multiply(a, b)
    return {"operation": "multiply", "a": a, "b": b, "result": result}


@mcp.tool
async def divide(a: float, b: float) -> dict:
    """Divide a by b.

    Args:
        a: Numerator
        b: Denominator

    Returns:
        Dictionary with result
    """
    result = calculator.divide(a, b)
    return {"operation": "divide", "a": a, "b": b, "result": result}


if __name__ == "__main__":
    # Run the MCP server
    mcp.run()
