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
5. The X11 helper snapshots existing clipboard text or image content.
6. It temporarily publishes the transcript without requesting clipboard-manager
   persistence, reactivates the captured window, and sends `Ctrl+V` with
   modifiers cleared.
7. It keeps the GTK event loop active while the destination requests the X11
   selection, then restores and re-publishes only the previous clipboard
   content.
8. The controller deletes successful transcript/target state and publishes the
   `done` state. The toggle deletes successful audio and recording state.

The paste helper never sends Enter.

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
| `desktop-transcript.txt` | Exact text awaiting desktop paste | Deleted after successful paste |
| `desktop-status.json` | Flow Bar state and friendly message | Last desktop state |
| `desktop-command.log` | Technical CLI/paste detail | Replaced each shortcut command |
| `desktop-overlay.log` | GTK startup/runtime diagnostics | Appended across sessions |
| `desktop-toggle.lock` | Serializes shortcut controllers | Persistent empty lock file |
| `desktop-overlay.lock` | Ensures a single Flow Bar observer | Persistent empty lock file |

The runtime directory must be a real directory owned by the current user and is
forced to mode `0700`; sensitive JSON and transcript files are mode `0600`.

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
