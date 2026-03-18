import json
import subprocess
import sys

def run_agent(question):
    result = subprocess.run(
        [sys.executable, "agent.py", question],
        capture_output=True,
        text=True,
        timeout=60
    )
    assert result.returncode == 0, f"Agent failed with stderr: {result.stderr}"
    try:
        return json.loads(result.stdout.strip())
    except json.JSONDecodeError:
        assert False, f"Output is not valid JSON. stdout was: {result.stdout}"

# Task 1 Test
def test_agent_basic_output():
    output = run_agent("What does HTML stand for?")
    assert "answer" in output, "Missing 'answer' key"
    assert "tool_calls" in output, "Missing 'tool_calls' key"

# Task 2 Test: Read File Logic
def test_agent_merge_conflict():
    output = run_agent("How do you resolve a merge conflict?")
    
    # Check that tool calls were made
    assert len(output.get("tool_calls", [])) > 0, "No tool calls were made"
    
    # Check if read_file was used
    tools_used = [tc["tool"] for tc in output["tool_calls"]]
    assert "read_file" in tools_used, "Agent did not use read_file tool"
    
    # Check if the source is correct
    source = output.get("source", "")
    assert "wiki/git" in source, f"Incorrect source found: {source}"

# Task 2 Test: List Files Logic
def test_agent_list_wiki():
    output = run_agent("What files are in the wiki?")
    
    assert len(output.get("tool_calls", [])) > 0, "No tool calls were made"
    
    tools_used = [tc["tool"] for tc in output["tool_calls"]]
    assert "list_files" in tools_used, "Agent did not use list_files tool"

# Task 3 Test: Source Code Read Logic
def test_agent_system_framework():
    output = run_agent("What framework does the backend use?")
    assert len(output.get("tool_calls", [])) > 0, "No tool calls were made"
    
    tools_used = [tc["tool"] for tc in output["tool_calls"]]
    assert "read_file" in tools_used, "Agent did not use read_file tool"

# Task 3 Test: Query API Logic
def test_agent_system_db_count():
    output = run_agent("How many items are in the database?")
    assert len(output.get("tool_calls", [])) > 0, "No tool calls were made"
    
    tools_used = [tc["tool"] for tc in output["tool_calls"]]
    assert "query_api" in tools_used, "Agent did not use query_api tool"
