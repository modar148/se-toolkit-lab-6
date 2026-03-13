#!/usr/bin/env python3
"""
Agent CLI — Call an LLM and return a structured JSON answer.

Usage:
    uv run agent.py "Your question here"

Output:
    JSON to stdout: {"answer": "...", "tool_calls": []}
"""

import argparse
import json
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv


def print_debug(message: str) -> None:
    """Print debug message to stderr."""
    print(message, file=sys.stderr)


def load_settings() -> dict:
    """Load LLM configuration from .env.agent.secret."""
    env_file = Path(__file__).parent / ".env.agent.secret"

    if not env_file.exists():
        raise FileNotFoundError(f"Environment file not found: {env_file}")

    load_dotenv(env_file)

    api_key = os.getenv("LLM_API_KEY")
    api_base = os.getenv("LLM_API_BASE")
    model = os.getenv("LLM_MODEL", "qwen3-coder-plus")

    if not api_key:
        raise ValueError("LLM_API_KEY not found in .env.agent.secret")
    if not api_base:
        raise ValueError("LLM_API_BASE not found in .env.agent.secret")

    return {
        "api_key": api_key,
        "api_base": api_base,
        "model": model,
    }


def call_llm(question: str, settings: dict) -> str:
    """Call the LLM API and return the answer."""
    url = f"{settings['api_base']}/chat/completions"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings['api_key']}",
    }

    payload = {
        "model": settings["model"],
        "messages": [
            {
                "role": "system",
                "content": "You are a helpful assistant. Answer questions concisely and accurately.",
            },
            {"role": "user", "content": question},
        ],
    }

    print_debug(f"Calling LLM at {url}...")

    with httpx.Client(timeout=60.0) as client:
        response = client.post(url, headers=headers, json=payload)
        response.raise_for_status()

    data = response.json()
    answer = data["choices"][0]["message"]["content"]

    print_debug(f"LLM response received.")

    return answer


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Ask a question and get an answer from an LLM."
    )
    parser.add_argument(
        "question",
        type=str,
        help="The question to ask the LLM",
    )

    args = parser.parse_args()

    if not args.question.strip():
        print_debug("Error: Question cannot be empty.")
        return 1

    try:
        settings = load_settings()
    except Exception as e:
        print_debug(f"Error loading settings: {e}")
        return 1

    try:
        answer = call_llm(args.question, settings)
    except Exception as e:
        print_debug(f"Error calling LLM: {e}")
        return 1

    # Output structured JSON to stdout
    result = {
        "answer": answer,
        "tool_calls": [],
    }

    print(json.dumps(result))

    return 0


if __name__ == "__main__":
    sys.exit(main())
