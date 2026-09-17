import asyncio

from app.database.connection import AsyncSessionLocal
from app.database.repository import (
    get_customer,
    get_orders,
    get_payments,
    get_transactions,
)


async def main():
    async with AsyncSessionLocal() as session:

        customer = await get_customer(session, 1024)

        print("CUSTOMER")
        print(customer.name)
        print(customer.email)
        print()

        orders = await get_orders(session, customer.id)

        print("ORDERS")
        for order in orders:
            print(order.order_number, order.status, order.total_amount)
        print()

        for order in orders:
            payments = await get_payments(session, order.id)

            print(f"PAYMENTS FOR {order.order_number}")
            for payment in payments:
                print(
                    payment.id,
                    payment.status,
                    payment.amount,
                    payment.failure_reason,
                )
            print()

            for payment in payments:
                transactions = await get_transactions(session, payment.id)

                print(f"TRANSACTIONS FOR PAYMENT {payment.id}")
                for transaction in transactions:
                    print(
                        transaction.transaction_reference,
                        transaction.status,
                        transaction.error_code,
                        transaction.error_message,
                    )
                print()


if __name__ == "__main__":
    asyncio.run(main())