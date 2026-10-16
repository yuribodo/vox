from __future__ import annotations

import os
import re
import subprocess

DEFAULT_PASTE_KEY = "ctrl+v"
TERMINAL_PASTE_KEY = "ctrl+shift+v"

# Lowercased WM_CLASS instance or class names of terminals that treat Ctrl+V as
# the literal-next control character and paste with Ctrl+Shift+V instead.
TERMINAL_CLASSES = frozenset(
    {
        "alacritty",
        "com.mitchellh.ghostty",
        "foot",
        "gnome-terminal",
        "gnome-terminal-server",
        "io.elementary.terminal",
        "kgx",
        "kitty",
        "konsole",
        "lxterminal",
        "mate-terminal",
        "org.gnome.console",
        "org.gnome.ptyxis",
        "org.gnome.terminal",
        "org.wezfurlong.wezterm",
        "qterminal",
        "terminator",
        "tilix",
        "x-terminal-emulator",
        "xfce4-terminal",
    }
)

_KEY_PATTERN = re.compile(r"[a-z0-9_]+(\+[a-z0-9_]+)*", re.IGNORECASE)
_CONTROL_RUN = re.compile(r"[\x00-\x1f\x7f\x80-\x9f\u2028\u2029]+")


def parse_wm_class(output: str) -> tuple[str, ...]:
    """Parse `xprop WM_CLASS` output into its quoted instance and class names."""
    _, separator, values = output.partition("=")
    if not separator:
        return ()
    return tuple(re.findall(r'"((?:[^"\\]|\\.)*)"', values))


def is_terminal(classes: tuple[str, ...]) -> bool:
    return any(name.lower() in TERMINAL_CLASSES for name in classes)


def paste_key_for_classes(classes: tuple[str, ...], override: str | None = None) -> str:
    if override:
        if not _KEY_PATTERN.fullmatch(override):
            raise ValueError(f"invalid VOX_PASTE_KEY: {override!r}")
        return override
    if is_terminal(classes):
        return TERMINAL_PASTE_KEY
    return DEFAULT_PASTE_KEY


def terminal_safe_text(text: str) -> str:
    """Flatten text so a terminal paste can never act as Enter or an escape.

    Without bracketed paste, a pasted newline submits the shell line. Control
    characters (including ESC, which could end a bracketed paste early) become
    single spaces.
    """
    return _CONTROL_RUN.sub(" ", text).strip()


def window_classes(window_id: str) -> tuple[str, ...]:
    try:
        process = subprocess.run(
            ["xprop", "-id", window_id, "WM_CLASS"],
            check=False,
            capture_output=True,
            text=True,
            timeout=2,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ()
    if process.returncode != 0:
        return ()
    return parse_wm_class(process.stdout)


def prepare_paste(window_id: str, text: str) -> tuple[str, str]:
    """Return the key chord and text to paste into the given X11 window.

    Detected terminals and any VOX_PASTE_KEY override use terminal-safe text.
    """
    classes = window_classes(window_id)
    override = os.environ.get("VOX_PASTE_KEY")
    key = paste_key_for_classes(classes, override)
    if override or is_terminal(classes):
        text = terminal_safe_text(text)
    return key, text
