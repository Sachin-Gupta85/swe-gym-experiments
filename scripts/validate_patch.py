"""Validate a model-generated patch for one SWE-Gym instance.

Steps:
  1. reset the checkout to the instance base_commit
  2. apply the model patch (fails fast if it does not apply)
  3. apply the hidden test_patch
  4. run FAIL_TO_PASS and PASS_TO_PASS tests one by one

Usage:
    python scripts/validate_patch.py --task data/tasks.jsonl --instance <id> \
        --repo-dir /path/to/checkout --patch patches/<id>.patch
"""
import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path


def git(repo: Path, *args, check=True):
    return subprocess.run(["git", "-C", str(repo), *args], check=check,
                          text=True, capture_output=True)


def find_instance(task_file: Path, instance_id: str) -> dict:
    with task_file.open() as f:
        for line in f:
            row = json.loads(line)
            if row["instance_id"] == instance_id:
                return row
    sys.exit(f"instance {instance_id} not found in {task_file}")


def apply_patch(repo: Path, patch_text: str, label: str) -> bool:
    with tempfile.NamedTemporaryFile("w", suffix=".patch", delete=False) as tmp:
        tmp.write(patch_text)
    if git(repo, "apply", "--check", tmp.name, check=False).returncode != 0:
        print(f"[{label}] patch does not apply")
        return False
    git(repo, "apply", tmp.name)
    return True


def run_test(repo: Path, test_id: str, timeout: int) -> bool:
    try:
        r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-x", test_id],
                           cwd=repo, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return False
    return r.returncode == 0


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--task", type=Path, required=True)
    p.add_argument("--instance", required=True)
    p.add_argument("--repo-dir", type=Path, required=True)
    p.add_argument("--patch", type=Path, required=True)
    p.add_argument("--timeout", type=int, default=300)
    args = p.parse_args()

    row = find_instance(args.task, args.instance)
    repo = args.repo_dir

    git(repo, "reset", "--hard")
    git(repo, "clean", "-fdq")
    git(repo, "checkout", "-q", row["base_commit"])

    model_patch = args.patch.read_text()
    if not model_patch.strip():
        print(json.dumps({"instance_id": args.instance, "status": "empty_patch"}))
        return 1
    if not apply_patch(repo, model_patch, "model"):
        print(json.dumps({"instance_id": args.instance, "status": "patch_failed"}))
        return 1
    apply_patch(repo, row["test_patch"], "tests")

    f2p = {t: run_test(repo, t, args.timeout) for t in row["FAIL_TO_PASS"]}
    p2p = {t: run_test(repo, t, args.timeout) for t in row["PASS_TO_PASS"]}
    resolved = all(f2p.values()) and all(p2p.values())

    report = {
        "instance_id": args.instance,
        "status": "resolved" if resolved else "unresolved",
        "fail_to_pass": f"{sum(f2p.values())}/{len(f2p)}",
        "pass_to_pass": f"{sum(p2p.values())}/{len(p2p)}",
        "failing": [t for t, ok in {**f2p, **p2p}.items() if not ok],
    }
    print(json.dumps(report, indent=2))
    return 0 if resolved else 1


if __name__ == "__main__":
    sys.exit(main())
