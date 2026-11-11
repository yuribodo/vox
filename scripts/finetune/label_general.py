#!/usr/bin/env python3
"""Label general.txt with the base S1-mini so fine-tuning keeps its behaviour.

Usage: label_general.py LLAMA_COMPLETION BASE_GGUF DATA_DIR
"""

import json
import subprocess
import sys
from pathlib import Path

from train import prompt

binary, model, data = sys.argv[1], sys.argv[2], Path(sys.argv[3])
with open(data / "general.jsonl", "w") as out:
    for line in (data / "general.txt").read_text().splitlines():
        result = subprocess.run(
            [binary, "-m", model, "-no-cnv", "--no-display-prompt", "--simple-io", "--no-warmup",
             "-fitt", "256", "-c", "2048", "-b", "512", "-ub", "256", "--temp", "0", "-n", "256",
             "-p", prompt(line)],
            capture_output=True, text=True, check=True)
        target = result.stdout.strip().removesuffix("[end of text]").strip()
        out.write(json.dumps({"input": line, "target": target}) + "\n")
        print(target, flush=True)
