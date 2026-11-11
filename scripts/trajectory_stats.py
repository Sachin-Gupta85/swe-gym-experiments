"""Summarise agent trajectories.

Expects one JSONL file per instance in --traj-dir. Each line is a step:
    {"tool": "bash", "action": "pytest tests/test_x.py", "observation": "..."}
An optional final line records the outcome:
    {"result": "resolved" | "unresolved" | "empty_patch" | "patch_failed"}

Usage:
    python scripts/trajectory_stats.py --traj-dir trajectories/
"""
import argparse
import json
import statistics
from collections import Counter
from pathlib import Path

TEST_HINTS = ("pytest", "python -m unittest", "tox", "make test")


def load(path: Path):
    steps, result = [], "unknown"
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        if "result" in rec:
            result = rec["result"]
        else:
            steps.append(rec)
    return steps, result


def ran_tests(steps) -> bool:
    return any(any(h in str(s.get("action", "")) for h in TEST_HINTS) for s in steps)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--traj-dir", type=Path, required=True)
    args = p.parse_args()

    files = sorted(args.traj_dir.glob("*.jsonl"))
    if not files:
        raise SystemExit(f"no .jsonl trajectories in {args.traj_dir}")

    lengths, tools, outcomes = [], Counter(), Counter()
    tested = 0
    for f in files:
        steps, result = load(f)
        lengths.append(len(steps))
        tools.update(s.get("tool", "unknown") for s in steps)
        outcomes[result] += 1
        tested += ran_tests(steps)

    n = len(files)
    print(f"instances:            {n}")
    print(f"resolved:             {outcomes['resolved']} ({outcomes['resolved'] / n:.0%})")
    print(f"steps (median / max): {statistics.median(lengths)} / {max(lengths)}")
    print(f"ran tests before end: {tested} ({tested / n:.0%})")
    print("\noutcomes:")
    for k, v in outcomes.most_common():
        print(f"  {k:<14} {v}")
    print("\ntool usage:")
    total = sum(tools.values()) or 1
    for k, v in tools.most_common():
        print(f"  {k:<14} {v:>5}  {v / total:.0%}")


if __name__ == "__main__":
    main()
