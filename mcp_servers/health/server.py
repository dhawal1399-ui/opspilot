import asyncio

import httpx
from mcp.server import MCPServer


server = MCPServer("Health MCP Server")


# Health status values:
# HEALTHY  -> service is responding successfully
# DEGRADED -> service is responding but with an unhealthy/slow condition
# DOWN     -> service cannot be reached or is returning server errors
# UNKNOWN   -> health state could not be determined


@server.tool()
async def check_api_health(
    url: str,
    timeout: float = 5.0,
) -> dict:
    """Check whether an API health endpoint is available."""
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url)

        if response.status_code == 200:
            return {
                "status": "HEALTHY",
                "url": url,
                "status_code": response.status_code,
            }

        if 400 <= response.status_code < 500:
            return {
                "status": "DEGRADED",
                "url": url,
                "status_code": response.status_code,
            }

        if response.status_code >= 500:
            return {
                "status": "DOWN",
                "url": url,
                "status_code": response.status_code,
            }

        return {
            "status": "UNKNOWN",
            "url": url,
            "status_code": response.status_code,
        }

    except httpx.TimeoutException:
        return {
            "status": "DOWN",
            "url": url,
            "error": "Request timed out",
        }

    except httpx.ConnectError:
        return {
            "status": "DOWN",
            "url": url,
            "error": "Connection failed",
        }

    except httpx.HTTPError as exc:
        return {
            "status": "UNKNOWN",
            "url": url,
            "error": str(exc),
        }


@server.tool()
async def check_endpoint(
    url: str,
    method: str = "GET",
    timeout: float = 5.0,
) -> dict:
    """Check an HTTP endpoint and return its health status."""
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:

            if method.upper() == "GET":
                response = await client.get(url)

            elif method.upper() == "HEAD":
                response = await client.head(url)

            else:
                return {
                    "status": "UNKNOWN",
                    "url": url,
                    "error": f"Unsupported HTTP method: {method}",
                }

        if 200 <= response.status_code < 300:
            status = "HEALTHY"

        elif 400 <= response.status_code < 500:
            status = "DEGRADED"

        elif response.status_code >= 500:
            status = "DOWN"

        else:
            status = "UNKNOWN"

        return {
            "status": status,
            "url": url,
            "method": method.upper(),
            "status_code": response.status_code,
        }

    except httpx.TimeoutException:
        return {
            "status": "DOWN",
            "url": url,
            "method": method.upper(),
            "error": "Request timed out",
        }

    except httpx.ConnectError:
        return {
            "status": "DOWN",
            "url": url,
            "method": method.upper(),
            "error": "Connection failed",
        }

    except httpx.HTTPError as exc:
        return {
            "status": "UNKNOWN",
            "url": url,
            "method": method.upper(),
            "error": str(exc),
        }


@server.tool()
async def get_service_status(
    service_name: str,
    url: str,
    timeout: float = 5.0,
) -> dict:
    """Get the current health status of a named service."""
    result = await check_api_health(
        url=url,
        timeout=timeout,
    )

    return {
        "service": service_name,
        **result,
    }


async def main():
    await server.run_stdio_async()


if __name__ == "__main__":
    asyncio.run(main())