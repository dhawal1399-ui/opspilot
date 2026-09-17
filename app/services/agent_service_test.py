import asyncio

from app.services.agent_service import AgentService


async def main():
    agent = AgentService()

    try:
        await agent.connect()

        print("Agent connected to MCP servers")

        selection = await agent.select_tools(
            "What errors occurred for order 1001?"
        )

        print("\nSelected tools:")

        for tool in selection.tools:
            print(f"- {tool.name}")
            print(f"  Arguments: {tool.arguments}")

            if tool.name == "get_error_logs":
                result = await agent.execute_tool(tool)

                llm_response = await agent.send_tool_result_to_llm(
                    query="What errors occurred for order 1001?",
                    tool_name=tool.name,
                    result=result,
                )

                print("\nLLM Analysis:")
                print(llm_response)

                print("\nTool execution result:")
                print(result)

    finally:
        await agent.disconnect()


if __name__ == "__main__":
    asyncio.run(main())