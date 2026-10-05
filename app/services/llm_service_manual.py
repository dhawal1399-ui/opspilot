from app.services.llm_service import LLMService
from app.services.prompts import SYSTEM_PROMPT, build_user_prompt




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


response = llm.generate(
    prompt=prompt,
    system_prompt=SYSTEM_PROMPT,
)


print("LLM Response:")
print(response)