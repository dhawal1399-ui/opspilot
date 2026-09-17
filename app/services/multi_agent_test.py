import asyncio

from app.services.agent_service import AgentService


async def main():

    agent = AgentService()

    await agent.connect()

    try:
        result = await agent.investigate(
            "Why are orders failing for customer 1024?"
        )

        print("\n===== FINAL ANSWER =====")
        print(result)

    finally:
        await agent.disconnect()


asyncio.run(main())