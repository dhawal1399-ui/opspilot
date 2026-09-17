import asyncio
import json
import logging
import sys
from contextlib import AsyncExitStack

from app.config import (
    MAX_RETRIES,
    MCP_TOOL_TIMEOUT,
    RETRY_BACKOFF_BASE,
    RETRY_BACKOFF_MAX,
)
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


logger = logging.getLogger(__name__)


class MCPClient:
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

    def __init__(self):
        python_executable = sys.executable

        self.server_configs = {
            "database": StdioServerParameters(
                command=python_executable,
                args=["-m", "mcp_servers.database.server"],
            ),
            "logs": StdioServerParameters(
                command=python_executable,
                args=["-m", "mcp_servers.logs.server"],
            ),
            "tickets": StdioServerParameters(
                command=python_executable,
                args=["-m", "mcp_servers.tickets.server"],
            ),
            "documentation": StdioServerParameters(
                command=python_executable,
                args=["-m", "mcp_servers.documentation.server"],
            ),
            "health": StdioServerParameters(
                command=python_executable,
                args=["-m", "mcp_servers.health.server"],
            ),
        }

        self.connections = {}
        self.unavailable_servers = {}
        self._exit_stack = AsyncExitStack()

    def _tool_failure(self, tool_name, message, retryable=False):
        failure = {
            "success": False,
            "error": f"MCP tool '{tool_name}' failed: {message}",
        }
        if retryable:
            failure["retryable"] = True
        return failure

    def _tool_error_message(self, result):
        if result.content:
            first_content = result.content[0]
            text = getattr(first_content, "text", None)
            if text:
                return text

        return "MCP server returned an error"

    def _is_transient_exception(self, exc):
        transient_types = {
            "ConnectionError",
            "TimeoutError",
            "ConnectError",
            "ReadTimeout",
            "WriteTimeout",
            "PoolTimeout",
            "NetworkError",
            "TransportError",
            "ServerError",
            "ServiceUnavailable",
        }
        return isinstance(exc, (ConnectionError, TimeoutError, OSError)) or (
            type(exc).__name__ in transient_types
        )

    def _is_transient_message(self, message):
        lowered = message.lower()
        return any(
            marker in lowered
            for marker in (
                "timed out",
                "timeout",
                "temporarily unavailable",
                "service unavailable",
                "connection",
                "network",
                "transport",
                "502",
                "503",
                "504",
            )
        )

    async def _wait_before_retry(self, attempt, category, operation):
        delay = min(
            RETRY_BACKOFF_BASE * (2 ** (attempt - 1)),
            RETRY_BACKOFF_MAX,
        )
        logger.warning(
            "MCP retry backoff: tool=%s attempt=%s delay=%ss category=%s",
            operation,
            attempt,
            delay,
            category,
        )
        await asyncio.sleep(delay)

    async def _call_tool_once(self, tool_name, arguments):
        for server_name, connection in self.connections.items():
            result = await connection["session"].list_tools()

            tool_names = {
                tool.name
                for tool in result.tools
            }

            if tool_name not in tool_names:
                continue

            try:
                result = await asyncio.wait_for(
                    connection["session"].call_tool(
                        tool_name,
                        arguments=arguments,
                    ),
                    timeout=MCP_TOOL_TIMEOUT,
                )
            except asyncio.TimeoutError:
                return self._tool_failure(
                    tool_name,
                    f"timed out after {MCP_TOOL_TIMEOUT} seconds",
                    retryable=True,
                )
            except Exception as exc:
                if self._is_transient_exception(exc):
                    raise
                return self._tool_failure(
                    tool_name,
                    type(exc).__name__,
                )

            if result.is_error:
                message = self._tool_error_message(result)
                if self._is_transient_message(message):
                    raise ConnectionError(message)
                return self._tool_failure(tool_name, message)

            if result.structured_content is not None:
                if not isinstance(
                    result.structured_content,
                    (dict, list),
                ):
                    return self._tool_failure(
                        tool_name,
                        "unexpected structured response",
                    )

                if (
                    isinstance(result.structured_content, dict)
                    and result.structured_content.get("error")
                ):
                    return self._tool_failure(
                        tool_name,
                        str(result.structured_content["error"]),
                    )

                return {
                    "success": True,
                    "data": result.structured_content,
                }

            if result.content:
                text = getattr(result.content[0], "text", None)
                if not text:
                    return self._tool_failure(
                        tool_name,
                        "unexpected response content",
                    )

                try:
                    data = json.loads(text)
                except (TypeError, json.JSONDecodeError):
                    return self._tool_failure(
                        tool_name,
                        "malformed response data",
                    )

                if isinstance(data, dict) and data.get("error"):
                    return self._tool_failure(
                        tool_name,
                        str(data["error"]),
                    )

                return {
                    "success": True,
                    "data": data,
                }

            return self._tool_failure(
                tool_name,
                "empty response",
            )

        if self.unavailable_servers:
            unavailable_names = list(self.unavailable_servers)
            raise RuntimeError(
                f"MCP tool '{tool_name}' is unavailable; unavailable MCP "
                f"servers: {unavailable_names}"
            )

        raise ValueError(f"MCP tool '{tool_name}' not found")

    async def connect(self):
        print("DEBUG: connecting MCP servers")

        for server_name, server_params in self.server_configs.items():
            print(
                f"DEBUG: starting MCP server '{server_name}' "
                f"with {server_params.command}"
            )

            try:
                read_stream, write_stream = (
                    await self._exit_stack.enter_async_context(
                        stdio_client(server_params)
                    )
                )

                session = ClientSession(
                    read_stream,
                    write_stream,
                )

                await self._exit_stack.enter_async_context(session)
                await session.initialize()

                self.connections[server_name] = {
                    "session": session,
                }

                print(f"DEBUG: MCP server '{server_name}' connected")
            except Exception as exc:
                self.unavailable_servers[server_name] = exc
                print(
                    f"ERROR: MCP server '{server_name}' connection failed: "
                    f"{exc}"
                )

        unavailable_names = list(self.unavailable_servers)
        print(
            f"DEBUG: MCP servers connected: "
            f"{len(self.connections)}/{len(self.server_configs)}"
        )
        if unavailable_names:
            print(f"DEBUG: unavailable MCP servers: {unavailable_names}")

    async def list_tools(self):
        all_tools = []

        for server_name, connection in self.connections.items():
            result = await connection["session"].list_tools()

            for tool in result.tools:
                all_tools.append(
                    {
                        "server": server_name,
                        "tool": tool,
                    }
                )

        return all_tools

    async def call_tool(
        self,
        tool_name: str,
        arguments: dict,
    ):
        retryable = tool_name in self.READ_ONLY_TOOLS
        total_attempts = 1 + MAX_RETRIES if retryable else 1

        for attempt in range(1, total_attempts + 1):
            try:
                result = await self._call_tool_once(
                    tool_name,
                    arguments,
                )
            except Exception as exc:
                if (
                    isinstance(exc, (RuntimeError, ValueError))
                    and (
                        "unavailable" in str(exc).lower()
                        or "not found" in str(exc).lower()
                    )
                ):
                    raise

                if not retryable or not self._is_transient_exception(exc):
                    return self._tool_failure(
                        tool_name,
                        type(exc).__name__,
                    )

                if attempt == total_attempts:
                    return self._tool_failure(
                        tool_name,
                        type(exc).__name__,
                    )

                logger.warning(
                    "MCP retry: tool=%s attempt=%s/%s category=%s",
                    tool_name,
                    attempt,
                    total_attempts,
                    type(exc).__name__,
                )
                await self._wait_before_retry(
                    attempt,
                    type(exc).__name__,
                    tool_name,
                )
                continue

            if result.get("success") is True:
                return result

            message = result.get("error", "MCP tool failure")
            if (
                retryable
                and result.get("retryable") is True
                and attempt < total_attempts
            ):
                logger.warning(
                    "MCP retry: tool=%s attempt=%s/%s category=%s",
                    tool_name,
                    attempt,
                    total_attempts,
                    "timeout",
                )
                await self._wait_before_retry(
                    attempt,
                    "timeout",
                    tool_name,
                )
                continue

            return result

    async def disconnect(self):
        print("DEBUG: disconnecting MCP servers")

        await self._exit_stack.aclose()
        self.connections.clear()
        self.unavailable_servers.clear()
        print("DEBUG: MCP servers disconnected")