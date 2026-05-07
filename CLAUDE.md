# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the main entry point (requires DEEPSEEK_API_KEY set)
python cmd/claw/main.py

# Run all tests
python -m pytest tests/ -v

# Run a single test file
python -m pytest tests/test_openai_provider.py -v

# Clean __pycache__ directories (excludes venv/)
bash clean.sh
```

## Project Overview

`python-tiny-claw` is a minimal Python implementation of a **two-stage ReAct agent loop** — a coding agent similar to Claude Code, built from scratch.

## Architecture

### Two-Stage ReAct Loop (`internal/engine/loop.py`)

`AgentEngine` processes each turn in two phases when `enableThinking=True`:

1. **Phase 1 (Thinking):** Calls the LLM provider *without* tool definitions, producing a free-text reasoning trace stored as `reasoning_content`.
2. **Phase 2 (Acting):** Calls the LLM provider *with* tool definitions, producing tool calls or a final answer.

If `enableThinking=False`, Phase 1 is skipped. The loop runs until the model produces a response with no tool calls.

`AgentEngine.__init__` takes: `llmprovider`, `registry`, `workdir`, `stream` (bool), and `enableThinking` (bool).

### Message Schema (`internal/schema/message.py`)

- **`Role`** — enum: `SYS`, `USER`, `ASSISTANT`
- **`Message`** — fields: `role`, `content`, `toolcalls` (list of `ToolCall`), `toolcall_id` (optional, for tool-result messages), `reasoning_content` (optional, for thinking-phase traces)
- **`ToolCall`** — fields: `id`, `name`, `arguments` (JSON string)
- **`ToolResult`** — fields: `toolcall_id`, `output`, `is_error`
- **`ToolDefinition`** — fields: `name`, `description`, `input_schema` (dict or JSON string, JSON Schema format)

### Provider Pattern (`internal/provider/`)

`LLMProvider` is an abstract base class with a single `generate(ctx, context_history, available_tools, stream) -> Message` method.

`OpenAIProvider` is the concrete implementation using the `openai` SDK:
- `create_deepseek_provider()` — factory classmethod that reads `DEEPSEEK_API_KEY`, `DEEPSEEK_BASE_URL`, and `DEEPSEEK_MODEL` from env vars
- Supports both stream and non-stream modes via `_generate_stream` / `_generate_nonstream`
- When `enable_thinking=True`, passes `reasoning_effort="high"` and `extra_body={"thinking": {"type": "enabled"}}` — DeepSeek-specific thinking tokens
- `_convert_message` maps internal `Message` → OpenAI-format dict (handles system/user/assistant/tool roles and reasoning_content)
- `_convert_tool` maps `ToolDefinition` → OpenAI tool dict

### Tool System (`internal/tools/`)

`BaseTool` — abstract tool class; subclasses implement `execute(ctx, args: str) -> str`.

`Registry` — holds registered tools, provides `get_available_tools()` (returns `list[ToolDefinition]`) and `execute(ctx, toolcall)` (returns `ToolResult`).

`ReadfileTool` — the one concrete tool; reads files relative to `work_dir`, returns content truncated to 8000 bytes.

### Placeholder Modules

- `internal/context/context.py` — `Context` class (empty stub, intended to carry execution state)
- `internal/feishu/` — placeholder for Feishu/Lark chatbot integration
- `internal/memory/` — placeholder for long-term/short-term memory management

### Environment Variables

| Variable | Purpose | Default |
|---|---|---|
| `DEEPSEEK_API_KEY` | API key for DeepSeek | (required) |
| `DEEPSEEK_BASE_URL` | DeepSeek API base URL | `https://api.deepseek.com/v1` |
| `DEEPSEEK_MODEL` | Model name | `deepseek-v4-flash` |

### Known Issues

- `Message.__init__` uses a mutable default argument: `toolcalls: list[ToolCall] = []`
- No `__init__.py` files — relies on implicit namespace packages
- No packaging config (`pyproject.toml` / `setup.py`)
