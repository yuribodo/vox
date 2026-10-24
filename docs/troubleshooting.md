# Troubleshooting

This guide starts with non-destructive checks. Vox keeps technical detail under
the private user runtime directory while the Flow Bar shows short messages.

## First checks

From the project root:

```bash
make build
make doctor
```

Inspect desktop state and logs:

```bash
runtime_dir="${XDG_RUNTIME_DIR:+${XDG_RUNTIME_DIR}/vox}"
runtime_dir="${runtime_dir:-/tmp/vox-$(id -u)}"

jq . "$runtime_dir/desktop-status.json"
tail -n 40 "$runtime_dir/desktop-command.log"
tail -n 40 "$runtime_dir/desktop-overlay.log"
```

Check active processes without changing them:

```bash
pgrep -af '^pw-record '
pgrep -af 'vox-overlay.py'
```

## `Super+V` does nothing

The automatic installer currently requires Cinnamon on X11.

```bash
printf 'desktop=%s session=%s\n' \
  "$XDG_CURRENT_DESKTOP" "$XDG_SESSION_TYPE"
```

Expected values include `X-Cinnamon` and `x11`. Reinstall the managed
shortcuts idempotently:

```bash
make desktop-shortcut
```

Read the installed bindings:

```bash
gsettings get org.cinnamon.desktop.keybindings custom-list
gsettings get \
  org.cinnamon.desktop.keybindings.custom-keybinding:/org/cinnamon/desktop/keybindings/custom-keybindings/vox-toggle/ \
  binding
gsettings get \
  org.cinnamon.desktop.keybindings.custom-keybinding:/org/cinnamon/desktop/keybindings/custom-keybindings/vox-toggle-fallback/ \
  binding
gsettings get \
  org.cinnamon.desktop.keybindings.custom-keybinding:/org/cinnamon/desktop/keybindings/custom-keybindings/vox-paste-last/ \
  binding
```

Expected bindings are `['<Super>v']`, `['<Control><Alt>space']`, and
`['<Super><Shift>v']`.

## The Flow Bar does not appear

Confirm the Python GTK dependencies:

```bash
python3 - <<'PY'
import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, Gtk
print("GTK overlay dependencies: ok")
PY
```

Then inspect `desktop-overlay.log`. The overlay does not accept focus and its
transparent area is intentionally click-through.

## The Flow Bar looks stuck in recording

First determine whether recording is actually active:

```bash
runtime_dir="${XDG_RUNTIME_DIR:+${XDG_RUNTIME_DIR}/vox}"
runtime_dir="${runtime_dir:-/tmp/vox-$(id -u)}"

test -f "$runtime_dir/recording.json" && jq . "$runtime_dir/recording.json"
pgrep -af '^pw-record '
```

If both recording state and `pw-record` exist, press the same shortcut once to
finish normally. Do not kill the process before trying the normal stop path;
`pw-record` needs `SIGINT` to finalize a valid WAV.

If the overlay exists but neither recording state nor `pw-record` exists, it is
only stale UI. Close that observer without touching audio:

```bash
pkill -f '^python3 .*vox-overlay.py --runtime-dir'
```

The next shortcut press launches a fresh observer.

If `recording.json` exists but its recorded PID no longer exists, preserve the
state for inspection instead of deleting it:

```bash
runtime_dir="${XDG_RUNTIME_DIR:+${XDG_RUNTIME_DIR}/vox}"
runtime_dir="${runtime_dir:-/tmp/vox-$(id -u)}"
mv "$runtime_dir/recording.json" \
  "$runtime_dir/recording.stale.$(date +%Y%m%d-%H%M%S).json"
```

Only do this after confirming the PID from the JSON is not running.

## Text is transcribed but not pasted

The desktop path captures the X11 window on the **first** shortcut press. Make
sure the intended application's text field has keyboard focus before starting.

Check:

```bash
runtime_dir="${XDG_RUNTIME_DIR:+${XDG_RUNTIME_DIR}/vox}"
runtime_dir="${runtime_dir:-/tmp/vox-$(id -u)}"
jq . "$runtime_dir/desktop-target.json"
tail -n 40 "$runtime_dir/desktop-command.log"
```

If paste fails after successful transcription, Vox preserves
`desktop-transcript.txt` in the runtime directory. Its mode is `0600`; copy or
inspect it before starting a new dictation, because the next start archives a
stale desktop transcript with a timestamp.

X11 paste depends on `xdotool` and a functioning Cinnamon clipboard manager.

Terminals paste with `Ctrl+Shift+V`. Vox detects common terminals through
`xprop WM_CLASS`; if your terminal receives a literal `^V` instead of the text,
check its class with `xprop WM_CLASS` (then click the window) and either add it
to `TERMINAL_CLASSES` in `scripts/vox_paste_keys.py` or set `VOX_PASTE_KEY`
(for example `ctrl+shift+v` or `shift+Insert`) in the environment that runs the
shortcut.
Wayland is not supported by this integration.

## `Nenhuma fala detectada`

This is a safe terminal state, not a crash. Whisper and Silero VAD returned an
empty transcript, so Vox left the destination untouched and preserved the WAV
for technical inspection.

Speak closer to the selected microphone and try again. Inspect PipeWire sources:

```bash
wpctl status
```

Record a direct sample when diagnosing the microphone:

```bash
./vox record --output microphone-check.wav
# Speak, then press Ctrl-C once.
```

The recorder refuses to overwrite `microphone-check.wav`; choose a new path for
another attempt.

## Wrong microphone

The current microphone appears on the right side of the Flow Bar. Click its
name and choose another available source. Vox discards the partial audio,
restarts the timer on the selected microphone, and preserves the original text
field destination.

If the menu is empty or a device disappeared, list PipeWire devices manually:

```bash
wpctl status
python3 scripts/vox_audio_sources.py list | jq .
```

The low-level recorder also supports a specific PipeWire target:

```bash
./vox record --source <pipewire-node> --output microphone-check.wav
```

Selecting a source in the Flow Bar updates WirePlumber's default, so future
desktop dictations continue using it. USB device IDs can change after
reconnection; Vox resolves the current node list every time the menu opens.

## Model or CUDA errors

Re-run the pinned preparation and doctor checks:

```bash
make fetch-whisper
make doctor
```

The current build expects:

- an NVIDIA driver and CUDA toolkit;
- `/usr/bin/gcc-15` and `/usr/bin/g++-15`;
- CUDA compute capability 8.6;
- the pinned files under `.local/`.

`fetch-whisper.sh` verifies every downloaded archive/model by SHA-256 and
checks the exact whisper.cpp Git commit. See [dependencies.md](dependencies.md)
for versions, checksums, sources, and licenses.

## Portuguese speech produces English-looking text

The Whisper configuration forces the decoder language to English. Portuguese
audio can therefore be coerced into English-looking output, but Vox is not
running Whisper translation mode and the result is not guaranteed translation.

This is the intended English-first behavior of the current benchmarked build.

## Recovering preserved audio

Failures report the exact WAV path in `desktop-command.log`. Files normally
live under `${XDG_RUNTIME_DIR}/vox` and may disappear when the user session or
machine ends. Copy a needed recording to a private durable location before
logout or reboot.

Never attach or commit preserved audio without reviewing it for private speech.
