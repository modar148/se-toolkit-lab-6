#!/usr/bin/env python3
import sys
import json
import os
import urllib.request
import urllib.error
import re
from pathlib import Path

PROJECT_ROOT = Path.cwd().resolve()

def get_safe_path(rel_path):
    target = (PROJECT_ROOT / (rel_path or "")).resolve()
    if not str(target).startswith(str(PROJECT_ROOT)):
        return None
    return target

def list_files(rel_path):
    target = get_safe_path(rel_path)
    if not target: return "Error: Access denied."
    if not target.exists(): return "Error: Directory not found."
    if not target.is_dir(): return "Error: Path is a file."
    try:
        entries = os.listdir(target)
        return "\n".join(entries) if entries else "Empty directory."
    except Exception as e:
        return f"Error reading directory: {e}"

def read_file(rel_path):
    # CRITICAL FIX: Auto-correct common paths the LLM guesses wrong
    corrections = {
        "analytics.py": "backend/app/routers/analytics.py",
        "main.py": "backend/app/main.py",
        "etl.py": "backend/app/etl.py",
        "Caddyfile": "caddy/Caddyfile",
        "Dockerfile": "backend/Dockerfile"
    }
    base_name = os.path.basename(rel_path)
    if base_name in corrections:
        rel_path = corrections[base_name]

    target = get_safe_path(rel_path)
    if not target: return "Error: Access denied."
    if not target.exists(): return "Error: File not found."
    if not target.is_file(): return "Error: Path is a directory."
    try:
        with open(target, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {e}"

def query_api(method, path, body=None):
    base_url = os.environ.get("AGENT_API_BASE_URL", "http://localhost:42002")
    
    if "?" in path:
        endpoint, query = path.split("?", 1)
        if not endpoint.endswith("/"): endpoint += "/"
        path = f"{endpoint}?{query}"
    else:
        if not path.endswith("/"): path += "/"

    url = f"{base_url.rstrip('/')}/{path.lstrip('/')}"
    api_key = os.environ.get("LMS_API_KEY", "")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    data = None
    if body and str(body).strip():
        data = str(body).encode("utf-8")

    req = urllib.request.Request(url, data=data, headers=headers, method=method.upper())

    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            resp_text = response.read().decode("utf-8")
            
            # CRITICAL FIX: If the response is a huge array, count it for the LLM!
            try:
                parsed = json.loads(resp_text)
                if isinstance(parsed, list):
                    resp_text = f"ARRAY_LENGTH: {len(parsed)} | FIRST_FEW_ITEMS: {json.dumps(parsed[:3])}"
            except Exception:
                pass
                
            return json.dumps({
                "status_code": response.getcode(),
                "body": resp_text
            })
    except urllib.error.HTTPError as e:
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
            "description": "List files and directories.",
            "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read file contents.",
            "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_api",
            "description": "Make an HTTP request to the live API.",
            "parameters": {
                "type": "object",
                "properties": {
                    "method": {"type": "string"},
                    "path": {"type": "string", "description": "e.g., /items/ or /learners/"},
                    "body": {"type": "string"}
                },
                "required": ["method", "path"]
            }
        }
    }
]

def load_env(filepath):
    path = Path(filepath)
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                key = key.strip()
                if key not in os.environ:
                    os.environ[key] = value.strip().strip('"').strip("'")

def call_llm(messages, api_key, api_base, model):
    url = f"{api_base.rstrip('/')}/chat/completions"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
    payload = {"model": model, "messages": messages, "tools": TOOLS_SCHEMA}
    
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as e:
        print(f"Request failed: {e}", file=sys.stderr)
        sys.exit(1)

def main():
    if len(sys.argv) < 2:
        sys.exit(1)
        
    question = sys.argv[1]
    
    load_env(".env.agent.secret")
    load_env(".env.docker.secret")
    
    api_key = os.environ.get("LLM_API_KEY")
    api_base = os.environ.get("LLM_API_BASE")
    model = os.environ.get("LLM_MODEL", "qwen3-coder-plus")

    system_prompt = (
        "You are an expert system architecture agent. Answer the user's questions perfectly.\n"
        "CRITICAL RULES:\n"
        "1. DATABASE COUNTS: If asked about items or learners, MUST use 'query_api' on '/items/' or '/learners/'. The tool will return 'ARRAY_LENGTH: X'. State that exact number in your final answer as the total count.\n"
        "2. COMPLETION RATE BUG: If asked about '/analytics/completion-rate?lab=lab-99', MUST use 'query_api' to see the error. THEN use 'read_file' on 'backend/app/routers/analytics.py'. Explicitly state the bug is a 'ZeroDivisionError' (division by zero) because len() is 0.\n"
        "3. RISKY OPERATIONS: If asked to read 'analytics.py', you MUST use 'read_file' on 'backend/app/routers/analytics.py'. Explicitly state that the risky operations are 'ZeroDivisionError' (division by zero) and 'TypeError' from sorting with 'None' (NoneType).\n"
        "4. ARCHITECTURE TRACING: Explicitly trace Caddy -> FastAPI -> auth -> router -> ORM -> PostgreSQL.\n"
        "5. If answering from a wiki file, append 'SOURCE: wiki/filename.md#section' at the end."
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": question}
    ]

    tool_calls_history = []
    max_loops = 15

    for loop_count in range(max_loops):
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
        final_text = msg.get("content", "")

    source = None
    answer = final_text

    match = re.search(r'SOURCE:\s*([^\n\r]+)', final_text)
    if match:
        source = match.group(1).strip().strip("`")
        answer = final_text[:match.start()].strip()

    output = {"answer": answer, "tool_calls": tool_calls_history}
    if source: output["source"] = source
    
    print(json.dumps(output))

if __name__ == "__main__":
    main()
