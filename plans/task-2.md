# Plan: Task 2 - The Documentation Agent

## 1. Tool Schemas
We will define two tools using the OpenAI-compatible function calling schema format:
* `read_file`: Accepts a `path` parameter. Used to read the contents of markdown files in the repository.
* `list_files`: Accepts a `path` parameter. Used to explore directory structures (especially the `wiki/` directory).

## 2. Agentic Loop Architecture
The `agent.py` script will use a `while` loop constrained to a maximum of 10 iterations to prevent infinite looping.
1. **Initialize:** Start with a system prompt and the user's question.
2. **Call LLM:** Send the conversation history and available `tools` to the API.
3. **Handle Response:**
   * If `finish_reason` is `tool_calls` (or the message contains tool calls), parse the calls.
   * Execute the mapped Python functions (`read_file`, `list_files`).
   * Append the results as `role: tool` messages to the conversation history.
   * Loop back to step 2.
   * If the LLM returns a standard text message without tool calls, break the loop.
4. **Final Output:** Format the final text answer, extract the `source`, compile the history of `tool_calls`, and print to `stdout` as JSON.

## 3. Security Measures
To prevent directory traversal attacks (e.g., `../../../etc/passwd`):
* We will establish the project root directory using `os.path.abspath(os.getcwd())`.
* For any incoming `path` argument, we will resolve it to an absolute path.
* We will strictly verify that the resolved path `.startswith()` the project root directory. If it escapes the boundary, the tool will return an explicit error string to the LLM.
