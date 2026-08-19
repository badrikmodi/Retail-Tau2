"""Download a small, reproducible retail lab dataset from public tau2-bench.

We intentionally keep the full retail DB and policy, but only five diverse tasks.
The DB stays outside model context unless a tool reads from it.
"""

from __future__ import annotations

import json
from pathlib import Path

import requests

UPSTREAM_COMMIT = "a2c024725189473d2d7cea3a5cfdbcc67478e41f"
BASE = f"https://raw.githubusercontent.com/sierra-research/tau2-bench/{UPSTREAM_COMMIT}/data/tau2/domains/retail"
TASK_IDS = {"0", "2", "38", "59", "113"}
DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def download(name: str) -> bytes:
    response = requests.get(f"{BASE}/{name}", timeout=60)
    response.raise_for_status()
    return response.content


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    all_tasks = json.loads(download("tasks.json"))
    tasks = [task for task in all_tasks if task["id"] in TASK_IDS]
    missing = TASK_IDS - {task["id"] for task in tasks}
    if missing:
        raise RuntimeError(f"Missing upstream tasks: {sorted(missing)}")

    (DATA_DIR / "tasks.json").write_text(
        json.dumps(tasks, indent=2), encoding="utf-8"
    )
    (DATA_DIR / "db.json").write_bytes(download("db.json"))
    (DATA_DIR / "policy.md").write_bytes(download("policy.md"))
    (DATA_DIR / "source.json").write_text(
        json.dumps(
            {
                "repository": "sierra-research/tau2-bench",
                "commit": UPSTREAM_COMMIT,
                "domain": "retail",
                "task_ids": sorted(TASK_IDS, key=int),
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"Wrote {len(tasks)} tasks, full retail DB, and full policy to {DATA_DIR}")


if __name__ == "__main__":
    main()
