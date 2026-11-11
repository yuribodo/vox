#!/usr/bin/env bash
set -euo pipefail
umask 077

readonly cmake_version="4.1.0"
readonly cmake_archive="cmake-${cmake_version}-linux-x86_64.tar.gz"
readonly cmake_sha256="2637dab096e65c7d011ca0504fc0c563f8ffb531919754156ddec4b7a2f8584d"
readonly cmake_url="https://github.com/Kitware/CMake/releases/download/v${cmake_version}/${cmake_archive}"

readonly whisper_version="1.9.1"
readonly whisper_commit="f049fff95a089aa9969deb009cdd4892b3e74916"
readonly whisper_repo="https://github.com/ggml-org/whisper.cpp.git"

readonly model_revision="5359861c739e955e79d9a303bcbc70fb988958b1"
readonly model_file="ggml-large-v3-turbo-q8_0.bin"
readonly model_sha256="317eb69c11673c9de1e1f0d459b253999804ec71ac4c23c17ecf5fbe24e259a1"
readonly model_url="https://huggingface.co/ggerganov/whisper.cpp/resolve/${model_revision}/${model_file}"

readonly vad_revision="9ffd54a1e1ee413ddf265af9913beaf518d1639b"
readonly vad_file="ggml-silero-v6.2.0.bin"
readonly vad_sha256="2aa269b785eeb53a82983a20501ddf7c1d9c48e33ab63a41391ac6c9f7fb6987"
readonly vad_url="https://huggingface.co/ggml-org/whisper-vad/resolve/${vad_revision}/${vad_file}"

readonly project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
readonly download_dir="${project_root}/.local/downloads"
readonly tool_dir="${project_root}/.local/tools"
readonly source_dir="${project_root}/.local/src/whisper.cpp-v${whisper_version}"
readonly runtime_dir="${project_root}/.local/runtime/whisper.cpp-v${whisper_version}-cuda"
readonly model_dir="${project_root}/.local/models/whisper-large-v3-turbo-q8_0"
readonly vad_dir="${project_root}/.local/models/whisper-vad"
readonly cmake_dir="${tool_dir}/cmake-${cmake_version}-linux-x86_64"

mkdir -p "$download_dir" "$tool_dir" "$(dirname "$source_dir")" "$runtime_dir" "$model_dir" "$vad_dir"

fetch_and_verify() {
  local url="$1"
  local output="$2"
  local expected="$3"

  if [[ ! -f "$output" ]]; then
    curl --fail --location --proto '=https' --proto-redir '=https' \
      --tlsv1.2 --continue-at - --output "$output" "$url"
  fi
  printf '%s  %s\n' "$expected" "$output" | sha256sum --check --status || {
    printf 'checksum mismatch: %s\n' "$output" >&2
    return 1
  }
}

fetch_and_verify "$cmake_url" "$download_dir/$cmake_archive" "$cmake_sha256"
if [[ ! -x "$cmake_dir/bin/cmake" ]]; then
  tar -xzf "$download_dir/$cmake_archive" -C "$tool_dir"
fi

if [[ ! -d "$source_dir/.git" ]]; then
  git clone --branch "v${whisper_version}" --depth 1 "$whisper_repo" "$source_dir"
fi
actual_commit="$(git -C "$source_dir" rev-parse HEAD)"
if [[ "$actual_commit" != "$whisper_commit" ]]; then
  printf 'unexpected whisper.cpp commit: got %s, want %s\n' "$actual_commit" "$whisper_commit" >&2
  exit 1
fi
if [[ -n "$(git -C "$source_dir" status --porcelain --untracked-files=all)" ]]; then
  printf 'whisper.cpp source tree has local changes; refusing an unreproducible build\n' >&2
  exit 1
fi

fetch_and_verify "$model_url" "$model_dir/$model_file" "$model_sha256"
fetch_and_verify "$vad_url" "$vad_dir/$vad_file" "$vad_sha256"

"$cmake_dir/bin/cmake" \
  -S "$source_dir" \
  -B "$runtime_dir" \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_C_COMPILER=/usr/bin/gcc-15 \
  -DCMAKE_CXX_COMPILER=/usr/bin/g++-15 \
  -DCMAKE_CUDA_HOST_COMPILER=/usr/bin/g++-15 \
  -DCMAKE_CUDA_ARCHITECTURES=86 \
  -DGGML_CUDA=ON \
  -DWHISPER_BUILD_TESTS=OFF
"$cmake_dir/bin/cmake" --build "$runtime_dir" --target whisper-cli whisper-server --parallel "$(nproc)"

printf 'Whisper runtime: %s/bin/whisper-cli\n' "$runtime_dir"
printf 'Whisper model:   %s/%s\n' "$model_dir" "$model_file"
printf 'Silero VAD:      %s/%s\n' "$vad_dir" "$vad_file"
