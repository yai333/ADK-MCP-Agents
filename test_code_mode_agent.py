"""Test the code mode agent with various scenarios"""

import asyncio
import os
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
import code_mode_agent

APP_NAME = "adk_mcp_test"
USER_ID = "test_user"
SESSION_ID = "test_session"


async def test_agent(query: str, test_name: str):
    """Run a single test query"""
    print(f"\n{'=' * 80}")
    print(f"{test_name}")
    print(f"{'=' * 80}")
    print(f"Query: {query}")

    session_service = InMemorySessionService()
    session = await session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=SESSION_ID
    )

    runner = Runner(
        agent=code_mode_agent.code_mode_agent,
        app_name=APP_NAME,
        session_service=session_service
    )

    content = types.Content(role='user', parts=[types.Part(text=query)])
    events = runner.run_async(
        user_id=USER_ID, session_id=session.id, new_message=content)

    async for event in events:
        if event.is_final_response():
            if event.content and event.content.parts:
                print(f"\nResponse: {event.content.parts[0].text}")
            else:
                print("\nNo response received")
            break


async def main():
    print("\n" + "█" * 80)
    print(" " * 25 + "CODE MODE AGENT TESTS")
    print("█" * 80)

    # Test 1: Tool discovery
    # await test_agent(
    #     "What MCP tools are available?",
    #     "TEST 1: Tool Discovery"
    # )

    # # Test 2: Simple calculation
    # await test_agent(
    #     "Calculate 15 + 27",
    #     "TEST 2: Simple Calculation"
    # )

    # # Test 3: Calculator with loop
    # await test_agent(
    #     "Calculate the sum of squares from 1 to 10 using calculator tools",
    #     "TEST 3: Sum of Squares (Calculator Loop)"
    # )

    # Test 4: File operations
    await test_agent(
        "Calculate 100 + 200 + 300, then create a PDF file named 'calculation.pdf' with the result. Use create-simple-pdf with filename parameter.",
        "TEST 4: Calculator + PDF Creation"
    )

    # Test 5: PDF creation
    # await test_agent(
    #     "Create a simple PDF with text 'Test Document'",
    #     "TEST 5: PDF Creation"
    # )

    # Test 6: BigQuery - List available tools
    # await test_agent(
    #     "What BigQuery tools are available? List all tools with 'bigquery' in their name.",
    #     "TEST 6: BigQuery Tool Discovery"
    # )

    # Test 7: BigQuery - List tables
    project = os.getenv("BIGQUERY_PROJECT", "lively-metrics-295911")
    dataset = os.getenv("BIGQUERY_DATASET", "analytics_254171871")
    await test_agent(
        f"List tables in BigQuery dataset {project}.{dataset}. Use INFORMATION_SCHEMA.TABLES and show the first 5 tables.",
        "TEST 7: BigQuery List Tables"
    )

    # Add delay between standalone tests to allow MCP cleanup
    print("\n⏳ Waiting 5 seconds for MCP cleanup before next test...")
    await asyncio.sleep(5)

    print("\n" + "█" * 80)
    print(" " * 30 + "TESTS COMPLETE")
    print("█" * 80 + "\n")


if __name__ == '__main__':
    asyncio.run(main())
