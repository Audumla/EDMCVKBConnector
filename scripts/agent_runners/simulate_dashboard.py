
import json
import os
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

def create_mock_run(agent, run_id, summary, state="succeeded", model="test-model", cost=0.0, tokens=1000):
    run_dir = PROJECT_ROOT / "agent_artifacts" / agent / "reports" / "plan_runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    
    status = {
        "state": state,
        "pid": 9999,
        "heartbeat_at": "2026-02-24T17:30:00Z",
        "cost_estimate": {"model": model, "total_usd": cost},
        "token_usage": {"output_tokens": tokens}
    }
    (run_dir / "status.json").write_text(json.dumps(status, indent=2), encoding="utf-8-sig")
    
    meta = {
        "task_summary": summary,
        "isolation": {"branch_name": f"agent/dummy-{run_id}"}
    }
    (run_dir / "metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8-sig")
    
    logs = [
        f"LOG: Initializing {model}...",
        f"LOG: Processed {tokens} tokens.",
        f"LOG: Final state: {state}",
        "LOG: Testing very long line to check if it breaks the right panel border or wraps into the next row unexpectedly."
    ]
    (run_dir / "stdout.log").write_text("
".join(logs), encoding="utf-8-sig")

def main():
    for agent in ["gemini", "opencode", "claude"]:
        path = PROJECT_ROOT / "agent_artifacts" / agent / "reports" / "plan_runs"
        if path.exists(): shutil.rmtree(path)
            
    create_mock_run("gemini", "RUN_001", "Add retry logic to downloader", "succeeded", "gemini-2.0-pro", 0.0012, 1500)
    create_mock_run("claude", "RUN_002", "Refactor VKB message formatting", "running", "claude-3-5-sonnet", 0.0045, 3200)
    create_mock_run("opencode", "RUN_003", "Update docs/DEVELOPMENT.md", "succeeded", "opencode-latest", 0.0000, 2100)
    create_mock_run("gemini", "RUN_004", "Very long summary that needs to be truncated safely without moving the bars on the side", "succeeded", "gemini-2.0-pro", 0.0005, 400)

    print("✅ Simulation data restored.")

if __name__ == "__main__":
    main()
