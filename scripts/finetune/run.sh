#!/usr/bin/env bash
# Fine-tune S1-mini by Superwhisper on developer dictation (LoRA, ~15 min on an
# RTX 3050) and install it where Vox prefers it over the base model.
# Run ./scripts/fetch-llm.sh first. Needs uv and about 6 GiB of downloads.
set -euo pipefail
umask 077

readonly base_revision="88f6b15896c73bbb13a3b596e0afe8ea0d5150b4"
readonly base_url="https://huggingface.co/superwhisper/s1-mini/resolve/${base_revision}"
readonly weights_sha256="69d2057077ab4dc738aaaab75d2a8ffa141e3a09fb9d956198cfce46f381131a"

readonly project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
readonly work="${project_root}/.local/finetune"
readonly scripts="${project_root}/scripts/finetune"
readonly runtime="${project_root}/.local/runtime/llama.cpp-b11912-cuda/bin"
readonly base_gguf="${project_root}/.local/models/s1-mini-q4_k_m/s1-mini-q4_k_m.gguf"
readonly output="${project_root}/.local/models/s1-mini-vox-q4_k_m/s1-mini-vox-q4_k_m.gguf"

[[ -f "$base_gguf" ]] || { printf 'run ./scripts/fetch-llm.sh first\n' >&2; exit 1; }
cd "$project_root"

if [[ ! -x "$work/venv/bin/python" ]]; then
  uv venv --python 3.12 "$work/venv"
  VIRTUAL_ENV="$work/venv" uv pip install torch transformers peft accelerate sentencepiece gguf
fi

fetch() {
  curl --fail --location --proto '=https' --tlsv1.2 --retry 10 --retry-all-errors \
    --continue-at - --output "$work/s1-mini/$1" "$base_url/$1"
}
verify_weights() {
  printf '%s  %s\n' "$weights_sha256" "$work/s1-mini/model.safetensors" | sha256sum --check --status
}
mkdir -p "$work/s1-mini"
for file in config.json generation_config.json tokenizer.json tokenizer_config.json vocab.json \
  merges.txt chat_template.jinja LICENSE NOTICE; do
  [[ -f "$work/s1-mini/$file" ]] || fetch "$file"
done
verify_weights || fetch model.safetensors
verify_weights || {
  printf 'checksum mismatch: S1-mini weights\n' >&2
  exit 1
}

if [[ ! -x "$runtime/llama-quantize" ]]; then
  "${project_root}/.local/tools/cmake-4.1.0-linux-x86_64/bin/cmake" \
    --build "$(dirname "$runtime")" --target llama-quantize --parallel "$(nproc)"
fi

python3 "$scripts/make_data.py" "$work/data"
(cd "$scripts" && "$work/venv/bin/python" label_general.py "$runtime/llama-completion" "$base_gguf" "$work/data" >/dev/null)
(cd "$scripts" && PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True \
  "$work/venv/bin/python" train.py "$work/s1-mini" "$work/data" "$work/s1-mini-vox")
"$scripts/export.sh" "$work/s1-mini-vox" "$output"
