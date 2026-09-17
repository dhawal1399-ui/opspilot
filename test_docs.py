import asyncio

from app.services.mcp_client import MCPClient


async def main():
    client = MCPClient()

    print("CONNECTING...")
    await client.connect()

    print("CALLING search_documentation...")

    result = await client.call_tool(
        "search_documentation",
        {
            "query": "INSUFFICIENT_FUNDS",
            "top_k": 3,
        },
    )

    print("RESULT:")
    print(result)

    await client.disconnect()

    print("DONE")


if __name__ == "__main__":
    asyncio.run(main())