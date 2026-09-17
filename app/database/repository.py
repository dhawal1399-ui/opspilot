from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import (
    Customer,
    Order,
    Payment,
    Transaction,
)



async def get_customer(session : AsyncSession, customer_id : int):

    customer = await session.execute(select(Customer).where(Customer.id == customer_id))

    return customer.scalar_one_or_none()


async def get_order(
    session: AsyncSession,
    order_id: int,
):
    result = await session.execute(
        select(Order).where(Order.id == order_id)
    )

    return result.scalar_one_or_none()

async def get_orders(
    session: AsyncSession,
    customer_id: int,
):
    result = await session.execute(
        select(Order).where(Order.customer_id == customer_id)
    )

    return result.scalars().all()


async def get_payment(session : AsyncSession, payment_id:int):

    result = await session.execute(select(Payment).where(Payment.id == payment_id))

    return result.scalar_one_or_none()

async def get_payments(
    session: AsyncSession,
    order_id: int,
):
    result = await session.execute(
        select(Payment).where(Payment.order_id == order_id)
    )

    return result.scalars().all()


async def get_transactions(
    session: AsyncSession,
    payment_id: int,
):
    result = await session.execute(
        select(Transaction).where(Transaction.payment_id == payment_id)
    )

    return result.scalars().all()


async def search_orders(
    session: AsyncSession,
    customer_id: int | None = None,
    status: str | None = None,
):
    query = select(Order)

    if customer_id is not None:
        query = query.where(Order.customer_id == customer_id)

    if status is not None:
        query = query.where(Order.status == status)

    result = await session.execute(query)

    return result.scalars().all()


async def get_recent_transactions(
    session: AsyncSession,
    limit: int = 10,
):
    result = await session.execute(
        select(Transaction)
        .order_by(Transaction.created_at.desc())
        .limit(limit)
    )

    return result.scalars().all()