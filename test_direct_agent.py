"""Test the direct agent with MCP tool calls"""

import asyncio
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
import direct_agent

APP_NAME = "adk_mcp_test"
USER_ID = "test_user"
SESSION_ID = "direct_session"


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
        agent=direct_agent.direct_agent,
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


async def main():
    print("\n" + "█" * 80)
    print(" " * 25 + "DIRECT AGENT TEST")
    print("█" * 80)

    # Initialize MCP tools first
    await direct_agent.initialize_mcp_tools()

    # Test: Calculate and save to PDF
    await test_agent(
        "Calculate 50 + 100 + 150 and create a PDF with the result",
        "TEST: Calculate and Save to PDF"
    )

    # Test: BigQuery
    import os
    project = os.getenv("BIGQUERY_PROJECT", "lively-metrics-295911")
    dataset = os.getenv("BIGQUERY_DATASET", "analytics_254171871")
    await test_agent(
        f"Query the BigQuery dataset {project}.{dataset} to list the first 5 tables using INFORMATION_SCHEMA.TABLES",
        "TEST: BigQuery List Tables"
    )

    print("\n" + "█" * 80)
    print(" " * 30 + "TEST COMPLETE")
    print("█" * 80 + "\n")


if __name__ == '__main__':
    asyncio.run(main())
