from app.services.agent_service import AgentService


agent = AgentService()

query = "Why are orders failing for customer 1024?"

identifiers = {
    "customer_id": 1024,
    "order_id": 1001,
    "request_id": "req-1001-a1",
    "error_codes": [
        "INSUFFICIENT_FUNDS",
        "PAYMENT_FAILED",
    ],
    "error_code": "INSUFFICIENT_FUNDS",
}

tool_results = [
    {
        "tool": "get_error_logs",
        "arguments": {
            "order_id": 1001,
        },
        "result": {
            "count": 2,
            "logs": [
                {
                    "service": "payment-service",
                    "message": "Payment gateway declined the transaction",
                    "error_code": "INSUFFICIENT_FUNDS",
                },
                {
                    "service": "order-service",
                    "message": "Order payment failed",
                    "error_code": "PAYMENT_FAILED",
                },
            ],
        },
    },
    {
        "tool": "search_documentation",
        "arguments": {
            "query": "INSUFFICIENT_FUNDS",
            "top_k": 3,
        },
        "result": {
            "count": 1,
            "results": [
                {
                    "section": "INSUFFICIENT_FUNDS",
                    "text": (
                        "The INSUFFICIENT_FUNDS error indicates "
                        "that the payment provider rejected the "
                        "transaction because the available account "
                        "balance or credit limit was insufficient. "
                        "Recommended action: verify the payment "
                        "transaction, check the gateway response, "
                        "confirm another valid payment method, and "
                        "do not retry repeatedly."
                    ),
                }
            ],
        },
    },
]


print("CALLING FINAL LLM...")

answer = agent.generate_final_answer(
    query=query,
    identifiers=identifiers,
    tool_results=tool_results,
)

print()
print("FINAL ANSWER:")
print(answer)