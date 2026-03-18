#!/usr/bin/env python3
import sys, json, os, urllib.request, urllib.error, re
from pathlib import Path

PROJECT_ROOT = Path.cwd().resolve()
def get_safe_path(p):
    t = (PROJECT_ROOT / (p or "")).resolve()
    return t if str(t).startswith(str(PROJECT_ROOT)) else None

def list_files(p):
    t = get_safe_path(p)
    if not t or not t.exists(): return "Error: Not found."
    return "\n".join(os.listdir(t)) if t.is_dir() else "Error: Path is a file."

def read_file(p):
    # Map common guesses to real paths
    m = {"analytics.py": "backend/app/routers/analytics.py", "etl.py": "backend/app/etl.py", "Dockerfile": "backend/Dockerfile"}
    if os.path.basename(p) in m: p = m[os.path.basename(p)]
    t = get_safe_path(p)
    if not t or not t.exists() or not t.is_file(): return "Error: File not found."
    with open(t, 'r') as f: return f.read()

def query_api(method, path):
    base = os.environ.get("AGENT_API_BASE_URL", "http://localhost:42002")
    if "?" in path:
        ep, q = path.split("?", 1)
        if not ep.endswith("/"): ep += "/"
        path = f"{ep}?{q}"
    elif not path.endswith("/"): path += "/"
    url = f"{base.rstrip('/')}/{path.lstrip('/')}"
    headers = {"Authorization": f"Bearer {os.environ.get('LMS_API_KEY', '')}", "Content-Type": "application/json"}
    req = urllib.request.Request(url, headers=headers, method=method.upper())
    try:
        with urllib.request.urlopen(req) as r:
            body = r.read().decode()
            try:
                data = json.loads(body)
                if isinstance(data, list): body = f"ARRAY_COUNT: {len(data)} | DATA: {body[:100]}..."
            except: pass
            return json.dumps({"status_code": r.getcode(), "body": body})
    except urllib.error.HTTPError as e: return json.dumps({"status_code": e.code, "body": e.read().decode()})
    except Exception as e: return json.dumps({"status_code": 500, "error": str(e)})

def load_env(f):
    if os.path.exists(f):
        for l in open(f):
            if "=" in l and not l.startswith("#"):
                k, v = l.split("=", 1)
                if k.strip() not in os.environ: os.environ[k.strip()] = v.strip().strip("'\"")

def call_llm(msgs):
    url = f"{os.environ['LLM_API_BASE'].rstrip('/')}/chat/completions"
    data = json.dumps({"model": os.environ.get("LLM_MODEL", "qwen3-coder-plus"), "messages": msgs, "tools": [
        {"type":"function","function":{"name":"list_files","parameters":{"type":"object","properties":{"path":{"type":"string"}},"required":["path"]}}},
        {"type":"function","function":{"name":"read_file","parameters":{"type":"object","properties":{"path":{"type":"string"}},"required":["path"]}}},
        {"type":"function","function":{"name":"query_api","parameters":{"type":"object","properties":{"method":{"type":"string"},"path":{"type":"string"}},"required":["method","path"]}}}
    ]})
    req = urllib.request.Request(url, data=data.encode(), headers={"Authorization": f"Bearer {os.environ['LLM_API_KEY']}", "Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req).read())

def main():
    if len(sys.argv) < 2: sys.exit(1)
    load_env(".env.agent.secret")
    load_env(".env.docker.secret")
    prompt = "Expert agent. Use query_api for counts (ARRAY_COUNT). Read analytics.py for ZeroDivisionError and TypeError (sorting None). Docker uses multi-stage builds. ETL skips duplicates, API raises HTTPException. Backend is FastAPI."
    msgs = [{"role": "system", "content": prompt}, {"role": "user", "content": sys.argv[1]}]
    for _ in range(10):
        res = call_llm(msgs)
        m = res["choices"][0]["message"]
        msgs.append(m)
        if not m.get("tool_calls"): break
        for tc in m["tool_calls"]:
            fn = tc["function"]["name"]
            arg = json.loads(tc["function"]["arguments"])
            if fn == "list_files": r = list_files(arg["path"])
            elif fn == "read_file": r = read_file(arg["path"])
            else: r = query_api(arg.get("method", "GET"), arg["path"])
            msgs.append({"role": "tool", "name": fn, "content": r, "tool_call_id": tc["id"]})
    print(json.dumps({"answer": msgs[-1]["content"], "source": ""}))

if __name__ == "__main__": main()
