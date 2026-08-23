# Third-party notices

The Vox source repository does not vendor third-party source, binaries, model
weights, fonts, icons, or media. The preparation script downloads the following
components into the gitignored `.local/` directory for local use.

## Downloaded components

| Component | Use | License and attribution |
| --- | --- | --- |
| [whisper.cpp 1.9.1](https://github.com/ggml-org/whisper.cpp/tree/v1.9.1) | Local Whisper inference | MIT; copyright 2023-2026 The ggml authors |
| [Whisper large-v3-turbo](https://huggingface.co/openai/whisper-large-v3-turbo) | Speech-recognition model | MIT; published by OpenAI |
| [whisper.cpp converted models](https://huggingface.co/ggerganov/whisper.cpp) | Q8_0 GGML conversion | MIT; published by the whisper.cpp maintainers |
| [Silero VAD 6.2.0](https://github.com/snakers4/silero-vad) | Voice-activity detection | MIT; copyright 2020-present Silero Team |
| [CMake 4.1.0](https://cmake.org/download/) | Local build tool | BSD 3-Clause; copyright 2000-2025 Kitware, Inc. and contributors |

The Vox application is written in Go. A distributed Vox executable contains
portions of the Go runtime and standard library under Go's BSD-style license
and must retain its license notice. See the [Go license](https://go.dev/LICENSE).

## Public website

The landing page uses the following npm dependencies. `npm ci` downloads them
into the gitignored `site/node_modules/` directory; they are not committed to
the source repository.

| Component | Use | License and attribution |
| --- | --- | --- |
| [Next.js 16.3.2](https://github.com/vercel/next.js/tree/v16.3.2) | Static site framework and client runtime | MIT; copyright 2025 Vercel, Inc. |
| [React 19.2.8](https://github.com/facebook/react/tree/v19.2.8) | Interactive landing-page controls | MIT; copyright Meta Platforms, Inc. and affiliates |
| [React DOM 19.2.8](https://github.com/facebook/react/tree/v19.2.8) | Browser rendering | MIT; copyright Meta Platforms, Inc. and affiliates |
| [GSAP 3.15.0](https://github.com/greensock/GSAP/tree/3.15.0) | Scroll-linked signal-path animation | GSAP Standard no-charge license; GreenSock, Inc. |
| [Motion 13.1.1](https://github.com/motiondivision/motion/tree/v13.1.1) | Spring and pointer interactions | MIT; copyright Motion contributors |
| [Instrument Sans 5.3.0](https://fontsource.org/fonts/instrument-sans) | Variable display typeface, self-hosted with Fontsource | SIL Open Font License 1.1; Instrument Sans contributors |
| [IBM Plex Mono 5.3.0](https://fontsource.org/fonts/ibm-plex-mono) | Monospaced interface typeface, self-hosted with Fontsource | SIL Open Font License 1.1; copyright IBM Corp. |

The deployed static export includes compiled client code from those packages.
A source copy of the main runtime notices lives at
[`site/public/third-party-licenses.txt`](site/public/third-party-licenses.txt).
During the build, a license generator overwrites the exported copy with a
comprehensive file covering every production npm dependency. The notices are
linked from the website footer. TypeScript, ESLint, and their plugins are
development-only tools and are not part of the deployed site.

System components such as PipeWire, GTK, PyGObject, Cinnamon, X11, tmux, CUDA,
and NVIDIA drivers are invoked from the user's installation and are not bundled
with this repository. Their own terms apply independently.

## Distribution rule

The current application source release does not include the downloaded model
or inference components. The public website does include compiled client code
and self-hosted font files together with their required license notices. If a future
release bundles a binary, model, build tool, or more third-party source, it must
also bundle the exact license text and required notices from that pinned
version. This summary is informational; upstream license files control.

Third-party names and marks identify their respective projects and do not imply
endorsement.
