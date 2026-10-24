#!/usr/bin/env python3
from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import fcntl
import hashlib
import json
import os
import stat
import sys
import tempfile
import unicodedata
import uuid
from pathlib import Path
from typing import Iterator, Mapping

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


@contextlib.contextmanager
def locked(directory: Path) -> Iterator[None]:
    """Serialize writers from different processes (dictation, paste-last, window)."""
    ensure_private_dir(directory)
    descriptor = os.open(
        directory / "history.lock",
        os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_CLOEXEC,
        0o600,
    )
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid():
            raise RuntimeError("history lock is not a private regular file")
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield
    finally:
        os.close(descriptor)


def entry_id(entry: Mapping[str, str]) -> str:
    value = entry.get("id")
    if isinstance(value, str) and value:
        return value
    # Entries written before ids existed get a stable id from their content.
    # Two legacy entries with the same timestamp and text share it (delete removes both).
    seed = f"{entry.get('timestamp', '')}\x00{entry['text']}".encode("utf-8")
    return hashlib.sha256(seed).hexdigest()[:32]


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
            entry["id"] = entry_id(entry)
            entries.append(entry)
    return entries


def write_entries(path: Path, entries: list[dict[str, str]]) -> None:
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
    with locked(path.parent):
        entries = read_entries(path)
        entries.append(
            {
                "id": uuid.uuid4().hex,
                "timestamp": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
                "text": text,
            }
        )
        write_entries(path, entries)
    return True


def readable_file(env: Mapping[str, str]) -> Path:
    path = history_file(env)
    if path is None:
        raise HistoryDisabled("history is disabled by VOX_HISTORY=0")
    if path.parent.is_symlink():
        raise RuntimeError(f"refusing symlink history directory: {path.parent}")
    return path


def last(env: Mapping[str, str] = os.environ) -> str | None:
    entries = read_entries(readable_file(env))
    return entries[-1]["text"] if entries else None


def list_entries(env: Mapping[str, str] = os.environ) -> list[dict[str, str]]:
    """Return entries newest first, each with a stable id."""
    return read_entries(readable_file(env))[::-1]


def delete(target_id: str, env: Mapping[str, str] = os.environ) -> bool:
    """Delete the entry with this id. Returns False when it is already gone."""
    path = readable_file(env)
    if not os.path.lexists(path.parent):
        return False
    with locked(path.parent):
        entries = read_entries(path)
        remaining = [entry for entry in entries if entry["id"] != target_id]
        if len(remaining) == len(entries):
            return False
        write_entries(path, remaining)
    return True


def clear(env: Mapping[str, str] = os.environ) -> None:
    path = history_file(env)
    if path is not None and os.path.lexists(path.parent):
        with locked(path.parent):
            path.unlink(missing_ok=True)


def normalize(text: str) -> str:
    """Fold case and accents so "acao" finds "ação"."""
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def matches(query: str, folded: str) -> bool:
    """folded is normalize(text), computed once per entry by the caller."""
    return all(word in folded for word in normalize(query).split())


def main() -> int:
    parser = argparse.ArgumentParser(description="Private local history of Vox transcripts")
    subcommands = parser.add_subparsers(dest="command", required=True)
    subcommands.add_parser("append", help="save stdin as the newest transcript")
    subcommands.add_parser("last", help="print the newest transcript")
    subcommands.add_parser("list", help="print all entries as JSON, newest first")
    delete_parser = subcommands.add_parser("delete", help="delete one entry by id")
    delete_parser.add_argument("id")
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
        elif args.command == "list":
            print(json.dumps(list_entries(), ensure_ascii=False))
        elif args.command == "delete":
            if not delete(args.id):
                print("vox: no history entry with that id", file=sys.stderr)
                return 1
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
