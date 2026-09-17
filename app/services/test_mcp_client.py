import asyncio

from app.services.mcp_client import MCPClient


async def main():
    client = MCPClient()

    try:
        await client.connect()

        tools = await client.list_tools()

        print("Available tools:")
        for tool in tools:
            print("-", tool.name)

        print("\nSEARCH DOCUMENTATION:")

        result = await client.call_tool(
            "search_documentation",
            {
                "query": "",
                "top_k": 3,
            },
        )

        print(result)
        

    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())