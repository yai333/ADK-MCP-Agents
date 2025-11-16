"""Example usage of ADK MCP agents"""

import os
import asyncio
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
import direct_agent
import code_mode_agent

# Get project directory
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
SAMPLE_PDF = os.path.join(PROJECT_DIR, "sample.pdf")

APP_NAME = "adk_mcp_test"
USER_ID = "test_user"
SESSION_ID_DIRECT = "direct_session"
SESSION_ID_CODE = "code_session"


async def setup_session_and_runner(agent, session_id):
    """Setup session and runner for an agent"""
    session_service = InMemorySessionService()
    session = await session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=session_id
    )
    runner = Runner(
        agent=agent,
        app_name=APP_NAME,
        session_service=session_service
    )
    return session, runner


async def call_agent(agent, session_id, query):
    """Call agent with a query and print response"""
    content = types.Content(role='user', parts=[types.Part(text=query)])
    session, runner = await setup_session_and_runner(agent, session_id)
    events = runner.run_async(
        user_id=USER_ID, session_id=session.id, new_message=content)

    async for event in events:
        if event.is_final_response():
            if event.content and event.content.parts:
                final_response = event.content.parts[0].text
                print(f"Response: {final_response}")
            else:
                print(f"Response: [No text response - check event: {event}]")


async def test_direct_agent():
    """Test direct agent with MCP tool calls"""
    print("=" * 80)
    print("TEST 1: DIRECT AGENT")
    print("=" * 80)

    # Example 1: Calculator tool (custom MCP server)
    print("\n[Calculator Tool] Calculate 15 + 27")
    await call_agent(direct_agent.direct_agent, SESSION_ID_DIRECT, "Calculate 15 + 27")

    # Example 2: Filesystem tool (pre-built MCP server)
    print("\n[Filesystem Tool] List files in /tmp")
    await call_agent(direct_agent.direct_agent, SESSION_ID_DIRECT, "List files in /tmp directory")

    # Example 3: PDF tool (pre-built MCP server)
    print("\n[PDF Tool] Create a simple PDF")
    await call_agent(direct_agent.direct_agent, SESSION_ID_DIRECT, "Create a simple PDF with the text 'Hello from ADK MCP Agent!'")


async def test_code_mode_agent():
    """Test code mode agent with code generation"""
    print("\n" + "=" * 80)
    print("TEST 2: CODE MODE AGENT")
    print("=" * 80)

    # Example 1: List available tools
    print("\n[Discover Tools] List all available MCP tools")
    await call_agent(code_mode_agent.code_mode_agent, SESSION_ID_CODE, "What MCP tools are available?")

    # Example 2: Calculator tools - complex calculation
    print("\n[Calculator Tools] Calculate sum of squares from 1 to 10")
    await call_agent(code_mode_agent.code_mode_agent, SESSION_ID_CODE, "Calculate the sum of squares from 1 to 10 using the calculator tools in a loop")

    # Example 3: Filesystem + PDF tools - workflow
    print("\n[Filesystem + PDF Tools] Create PDF and save info to /tmp")
    await call_agent(code_mode_agent.code_mode_agent, SESSION_ID_CODE, "Create a simple PDF with text 'Test Document', then write a confirmation message to /tmp/pdf_created.txt")

    # Example 4: Multi-tool workflow
    print("\n[Multi-tool Workflow] Calculator + Filesystem")
    await call_agent(code_mode_agent.code_mode_agent, SESSION_ID_CODE, "Calculate 100 + 200 + 300, then write the result to /tmp/calculation.txt")


async def main():
    print("\n" + "█" * 80)
    print(" " * 20 + "ADK MCP AGENTS TEST")
    print("█" * 80)
    print("\nTesting MCP servers:")
    print("  • calculator (custom) - Arithmetic operations")
    print("  • filesystem (pre-built) - File operations")
    print("  • pdf (pre-built) - PDF creation")
    print("\nTwo agent patterns:")
    print("  1. Direct Agent - Traditional MCP tool calls")
    print("  2. Code Mode Agent - Generates and executes code")
    print("█" * 80 + "\n")

    await test_direct_agent()
    await test_code_mode_agent()

    print("\n" + "█" * 80)
    print(" " * 25 + "TESTS COMPLETE")
    print("█" * 80 + "\n")


if __name__ == '__main__':
    asyncio.run(main())
