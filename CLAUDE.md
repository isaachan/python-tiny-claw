# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the main entry point
python cmd/claw/main.py

# Run tests
python tests/test_main_loop.py

# Clean __pycache__ directories (excludes venv/)
bash clean.sh
```

## Project Overview

`python-tiny-claw` is a minimal Python implementation of a **two-stage ReAct agent loop** — a coding agent similar to Claude Code, built from scratch. It is a work-in-progress with several stub/placeholder modules.

## Architecture

### Two-Stage ReAct Loop (`internal/engine/loop.py`)

The core loop (`AgentEngine.run()`) processes each turn in two phases:

1. **Phase 1 (Thinking):** Calls the LLM provider *without* tool definitions, producing a free-text reasoning trace.
2. **Phase 2 (Acting):** Calls the LLM provider *with* tool definitions, producing tool calls or a final answer.

If the response contains tool calls, they are executed and results are fed back as user-role messages.

### Provider Pattern (`internal/provider/llmprovider.py`)

`LLMProvider` is an abstract base class with a single `generate()` method. Concrete implementations connect to different LLM backends:

- `openai.py` — placeholder for OpenAI API integration (currently empty)
- Mock providers in `tests/test_main_loop.py` (`One_Stage_Mock_Provider`, `Two_Stage_Mock_Provider`) for testing

### Tool Registry (`internal/tools/registry.py`)

`Registry` is a stub class with `get_available_tools()` and `execute()` methods. Intended to manage tool registration and dispatch.

### Placeholder Modules

- `internal/context/context.py` — `Context` class (empty stub, intended to carry execution state)
- `internal/feishu/` — placeholder for Feishu/Lark chatbot integration
- `internal/memory/` — placeholder for long-term/short-term memory management

### Known Issues

- `AgentEngine.run()` has a `return None` inside the tool-execution loop that causes it to exit after a single turn instead of looping
- `Message.__init__` uses a mutable default argument: `toolcalls: list[ToolCall] = []`
- Imports are inconsistent: production code (`internal/`) uses bare-name imports (e.g., `from context.context import Context`), while the test file uses full paths (`from internal.context.context import Context`)
- No `__init__.py` files — relies on implicit namespace packages
- No packaging config (`pyproject.toml` / `setup.py`)
