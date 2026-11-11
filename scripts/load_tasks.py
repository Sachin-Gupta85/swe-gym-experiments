"""Load SWE-Gym instances, filter them by config, and export JSONL.

Usage:
    python scripts/load_tasks.py --config configs/experiment.yaml --out data/tasks.jsonl
"""
import argparse
import json
import random
from pathlib import Path

import yaml
from datasets import load_dataset

KEEP_FIELDS = [
    "instance_id", "repo", "base_commit", "problem_statement",
    "patch", "test_patch", "FAIL_TO_PASS", "PASS_TO_PASS",
]


def as_list(value):
    """Test lists are stored as JSON strings in the dataset."""
    if isinstance(value, str):
        return json.loads(value) if value else []
    return list(value or [])


def patch_size(patch: str) -> int:
    return sum(
        1 for line in patch.splitlines()
        if line[:1] in "+-" and not line.startswith(("+++", "---"))
    )


def keep(row, cfg) -> bool:
    if cfg.get("repos") and row["repo"] not in cfg["repos"]:
        return False
    if row["repo"] in cfg.get("exclude_repos", []):
        return False
    if patch_size(row["patch"]) > cfg.get("max_patch_lines", 10**9):
        return False
    if len(as_list(row["FAIL_TO_PASS"])) > cfg.get("max_fail_to_pass", 10**9):
        return False
    return True


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--config", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()

    cfg = yaml.safe_load(args.config.read_text())
    ds = load_dataset(cfg["dataset"], split=cfg["split"])

    rows = [r for r in ds if keep(r, cfg)]
    random.Random(cfg.get("seed", 0)).shuffle(rows)
    rows = rows[: cfg.get("limit", len(rows))]

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w") as f:
        for r in rows:
            item = {k: r[k] for k in KEEP_FIELDS}
            item["FAIL_TO_PASS"] = as_list(item["FAIL_TO_PASS"])
            item["PASS_TO_PASS"] = as_list(item["PASS_TO_PASS"])
            f.write(json.dumps(item) + "\n")

    repos = sorted({r["repo"] for r in rows})
    print(f"kept {len(rows)} of {len(ds)} instances across {len(repos)} repos -> {args.out}")


if __name__ == "__main__":
    main()
