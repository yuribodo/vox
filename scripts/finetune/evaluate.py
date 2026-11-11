#!/usr/bin/env python3
"""Score a GGUF model on the held-out synthetic pairs.

Usage: evaluate.py LLAMA_COMPLETION MODEL.gguf eval.jsonl
Prints exact-match rate and word error rate (case-sensitive, so casing of
identifiers counts).
"""

import json
import subprocess
import sys

from train import prompt


def word_errors(expected, actual):
    a, b = expected.split(), actual.split()
    row = list(range(len(b) + 1))
    for i, x in enumerate(a):
        diagonal, row[0] = row[0], i + 1
        for j, y in enumerate(b):
            diagonal, row[j + 1] = row[j + 1], min(row[j + 1] + 1, row[j] + 1, diagonal + (x != y))
    return row[-1], len(a)


binary, model, path = sys.argv[1:4]
exact = edits = words = 0
rows = [json.loads(line) for line in open(path)]
for row in rows:
    output = subprocess.run(
        [binary, "-m", model, "-no-cnv", "--no-display-prompt", "--simple-io", "--no-warmup",
         "-fitt", "256", "-c", "2048", "-b", "512", "-ub", "256", "--temp", "0", "-n", "256",
         "-p", prompt(row["input"])],
        capture_output=True, text=True, check=True).stdout.strip().removesuffix("[end of text]").strip()
    exact += output == row["target"]
    e, n = word_errors(row["target"], output)
    edits, words = edits + e, words + n
print(f"exact match {exact}/{len(rows)} ({100 * exact / len(rows):.1f}%), WER {100 * edits / words:.1f}%")
