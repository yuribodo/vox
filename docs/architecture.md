# Architecture and safety invariants

Vox is a process-per-dictation application composed from a Go CLI and small
desktop integration scripts.

## Design goals

- Keep audio and inference local during normal use.
- Make push-to-talk state obvious without taking keyboard focus.
- Return text to the destination selected when recording began.
- Preserve exact Unicode and multiline content.
- Never submit or execute a transcript automatically.
- Keep model and insertion mechanisms replaceable and independently testable.

## Components

| Component | Implementation | Responsibility |
| --- | --- | --- |
| CLI | `cmd/vox` | Parse commands, configure Whisper, and compose services |
| Recorder | `internal/record` | Produce finalized mono 16 kHz signed-16-bit PCM WAV files through PipeWire |
| Toggle state machine | `internal/toggle` | Start/stop recording, persist destination, run inference, and clean successful state |
| Whisper adapter | `internal/asr/whispercpp.go` | Invoke the pinned whisper.cpp runtime with the Q8_0 model and Silero VAD |
| tmux inserter | `internal/tmux` | Load transcript bytes through stdin and bracket-paste into an explicit pane |
| Desktop controller | `scripts/vox-desktop-toggle.sh` | Capture an X11 target, serialize shortcut actions, drive the CLI, and publish UI state |
| Flow Bar | `scripts/vox-overlay.py` | Render recording feedback and expose the current microphone picker |
| Source helper | `scripts/vox_audio_sources.py` | Enumerate real PipeWire capture nodes and change the WirePlumber default |
| X11 paste helper | `scripts/paste-x11.py` | Reactivate the captured window, paste without Enter, and restore clipboard content |
| History store | `scripts/vox_history.py` | Private, locked transcript history: append, list, delete, clear |
| History window | `scripts/vox-history-window.py` | Search, paste, copy, and delete history entries |
| Shortcut installer | `scripts/install-desktop-shortcut.py` | Manage Cinnamon GSettings bindings idempotently |

## Desktop dictation path

### First shortcut press

1. Cinnamon invokes `vox-desktop-toggle.sh`.
2. The controller takes a non-blocking `flock` to serialize shortcut actions.
3. It captures the active X11 window ID and human-readable window title.
4. It writes `desktop-target.json` atomically with `0600` permissions.
5. It resolves and persists PipeWire's current default capture source.
6. It publishes the `starting` state and launches the non-focusable Flow Bar.
7. `vox toggle --source <node> --output <runtime>/desktop-transcript.txt`
   starts `pw-record` in a new process group on that explicit source.
8. `recording.json` persists the recorder PID, Linux process start ticks, audio
   path, output path, and UTC start time.
9. The controller closes its lock descriptor before spawning long-lived child
   processes, so the second shortcut press can acquire the lock.

### While recording

`pw-record` writes mono 16 kHz PCM to a private runtime WAV. Every 50 ms, the
Flow Bar reads only a small tail of the growing file and calculates an RMS
level. The meter therefore reflects real microphone input rather than a
decorative animation.

The overlay uses a GTK notification window that:

- stays above ordinary windows;
- does not accept focus;
- is excluded from the taskbar and pager;
- limits its X11 input region to the microphone button so every other click
  passes through;
- recalculates its centered position after every size allocation.

### Microphone switch

1. The user clicks the microphone name and the Flow Bar lists current
   `Audio/Source` nodes from `pw-dump`.
2. Selecting a different node calls `wpctl set-default` after verifying the
   chosen numeric ID still belongs to a capture source.
3. The desktop controller keeps the original `desktop-target.json`, publishes
   `starting`, and calls `vox cancel`.
4. `cancel` first confirms that the PID still has the recorded Linux process
   start time and is its process-group leader. It then sends `SIGINT`, waits for
   exit, and deletes only that session's partial WAV and state. It never invokes
   ASR or insertion.
5. The controller starts a fresh explicit-source recording. The timer resets
   and the Flow Bar publishes the selected device name.

### Second shortcut press

1. The controller recognizes the existing `recording.json` and publishes the
   `processing` state.
2. The toggle state machine sends `SIGINT` to the recorder process group and
   waits for the WAV to finalize.
3. The Whisper adapter validates the WAV, runs VAD-assisted inference in a
   private temporary output directory, and parses bounded whisper.cpp JSON.
4. The exact non-empty transcript is created with `O_EXCL` and `0600`
   permissions. Existing output is never overwritten.
5. The controller appends the transcript to the persistent history (see below)
   before any paste attempt. A history failure is logged and does not block the
   paste; the runtime transcript is then kept even after a successful paste.
6. The X11 helper snapshots existing clipboard text or image content.
7. It temporarily publishes the transcript without requesting clipboard-manager
   persistence, reactivates the captured window, and sends `Ctrl+V` with
   modifiers cleared. Terminals detected by their `WM_CLASS` receive
   `Ctrl+Shift+V` instead; `VOX_PASTE_KEY` overrides the key. Terminal pastes
   (and any override) replace newlines and control characters with spaces so
   the transcript cannot submit a shell line or end a bracketed paste early.
