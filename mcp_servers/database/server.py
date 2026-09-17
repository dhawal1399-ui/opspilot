import asyncio
from sqlalchemy.exc import SQLAlchemyError
from mcp.server import MCPServer

from app.database.connection import AsyncSessionLocal
from app.database.repository import (
    get_customer as db_get_customer,
    get_order as db_get_order,
    get_payment as db_get_payment,
    search_orders as db_search_orders,
    get_recent_transactions as db_get_recent_transactions,
)

server = MCPServer("OpsPilot Database Server")


READ_TOOLS = {
    "get_customer",
    "get_order",
    "get_payment",
    "search_orders",
    "get_recent_transactions",
}


@server.tool()
async def get_customer(customer_id: int) -> dict:
    """Get a customer by their customer ID."""
    try : 
        async with AsyncSessionLocal() as session:
            customer = await db_get_customer(
                session,
                customer_id,
            )

            if customer is None:
                return {
                    "found": False,
                    "customer": None,
                }


        return {
            "found": True,
            "customer": {
                "id": customer.id,
                "name": customer.name,
                "email": customer.email,
                "status": customer.status,
                "created_at": customer.created_at.isoformat(),
            },
        }
    except SQLAlchemyError:
        return {
            "found": False,
            "customer": None,
            "error": "Database error",
        }


@server.tool()
async def get_order(order_id:int) -> dict:
    """Get an order by its order ID."""
    try : 
        async with AsyncSessionLocal() as session:

            order = await db_get_order(
                session,
                order_id,
            )

            if order is None:
                return {
                    "found": False,
                    "order": None,
                }

        return {
            "found": True,
            "order": {
                "id": order.id,
                "customer_id": order.customer_id,
                "order_number": order.order_number,
                "status": order.status,
                "total_amount": str(order.total_amount),
                "created_at": order.created_at.isoformat(),
            },
        }
    except SQLAlchemyError:
        return {
            "found": False,
            "order": None,
            "error": "Database error",
        }
    

@server.tool()
async def get_payment(payment_id: int) -> dict:
    """Get a payment by its payment ID."""
    try : 
        async with AsyncSessionLocal() as session:
            payment = await db_get_payment(
                session,
                payment_id,
            )

        if payment is None:
            return {
                "found": False,
                "payment": None,
            }

        return {
            "found": True,
            "payment": {
                "id": payment.id,
                "order_id": payment.order_id,
                "payment_method": payment.payment_method,
                "status": payment.status,
                "amount": str(payment.amount),
                "failure_reason": payment.failure_reason,
                "created_at": payment.created_at.isoformat(),
            },
        }
    except SQLAlchemyError:
        return {
            "found": False,
            "payment": None,
            "error": "Database error",
        }


@server.tool()
async def search_orders(
    customer_id: int | None = None,
    status: str | None = None,
) -> dict:
    """Search orders by optional customer ID and order status."""
    try : 
        async with AsyncSessionLocal() as session:
            orders = await db_search_orders(
                session,
                customer_id=customer_id,
                status=status,
            )

        return {
            "count": len(orders),
            "orders": [
                {
                    "id": order.id,
                    "customer_id": order.customer_id,
                    "order_number": order.order_number,
                    "status": order.status,
                    "total_amount": str(order.total_amount),
                    "created_at": order.created_at.isoformat(),
                }
                for order in orders
            ],
        }
    except SQLAlchemyError:
        return {
            "found": False,
            "payment": None,
            "error": "Database error",
        }


@server.tool()
async def get_recent_transactions(limit: int = 10) -> dict:
    """Get the most recent payment transactions."""
    try : 
        async with AsyncSessionLocal() as session:
            transactions = await db_get_recent_transactions(
                session,
                limit=limit,
            )

        return {
            "count": len(transactions),
            "transactions": [
                {
                    "id": transaction.id,
                    "payment_id": transaction.payment_id,
                    "transaction_reference": transaction.transaction_reference,
                    "status": transaction.status,
                    "amount": str(transaction.amount),
                    "error_code": transaction.error_code,
                    "error_message": transaction.error_message,
                    "created_at": transaction.created_at.isoformat(),
                }
                for transaction in transactions
            ],
        }
    except SQLAlchemyError:
        return {
            "found": False,
            "payment": None,
            "error": "Database error",
        }


async def main():
    await server.run_stdio_async()

if __name__ == "__main__":
    asyncio.run(main())