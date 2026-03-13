# Task 1: Call an LLM from Code — Implementation Plan

## LLM Provider and Model

**Provider:** Qwen Code API (self-hosted on VM)

**Model:** `qwen3-coder-plus`

**Reason:** 1000 free requests/day, works from Russia, no credit card needed, supports OpenAI-compatible API.

## Environment Configuration

The agent reads LLM credentials from `.env.agent.secret`:

- `LLM_API_KEY` — API key for authentication
- `LLM_API_BASE` — Base URL (e.g., `http://10.93.24.169:42005/v1`)
- `LLM_MODEL` — Model name (`qwen3-coder-plus`)

## Agent Architecture

### Input

- Single command-line argument: the user's question
- Example: `uv run agent.py "What does REST stand for?"`

### Processing Flow

1. Parse command-line arguments using `argparse`
2. Load environment variables from `.env.agent.secret` using `python-dotenv`
3. Build system prompt (minimal for Task 1)
4. Call LLM via OpenAI-compatible chat completions API using `httpx`
5. Extract the assistant's answer from the response
6. Format output as JSON

### Output

Single JSON line to stdout:

```json
{"answer": "<llm response>", "tool_calls": []}
```

- `answer`: The LLM's response text
- `tool_calls`: Empty array (tools added in Task 2)

### Error Handling

- Exit code 0 on success
- Exit code 1 on errors (missing args, API failures, invalid JSON)
- All debug/logging output goes to stderr (not stdout)
- Timeout: 60 seconds for API call

## Dependencies

Using existing project dependencies from `pyproject.toml`:

- `httpx` — HTTP client for API calls (already in project)
- `pydantic-settings` — Environment variable loading (already in project)
- `python-dotenv` — Load `.env` files (transitive via pydantic-settings)

No new dependencies needed.

## File Structure

```
se-toolkit-lab-6/
├── agent.py              # Main CLI agent
├── .env.agent.secret     # LLM credentials (gitignored)
├── plans/
│   └── task-1.md         # This plan
├── AGENT.md              # Architecture documentation (created in this task)
└── backend/tests/
    └── e2e/
        └── test_agent_task1.py  # Regression test
```

## Testing Strategy

Create one regression test in `backend/tests/e2e/test_agent_task1.py`:

1. Run `agent.py` as subprocess with a test question
2. Parse stdout as JSON
3. Assert `answer` field exists and is non-empty
4. Assert `tool_calls` field exists and is an empty list
5. Assert exit code is 0

## Acceptance Criteria Checklist

- [ ] Plan created before code
- [ ] `agent.py` in project root
- [ ] Outputs valid JSON with `answer` and `tool_calls`
- [ ] API key from `.env.agent.secret` (not hardcoded)
- [ ] `AGENT.md` documents architecture
- [ ] 1 regression test passes
- [ ] Git workflow followed
