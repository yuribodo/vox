# Security audit and threat model

Audit date: 2026-08-23

Version reviewed: 0.1.0 pre-release

## Scope and method

This review covered every tracked Go, Python, shell, workflow, and documentation
file; the 46-commit private development history; runtime state and process
signaling; recording and paste paths; benchmark handling; external downloads;
and CI permissions. The public repository begins with a separate sanitized root
commit. Dependency copyright and licenses are documented separately in
[`licensing-audit.md`](licensing-audit.md). This review combined manual data-flow
analysis with:

- `make verify` (race-enabled Go tests, Python tests, `go vet`, syntax checks);
- the official Go vulnerability scanner, `govulncheck` v1.7.0;
- Gitleaks v8.30.1 with redaction across the complete Git history;
- targeted searches for credentials, private keys, unsafe subprocess use,
  shell evaluation, unbounded reads, personal paths, and generated recordings.

The audit is not a formal proof or a substitute for review after future
changes. Results describe this repository at the version and date above.

## Security properties

- Dictation inference is local. Network access occurs only when the user
  explicitly prepares pinned dependencies.
- Transcript text is data, never a shell command, and no insertion path sends
  Enter.
- Runtime state is private, owned by the current user, and rejects a symlinked
  runtime directory or state file.
- Output files use exclusive creation. Existing recordings and transcripts are
  not overwritten.
- Recorder signals are sent only after checking the PID's Linux start time and
  process-group identity.
- Whisper and recorder temporary outputs are hidden behind `0700` directories.
- External downloads use HTTPS-only redirects, immutable revisions or commits,
  and pinned SHA-256 digests. A dirty whisper.cpp source tree is rejected.
- CI has read-only repository permissions, no persisted checkout credential,
  fixed action commit SHAs, a timeout, tests, syntax checks, and `govulncheck`.

## Findings remediated for 0.1.0

| Severity | Finding | Resolution |
| --- | --- | --- |
| High | A stale or edited recorder PID could target a reused process group | State now records `/proc` start ticks and verifies start time plus process-group leadership before signaling |
| Medium | whisper.cpp could create transcript JSON with a permissive mode under shared `/tmp` | Output now lives in a new private `0700` temporary directory |
| Medium | `pw-record` could briefly create audio with a permissive mode in an existing public output directory | Recording now occurs inside a private sibling directory and is linked only after mode `0600` is applied |
| Medium | `clipboard.store()` asked clipboard managers to persist the transient transcript | The transcript is never stored; only the user's original clipboard is persisted again after restoration |
| Medium | A crafted WAV chunk could request a multi-gigabyte allocation or claim bytes beyond EOF | Parsing uses a fixed-size format buffer and validates every chunk against the regular file size |
| Medium | Resolving the runtime beside the current working directory could execute a lookalike inference binary from another Go project | Runtime discovery is anchored beside the resolved Vox executable |
| Medium | Predictable fallback runtime paths did not consistently reject symlinks, foreign ownership, or broad modes | Go, shell, and overlay paths validate ownership/type and enforce mode `0700`; fallback paths are now consistent |
| Low | CLI/paste reads and inference JSON were unbounded | Inputs are capped at 1 MiB for insertion/paste and 8 MiB for inference JSON |
| Low | Rejected experiments and internal project records expanded maintenance and exposed private project process | Unused implementation paths, stale reports, internal requirements and decisions, and the machine inventory were removed |

## Automated scan results

- `govulncheck`: no reachable vulnerabilities found.
- Gitleaks: the 46-commit private development history and the public snapshot
  were scanned; no leaks found.
- Current tracked tree: no recordings, private benchmark manifest, model weights,
  private keys, environment files, tokens, or generated transcript results.
- Go module graph: standard library only; the application has no third-party Go
  module dependency at runtime.

## Residual risks

1. **X11 is not an isolation boundary.** Another client in the same X11 session
   can potentially observe windows, synthetic input, or clipboard ownership.
   Wayland support will require a different, permission-aware insertion design.
2. **Clipboard observers may still see changes.** Vox never calls
   `clipboard.store()` while the transcript owns the selection, but a
   clipboard-history tool may independently record any ownership change.
   Disable clipboard history for highly sensitive dictation or use the tmux
   path.
3. **Failure artifacts are intentionally retained.** Audio or transcripts needed
   for recovery remain in the private runtime directory after some failures.
   Inspect and delete them after recovery; the login runtime is normally cleared
   at session end.
4. **Pinned artifacts still require upstream trust.** Digests prevent unnoticed
   changes but do not prove that CMake, whisper.cpp, the models, CUDA, or drivers
   are free of malicious behavior or vulnerabilities.
5. **Explicit environment overrides are trusted.** `VOX_WHISPER_BIN` and model
   override variables deliberately allow the current user to select different
   local files. Do not set them from untrusted shell configuration.
6. **Context prompts appear in process arguments.** Hotword/context vocabulary is
   passed to whisper.cpp as an argument and may be visible to other processes
   with permission to inspect the user's process list. Do not put secrets in a
   hotword file.
7. **Captured X11 IDs are best-effort.** Closing a destination window during a
   dictation can cause a safe paste failure; X11 cannot provide the stronger
   destination identity guarantees expected from a modern portal.
8. **The local account is trusted.** Vox does not defend against malware already
   running as the same user, a compromised desktop session, kernel, or driver.

## Publication controls

- The public repository starts from a single sanitized root commit. The prior
  development history remains in a separate private repository.
- Public commits use the repository owner's GitHub `noreply` address.
- `main` requires a pull request, an up-to-date successful `test` check, linear
  history, and resolved conversations. The rule includes administrators and
  blocks force-pushes and branch deletion. No external approval is required so
  the solo maintainer can merge after CI passes.
- Private vulnerability reporting, secret scanning, push protection, Dependabot
  alerts, and automated security fixes are enabled.
- Merge commits are disabled and merged branches are deleted automatically.
- Create and sign the `v0.1.0` tag only after reviewing the final public diff.
