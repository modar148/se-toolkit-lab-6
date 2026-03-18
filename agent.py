#!/usr/bin/env python3
import sys
import json
import os
import urllib.request
import urllib.error
from pathlib import Path

def load_env(filepath=".env.agent.secret"):
    """Manually load environment variables to avoid requiring python-dotenv."""
    path = Path(filepath)
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, _, value = line.partition("=")
            # Remove potential quotes around the value
            os.environ[key.strip()] = value.strip().strip('"').strip("'")

def main():
    # 1. Parse command-line argument
    if len(sys.argv) < 2:
        print("Error: Please provide a question as the first argument.", file=sys.stderr)
        sys.exit(1)
    
    question = sys.argv[1]

    # 2. Load configuration
    load_env()
    api_key = os.environ.get("LLM_API_KEY")
    api_base = os.environ.get("LLM_API_BASE")
    model = os.environ.get("LLM_MODEL", "qwen3-coder-plus")

    if not api_key or not api_base:
        print("Error: LLM_API_KEY and LLM_API_BASE must be set in .env.agent.secret", file=sys.stderr)
        sys.exit(1)

    # 3. Prepare the API request (OpenAI-compatible format)
    url = f"{api_base.rstrip('/')}/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": question}]
    }
    
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")

    # 4. Make the call with a 60-second timeout as required by the spec
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        print(f"HTTP Error {e.code}: {error_body}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Request failed: {e}", file=sys.stderr)
        sys.exit(1)

    # 5. Extract answer and format exact JSON output
    try:
        answer_content = result["choices"][0]["message"]["content"]
        
        output = {
            "answer": answer_content,
            "tool_calls": []
        }
        
        # Print ONLY the valid JSON to stdout
        print(json.dumps(output))
        sys.exit(0)
    except (KeyError, IndexError) as e:
        print(f"Failed to parse LLM response structure: {result}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
