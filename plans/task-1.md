# Plan: Task 1 - Call an LLM from Code

## 1. LLM Provider and Model
* **Provider:** Qwen Code API (hosted locally on the remote VM via proxy).
* **Model:** `qwen3-coder-plus`.
* **Configuration:** Endpoints and keys will be read from `.env.agent.secret`.

## 2. Agent Architecture
The `agent.py` script will be built with the following steps:
1. **Input:** Read the question from the first CLI argument (`sys.argv[1]`).
2. **Environment:** Use the `dotenv` package to load variables securely.
3. **API Call:** Send a POST request to the Qwen proxy using the `requests` library.
4. **Output Format:** Extract the answer and print a strict JSON string to `stdout` containing `{"answer": "...", "tool_calls": []}`.
5. **Error Handling:** Route any errors or debug logs strictly to `stderr` to avoid breaking the JSON output.
