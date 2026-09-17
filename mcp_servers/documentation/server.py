import asyncio
import logging
from mcp.server import MCPServer

from app.config import (
    MAX_RETRIES,
    RAG_TIMEOUT,
    RETRY_BACKOFF_BASE,
    RETRY_BACKOFF_MAX,
)
from rag.retrieval import RAGRetriever



server = MCPServer("OpsPilot Documentation Server")
logger = logging.getLogger(__name__)

retriever = None


def get_retriever() -> RAGRetriever:
    global retriever

    if retriever is None:
        retriever = RAGRetriever()

    return retriever


def retrieve_documentation(
    query: str,
    top_k: int,
) -> list[dict]:
    return get_retriever().retrieve(
        query=query,
        top_k=top_k,
    )


def is_transient_rag_error(exc):
    if isinstance(exc, (ConnectionError, TimeoutError, OSError)):
        return True

    message = str(exc).lower()
    return any(
        marker in message
        for marker in (
            "timeout",
            "timed out",
            "temporarily unavailable",
            "connection",
            "network",
            "transport",
        )
    )


async def wait_before_retry(attempt, category):
    delay = min(
        RETRY_BACKOFF_BASE * (2 ** (attempt - 1)),
        RETRY_BACKOFF_MAX,
    )
    logger.warning(
        "RAG retry backoff: operation=retrieve attempt=%s delay=%ss "
        "category=%s",
        attempt,
        delay,
        category,
    )
    await asyncio.sleep(delay)


@server.tool()
async def search_documentation(
    query: str,
    top_k: int = 5,
) -> dict:
    """Search OpsPilot documentation using the RAG pipeline."""

    if not query.strip():
        return {
            "count": 0,
            "results": [],
            "error": "Search query cannot be empty",
        }
    total_attempts = 1 + MAX_RETRIES

    for attempt in range(1, total_attempts + 1):
        try:
            results = await asyncio.wait_for(
                asyncio.to_thread(
                    retrieve_documentation,
                    query,
                    top_k,
                ),
                timeout=RAG_TIMEOUT,
            )

            if not results:
                return {
                    "count": 0,
                    "results": [],
                    "message": "No documentation found",
                }

            return {
                "count": len(results),
                "query": query,
                "results": results,
            }

        except asyncio.TimeoutError:
            if attempt < total_attempts:
                logger.warning(
                    "RAG retry: operation=retrieve attempt=%s/%s "
                    "category=timeout",
                    attempt,
                    total_attempts,
                )
                await wait_before_retry(attempt, "timeout")
                continue

            logger.warning(
                "RAG retrieval timeout: timeout=%ss",
                RAG_TIMEOUT,
            )
            return {
                "count": 0,
                "results": [],
                "error": (
                    f"RAG retrieval timed out after {RAG_TIMEOUT} seconds"
                ),
            }
        except Exception as exc:
            if (
                is_transient_rag_error(exc)
                and attempt < total_attempts
            ):
                logger.warning(
                    "RAG retry: operation=retrieve attempt=%s/%s "
                    "category=transient_error",
                    attempt,
                    total_attempts,
                )
                await wait_before_retry(attempt, "transient_error")
                continue

            return {
                "count": 0,
                "results": [],
                "error": "Documentation retrieval error",
                "details": str(exc),
            }






async def main():
    await server.run_stdio_async()


if __name__ == "__main__":
    asyncio.run(main())