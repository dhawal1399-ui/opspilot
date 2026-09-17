import asyncio
from decimal import Decimal

from sqlalchemy import select

from app.database.connection import AsyncSessionLocal
from app.database.models import Customer, Order, Payment, Transaction


async def seed_data():
    async with AsyncSessionLocal() as session:

        # Customers
        customers = [
            Customer(
                id=1024,
                name="Acme Retail Pvt Ltd",
                email="ops@acmeretail.com",
                status="active",
            ),
            Customer(
                id=1025,
                name="Nova Technologies",
                email="admin@novatech.com",
                status="active",
            ),
            Customer(
                id=1026,
                name="GreenMart Solutions",
                email="finance@greenmart.com",
                status="active",
            ),
        ]

        session.add_all(customers)
        await session.flush()

        # Orders
        orders = [
            Order(
                id=1001,
                customer_id=1024,
                order_number="ORD-2026-1001",
                status="failed",
                total_amount=Decimal("2499.00"),
            ),
            Order(
                id=1002,
                customer_id=1024,
                order_number="ORD-2026-1002",
                status="completed",
                total_amount=Decimal("1599.00"),
            ),
            Order(
                id=1003,
                customer_id=1025,
                order_number="ORD-2026-1003",
                status="completed",
                total_amount=Decimal("4999.00"),
            ),
            Order(
                id=1004,
                customer_id=1026,
                order_number="ORD-2026-1004",
                status="pending",
                total_amount=Decimal("899.00"),
            ),
        ]

        session.add_all(orders)
        await session.flush()

        # Payments
        payments = [
            Payment(
                id=2001,
                order_id=1001,
                payment_method="credit_card",
                status="failed",
                amount=Decimal("2499.00"),
                failure_reason="Payment gateway declined the transaction",
            ),
            Payment(
                id=2002,
                order_id=1002,
                payment_method="upi",
                status="success",
                amount=Decimal("1599.00"),
            ),
            Payment(
                id=2003,
                order_id=1003,
                payment_method="credit_card",
                status="success",
                amount=Decimal("4999.00"),
            ),
            Payment(
                id=2004,
                order_id=1004,
                payment_method="upi",
                status="pending",
                amount=Decimal("899.00"),
            ),
        ]

        session.add_all(payments)
        await session.flush()

        # Transactions
        transactions = [
            Transaction(
                id=3001,
                payment_id=2001,
                transaction_reference="TXN-2026-3001",
                status="failed",
                amount=Decimal("2499.00"),
                error_code="INSUFFICIENT_FUNDS",
                error_message="The payment method was declined due to insufficient funds",
            ),
            Transaction(
                id=3002,
                payment_id=2002,
                transaction_reference="TXN-2026-3002",
                status="success",
                amount=Decimal("1599.00"),
            ),
            Transaction(
                id=3003,
                payment_id=2003,
                transaction_reference="TXN-2026-3003",
                status="success",
                amount=Decimal("4999.00"),
            ),
            Transaction(
                id=3004,
                payment_id=2004,
                transaction_reference="TXN-2026-3004",
                status="pending",
                amount=Decimal("899.00"),
            ),
        ]

        session.add_all(transactions)

        await session.commit()

        print("Seed data inserted successfully.")


if __name__ == "__main__":
    asyncio.run(seed_data())