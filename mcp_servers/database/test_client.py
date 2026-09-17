import asyncio

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


server_params = StdioServerParameters(
    command="python",
    args=["-m", "mcp_servers.database.server"],
)


async def main():
    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:

            await session.initialize()

            tools = await session.list_tools()

            print("Available tools:")
            for tool in tools.tools:
                print(tool.name)

            customer = await session.call_tool(
                "get_customer",
                arguments={"customer_id": 1024},
            )

            orders = await session.call_tool(
                "search_orders",
                arguments={"customer_id": 1024},
            )

            order = await session.call_tool(
                "get_order",
                arguments={"order_id": 1001},
            )

            payment = await session.call_tool(
                "get_payment",
                arguments={"payment_id": 2001},
            )

            transactions = await session.call_tool(
                "get_recent_transactions",
                arguments={"limit": 10},
            )


if __name__ == "__main__":
    asyncio.run(main())