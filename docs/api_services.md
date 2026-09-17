# API Services

## Service Health

API health should be checked when an operation appears to fail unexpectedly.

The Health MCP Server can check service health and individual endpoints.

Health statuses are:

- HEALTHY
- DEGRADED
- DOWN
- UNKNOWN

## Payment API

The payment API is responsible for communicating with the external payment gateway.

If the payment API is DOWN, investigate service availability before retrying failed payments.

If the payment API is HEALTHY but a specific transaction fails, investigate the transaction and gateway response.