8. It keeps the GTK event loop active while the destination requests the X11
   selection, then restores and re-publishes only the previous clipboard
   content.
9. The controller deletes successful transcript/target state and publishes the
   `done` state. The toggle deletes successful audio and recording state.

The paste helper never sends Enter.

### Paste last (`Super+Shift+V`)

`vox-desktop-toggle.sh --paste-last` takes the same controller lock, reads the
newest history entry into a private `0600` file in the runtime directory,
pastes it with the same X11 helper into the window focused at that moment, and
deletes the temporary file. It publishes `done` or a friendly `error` (no
focused window, empty history, history disabled, paste failed). It is a silent
no-op while Vox is recording (`recording.json` exists) or busy (another
controller holds the lock while transcribing or pasting), so it can neither
interrupt a dictation nor replace the `recording` Flow Bar state.

### History window (`Super+Alt+V`)

`vox-desktop-toggle.sh --history` follows the same rules as `--paste-last`
(controller lock, silent no-op while recording or busy). It reads
`xdotool getactivewindow` before the window exists, so the target is the
window the user was working in, and starts `vox-history-window.py --window-id N`
detached (`setsid`, controller lock closed, output appended to
`desktop-overlay.log`). Without a valid window ID the window still opens, with
Paste disabled.

- Single instance: the window is a `Gtk.Application` with a fixed application
  ID. A second launch only activates the running instance on the session bus,
  which comes to the front. Without a session bus, GLib falls back to a
  non-unique instance.
- The window closes when it loses focus, so its target can never go stale:
  after the user moves to another window, the next `Super+Alt+V` captures that
  window. Focus loss is ignored while a paste runs (the window hides itself)
  and while the Clear confirmation is open.
- Paste hides the window, pipes the entry to `paste-x11.py` (so the clipboard
  is restored and Enter is never sent), and closes on success. On failure the
  window comes back with a message. A helper still running after 15 seconds
  gets `SIGTERM`, which `paste-x11.py` turns into an exception so its clipboard
  restore still runs; `SIGKILL` follows only if it has not exited 3 seconds
  later. While the helper runs, the window keeps
  serving X11 events, because after a Copy it owns the clipboard the helper
  snapshots.
- Copy sets the clipboard and calls `clipboard.store()`, so a clipboard
  manager keeps the text after the window exits. This is an explicit user
  action, unlike the transient transcript in a paste.
- Delete and Clear use `vox_history.delete`/`clear` and identify entries by
  ID, never by position.
- Search folds case and accents (`NFKD` without combining marks, then
  `casefold`); every word in the query must appear in the entry.

## tmux dictation path

`vox toggle --target %N` uses the same recorder, state machine, and ASR adapter,
but finishes through `internal/tmux.Inserter` instead of the desktop transcript
file.

The inserter:

1. validates the target against `^%[0-9]+$`;
2. sends transcript bytes on stdin to `tmux load-buffer`;
3. uses a unique named buffer;
4. invokes `paste-buffer -p -d` for bracketed paste and cleanup;
5. never appends a newline or sends Enter;
6. deletes the temporary buffer if paste fails.

Because the pane ID is stored at recording start, changing the active pane does
not redirect the final text.

## State lifecycle

| UI state | Meaning | Terminal transition |
| --- | --- | --- |
| `starting` | The controller is connecting to the microphone | `recording` or `error` |
| `recording` | PipeWire is writing audio | `processing` |
| `processing` | Audio is finalizing or local inference is running | `done` or `error` |
| `done` | Text was pasted without submission | Overlay exits after 1.2 seconds |
| `error` | The action was safe but could not complete | Overlay exits after 4.5 seconds |

Only one recording state is allowed per user runtime directory. An exclusive
creation of `recording.json` rejects competing sessions, while the controller
lock prevents two shortcut handlers from mutating desktop state concurrently.

## Runtime layout

The default runtime root is `${XDG_RUNTIME_DIR}/vox`. If
`XDG_RUNTIME_DIR` is unavailable, Vox falls back to `/tmp/vox-$UID`.

| File | Purpose | Lifetime |
| --- | --- | --- |
| `recording.json` | Authoritative recorder PID/start ticks, destination, and WAV | One active dictation |
| `recording-*.wav` | Private audio being recorded or preserved after failure | Deleted on success |
| `desktop-target.json` | Captured X11 window ID/title | One desktop dictation |
| `desktop-source.json` | Explicit PipeWire node ID, name, and display label | Last selected source |
| `desktop-transcript.txt` | Exact text awaiting desktop paste | Deleted after successful paste, unless the history append failed |
| `.desktop-paste-last.*` | Newest history text being pasted by `--paste-last` | Deleted when that command exits |
| `desktop-status.json` | Flow Bar state and friendly message | Last desktop state |
| `desktop-command.log` | Technical CLI/paste detail | Replaced each shortcut command |
| `desktop-overlay.log` | GTK startup/runtime diagnostics | Appended across sessions |
| `desktop-toggle.lock` | Serializes shortcut controllers | Persistent empty lock file |
| `desktop-overlay.lock` | Ensures a single Flow Bar observer | Persistent empty lock file |

