from app.services.llm_service import LLMService
from app.services.prompts import (
    STRUCTURED_SYSTEM_PROMPT,
    build_user_prompt,
)


def main():
    llm = LLMService()

    query = "Why did order 1001 fail?"

    context = """
    Customer 1024 has order 1001.

    Order 1001 status: failed.

    Payment 2001 status: failed.

    Transaction 3001 status: failed.

    Transaction error code: INSUFFICIENT_FUNDS.
    """

    prompt = build_user_prompt(
        query=query,
        context=context,
    )

    result = llm.generate_structured(
        prompt=prompt,
        system_prompt=STRUCTURED_SYSTEM_PROMPT,
    )

    print("=== OpsPilot LLM Integration Test ===")
    print()
    print("Question:")
    print(query)

    print("\nAnswer:")
    print(result.answer)

    print("\nRoot Cause:")
    print(result.root_cause)

    print("\nEvidence:")
    for item in result.evidence:
        print(f"- {item}")

    print("\nRecommendations:")
    for item in result.recommendations:
        print(f"- {item}")


if __name__ == "__main__":
    main()