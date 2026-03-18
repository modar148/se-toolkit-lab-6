import json
import subprocess
import sys

def test_agent_basic_output():
    """
    Test that agent.py returns valid JSON with 'answer' and 'tool_calls'
    when given a basic question.
    """
    question = "What does HTML stand for?"
    
    # Run the agent as a subprocess
    result = subprocess.run(
        [sys.executable, "agent.py", question],
        capture_output=True,
        text=True,
        timeout=30
    )
    
    # Ensure the script exited successfully
    assert result.returncode == 0, f"Agent failed with stderr: {result.stderr}"
    
    # Parse the stdout as JSON
    try:
        output_data = json.loads(result.stdout.strip())
    except json.JSONDecodeError:
        assert False, f"Output is not valid JSON. stdout was: {result.stdout}"
        
    # Check for the required keys
    assert "answer" in output_data, "Missing 'answer' key in JSON output"
    assert "tool_calls" in output_data, "Missing 'tool_calls' key in JSON output"
    
    # Check that tool_calls is a list
    assert isinstance(output_data["tool_calls"], list), "'tool_calls' should be a list"
