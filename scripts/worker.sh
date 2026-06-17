#!/bin/bash
model=$1; cond=$2; i=$3
p="/tmp/sweep/prompts/$cond.txt"; out="/tmp/sweep/out/$model/${cond}_${i}.txt"
if [ "$model" = "gpt" ]; then
  codex exec --skip-git-repo-check -C /tmp/sweep/wd "$(cat "$p")" </dev/null >"$out" 2>/dev/null
else
  claude -p --model claude-sonnet-4-6 "$(cat "$p")" </dev/null >"$out" 2>/dev/null
fi
echo "done $model $cond $i"
