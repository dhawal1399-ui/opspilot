from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import  ForeignKey, Index, Integer, Numeric, String, Text, DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    pass


class Customer(Base):
    __tablename__ = "customers"
    id : Mapped[int] = mapped_column(Integer, primary_key=True)
    name : Mapped[str] = mapped_column(String(100), nullable=False)
    email : Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    status : Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
    orders : Mapped[list["Order"]] = relationship(back_populates="customer")

class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.id"),
        nullable=False,
    )
    order_number: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    customer: Mapped["Customer"] = relationship(
        back_populates="orders"
    )

    payments: Mapped[list["Payment"]] = relationship(
        back_populates="order"
    )

    __table_args__ = (
        Index("ix_orders_customer_id", "customer_id"),
        Index("ix_orders_status", "status"),
    )


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id"),
        nullable=False,
    )
    payment_method: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )
    failure_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    order: Mapped["Order"] = relationship(
        back_populates="payments"
    )

    transactions: Mapped[list["Transaction"]] = relationship(
        back_populates="payment"
    )

    __table_args__ = (
        Index("ix_payments_order_id", "order_id"),
        Index("ix_payments_status", "status"),
    )


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    payment_id: Mapped[int] = mapped_column(
        ForeignKey("payments.id"),
        nullable=False,
    )
    transaction_reference: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )
    error_code: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    payment: Mapped["Payment"] = relationship(
        back_populates="transactions"
    )

    __table_args__ = (
        Index("ix_transactions_payment_id", "payment_id"),
        Index("ix_transactions_status", "status"),
    )