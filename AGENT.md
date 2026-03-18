# Agent Documentation

## Overview
This is a lightweight CLI agent built in Python. It accepts a question via the command line, sends it to a Large Language Model, and returns a structured JSON answer containing an `answer` string and an empty `tool_calls` list.

## Architecture
- **Language:** Python 3 (using standard libraries like `urllib`).
- **LLM Provider:** Qwen Code API (hosted locally on the remote VM via `qwen-code-oai-proxy`).
- **Model:** `qwen3-coder-plus`.
- **Environment:** Secrets are loaded safely from `.env.agent.secret`.

## Usage
Run the agent using `uv`:
`uv run agent.py "What does REST stand for?"`

## Data Flow
1. **Input:** Arguments are parsed from `sys.argv`.
2. **Processing:** An HTTP POST request is dispatched to the OpenAI-compatible `/v1/chat/completions` endpoint.
3. **Output:** The agent extracts the generated text and prints strict, parseable JSON to `stdout`. All error handling is routed to `stderr`.