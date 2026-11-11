# Pinned local dependencies

Vox uses `whisper.cpp` v1.9.1 built locally with CUDA for
compute capability 8.6 and the official `large-v3-turbo-q8_0` GGML conversion.
It does not install system packages. Because CMake is absent on the target
machine, the preparation script downloads an official project-local CMake
binary under `.local/tools`.

Run:

```bash
./scripts/fetch-whisper.sh
```

Pinned inputs:

- CMake 4.1.0 Linux x86_64 archive, SHA-256
  `2637dab096e65c7d011ca0504fc0c563f8ffb531919754156ddec4b7a2f8584d`.
- `ggml-org/whisper.cpp` v1.9.1, Git commit
  `f049fff95a089aa9969deb009cdd4892b3e74916`.
- `ggml-large-v3-turbo-q8_0.bin` from the official whisper.cpp Hugging Face
  repository, immutable revision `5359861c739e955e79d9a303bcbc70fb988958b1`,
  SHA-256 `317eb69c11673c9de1e1f0d459b253999804ec71ac4c23c17ecf5fbe24e259a1`.
- `ggml-silero-v6.2.0.bin` from the official `ggml-org/whisper-vad` repository,
  immutable revision `9ffd54a1e1ee413ddf265af9913beaf518d1639b`, SHA-256
  `2aa269b785eeb53a82983a20501ddf7c1d9c48e33ab63a41391ac6c9f7fb6987`.

Optional transcript polish (`./scripts/fetch-llm.sh`, after the Whisper script):

- `ggml-org/llama.cpp` release `b11912`, Git commit
  `961c376a2daa42220ec09663b9bde32c5fba1f70`, built for CUDA 8.6 with only the
  `llama-completion` target.
- `s1-mini-q4_k_m.gguf`, "S1-mini" by "Superwhisper", from
  `superwhisper/s1-mini-GGUF`, immutable revision
  `34add00a48a2e5d24e5a4ee5405a99620a3a240c`, SHA-256
  `3b41ebe2502cbd03e811d5d16b022f5ab551eda58d62597d152f89535003c634`
  (462 MiB). llama.cpp is MIT. S1-mini is Apache 2.0 with an additional term:
  any use or integration must keep identifying it as "S1-mini" by
  "Superwhisper".

The Whisper model, its GGML conversion repository, whisper.cpp, and Silero VAD
are MIT licensed. CMake is BSD-3-Clause. Vox downloads them only into an ignored
local directory and does not redistribute them. A binary or model distribution
must include the applicable upstream license and notices described in
[`THIRD_PARTY_NOTICES.md`](../THIRD_PARTY_NOTICES.md).

Sources:

- https://github.com/ggml-org/whisper.cpp/releases/tag/v1.9.1
- https://github.com/ggml-org/whisper.cpp#nvidia-gpu-support
- https://huggingface.co/ggerganov/whisper.cpp
- https://cmake.org/download/
