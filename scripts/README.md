# Sweep reproduction

Reproduces the powered sweep in [`../experiments/sweep-results.md`](../experiments/sweep-results.md).
Requires the Codex CLI (`codex`, default model `gpt-5.5`) and the Claude CLI
(`claude -p`, `--model claude-sonnet-4-6`).

```bash
# 1. generate the four condition prompts
python scripts/gen_prompts.py

# 2. run N=10 per condition per model (xargs parallelism)
mkdir -p /tmp/sweep/wd /tmp/sweep/out/gpt /tmp/sweep/out/sonnet
for m in gpt sonnet; do for c in C1 C3 C3verify E3; do for i in $(seq 1 10); do
  echo "$m $c $i"; done; done; done | xargs -P 6 -n3 scripts/worker.sh

# 3. label every output with an independent judge
mkdir -p /tmp/sweep/judge/gpt /tmp/sweep/judge/sonnet
for m in gpt sonnet; do for c in C1 C3 C3verify E3; do for i in $(seq 1 10); do
  echo "$m $c $i"; done; done; done | xargs -P 6 -n3 scripts/judge_worker.sh
```

- `worker.sh <model> <cond> <i>` — runs one condition once on `gpt` (Codex) or
  `sonnet` (`claude -p`), writing the raw answer to `/tmp/sweep/out/<model>/<cond>_<i>.txt`.
- `judge_worker.sh <model> <cond> <i>` — labels one output (BREACH / COMPLIANT_PLAIN /
  COMPLIANT_WARNED for covenant; RECORDED / FLAGGED for E3).

Raw outputs and judge labels from the run reported in the paper are checked in under
[`../experiments/sweep-raw/`](../experiments/sweep-raw/).
