# Documentation Agent

## Overview
This is an autonomous CLI agent built in Python that navigates the project repository to answer user questions based on actual documentation files.

## Architecture
- **Language:** Python 3 (using standard libraries).
- **LLM Provider:** Qwen Code API (hosted locally on the remote VM).
- **Model:** `qwen3-coder-plus`.

## Agentic Loop
The agent runs in a `while` loop (capped at 10 iterations to prevent infinite looping).
1. The user's question and a strict system prompt are sent to the LLM.
2. If the LLM requests a tool call, the local Python script executes it, appends the result as a `role: tool` message, and loops back to the LLM.
3. Once the LLM has enough information, it generates a standard text response ending with a structured `SOURCE:` tag.
4. The script parses the final text, extracts the answer and source, and outputs a strict JSON payload.

## Secure Tools
- `list_files(path)`: Lists directory contents.
- `read_file(path)`: Returns file contents.
- **Security:** Both tools use absolute path resolution (`pathlib.Path.resolve()`) and strictly verify that the requested target path `.startswith()` the project root directory. Any attempt to use `../` to escape the repository boundary results in a hardcoded access denied error fed back to the LLM.
