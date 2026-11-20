# Contributing to Vox

Thanks for helping improve private, local dictation on Linux.

## Before opening a change

- Read the current limitations in `README.md`. The supported desktop target is
  intentionally narrow: Cinnamon, X11, PipeWire, and NVIDIA CUDA compute 8.6.
- Open an issue before making a large architectural change or adding another
  speech-recognition engine.
- Never commit recordings, real transcripts, model weights, benchmark
  manifests, credentials, or machine-identifying diagnostics.
- Report security issues privately as described in `SECURITY.md`.

## Development checks

```bash
make verify
go run golang.org/x/vuln/cmd/govulncheck@v1.7.0 ./...
```

Changes to recording, process signaling, clipboard handling, tmux insertion,
runtime files, or external downloads should include tests for their security
invariants. Keep every insertion path review-only: Vox must never send Enter or
otherwise submit transcribed text.

## Pull requests

Keep pull requests focused, explain user-visible behavior and security impact,
and update the relevant documentation. By contributing, you represent that the
work is original or that you have the right to submit it, that it contains no
confidential material, and that it is licensed under the repository's MIT
License.

## Landing page browser smoke

The CI `site` job builds the static export with `NEXT_PUBLIC_BASE_PATH=/vox`,
then installs and runs the isolated harness with `npm test` in `site/e2e/`.
Its separate lockfile keeps Playwright out of Next's production peer graph; its
dev tooling is audited at the same critical threshold as other dev dependencies.
The smoke files use `.mjs` so the site typecheck and Pages build can run without
installing the harness. The smoke serves only `site/out`
under `/vox/` on loopback port 4173 (no deployment or `next start`). It uses
Google Chrome already installed on the GitHub Ubuntu runner, without browser
installation scripts. Chromium sandbox is explicitly enabled; missing Chrome
or an unavailable sandbox fails the run without fallback.
This follows the installed-browser precedent in
[Cadence #126](https://github.com/Dnreikronos/cadence/pull/126).

It checks desktop (1440×900) and mobile (390×844), page-wide horizontal overflow,
all three copy buttons and repeated copies including feedback reset. Clipboard
permissions apply only to the synthetic loopback origin. External page requests
are blocked; copied install commands are compared as text, never executed.
Reduced motion is enabled for deterministic geometry, so animation, full visual
appearance, accessibility and actual installation are not covered. No screenshots
or traces are published. Browser runtime must be validated on an authorized
runner; config discovery (`npm test -- --list` in `site/e2e/`) does not launch Chrome.
