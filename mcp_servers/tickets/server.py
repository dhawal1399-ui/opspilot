import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path

from mcp.server import MCPServer


server = MCPServer("Tickets MCP Server")

TICKET_FILE = Path("tickets/tickets.json")

VALID_STATUSES = {
    "open",
    "in_progress",
    "resolved",
    "closed",
}

VALID_PRIORITIES = {
    "low",
    "medium",
    "high",
    "critical",
}


def load_tickets() -> list[dict]:
    """Load tickets from the JSON file."""
    with TICKET_FILE.open("r", encoding="utf-8") as file:
        return json.load(file)


def save_tickets(tickets: list[dict]) -> None:
    """Save tickets to the JSON file."""
    with TICKET_FILE.open("w", encoding="utf-8") as file:
        json.dump(tickets, file, indent=2)


def get_next_ticket_id(tickets: list[dict]) -> int:
    """Generate the next ticket ID."""
    if not tickets:
        return 5001

    return max(ticket["id"] for ticket in tickets) + 1


@server.tool()
async def get_ticket(ticket_id: int) -> dict:
    """Get a ticket by ticket ID."""
    try:
        tickets = load_tickets()

        for ticket in tickets:
            if ticket["id"] == ticket_id:
                return {
                    "found": True,
                    "ticket": ticket,
                }

        return {
            "found": False,
            "ticket_id": ticket_id,
            "error": "Ticket not found",
        }

    except (OSError, json.JSONDecodeError):
        return {
            "found": False,
            "ticket_id": ticket_id,
            "error": "Ticket lookup error",
        }


@server.tool()
async def search_tickets(
    customer_id: int | None = None,
    order_id: int | None = None,
    status: str | None = None,
    priority: str | None = None,
    keyword: str | None = None,
) -> dict:
    """Search tickets using optional filters."""
    try:
        tickets = load_tickets()
        filtered_tickets = []

        for ticket in tickets:

            if customer_id is not None:
                if ticket["customer_id"] != customer_id:
                    continue

            if order_id is not None:
                if ticket["order_id"] != order_id:
                    continue

            if status is not None:
                if ticket["status"] != status:
                    continue

            if priority is not None:
                if ticket["priority"] != priority:
                    continue

            if keyword is not None:
                searchable_text = json.dumps(ticket).lower()

                if keyword.lower() not in searchable_text:
                    continue

            filtered_tickets.append(ticket)

        return {
            "count": len(filtered_tickets),
            "tickets": filtered_tickets,
        }

    except (OSError, json.JSONDecodeError):
        return {
            "count": 0,
            "tickets": [],
            "error": "Ticket search error",
        }


@server.tool()
async def get_customer_tickets(customer_id: int) -> dict:
    """Get all tickets belonging to a customer."""
    try:
        tickets = load_tickets()

        customer_tickets = [
            ticket
            for ticket in tickets
            if ticket["customer_id"] == customer_id
        ]

        return {
            "customer_id": customer_id,
            "count": len(customer_tickets),
            "tickets": customer_tickets,
        }

    except (OSError, json.JSONDecodeError):
        return {
            "customer_id": customer_id,
            "count": 0,
            "tickets": [],
            "error": "Customer ticket lookup error",
        }


@server.tool()
async def create_ticket(
    customer_id: int,
    order_id: int | None,
    title: str,
    description: str,
    priority: str = "medium",
) -> dict:
    """Create a new support ticket."""
    try:
        if priority not in VALID_PRIORITIES:
            return {
                "created": False,
                "error": f"Invalid priority: {priority}",
            }

        tickets = load_tickets()

        now = datetime.now(timezone.utc).isoformat()

        ticket = {
            "id": get_next_ticket_id(tickets),
            "customer_id": customer_id,
            "order_id": order_id,
            "title": title,
            "description": description,
            "status": "open",
            "priority": priority,
            "created_at": now,
            "updated_at": now,
        }

        tickets.append(ticket)
        save_tickets(tickets)

        return {
            "created": True,
            "ticket": ticket,
        }

    except (OSError, json.JSONDecodeError):
        return {
            "created": False,
            "error": "Ticket creation error",
        }


@server.tool()
async def update_ticket(
    ticket_id: int,
    status: str | None = None,
    priority: str | None = None,
    title: str | None = None,
    description: str | None = None,
) -> dict:
    """Update an existing support ticket."""
    try:
        if status is not None and status not in VALID_STATUSES:
            return {
                "updated": False,
                "error": f"Invalid status: {status}",
            }

        if priority is not None and priority not in VALID_PRIORITIES:
            return {
                "updated": False,
                "error": f"Invalid priority: {priority}",
            }

        tickets = load_tickets()

        for ticket in tickets:
            if ticket["id"] == ticket_id:

                if status is not None:
                    ticket["status"] = status

                if priority is not None:
                    ticket["priority"] = priority

                if title is not None:
                    ticket["title"] = title

                if description is not None:
                    ticket["description"] = description

                ticket["updated_at"] = datetime.now(
                    timezone.utc
                ).isoformat()

                save_tickets(tickets)

                return {
                    "updated": True,
                    "ticket": ticket,
                }

        return {
            "updated": False,
            "ticket_id": ticket_id,
            "error": "Ticket not found",
        }

    except (OSError, json.JSONDecodeError):
        return {
            "updated": False,
            "ticket_id": ticket_id,
            "error": "Ticket update error",
        }


async def main():
    await server.run_stdio_async()


if __name__ == "__main__":
    asyncio.run(main())