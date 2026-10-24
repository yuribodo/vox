#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import stat
import sys
import tempfile
from pathlib import Path
from typing import Mapping

MAX_ENTRIES = 50
MAX_TEXT_BYTES = 1024 * 1024
EXIT_EMPTY = 3
EXIT_DISABLED = 4


class HistoryDisabled(RuntimeError):
    pass


def history_file(env: Mapping[str, str] = os.environ) -> Path | None:
    """Return the history path, or None when VOX_HISTORY=0 disables it."""
    if env.get("VOX_HISTORY") == "0":
        return None
    data_home = env.get("XDG_DATA_HOME", "")
    # The XDG spec says relative values must be ignored.
    if not data_home.startswith("/") or data_home == "/":
        home = env.get("HOME", "")
        if not home.startswith("/") or home == "/":
            raise RuntimeError("HOME must be an absolute, non-root path")
        data_home = f"{home}/.local/share"
    return Path(data_home) / "vox" / "history.jsonl"


def ensure_private_dir(directory: Path) -> None:
    if directory.is_symlink():
        raise RuntimeError(f"refusing symlink history directory: {directory}")
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    info = directory.lstat()
    if not stat.S_ISDIR(info.st_mode):
        raise RuntimeError(f"history path is not a real directory: {directory}")
    if info.st_uid != os.getuid():
        raise RuntimeError("history directory is not owned by the current user")
    os.chmod(directory, 0o700)


def read_entries(path: Path) -> list[dict[str, str]]:
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    except FileNotFoundError:
        return []
    with os.fdopen(descriptor, encoding="utf-8", errors="replace") as handle:
        info = os.fstat(handle.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid():
            raise RuntimeError(f"history file is not a private regular file: {path}")
        lines = handle.readlines()
    entries = []
    for line in lines:
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(entry, dict) and isinstance(entry.get("text"), str) and entry["text"]:
            entries.append(entry)
    return entries


def validate_text(text: str) -> None:
    if not text.strip():
        raise ValueError("refusing to save empty text")
    if "\x00" in text:
        raise ValueError("refusing to save text containing NUL")
    if len(text.encode("utf-8")) > MAX_TEXT_BYTES:
        raise ValueError("transcript exceeds the 1 MiB history limit")


def append(text: str, env: Mapping[str, str] = os.environ) -> bool:
    """Append one entry and keep the newest MAX_ENTRIES. Returns False when disabled."""
    validate_text(text)
    path = history_file(env)
    if path is None:
        return False
    ensure_private_dir(path.parent)
    entries = read_entries(path)
    entries.append(
        {
            "timestamp": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
            "text": text,
        }
    )
    descriptor, temporary = tempfile.mkstemp(prefix=".history.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            for entry in entries[-MAX_ENTRIES:]:
                handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        os.unlink(temporary)
        raise
    return True


def last(env: Mapping[str, str] = os.environ) -> str | None:
    path = history_file(env)
    if path is None:
        raise HistoryDisabled("history is disabled by VOX_HISTORY=0")
    if path.parent.is_symlink():
        raise RuntimeError(f"refusing symlink history directory: {path.parent}")
    entries = read_entries(path)
    return entries[-1]["text"] if entries else None


def clear(env: Mapping[str, str] = os.environ) -> None:
    path = history_file(env)
    if path is not None:
        path.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Private local history of Vox transcripts")
    subcommands = parser.add_subparsers(dest="command", required=True)
    subcommands.add_parser("append", help="save stdin as the newest transcript")
    subcommands.add_parser("last", help="print the newest transcript")
    subcommands.add_parser("clear", help="delete the history file")
    args = parser.parse_args()

    try:
        if args.command == "append":
            data = sys.stdin.buffer.read(MAX_TEXT_BYTES + 1)
            if len(data) > MAX_TEXT_BYTES:
                raise ValueError("transcript exceeds the 1 MiB history limit")
            append(data.decode("utf-8"))
        elif args.command == "last":
            text = last()
            if text is None:
                print("vox: history is empty", file=sys.stderr)
                return EXIT_EMPTY
            sys.stdout.buffer.write(text.encode("utf-8"))
        else:
            clear()
        return 0
    except HistoryDisabled as error:
        print(f"vox: {error}", file=sys.stderr)
        return EXIT_DISABLED
    except (OSError, RuntimeError, ValueError) as error:
        print(f"vox: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
