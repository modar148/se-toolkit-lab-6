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
    target = (PROJECT_ROOT / (rel_path or "")).resolve()
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

def query_api(method, path, body=None):
    base_url = os.environ.get("AGENT_API_BASE_URL", "http://localhost:42002")
    url = f"{base_url.rstrip('/')}/{path.lstrip('/')}"
    api_key = os.environ.get("LMS_API_KEY", "")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    data = body.encode("utf-8") if body else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method.upper())

    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.dumps({
                "status_code": response.getcode(),
                "body": response.read().decode("utf-8")
            })
    except urllib.error.HTTPError as e:
        # LLM needs to read HTTP errors (like 401 or 500) to diagnose them
        return json.dumps({
            "status_code": e.code,
            "body": e.read().decode("utf-8")
        })
    except Exception as e:
        return json.dumps({"status_code": 500, "error": str(e)})

TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files and directories at a given path to explore the repository.",
            "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a file to find answers.",
            "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_api",
            "description": "Make an HTTP request to the live backend API to check dynamic data, test endpoints, or get status codes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "method": {"type": "string", "description": "HTTP method (e.g., GET, POST)"},
                    "path": {"type": "string", "description": "Endpoint path (e.g., /items/)"},
                    "body": {"type": "string", "description": "Optional JSON payload"}
                },
                "required": ["method", "path"]
            }
        }
    }
]

# --- ENVIRONMENT & API ---
def load_env(filepath):
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
    
    # Load both secret files
    load_env(".env.agent.secret")
    load_env(".env.docker.secret")
    
    api_key = os.environ.get("LLM_API_KEY")
    api_base = os.environ.get("LLM_API_BASE")
    model = os.environ.get("LLM_MODEL", "qwen3-coder-plus")

    if not api_key or not api_base:
        print("Error: Missing LLM credentials.", file=sys.stderr)
        sys.exit(1)

    system_prompt = (
        "You are a system architecture agent. Answer questions by using tools.\n"
        "1. For static documentation, use 'list_files' and 'read_file' in the 'wiki' folder.\n"
        "2. For source code questions (like frameworks), use 'read_file' on backend files.\n"
        "3. For live system data (database counts, live endpoints, status codes, diagnosing API bugs), use 'query_api'.\n"
        "4. If the question comes from a wiki file, append SOURCE: wiki/filename.md#section at the end."
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": question}
    ]

    tool_calls_history = []
    max_loops = 10
    final_text = ""

    for loop_count in range(max_loops):
        print(f"[*] Loop {loop_count + 1} - Thinking...", file=sys.stderr)
        result = call_llm(messages, api_key, api_base, model)
        msg = result["choices"][0]["message"]
        
        asst_msg = {"role": "assistant"}
        if msg.get("content"): asst_msg["content"] = msg["content"]
        if msg.get("tool_calls"): asst_msg["tool_calls"] = msg["tool_calls"]
        messages.append(asst_msg)

        if not msg.get("tool_calls"):
            final_text = msg.get("content", "")
            break

        for tc in msg["tool_calls"]:
            func_name = tc["function"]["name"]
            try:
                args = json.loads(tc["function"]["arguments"])
            except json.JSONDecodeError:
                args = {}

            print(f"  -> Calling tool: {func_name}({args})", file=sys.stderr)
            
            if func_name == "list_files":
                func_result = list_files(args.get("path", ""))
            elif func_name == "read_file":
                func_result = read_file(args.get("path", ""))
            elif func_name == "query_api":
                func_result = query_api(args.get("method", "GET"), args.get("path", ""), args.get("body"))
            else:
                func_result = f"Error: Unknown tool {func_name}"

            tool_calls_history.append({"tool": func_name, "args": args, "result": func_result})

            messages.append({"role": "tool", "name": func_name, "content": func_result, "tool_call_id": tc["id"]})
    else:
        final_text = msg.get("content", "Error: Max tool calls reached.")

    # --- EXTRACT OUTPUT ---
    source = None
    answer = final_text

    match = re.search(r'SOURCE:\s*([^\n\r]+)', final_text)
    if match:
        source = match.group(1).strip().strip("`")
        answer = final_text[:match.start()].strip()

    output = {"answer": answer, "tool_calls": tool_calls_history}
    if source: output["source"] = source # Source is now optional
    
    print(json.dumps(output))

if __name__ == "__main__":
    main()
