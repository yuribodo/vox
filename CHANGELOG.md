# Changelog

All notable changes follow [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and versions follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

- Desktop paste into terminals (kitty, Alacritty, GNOME Terminal, Konsole, and
  others) now uses `Ctrl+Shift+V` and flattens the transcript to a single line
  so it can never submit the shell prompt.

## [0.1.0] - 2026-08-23

### Added

- Local Whisper large-v3-turbo dictation with Silero VAD.
- Cinnamon/X11 global shortcut, Flow Bar, microphone selection, and safe live
  source switching.
- Exact review-before-submit insertion for X11 and tmux.
- Private runtime state, reproducible pinned downloads, benchmarks, tests, and
  security documentation.

### Security

- Isolated recorder and Whisper outputs in private temporary directories.
- Bound recorder state to Linux process start time to prevent stale-PID signals.
- Removed clipboard persistence requests and limited untrusted input sizes.
- Hardened WAV parsing, runtime-directory validation, CI permissions, and
  dependency pinning.

[0.1.0]: https://github.com/yuribodo/vox/releases/tag/v0.1.0
