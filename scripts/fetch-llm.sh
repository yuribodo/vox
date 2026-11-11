#!/usr/bin/env bash
# Prepare the optional local transcript polish: llama.cpp + S1-mini by Superwhisper.
# Run ./scripts/fetch-whisper.sh first: it provides the pinned CMake.
set -euo pipefail
umask 077

readonly cmake_version="4.1.0"

readonly llama_tag="b11912"
readonly llama_commit="961c376a2daa42220ec09663b9bde32c5fba1f70"
readonly llama_repo="https://github.com/ggml-org/llama.cpp.git"

readonly model_revision="34add00a48a2e5d24e5a4ee5405a99620a3a240c"
readonly model_file="s1-mini-q4_k_m.gguf"
readonly model_sha256="3b41ebe2502cbd03e811d5d16b022f5ab551eda58d62597d152f89535003c634"
readonly model_url="https://huggingface.co/superwhisper/s1-mini-GGUF/resolve/${model_revision}/${model_file}"

readonly project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
readonly cmake_bin="${project_root}/.local/tools/cmake-${cmake_version}-linux-x86_64/bin/cmake"
readonly source_dir="${project_root}/.local/src/llama.cpp-${llama_tag}"
readonly runtime_dir="${project_root}/.local/runtime/llama.cpp-${llama_tag}-cuda"
readonly model_dir="${project_root}/.local/models/s1-mini-q4_k_m"

if [[ ! -x "$cmake_bin" ]]; then
  printf 'pinned CMake not found; run ./scripts/fetch-whisper.sh first\n' >&2
  exit 1
fi
mkdir -p "$(dirname "$source_dir")" "$runtime_dir" "$model_dir"

if [[ ! -d "$source_dir/.git" ]]; then
  git clone --branch "$llama_tag" --depth 1 "$llama_repo" "$source_dir"
fi
actual_commit="$(git -C "$source_dir" rev-parse HEAD)"
if [[ "$actual_commit" != "$llama_commit" ]]; then
  printf 'unexpected llama.cpp commit: got %s, want %s\n' "$actual_commit" "$llama_commit" >&2
  exit 1
fi
if [[ -n "$(git -C "$source_dir" status --porcelain --untracked-files=all)" ]]; then
  printf 'llama.cpp source tree has local changes; refusing an unreproducible build\n' >&2
  exit 1
fi

model_path="$model_dir/$model_file"
verify_model() { printf '%s  %s\n' "$model_sha256" "$model_path" | sha256sum --check --status; }
# A slow download can drop midway: resume a partial file and retry.
if [[ ! -f "$model_path" ]] || ! verify_model; then
  curl --fail --location --proto '=https' --proto-redir '=https' \
    --tlsv1.2 --retry 10 --retry-all-errors --continue-at - \
    --output "$model_path" "$model_url"
fi
verify_model || {
  printf 'checksum mismatch: %s\n' "$model_path" >&2
  exit 1
}

"$cmake_bin" \
  -S "$source_dir" \
  -B "$runtime_dir" \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_C_COMPILER=/usr/bin/gcc-15 \
  -DCMAKE_CXX_COMPILER=/usr/bin/g++-15 \
  -DCMAKE_CUDA_HOST_COMPILER=/usr/bin/g++-15 \
  -DCMAKE_CUDA_ARCHITECTURES=86 \
  -DGGML_CUDA=ON \
  -DLLAMA_CURL=OFF \
  -DLLAMA_BUILD_TESTS=OFF
"$cmake_bin" --build "$runtime_dir" --target llama-completion llama-server --parallel "$(nproc)"

printf 'llama.cpp runtime: %s/bin/llama-completion\n' "$runtime_dir"
printf 'Polish model:      %s\n' "$model_path"
