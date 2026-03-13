# Agent Architecture

## Overview

This agent is a CLI tool that answers questions by calling an LLM API. It is the foundation for the more advanced agent you will build in Tasks 2–3, which will add tools and an agentic loop.

## LLM Provider

**Provider:** Qwen Code API (self-hosted on VM)

**Model:** `qwen3-coder-plus`

**Why Qwen Code?**
- 1000 free requests per day
- Works from Russia without VPN
- No credit card required
- OpenAI-compatible API

## Configuration

The agent reads LLM credentials from `.env.agent.secret` in the project root:

```text
LLM_API_KEY=<your-api-key>
LLM_API_BASE=http://<vm-ip>:42005/v1
LLM_MODEL=qwen3-coder-plus
```

> **Note:** This is **not** the same as `LMS_API_KEY` in `.env.docker.secret`. That key protects your backend LMS endpoints. `LLM_API_KEY` authenticates with the LLM provider.

## How It Works

### Input

The agent accepts a single command-line argument — the user's question:

```bash
uv run agent.py "What does REST stand for?"
```

### Processing Flow

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Command-line   │────▶│  Load settings   │────▶│  Call LLM API   │
│  argument       │     │  from .env       │     │  (HTTP POST)    │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                                                        │
                                                        ▼
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  JSON output    │◀────│  Format answer   │◀────│  Parse response │
│  to stdout      │     │  + tool_calls    │     │  from LLM       │
└─────────────────┘     └──────────────────┘     └─────────────────┘
```

1. **Parse arguments** — `argparse` extracts the question from command line
2. **Load settings** — Read `.env.agent.secret` using `python-dotenv`
3. **Call LLM** — HTTP POST to `{LLM_API_BASE}/chat/completions` with:
   - System prompt: "You are a helpful assistant..."
   - User message: the question
4. **Parse response** — Extract `choices[0].message.content`
5. **Output JSON** — Print `{"answer": "...", "tool_calls": []}` to stdout

### Output

Single JSON line to stdout:

```json
{"answer": "Representational State Transfer.", "tool_calls": []}
```

- `answer`: The LLM's response text
- `tool_calls`: Empty array (tools will be added in Task 2)

### Error Handling

- **Exit code 0** — Success
- **Exit code 1** — Error (missing args, API failure, invalid response)
- **Debug output** — All logs go to stderr (not stdout)
- **Timeout** — 60 seconds for API calls

## File Structure

```
se-toolkit-lab-6/
├── agent.py              # Main CLI agent
├── .env.agent.secret     # LLM credentials (gitignored)
├── AGENT.md              # This documentation
├── plans/
│   └── task-1.md         # Implementation plan
└── backend/tests/e2e/
    └── test_agent_task1.py  # Regression test
```

## Dependencies

The agent uses existing project dependencies from `pyproject.toml`:

| Package | Purpose |
|---------|---------|
| `httpx` | HTTP client for API calls |
| `python-dotenv` | Load `.env` files |
| `argparse` | Command-line argument parsing (stdlib) |
| `json` | JSON encoding/decoding (stdlib) |

No new dependencies required.

## Running the Agent

```bash
# Basic usage
uv run agent.py "Your question here"

# Example
uv run agent.py "What does REST stand for?"

# Output
{"answer": "Representational State Transfer.", "tool_calls": []}
```

## Testing

Run the regression test:

```bash
uv run pytest backend/tests/e2e/test_agent_task1.py -v
```

The test:
1. Runs `agent.py` as a subprocess
2. Parses stdout as JSON
3. Verifies `answer` field exists and is non-empty
4. Verifies `tool_calls` field exists and is an empty list
5. Checks exit code is 0

## Next Steps (Tasks 2–3)

In the next tasks, you will extend this agent with:

- **Task 2:** Add tools (`read_file`, `list_files`, `query_api`) to answer questions about the codebase and backend API
- **Task 3:** Add an agentic loop that allows the agent to make multiple tool calls before giving a final answer
