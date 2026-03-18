# Plan: Task 3 - The System Agent

## 1. Tool Schema (`query_api`)
We will introduce a new tool `query_api` that allows the LLM to make HTTP requests to the live backend.
* **Parameters**: `method` (GET, POST, etc.), `path` (endpoint path, e.g., `/items/`), and an optional `body` (JSON string).
* **Return**: A JSON string containing `status_code` and `body` of the HTTP response.

## 2. Authentication & Environment Variables
* The backend is protected. We will load `.env.docker.secret` using our custom env parser and read `LMS_API_KEY`.
* This key will be injected into the `Authorization` header as a Bearer token.
* `AGENT_API_BASE_URL` will be read from the environment, defaulting to `http://localhost:42002`.

## 3. System Prompt Strategy
The prompt will be updated to explicitly guide the LLM:
* Use `list_files` and `read_file` to search the `wiki/` directory for documentation and backend directories for source code.
* Use `query_api` strictly for dynamic data (e.g., database counts, API errors, live status).

## 4. Benchmark Iteration & Diagnosis
Initial strategy: Start with generous token limits. If `NoneType` errors occur, handle `null` content strings. Refine prompt if tools are confused.
