import asyncio
import json
import re
from enum import Enum
import secrets
from app.models.confirmation import PendingAction


from app.models.agent import AgentDecision
from app.services.llm_service import LLMService
from app.services.llm_service import LLMServiceError
from app.services.mcp_client import MCPClient
from app.services.prompts import SYSTEM_PROMPT

from app.services.confirmation_service import ConfirmationService


class ToolPermission(str, Enum):
    READ = "read"
    WRITE = "write"

DESTRUCTIVE_TOOL_NAMES = frozenset(
    {
        "delete",
        "delete_ticket",
        "delete_customer",
        "remove",
        "remove_ticket",
        "drop",
        "truncate",
    }
)

TOOL_PERMISSIONS = {
    # Database
    "get_customer": ToolPermission.READ,
    "get_order": ToolPermission.READ,
    "get_payment": ToolPermission.READ,
    "search_orders": ToolPermission.READ,
    "get_recent_transactions": ToolPermission.READ,

    # Logs
    "search_logs": ToolPermission.READ,
    "get_error_logs": ToolPermission.READ,
    "get_request_logs": ToolPermission.READ,

    # Tickets
    "get_ticket": ToolPermission.READ,
    "search_tickets": ToolPermission.READ,
    "get_customer_tickets": ToolPermission.READ,

    # Documentation
    "search_documentation": ToolPermission.READ,

    # Health
    "check_api_health": ToolPermission.READ,
    "check_endpoint": ToolPermission.READ,
    "get_service_status": ToolPermission.READ,

    # Write operations
    "create_ticket": ToolPermission.WRITE,
    "update_ticket": ToolPermission.WRITE,
}


