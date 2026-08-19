"""Run one standalone retail experiment.

Prerequisite: python scripts/bootstrap_data.py
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from lab.observability import flush_traces, trace_experiment
from lab.user_sim import UserSimulator
from lab.v0 import V0Agent

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
RESULTS = ROOT / "results"


def load_task(task_id: str) -> dict:
    tasks = json.loads((DATA / "tasks.json").read_text(encoding="utf-8"))
    for task in tasks:
        if task["id"] == task_id:
            return task
    raise SystemExit(f"Task {task_id!r} not in the lab dataset")


def action_coverage(expected: list[dict], observed: list[dict]) -> tuple[int, int]:
    wanted = [
        {"name": action["name"], "arguments": action["arguments"]}
        for action in expected
    ]
    remaining = list(observed)
    matched = 0
    for action in wanted:
        if action in remaining:
            matched += 1
            remaining.remove(action)
    return matched, len(wanted)


@trace_experiment
def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", default="0")
    parser.add_argument("--agent-model", default="gpt-4.1-mini")
    parser.add_argument("--user-model", default="gpt-4.1-mini")
    parser.add_argument("--max-turns", type=int, default=20)
    args = parser.parse_args()

    for required in ("tasks.json", "db.json", "policy.md"):
        if not (DATA / required).exists():
            raise SystemExit("Missing data. Run: python scripts/bootstrap_data.py")

    task = load_task(args.task)
    agent = V0Agent(
        model=args.agent_model,
        policy_path=DATA / "policy.md",
        db_path=DATA / "db.json",
    )
    user = UserSimulator(model=args.user_model, task=task)

    user_text = user.next_message()
    transcript: list[dict[str, str]] = []

    for _ in range(args.max_turns):
        print(f"\nUSER: {user_text}")
        transcript.append({"role": "user", "content": user_text})
        if "###STOP###" in user_text:
            break

        assistant_text = agent.respond(user_text)
        print(f"\nASSISTANT: {assistant_text}")
        transcript.append({"role": "assistant", "content": assistant_text})
        user_text = user.next_message(assistant_text)
    else:
        print("\nReached max turns.")

    expected = task.get("evaluation_criteria", {}).get("actions", [])
    matched, total = action_coverage(expected, agent.actions)

    RESULTS.mkdir(exist_ok=True)
    result = {
        "task_id": task["id"],
        "agent_model": args.agent_model,
        "user_model": args.user_model,
        "expected_action_coverage": {"matched": matched, "total": total},
        "observed_actions": agent.actions,
        "expected_actions": expected,
        "token_metrics": agent.meter.summary(),
        "transcript": transcript,
    }
    out = RESULTS / f"task_{task['id']}_v0.json"
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    agent.world.save(RESULTS / f"task_{task['id']}_final_db.json")

    print(f"\nExpected action coverage: {matched}/{total}")
    print(
        "Agent API tokens: "
        f"input={result['token_metrics']['cumulative_input_tokens_api']} "
        f"output={result['token_metrics']['cumulative_output_tokens_api']}"
    )
    print(f"Result: {out}")


if __name__ == "__main__":
    try:
        main()
    finally:
        flush_traces()
