# Payment Service

## Payment Failure

The payment service processes customer payments through the configured payment gateway.

When a payment fails, check the payment status and transaction record.

Common payment failure error codes include:

- INSUFFICIENT_FUNDS
- PAYMENT_FAILED
- GATEWAY_TIMEOUT
- INVALID_PAYMENT_METHOD
- GATEWAY_DECLINED

## INSUFFICIENT_FUNDS

The INSUFFICIENT_FUNDS error indicates that the payment provider rejected the transaction because the available account balance or credit limit was insufficient.

Recommended action:

1. Verify the payment transaction.
2. Check the gateway response.
3. Confirm whether the customer has another valid payment method.
4. Do not retry repeatedly if the gateway continues returning INSUFFICIENT_FUNDS.

## Gateway Declined

A GATEWAY_DECLINED response means the external payment gateway rejected the payment request.

Check:

- Gateway response code
- Transaction status
- Payment method
- Gateway availability
- Related application logs