#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import subprocess
import sys
import time
from dataclasses import dataclass

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, Gtk  # noqa: E402


@dataclass
class ClipboardSnapshot:
    text: str | None = None
    image: object | None = None


def snapshot_clipboard(clipboard: Gtk.Clipboard) -> ClipboardSnapshot:
    if clipboard.wait_is_text_available():
        return ClipboardSnapshot(text=clipboard.wait_for_text())
    if clipboard.wait_is_image_available():
        image = clipboard.wait_for_image()
        return ClipboardSnapshot(image=image.copy() if image is not None else None)
    return ClipboardSnapshot()


def set_text(clipboard: Gtk.Clipboard, text: str) -> None:
    clipboard.set_text(text, -1)
    pump_events(0.05)


def pump_events(duration: float) -> None:
    """Keep serving X11 selection requests for at least duration seconds."""
    deadline = time.monotonic() + duration
    while True:
        while Gtk.events_pending():
            Gtk.main_iteration_do(False)
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return
        time.sleep(min(0.01, remaining))


def persist_restored_clipboard(clipboard: Gtk.Clipboard) -> None:
    # Ownership has already changed back to the user's original clipboard.
    # Persisting it here cannot persist the transient transcript.
    clipboard.store()
    pump_events(0.05)


def restore_clipboard(clipboard: Gtk.Clipboard, snapshot: ClipboardSnapshot) -> None:
    if snapshot.text is not None:
        set_text(clipboard, snapshot.text)
        persist_restored_clipboard(clipboard)
    elif snapshot.image is not None:
        clipboard.set_image(snapshot.image)
        pump_events(0.05)
        persist_restored_clipboard(clipboard)
    else:
        clipboard.clear()
        pump_events(0.05)


def xdotool(*args: str) -> None:
    process = subprocess.run(
        ["xdotool", *args],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )
    if process.returncode != 0:
        detail = process.stderr.strip() or f"exit status {process.returncode}"
        raise RuntimeError(f"xdotool {' '.join(args)} failed: {detail}")


def paste(window_id: str, text: str) -> None:
    if not re.fullmatch(r"[0-9]+", window_id):
        raise ValueError(f"invalid X11 window id: {window_id!r}")
    if not text:
        raise ValueError("refusing to paste empty text")
    if "\x00" in text:
        raise ValueError("refusing to paste text containing NUL")

    xdotool("getwindowname", window_id)
    clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
    snapshot = snapshot_clipboard(clipboard)
    try:
        # Never call clipboard.store() while the transcript owns the selection:
        # that would ask a clipboard manager to retain sensitive dictated text.
        set_text(clipboard, text)
        xdotool("windowactivate", "--sync", window_id)
        xdotool("key", "--clearmodifiers", "ctrl+v")
        # Clipboard transfer is asynchronous on X11. Electron and other clients
        # request the selection after the key event; sleeping here would stop
        # GTK from answering and can make the destination appear frozen.
        pump_events(1.0)
    finally:
        restore_clipboard(clipboard, snapshot)


def main() -> int:
    parser = argparse.ArgumentParser(description="Paste stdin into an X11 window without submitting")
    parser.add_argument("--window-id", required=True)
    args = parser.parse_args()
    try:
        maximum_bytes = 1024 * 1024
        data = sys.stdin.buffer.read(maximum_bytes + 1)
        if len(data) > maximum_bytes:
            raise ValueError("transcript exceeds the 1 MiB paste limit")
        text = data.decode("utf-8")
        paste(args.window_id, text)
        return 0
    except (OSError, RuntimeError, ValueError) as error:
        print(f"vox: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