The runtime directory must be a real directory owned by the current user and is
forced to mode `0700`; sensitive JSON and transcript files are mode `0600`.

## Transcript history

`scripts/vox_history.py` keeps `${XDG_DATA_HOME:-$HOME/.local/share}/vox/history.jsonl`
(a relative `XDG_DATA_HOME` is ignored, per the XDG spec). Each line is a JSON
object with `id`, `timestamp`, and `text`. Window titles are deliberately not stored:
they can contain sensitive data and would outlive the session.

- The directory is refused if it is a symlink or not owned by the current user,
  and is forced to `0700`. The file is opened with `O_NOFOLLOW` and must be a
  regular file owned by the current user.
- Each append or delete rewrites the newest 50 entries to a `mkstemp` file
  (`0600`), then `fsync` and `os.replace`, so a crash leaves either the old or
  the new history. Readers never see a partial file.
- Append, delete, and clear hold an exclusive `flock` on `history.lock`
  (`0600`, opened with `O_NOFOLLOW`, owner-checked) in the history directory,
  so writers from the dictation controller and the history window cannot drop
  each other's changes, and a clear cannot race an append.
- `id` is a random UUID set on append. Entries written before IDs existed get a
  stable ID derived from a SHA-256 of their timestamp and text, which is stored
  on the next write. IDs stay valid when other entries are added or removed.
- Empty, NUL-containing, or over 1 MiB text is rejected. Malformed lines are
  skipped on read and therefore dropped by the next append or delete, which
  rewrites only the valid entries.
- `VOX_HISTORY=0` disables writing; `last` then exits with status 4. An empty
  history exits with status 3. `list` prints a JSON array, newest first;
  `delete ID` removes one entry (status 1 if it is gone); `clear` deletes the
  file.

Unlike the runtime directory, this file persists across reboots.

## ASR boundary

The Whisper adapter implements `asr.Transcriber`:

```go
type Transcriber interface {
    Transcribe(context.Context, Request) (Result, error)
}
```

The result includes exact text plus duration, latency, model-load latency,
inference latency, and real-time factor. Benchmarks exercise the same adapters
used by interactive dictation.

Whisper is the accepted default. Its current bounded configuration is:

- whisper.cpp 1.9.1;
- Whisper large-v3-turbo Q8_0;
- Silero VAD 6.2.0;
- English decoder language;
- eight threads by default;
- CUDA enabled for compute capability 8.6;
- optional context prompt limited to 16 KiB.

## Safety invariants

These are product requirements, not implementation conveniences:

1. **No automatic submission.** No path sends Enter or appends a submission
   newline.
2. **No shell interpolation.** Transcript content is passed through files,
   stdin, clipboard ownership, or tmux buffers—not constructed shell commands.
3. **Explicit destination capture.** X11 window IDs and tmux pane IDs are fixed
   at recording start.
4. **No silent overwrite.** Recordings and transcript outputs use exclusive
   creation or link semantics.
5. **Empty text changes nothing.** VAD/ASR silence returns an error and does not
   touch the destination field.
6. **Failures preserve evidence.** Audio or transcript files required for
   recovery are kept and their locations are recorded in technical logs.
7. **Private-by-default state.** Runtime and generated benchmark data use
   restrictive permissions and are excluded from Git.
8. **Bounded context.** Whisper prompt input is normalized and capped at 16 KiB.
9. **Safe source switching.** Audio captured before a microphone change is
   discarded and never reaches transcription or insertion.
10. **Process identity binding.** A stale or altered PID cannot make Vox signal
    a process whose Linux start time or process group does not match the state.
11. **Bounded untrusted input.** WAV chunks, inference JSON, stdin insertion,
    and desktop paste input are validated or size-limited before use.

Any future auto-submit, voice-command, or transcript-rewriting feature requires
a separate safety decision and explicit user confirmation design.

## Known architectural constraints

- X11 window activation and synthetic paste are not portable to Wayland.
- Cinnamon GSettings paths make shortcut installation desktop-specific.
- Process-per-dictation inference pays model startup cost after every recording.
- The desktop controller is a shell composition layer rather than a daemon.
- Clipboard snapshot restoration currently covers prior text and images.
- X11 clients and clipboard managers in the same session remain outside Vox's
  isolation boundary and may observe clipboard changes.
- English is fixed in the default Whisper configuration.
- The pinned whisper.cpp build is compiled for one NVIDIA GPU architecture.

These constraints define the supported scope of the current release.
