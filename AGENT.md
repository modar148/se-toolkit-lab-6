# Documentation and System Agent

## Overview
This is an autonomous CLI agent built in Python that navigates the project repository to answer user questions based on actual documentation files, source code analysis, and live application data gathering. 

## Architecture
- **Language:** Python 3 (using strict standard libraries such as `urllib` and `os` to avoid external dependencies).
- **LLM Provider:** Qwen Code API (hosted locally on the remote VM).
- **Model:** `qwen3-coder-plus`.

## Agentic Loop & Tools
The agent runs in a `while` loop constrained to a maximum of 10 iterations. The LLM decides what to do based on the system prompt logic:
1. `list_files(path)`: Used to discover files in the repository. Security is enforced by absolute path resolution ensuring the agent cannot escape the project root directory.
2. `read_file(path)`: Used to read wiki documentation or inspect raw source code (like checking what web framework the backend uses).
3. `query_api(method, path, body)`: Used to directly request data from the live backend API. 

## Authentication and Environments
The agent relies purely on environment variables for configuration. The LLM credentials (`LLM_API_KEY`, `LLM_API_BASE`, `LLM_MODEL`) are retrieved from `.env.agent.secret`. Crucially, backend authentication relies on the `LMS_API_KEY` fetched from `.env.docker.secret`. This key is automatically injected into the HTTP request headers as a Bearer token when the `query_api` tool is invoked. The API target defaults to `http://localhost:42002` but can be overridden by the `AGENT_API_BASE_URL` environment variable.

## Lessons Learned from Benchmark
During the development and testing process, several key lessons were learned:
- **Error Handling:** The `urllib.request` library throws exceptions for non-200 HTTP responses. We had to ensure the `query_api` tool catches `HTTPError` exceptions and manually returns the status code and error body back to the LLM. Without this, the agent would crash instead of diagnosing backend bugs.
- **Null Safety:** Sometimes the LLM returns `null` for the message content when making tool calls. We learned to gracefully handle `msg.get("content") or ""` to prevent `NoneType` attribute errors.
- **Token Limits:** Large files can quickly consume the LLM context window, forcing us to ensure our system prompt was highly specific about which tools to use and when.
