## Runtime Configuration

`MCP_TOOL_TIMEOUT` limits how long the client waits for an individual MCP
tool call. It defaults to 60 seconds and can be overridden through the
environment, for example:

```bash
MCP_TOOL_TIMEOUT=5 ./myvenv/bin/python -u -m app.services.agent_service
```

`LLM_TIMEOUT` limits the Ollama HTTP request and the async wait around the
synchronous client call. It defaults to 30 seconds:

```bash
LLM_TIMEOUT=15 ./myvenv/bin/python -u -m app.services.agent_service
```

`RAG_TIMEOUT` bounds the documentation retrieval operation, including its
hybrid search and reranking work. It defaults to 60 seconds:

```bash
RAG_TIMEOUT=30 ./myvenv/bin/python -u -m app.services.agent_service
```

`MAX_RETRIES` controls bounded retries for transient read-only MCP, LLM, and
RAG failures. It defaults to 2 retries after the initial attempt. No backoff
is applied yet:

```bash
MAX_RETRIES=2 ./myvenv/bin/python -u -m app.services.agent_service
```

Retry delays use exponential backoff capped at 5 seconds by default:

```text
delay = min(RETRY_BACKOFF_BASE * 2 ** (attempt - 1), RETRY_BACKOFF_MAX)
```

Configure the values with `RETRY_BACKOFF_BASE` and `RETRY_BACKOFF_MAX`.