class AgentService:
    READ_ONLY_TOOLS = frozenset(
        {
            "get_customer",
            "get_order",
            "get_payment",
            "search_orders",
            "get_recent_transactions",
            "search_logs",
            "get_error_logs",
            "get_request_logs",
            "get_ticket",
            "search_tickets",
            "get_customer_tickets",
            "search_documentation",
            "check_api_health",
            "check_endpoint",
            "get_service_status",
        }
    )

    WRITE_TOOLS = frozenset(
        {
            "create_ticket",
            "update_ticket",
        }
    )

    def __init__(self, confirmation_service: ConfirmationService | None = None):
        self.llm = LLMService()
        self.mcp = MCPClient()
        self.confirmation_service = confirmation_service
        self.last_tool_results = []
        self.last_tools_used = []

    def get_tool_permission(self, tool_name: str) -> ToolPermission | None:
        return TOOL_PERMISSIONS.get(tool_name)

    def is_write_tool(self, tool_name: str) -> bool:
        return self.get_tool_permission(tool_name) == ToolPermission.WRITE


    def is_destructive_tool(self, tool_name: str) -> bool:
        normalized_name = tool_name.lower()

        return (
            normalized_name in DESTRUCTIVE_TOOL_NAMES
            or normalized_name.startswith("delete_")
            or normalized_name.startswith("remove_")
            or normalized_name.startswith("drop_")
            or normalized_name.startswith("truncate_")
        )


    def request_confirmation(
        self,
        tool_name: str,
        arguments: dict,
    ) -> str:
        return self.confirmation_service.create(
            tool_name=tool_name,
            arguments=arguments,
        )


    def create_pending_action(
        self,
        tool_name: str,
        arguments: dict,
    ) -> PendingAction:
        action = PendingAction(
            token=secrets.token_urlsafe(32),
            tool_name=tool_name,
            arguments=arguments,
        )

        self.pending_action = action
        return action


    async def connect(self):
        await self.mcp.connect()

    async def disconnect(self):
        await self.mcp.disconnect()

    async def get_available_tools(self):
        tools = await self.mcp.list_tools()

        available_tools = []

        for item in tools:
            tool = item["tool"]

            schema = getattr(
                tool,
                "input_schema",
                getattr(tool, "inputSchema", {}),
            )

            available_tools.append(
                {
                    "server": item["server"],
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": schema,
                }
            )

        return available_tools

    # ---------------------------------------------------------
    # JSON parsing
    # ---------------------------------------------------------

    def parse_json_response(self, response: str) -> dict:
        response = response.strip()

        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass

        match = re.search(
            r"\{.*\}",
            response,
            re.DOTALL,
        )

        if not match:
            raise ValueError(
                "LLM response does not contain valid JSON"
            )

        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError as exc:
            raise ValueError(
                "LLM response contains invalid JSON"
            ) from exc

    # ---------------------------------------------------------
    # Tool validation
    # ---------------------------------------------------------

    def validate_tool_call(
        self,
        tool_call,
        available_tools,
    ):
        tool_name = (
            tool_call.name
            if hasattr(tool_call, "name")
            else tool_call["name"]
        )

        arguments = (
            tool_call.arguments
            if hasattr(tool_call, "arguments")
            else tool_call["arguments"]
        )

        available_names = {
            tool["name"]
            for tool in available_tools
        }

        if tool_name not in available_names:
            raise ValueError(
                f"Unsupported tool selected: {tool_name}"
            )

        if not isinstance(arguments, dict):
            raise ValueError(
                "Tool arguments must be an object"
            )

        tool_definition = next(
            tool
            for tool in available_tools
            if tool["name"] == tool_name
        )

        required_arguments = tool_definition["input_schema"].get(
            "required",
            [],
        )

        missing_arguments = [
            name
            for name in required_arguments
            if arguments.get(name) is None
        ]

        if missing_arguments:
            raise ValueError(
                f"Missing required tool arguments for {tool_name}: "
                f"{', '.join(missing_arguments)}"
            )

        return True

    # ---------------------------------------------------------
    # Identifier extraction
    # ---------------------------------------------------------

    def extract_identifiers(
        self,
        result,
        identifiers,
        tool_name=None,
    ):
        if not isinstance(result, dict):
            return

        if tool_name == "get_customer":
            customer = result.get("customer")

            if (
                isinstance(customer, dict)
                and customer.get("id") is not None
            ):
                self._update_identifier(
                    identifiers,
                    "customer_id",
                    customer["id"],
                )

        if tool_name == "search_orders":
            orders = result.get("orders")

            if isinstance(orders, list):
                for order in orders:
                    if (
                        isinstance(order, dict)
                        and order.get("id") is not None
                    ):
                        self._update_identifier(
                            identifiers,
                            "order_id",
                            order["id"],
                        )
                        break

        def walk(value):
            if isinstance(value, dict):
                for key, child in value.items():

                    normalized_key = key.lower()

                    if normalized_key in {
                        "customer_id",
                        "order_id",
                        "payment_id",
                        "transaction_id",
                        "request_id",
                        "ticket_id",
                        "error_code",
                    }:
                        if child is not None:
                            self._update_identifier(
                                identifiers,
                                normalized_key,
                                child,
                            )

                    walk(child)

            elif isinstance(value, list):
                for item in value:
                    walk(item)

        walk(result)

    def _update_identifier(
        self,
        identifiers,
        key,
        value,
    ):
        if key != "error_code":
            if key not in identifiers:
                identifiers[key] = value
            return

        if value is None:
            return

        error_codes = identifiers.setdefault(
            "error_codes",
            [],
        )

        if value not in error_codes:
            error_codes.append(value)

        # Prefer a specific root-cause error code
        specific_codes = {
            "INSUFFICIENT_FUNDS",
            "GATEWAY_DECLINED",
            "CARD_DECLINED",
            "EXPIRED_CARD",
            "INVALID_CARD",
            "AUTHENTICATION_FAILED",
            "TIMEOUT",
        }

        if value in specific_codes:
            identifiers["error_code"] = value

        elif "error_code" not in identifiers:
            identifiers["error_code"] = value

    # ---------------------------------------------------------
    # Call tracking
    # ---------------------------------------------------------

    def make_call_key(
        self,
        tool_name,
        arguments,
    ):
        normalized_arguments = json.dumps(
            arguments,
            sort_keys=True,
        )

        return f"{tool_name}:{normalized_arguments}"

    # ---------------------------------------------------------
    # Deterministic investigation policy
    # ---------------------------------------------------------

    def get_next_policy_tool(
        self,
        query,
        identifiers,
        executed_calls,
        available_tools,
    ):
        available_names = {
            tool["name"]
            for tool in available_tools
        }

        customer_id = identifiers.get("customer_id")
        order_id = identifiers.get("order_id")
        payment_id = identifiers.get("payment_id")
        error_code = identifiers.get("error_code")

        # -----------------------------------------------------
        # Customer -> orders
        # -----------------------------------------------------

        if (
            customer_id is not None
            and order_id is None
            and "search_orders" in available_names
        ):
            arguments = {
                "customer_id": customer_id
            }

            key = self.make_call_key(
                "search_orders",
                arguments,
            )

            if key not in executed_calls:
                return {
                    "name": "search_orders",
                    "arguments": arguments,
                }

        # -----------------------------------------------------
        # Order -> error logs
        # -----------------------------------------------------

        if (
            order_id is not None
            and error_code is None
            and "get_error_logs" in available_names
        ):
            arguments = {
                "order_id": order_id
            }

            key = self.make_call_key(
                "get_error_logs",
                arguments,
            )

            if key not in executed_calls:
                return {
                    "name": "get_error_logs",
                    "arguments": arguments,
                }

        # -----------------------------------------------------
        # Error code -> documentation
        # -----------------------------------------------------

        if (
            error_code is not None
            and "search_documentation" in available_names
        ):
            arguments = {
                "query": str(error_code),
                "top_k": 3,
            }

            key = self.make_call_key(
                "search_documentation",
                arguments,
            )

            if key not in executed_calls:
                return {
                    "name": "search_documentation",
                    "arguments": arguments,
                }

        return None

    # ---------------------------------------------------------
    # LLM tool selection
    # ---------------------------------------------------------

    async def select_tools(
        self,
        query,
        identifiers,
        tool_results,
        available_tools,
    ):
        tool_descriptions = []

        for tool in available_tools:
            tool_descriptions.append(
                {
                    "name": tool["name"],
                    "description": tool["description"],
                    "input_schema": tool["input_schema"],
                }
            )

        prompt = f"""
You are an investigation agent.

User question:
{query}

Known identifiers:
{json.dumps(identifiers, indent=2)}

Previous tool results:
{json.dumps(tool_results, indent=2)}

Available tools:
{json.dumps(tool_descriptions, indent=2)}

Select ONLY a tool that is directly useful for answering
the user's question.

Rules:

1. Return JSON only.
2. Do not invent identifiers.
3. Do not use "..." as an argument value.
4. Never pass null for an argument when a useful real value
   is already known.
5. Never change the user's question.
6. Do not call unrelated tools.
7. If the available evidence is sufficient to answer the
   question, return:
   {{"action": "final", "tools": []}}

Return:

{{
    "action": "tool_call",
    "tools": [
        {{
            "name": "tool_name",
            "arguments": {{}}
        }}
    ]
}}
"""

        response = await self.llm.generate_async(
            prompt,
            SYSTEM_PROMPT,
        )

        data = self.parse_json_response(response)

        decision = AgentDecision.model_validate(data)

        return decision

    # ---------------------------------------------------------
    # Execute MCP tool
    # ---------------------------------------------------------

    async def execute_tool(
        self,
        tool_name,
        arguments,
        confirmed=False,
    ):
        if self.is_destructive_tool(tool_name):
            raise PermissionError(
                f"Destructive tool '{tool_name}' is not permitted"
            )
        permission = self.get_tool_permission(tool_name)

        if permission is None:
            raise ValueError(
                f"Tool '{tool_name}' does not have a defined permission"
            )

        if permission == ToolPermission.WRITE and not confirmed:
            raise PermissionError(
                f"Write tool '{tool_name}' requires explicit user confirmation"
            )

        print()
        print("EXECUTING:")
        print(tool_name)

        return await self.mcp.call_tool(
            tool_name,
            arguments,
        )

    async def execute_tools_concurrently(
        self,
        tool_calls,
        executed_calls=None,
        available_tools=None,
    ):
        """Execute independent read-only calls without cancelling peers."""

        executed_calls = (
            executed_calls
            if executed_calls is not None
            else set()
        )

        tasks = []
        results = []

        for tool_call in tool_calls:
            tool_name = tool_call["name"]
            arguments = tool_call["arguments"]

            call_key = self.make_call_key(
                tool_name,
                arguments,
            )

            if tool_name not in self.READ_ONLY_TOOLS:
                results.append(
                    {
                        "tool": tool_name,
                        "arguments": arguments,
                        "success": False,
                        "error": (
                            f"Tool '{tool_name}' is not eligible for "
                            "concurrent execution"
                        ),
                    }
                )
                continue

            if call_key in executed_calls:
                results.append(
                    {
                        "tool": tool_name,
                        "arguments": arguments,
                        "success": False,
                        "error": "Duplicate tool call rejected",
                    }
                )
                continue

            if available_tools is not None:
                try:
                    self.validate_tool_call(
                        {
                            "name": tool_name,
                            "arguments": arguments,
                        },
                        available_tools,
                    )

                except ValueError as exc:
                    results.append(
                        {
                            "tool": tool_name,
                            "arguments": arguments,
                            "success": False,
                            "error": str(exc),
                        }
                    )
                    continue

            permission = self.get_tool_permission(tool_name)

            if permission is None:
                results.append(
                    {
                        "tool": tool_name,
                        "arguments": arguments,
                        "success": False,
                        "error": (
                            f"Tool '{tool_name}' has no "
                            "permission definition"
                        ),
                    }
                )
                continue

            if permission == ToolPermission.WRITE:
                results.append(
                    {
                        "tool": tool_name,
                        "arguments": arguments,
                        "success": False,
                        "error": (
                            f"Write tool '{tool_name}' requires "
                            "explicit user confirmation"
                        ),
                    }
                )
                continue

            executed_calls.add(call_key)

            tasks.append(
                (
                    tool_name,
                    arguments,
                    self.execute_tool(
                        tool_name,
                        arguments,
                    ),
                )
            )

        gathered = await asyncio.gather(
            *(task[2] for task in tasks),
            return_exceptions=True,
        )

        for (tool_name, arguments, _), result in zip(
            tasks,
            gathered,
        ):
            if isinstance(result, BaseException):
                results.append(
                    {
                        "tool": tool_name,
                        "arguments": arguments,
                        "success": False,
                        "error": str(result),
                    }
                )
                continue

            if (
                isinstance(result, dict)
                and result.get("success") is False
            ):
                results.append(
                    {
                        "tool": tool_name,
                        "arguments": arguments,
                        "success": False,
                        "error": result.get(
                            "error",
                            "Unknown MCP tool failure",
                        ),
                    }
                )
                continue

            data = (
                result.get("data")
                if isinstance(result, dict)
                and result.get("success") is True
                else result
            )

            results.append(
                {
                    "tool": tool_name,
                    "arguments": arguments,
                    "success": True,
                    "data": data,
                }
            )

        return results

    # ---------------------------------------------------------
    # Process tool result
    # ---------------------------------------------------------

    def process_tool_result(
        self,
        tool_name,
        arguments,
        result,
        identifiers,
    ):
        self.extract_identifiers(
            result,
            identifiers,
            tool_name=tool_name,
        )

        print()
        print("TOOL RESULT RECEIVED:")
        print(f"Tool: {tool_name}")
        print(f"Result type: {type(result).__name__}")

        print()
        print("IDENTIFIERS DISCOVERED:")
        print(f"Fields: {list(identifiers.keys())}")

    # ---------------------------------------------------------
    # Final grounded answer
    # ---------------------------------------------------------

    def generate_final_answer(
        self,
        query,
        identifiers,
        tool_results,
    ):
        prompt = f"""
    You are the final response generator for an operations
    investigation system.

    Answer the user's question using ONLY the evidence collected
    during the investigation.

    USER QUESTION:
    {query}

    IDENTIFIERS:
    {json.dumps(identifiers, indent=2)}

    INVESTIGATION EVIDENCE:
    {json.dumps(tool_results, indent=2, default=str)}

    IMPORTANT INTERPRETATION RULES:

    1. Distinguish the ROOT CAUSE from downstream/system errors.

    2. If multiple error codes exist, determine whether one is
    the underlying cause and another is a consequence.

    3. For example, if logs show:
    - payment gateway declined
    - INSUFFICIENT_FUNDS
    - order payment failed
    - PAYMENT_FAILED

    then:
    ROOT CAUSE = INSUFFICIENT_FUNDS
    DOWNSTREAM RESULT = PAYMENT_FAILED

    4. Do not claim that PAYMENT_FAILED itself caused the failure
    if the evidence shows it occurred after the payment gateway
    failure.

    5. Use documentation to explain the meaning of the root-cause
    error.

    6. Do not invent facts.

    7. Do not mention tools, agents, prompts, or internal
    investigation steps.

    8. Do not say that evidence is missing when the provided
    evidence supports the conclusion.

    9. Clearly answer:
    - What failed?
    - Why did it fail?
    - What evidence supports the conclusion?
    - What should be done next?

    10. If the evidence is insufficient to establish a root cause,
        explicitly state that instead of guessing.

    Return a concise natural-language response.

    Recommended structure:

    Root cause:
    <root cause>

    Evidence:
    <important evidence>

    Recommended action:
    <action based on documentation>
    """

        return self.llm.generate(
            prompt=prompt,
            system_prompt=SYSTEM_PROMPT,
        )

    async def generate_final_answer_async(
        self,
        query,
        identifiers,
        tool_results,
    ):
        try:
            return await asyncio.wait_for(
                asyncio.to_thread(
                    self.generate_final_answer,
                    query,
                    identifiers,
                    tool_results,
                ),
                timeout=self.llm.timeout,
            )

        except asyncio.TimeoutError as exc:
            raise LLMServiceError(
                f"LLM request timed out after {self.llm.timeout} seconds"
            ) from exc

    # ---------------------------------------------------------
    # Main investigation
    # ---------------------------------------------------------

    async def investigate(
        self,
        query,
        max_steps=10,
    ):
        await self.connect()

        executed_calls = set()
        identifiers = {}
        tool_results = []

        try:
            available_tools = await self.get_available_tools()

            if not available_tools:
                raise RuntimeError(
                    "No MCP tools are available"
                )

            print("MCP servers connected.")

            print()
            print("AVAILABLE TOOLS:")
            print(
                [
                    tool["name"]
                    for tool in available_tools
                ]
            )

            for step in range(1, max_steps + 1):

                print()
                print(
                    f"===== AGENT STEP {step} ====="
                )

                print()
                print("AVAILABLE TOOLS:")
                print(
                    [
                        tool["name"]
                        for tool in available_tools
                    ]
                )

                # -------------------------------------------------
                # Deterministic workflow policy first
                # -------------------------------------------------

                policy_tool = self.get_next_policy_tool(
                    query=query,
                    identifiers=identifiers,
                    executed_calls=executed_calls,
                    available_tools=available_tools,
                )

                if policy_tool:
                    print()
                    print("POLICY SELECTED:")
                    print(f"Tool: {policy_tool['name']}")

                    tool_name = policy_tool["name"]
                    arguments = policy_tool["arguments"]

                else:
                    # ---------------------------------------------
                    # Ask LLM only when policy has no next step
                    # ---------------------------------------------

                    decision = await self.select_tools(
                        query=query,
                        identifiers=identifiers,
                        tool_results=tool_results,
                        available_tools=available_tools,
                    )

                    print()
                    print(
                        "AGENT DECISION:",
                        decision.action,
                    )

                    # ---------------------------------------------
                    # LLM says enough evidence exists
                    # ---------------------------------------------

                    if decision.action == "final":
                        break

                    if not decision.tools:
                        break

                    selected_tool = decision.tools[0]

                    tool_name = selected_tool.name
                    arguments = selected_tool.arguments

                    print()
                    print("LLM SELECTED:")
                    print(f"Tool: {tool_name}")

                # -------------------------------------------------
                # Validate selected tool
                # -------------------------------------------------

                try:
                    self.validate_tool_call(
                        {
                            "name": tool_name,
                            "arguments": arguments,
                        },
                        available_tools,
                    )

                except ValueError as exc:
                    print()
                    print("INVALID TOOL CALL REJECTED:")
                    print(str(exc))
                    break

                # -------------------------------------------------
                # Security permission check
                # -------------------------------------------------

                permission = self.get_tool_permission(tool_name)

                if permission is None:
                    print()
                    print("UNAUTHORIZED TOOL REJECTED:")
                    print(
                        f"Tool '{tool_name}' has no permission definition."
                    )
                    break

                if permission == ToolPermission.WRITE:
                    if self.confirmation_service is None:
                        raise RuntimeError(
                            "Confirmation service is not configured"
                        )

                    confirmation_token = self.request_confirmation(
                        tool_name=tool_name,
                        arguments=arguments,
                    )

                    print()
                    print("CONFIRMATION REQUIRED:")
                    print(f"Tool: {tool_name}")
                    print("Confirmation token: [REDACTED]")

                    self.last_tool_results = list(tool_results)
                    self.last_tools_used = [
                        result["tool"]
                        for result in tool_results
                    ]

                    return {
                        "confirmation_required": True,
                        "confirmation_token": confirmation_token,
                        "tool": tool_name,
                        "arguments": arguments,
                    }

                # -------------------------------------------------
                # Prevent duplicate calls
                # -------------------------------------------------

                call_key = self.make_call_key(
                    tool_name,
                    arguments,
                )

                if call_key in executed_calls:
                    print()
                    print("DUPLICATE TOOL CALL REJECTED:")
                    print(f"Tool: {tool_name}")

                    break

                executed_calls.add(call_key)

                # -------------------------------------------------
                # Execute
                # -------------------------------------------------

                try:
                    result = await self.execute_tool(
                        tool_name,
                        arguments,
                    )

                except Exception as exc:
                    print()
                    print(f"TOOL FAILED: {tool_name}")
                    print(f"Error type: {type(exc).__name__}")

                    tool_results.append(
                        {
                            "tool": tool_name,
                            "arguments": arguments,
                            "success": False,
                            "error": str(exc),
                        }
                    )

                    continue

                if (
                    isinstance(result, dict)
                    and result.get("success") is False
                ):
                    error = result.get(
                        "error",
                        "Unknown MCP tool failure",
                    )

                    print()
                    print(f"TOOL FAILED: {tool_name}")
                    print("MCP tool returned an error.")

                    tool_results.append(
                        {
                            "tool": tool_name,
                            "arguments": arguments,
                            "success": False,
                            "error": error,
                        }
                    )

                    continue

                if (
                    isinstance(result, dict)
                    and result.get("success") is True
                ):
                    evidence = result.get("data")

                else:
                    evidence = result

                # -------------------------------------------------
                # Store result
                # -------------------------------------------------

                tool_results.append(
                    {
                        "tool": tool_name,
                        "arguments": arguments,
                        "success": True,
                        "data": evidence,
                    }
                )

                self.process_tool_result(
                    tool_name=tool_name,
                    arguments=arguments,
                    result=evidence,
                    identifiers=identifiers,
                )

                # -------------------------------------------------
                # TERMINAL CONDITION
                #
                # Once documentation has been retrieved,
                # we have enough evidence to synthesize the
                # final grounded answer.
                # -------------------------------------------------

                if (
                    tool_name == "search_documentation"
                    and evidence is not None
                ):
                    print()
                    print(
                        "Documentation evidence retrieved."
                    )
                    print(
                        "Generating final grounded answer..."
                    )

                    break

            else:
                print()
                print(
                    "Maximum investigation steps reached."
                )

            # -----------------------------------------------------
            # Final answer
            # -----------------------------------------------------

            final_answer = await self.generate_final_answer_async(
                query=query,
                identifiers=identifiers,
                tool_results=tool_results,
            )

            self.last_tool_results = list(tool_results)

            self.last_tools_used = [
                result["tool"]
                for result in tool_results
            ]

            print()
            print("===== FINAL ANSWER =====")
            print(final_answer)

            return final_answer

        finally:
            await self.disconnect()


if __name__ == "__main__":
    import asyncio

    asyncio.run(
        AgentService().investigate(
            "Why are orders failing for customer 1024?"
        )
    )