#!/usr/bin/env bash
# Convert the merged fine-tune to a Q4_K_M GGUF, the format Vox loads.
# Usage: export.sh MODEL_DIR OUT.gguf   (run from the repository root)
set -euo pipefail

readonly model_dir="$1"
readonly output="$2"
readonly local_dir="$(pwd)/.local"
readonly llama_src="${local_dir}/src/llama.cpp-b11912"
readonly python="${local_dir}/finetune/venv/bin/python"
readonly f16="${output%.gguf}-f16.gguf"
mkdir -p "$(dirname "$output")"

PYTHONPATH="${llama_src}/gguf-py" "$python" "${llama_src}/convert_hf_to_gguf.py" \
  "$model_dir" --outtype f16 --outfile "$f16"
"${local_dir}/runtime/llama.cpp-b11912-cuda/bin/llama-quantize" "$f16" "$output" Q4_K_M
rm "$f16"
printf 'Fine-tuned S1-mini by Superwhisper: %s\n' "$output"
