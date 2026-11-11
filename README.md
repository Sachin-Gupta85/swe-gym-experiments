# swe-gym-experiments

Experiments with coding agents on [SWE-Gym](https://huggingface.co/datasets/SWE-Gym/SWE-Gym) style tasks: real GitHub issues from Python repositories, where the agent must produce a patch that makes failing tests pass without breaking existing ones.

This repo holds the tooling around the agent: loading and filtering task instances, validating patches against the task's tests, and analysing agent trajectories.

## Pipeline

```
load_tasks.py  ->  agent rollout  ->  validate_patch.py  ->  trajectory_stats.py
 (filter by        (your agent,        (apply patch, run       (steps, tool usage,
  repo / size)      writes .patch)      FAIL_TO_PASS and        failure modes)
                                        PASS_TO_PASS tests)
```

## Repo layout

```
swe-gym-experiments/
├── configs/
│   └── experiment.yaml       # dataset split, repo filters, limits
├── scripts/
│   ├── load_tasks.py         # pull and filter instances into JSONL
│   ├── validate_patch.py     # apply a model patch and run the task tests
│   └── trajectory_stats.py   # summarise agent trajectories
├── requirements.txt
└── README.md
```

## Quick start

```bash
pip install -r requirements.txt

# 1. export a filtered task set
python scripts/load_tasks.py --config configs/experiment.yaml --out data/tasks.jsonl

# 2. run your agent on each instance, saving one .patch per instance_id

# 3. validate a patch inside a checkout of the task repo
python scripts/validate_patch.py --task data/tasks.jsonl --instance <instance_id> \
    --repo-dir /path/to/checkout --patch patches/<instance_id>.patch

# 4. summarise trajectories
python scripts/trajectory_stats.py --traj-dir trajectories/
```

## How a patch is judged

An instance is **resolved** only if both hold after applying the model patch and the hidden test patch:

- every test in `FAIL_TO_PASS` now passes
- every test in `PASS_TO_PASS` still passes

## Trajectory analysis

`trajectory_stats.py` reads JSONL trajectories (one step per line: `action`, `tool`, `observation`) and reports:

- steps per instance and tool usage mix
- how often the agent ran tests before submitting
- common failure modes: empty patch, patch does not apply, regression in PASS_TO_PASS

## Stack

Python, Hugging Face Datasets, pytest, git

## Roadmap

- [ ] Docker image per repo/version for isolated validation
- [ ] Batch validation with a results table
- [ ] Compare agents side by side on the same instance set

## Author

Sachin Gupta · [LinkedIn](https://www.linkedin.com/in/saching85/)
