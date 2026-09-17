# Order Service

## Order Lifecycle

Orders can have the following statuses:

- pending
- processing
- completed
- failed
- cancelled

## Failed Orders

An order is marked as failed when a required operation in the order workflow cannot be completed.

For payment-related failures:

1. Check the order status.
2. Retrieve the associated payment.
3. Retrieve the payment transaction.
4. Search application logs using the order ID.
5. Identify the underlying payment or gateway error.

A PAYMENT_FAILED error may be caused by a payment gateway rejection.

## Order Investigation

For a customer order investigation, start with:

Customer → Order → Payment → Transaction

Then correlate the results with application logs.