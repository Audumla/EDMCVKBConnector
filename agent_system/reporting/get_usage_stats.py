"""
get_usage_stats.py - Fetches detailed usage stats for a specific provider.
"""
import sys
import subprocess
import shutil

def get_binary_path(name: str) -> str | None:
    """Find the absolute path for a binary."""
    return shutil.which(name)

def get_gemini_stats() -> str:
    gemini_bin = get_binary_path("gemini")
    if not gemini_bin:
        return "ERROR: 'gemini' command not found in PATH."
    # Use JSON output to get the stats field directly.
    # This avoids the conversational response and provides raw data.
    cmd = [gemini_bin, "-p", "/stats", "--output-format", "json"]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=45, encoding="utf-8", errors="replace")
        if res.returncode != 0:
            return res.stderr
        
        import json
        try:
            # Find the first '{' to skip any warnings/logs before the JSON object
            start_idx = res.stdout.find('{')
            if start_idx == -1:
                return f"ERROR: No JSON object found in output: {res.stdout}"
            
            data = json.loads(res.stdout[start_idx:])
            if "stats" in data:
                return json.dumps(data["stats"], indent=2)
            return "ERROR: 'stats' field missing from JSON output."
        except json.JSONDecodeError as e:
            return f"ERROR: Failed to parse JSON: {e}\nOutput: {res.stdout}"
            
    except Exception as e:
        return f"ERROR: Failed to run Gemini: {e}"

def get_opencode_stats() -> str:
    opencode_bin = get_binary_path("opencode")
    if not opencode_bin:
        return "ERROR: 'opencode' command not found in PATH."
    cmd = [opencode_bin, "stats", "--models"]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=30, encoding="utf-8", errors="replace")
        return res.stdout if res.returncode == 0 else res.stderr
    except Exception as e:
        return f"ERROR: Failed to run OpenCode: {e}"

def get_claude_stats() -> str:
    claude_bin = get_binary_path("claude")
    if not claude_bin:
        return "ERROR: 'claude' command not found in PATH."
    cmd = [claude_bin, "-p", "What is my current account usage?"]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=30, encoding="utf-8", errors="replace")
        return res.stdout if res.returncode == 0 else res.stderr
    except Exception as e:
        return f"ERROR: Failed to run Claude: {e}"

def get_local_llm_stats() -> str:
    ollama_bin = get_binary_path("ollama")
    if not ollama_bin:
        return "INFO: 'ollama' command not found. Cannot retrieve local model stats."
    cmd = [ollama_bin, "ps"]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=10, encoding="utf-8", errors="replace")
        return res.stdout if res.returncode == 0 else res.stderr
    except Exception as e:
        return f"ERROR: Failed to run Ollama: {e}"

def main():
    if len(sys.argv) != 2:
        print("Usage: python get_usage_stats.py <provider_name>")
        sys.exit(1)
        
    provider = sys.argv[1].lower()
    
    if provider == "gemini":
        print(get_gemini_stats())
    elif provider == "opencode":
        print(get_opencode_stats())
    elif provider == "claude":
        print(get_claude_stats())
    elif provider == "local-llm":
        print(get_local_llm_stats())
    else:
        print(f"Stats command not implemented for '{provider}'.")

if __name__ == "__main__":
    main()
