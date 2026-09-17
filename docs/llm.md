# LLM Integration

## LLM Provider

OpsPilot uses Ollama for local LLM inference.

## Model

The default model is:

- llama3.2

## Why Ollama?

Ollama was selected for local development because it allows the
application to run LLM inference without depending on an external
LLM API or API key.

It also makes development and testing easier while keeping the
LLM integration replaceable through the LLM service abstraction.

## Current LLM Responsibilities

The LLM is used for:

- Query intent classification
- Query rewriting
- Conversational understanding
- Final troubleshooting response generation

## Configuration

The LLM model is configurable through the application configuration
rather than being hardcoded throughout the application.

## Future Providers

The LLM service should be designed so that external providers such
as OpenAI or Anthropic can be added later without changing the
rest of the OpsPilot architecture.