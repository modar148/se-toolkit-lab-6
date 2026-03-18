#!/usr/bin/env python3
import sys
import json
import os
import urllib.request
import urllib.error
import re
from pathlib import Path

# --- SECURITY & PATH RESOLUTION ---
PROJECT_ROOT = Path.cwd().resolve()

def get_safe_path(rel_path):
    """Resolves a path and ensures it does not escape the project directory."""
    target = (PROJECT_ROOT / (rel_path or "")).resolve()
    # If the resolved target doesn't start with the root, it's a directory traversal attempt
    if not str(target).startswith(str(PROJECT_ROOT)):
        return None
    return target

# --- TOOLS ---
def list_files(rel_path):
    target = get_safe_path(rel_path)
    if not target: return "Error: Access denied. Path outside project."
    if not target.exists(): return "Error: Directory not found."
    if not target.is_dir(): return "Error: Path is a file, not a directory."
    try:
        entries = os.listdir(target)
        return "\n".join(entries) if entries else "Empty directory."
    except Exception as e:
        return f"Error reading directory: {e}"

def read_file(rel_path):
    target = get_safe_path(rel_path)
    if not target: return "Error: Access denied. Path outside project."
    if not target.exists(): return "Error: File not found."
    if not target.is_file(): return "Error: Path is a directory, not a file."
    try:
        with open(target, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {e}"

TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files and directories at a given path to explore the repository.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative directory path from project root (e.g., 'wiki')."}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a file to find answers.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative file path from project root (e.g., 'wiki/git-workflow.md')."}
                },
                "required": ["path"]
            }
        }
    }
]

# --- ENVIRONMENT & API ---
def load_env(filepath=".env.agent.secret"):
    path = Path(filepath)
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ[key.strip()] = value.strip().strip('"').strip("'")

def call_llm(messages, api_key, api_base, model):
    url = f"{api_base.rstrip('/')}/chat/completions"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
    payload = {"model": model, "messages": messages, "tools": TOOLS_SCHEMA}
    
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"HTTP Error {e.code}: {e.read().decode('utf-8')}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Request failed: {e}", file=sys.stderr)
        sys.exit(1)

# --- MAIN AGENTIC LOOP ---
def main():
    if len(sys.argv) < 2:
        print("Error: Provide a question.", file=sys.stderr)
        sys.exit(1)
        
    question = sys.argv[1]
    load_env()
    api_key = os.environ.get("LLM_API_KEY")
    api_base = os.environ.get("LLM_API_BASE")
    model = os.environ.get("LLM_MODEL", "qwen3-coder-plus")

    if not api_key or not api_base:
        print("Error: Missing LLM_API_KEY or LLM_API_BASE.", file=sys.stderr)
        sys.exit(1)

    system_prompt = (
        "You are a repository documentation agent. Answer questions by reading the project files.\n"
        "1. Use 'list_files' to discover files in the 'wiki' or other directories.\n"
        "2. Use 'read_file' to read specific files and find the answer.\n"
        "3. When you have the answer, provide a helpful text response.\n"
        "4. YOU MUST append the source reference at the very end of your final response exactly in this format: "
        "SOURCE: wiki/file-name.md#section-anchor"
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": question}
    ]

    tool_calls_history = []
    max_loops = 10
    final_text = ""

    print(f"[*] Starting agentic loop for question: '{question}'", file=sys.stderr)

    for loop_count in range(max_loops):
        print(f"[*] Loop {loop_count + 1} - Thinking...", file=sys.stderr)
        result = call_llm(messages, api_key, api_base, model)
        msg = result["choices"][0]["message"]
        
        # Append the assistant's message exactly as received
        asst_msg = {"role": "assistant"}
        if msg.get("content"): asst_msg["content"] = msg["content"]
        if msg.get("tool_calls"): asst_msg["tool_calls"] = msg["tool_calls"]
        messages.append(asst_msg)

        if not msg.get("tool_calls"):
            print("[*] Agent provided final text answer.", file=sys.stderr)
            final_text = msg.get("content", "")
            break

        for tc in msg["tool_calls"]:
            func_name = tc["function"]["name"]
            try:
                args = json.loads(tc["function"]["arguments"])
            except json.JSONDecodeError:
                args = {}

            print(f"  -> Calling tool: {func_name}({args})", file=sys.stderr)
            
            # Execute tool
            if func_name == "list_files":
                func_result = list_files(args.get("path", ""))
            elif func_name == "read_file":
                func_result = read_file(args.get("path", ""))
            else:
                func_result = f"Error: Unknown tool {func_name}"

            # Save to history for the final output
            tool_calls_history.append({
                "tool": func_name,
                "args": args,
                "result": func_result
            })

            # Append the result for the LLM to read on the next loop
            messages.append({
                "role": "tool",
                "name": func_name,
                "content": func_result,
                "tool_call_id": tc["id"]
            })
    else:
        print("[!] Max loop limit reached.", file=sys.stderr)
        final_text = msg.get("content", "Error: Max tool calls reached.")

    # --- EXTRACT OUTPUT ---
    source = ""
    answer = final_text

    # Extract the SOURCE tag requested in the system prompt
    match = re.search(r'SOURCE:\s*([^\n\r]+)', final_text)
    if match:
        source = match.group(1).strip().strip("`")
        answer = final_text[:match.start()].strip() # Remove the source line from the actual answer

    output = {
        "answer": answer,
        "source": source,
        "tool_calls": tool_calls_history
    }
    
    # This is the ONLY thing printed to stdout
    print(json.dumps(output))

if __name__ == "__main__":
    main()
