# Troubleshooting Guide

## Payment Failure Investigation

When a customer reports that an order failed, collect:

- Customer ID
- Order ID
- Payment ID
- Transaction ID
- Application request ID
- Payment error code

Use the application logs to identify the exact failure point.

## Recommended Investigation Flow

1. Find the customer.
2. Find the customer's order.
3. Check the order status.
4. Check the associated payment.
5. Check the payment transaction.
6. Search application error logs.
7. Search the documentation for the identified error code.

## INSUFFICIENT_FUNDS

If the transaction contains INSUFFICIENT_FUNDS, the payment provider rejected the transaction because sufficient funds or credit were unavailable.

The order may therefore be marked as failed.

The recommended customer-facing action is to retry using a valid payment method after confirming the payment provider response.