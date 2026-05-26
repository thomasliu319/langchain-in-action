# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a LangChain learning project demonstrating LLM chains, agents, and API patterns. Content is primarily in Chinese. The codebase has been reorganized from flat chapter files into topic-based subdirectories.

## Environment

- Conda environment: `langchain-dev`
- Activate: `conda activate langchain-dev`
- Python version: 3.10+

## Dependency Installation

There are **two separate requirements files** serving different parts of the codebase:

```bash
# For chapter1 (PyTorch Transformer, basic chains) — torch/torchtext/transformers/scikit-learn etc.
pip install -r requirements.txt

# For agent_api (FastAPI server, agents, tools, langgraph) — langchain/fastapi/tavily/langgraph etc.
pip install -r com/thomasliu/langchain/agent_api/requirements.txt
```

Both are needed to run all examples in the project.

## Running Files

Each Python file is a self-contained example. Run them from the **project root**:

```bash
python com/thomasliu/langchain/chapter1/llm_chain_basic.py
python com/thomasliu/langchain/chapter1/sequential_chain.py
python com/thomasliu/langchain/agent_api/structured_output_demo.py
python com/thomasliu/langchain/agent_api/search_agent_demo.py
python com/thomasliu/langchain/agent_api/InMemorySaver.py
python com/thomasliu/langchain/agent_api/agent_api.py       # starts FastAPI server on :8000
```

### `.env` file location — IMPORTANT

The `.env` file lives in `com/thomasliu/langchain/agent_api/.env`, **not** the project root. `load_dotenv()` searches the current working directory. When running from the project root (as recommended above), the `.env` **will not be found automatically**.

Two ways to handle this:
1. `cd com/thomasliu/langchain/agent_api && python agent_api.py` (cd into the directory first)
2. Set environment variables manually before running: `export OPENAI_API_KEY=...`

Chapter1 examples do **not** call `load_dotenv()` at all — you must export env vars yourself or wrap them with dotenv loading.

## LLM Provider: DeepSeek

All examples use DeepSeek API. There are two client approaches with **two different env var naming conventions**:

### agent_api (newer examples — agents, tools, structured output)
Uses `ChatOpenAI` from `langchain_openai`. Reads these env vars:
```
OPENAI_API_KEY=sk-xxx          # Your DeepSeek API key
OPENAI_BASE_URL=https://api.deepseek.com
OPENAI_MODEL=deepseek-v4-pro
TAVILY_API_KEY=tvly-xxx        # Only for search_agent_demo.py
```

### chapter1 (older examples — basic chains)
Uses `ChatDeepSeek` from `langchain_deepseek`. Reads these env vars:
```
DEEPSEEK_API_KEY=sk-xxx
DEEPSEEK_BASE_URL=https://api.deepseek.com
MODEL_NAME=deepseek-chat
```

**Keep these naming conventions separate.** Changing chapter1 files to use `OPENAI_*` vars will break them — they look for `DEEPSEEK_*`.

## DeepSeek Quirks to Know

- **No `response_format`**: DeepSeek does not support OpenAI-style structured output (JSON schema mode). Use `PydanticOutputParser` with prompt-based format instructions instead.
- **Thinking mode breaks agents**: DeepSeek V4's thinking mode returns `reasoning_content` that must be passed back in multi-turn requests. LangChain's agent framework strips these. Always disable thinking (`{"type": "disabled"}`) when using `create_agent`. See `search_agent_demo.py:31` for the canonical pattern.
- **Thinking type is a struct**: Setting `thinking=False` (boolean) fails — it must be `{"type": "disabled"}`.
- **`agent_api.py` is missing thinking disable**: The FastAPI server at `agent_api.py:13-17` does NOT disable thinking mode. This is a known issue — basic `/chat` may work but agent behavior can be erratic. If you add tools to this server, add `model_kwargs={"extra_body": {"thinking": {"type": "disabled"}}}`.

## Codebase Structure

- **`agent_api/`** — Practical agent examples built with FastAPI + LangChain + LangGraph:
  - `agent_api.py` — FastAPI server exposing `/chat` (one-shot) and `/stream` (SSE) endpoints. CORS enabled for all origins.
  - `structured_output_demo.py` — Extracting typed data from unstructured text via `PydanticOutputParser` (DeepSeek doesn't support native structured output).
  - `search_agent_demo.py` — Agent with Tavily web search tool. Uses `@tool` decorator to define `search_web`, binds it via `create_agent`.
  - `InMemorySaver.py` — Agent with conversation memory via `langgraph.checkpoint.memory.InMemorySaver`. Same `thread_id` = same conversation context.
  - `test.html` — Browser-based test page for the FastAPI endpoints.
- **`chapter1/`** — Foundational LangChain concepts:
  - `transformer_model.py` — PyTorch Transformer from scratch (text classification with AG_NEWS dataset, 4-class). Trains 3 epochs.
  - `sequential_chain.py` — Manual multi-step chain (intent → entity → action → response) using `ChatDeepSeek`. Demonstrates the chain pattern without using LangChain's `SequentialChain` class.
  - `sequential_chain_shared_memory.py` — Variant with shared memory dictionary across steps.
  - `llm_chain_basic.py` — Minimal LLM chain with `PromptTemplate | llm` pipe syntax.
  - `llm_chain_with_memory.py` — LLM chain with conversation memory.
