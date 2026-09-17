import asyncio

from app.services.mcp_client import MCPClient


async def main():
    client = MCPClient()

    print("CONNECTING...")
    await client.connect()

    print("CALLING get_error_logs...")

    result = await client.call_tool(
        "get_error_logs",
        {"order_id": 1001},
    )

    print("RESULT:")
    print(result)

    await client.disconnect()

    print("DONE")


if __name__ == "__main__":
    asyncio.run(main())