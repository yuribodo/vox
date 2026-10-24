from __future__ import annotations

import io
import json
import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import vox_history


class HistoryTest(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.env = {"XDG_DATA_HOME": str(self.root), "HOME": "/nonexistent"}
        self.path = self.root / "vox" / "history.jsonl"

    def entries(self) -> list[dict[str, str]]:
        return [json.loads(line) for line in self.path.read_text(encoding="utf-8").splitlines()]

    def test_history_path_respects_xdg_and_home(self) -> None:
        self.assertEqual(vox_history.history_file(self.env), self.path)
        self.assertEqual(
            vox_history.history_file({"XDG_DATA_HOME": "relative", "HOME": "/home/u"}),
            Path("/home/u/.local/share/vox/history.jsonl"),
        )
        with self.assertRaises(RuntimeError):
            vox_history.history_file({"HOME": ""})

    def test_append_creates_private_files_and_reads_last(self) -> None:
        self.assertIsNone(vox_history.last(self.env))
        self.assertTrue(vox_history.append("olá mundo\n", self.env))
        self.assertTrue(vox_history.append("segundo", self.env))

        self.assertEqual(stat.S_IMODE(self.path.parent.stat().st_mode), 0o700)
        self.assertEqual(stat.S_IMODE(self.path.stat().st_mode), 0o600)
        self.assertEqual(vox_history.last(self.env), "segundo")
        first = self.entries()[0]
        self.assertEqual(first["text"], "olá mundo\n")
        self.assertEqual(set(first), {"timestamp", "text"})
        self.assertIn("T", first["timestamp"])
        self.assertEqual(list(self.path.parent.iterdir()), [self.path])

    def test_append_trims_to_newest_entries(self) -> None:
        for index in range(vox_history.MAX_ENTRIES + 5):
            vox_history.append(f"texto {index}", self.env)
        texts = [entry["text"] for entry in self.entries()]
        self.assertEqual(len(texts), vox_history.MAX_ENTRIES)
        self.assertEqual(texts[0], "texto 5")
        self.assertEqual(texts[-1], f"texto {vox_history.MAX_ENTRIES + 4}")

    def test_opt_out_writes_nothing(self) -> None:
        env = {**self.env, "VOX_HISTORY": "0"}
        self.assertFalse(vox_history.append("segredo", env))
        self.assertFalse(self.path.parent.exists())
        with self.assertRaises(vox_history.HistoryDisabled):
            vox_history.last(env)

    def test_rejects_invalid_text(self) -> None:
        for text in ["", "  \n", "a\x00b"]:
            with self.subTest(text=text), self.assertRaises(ValueError):
                vox_history.append(text, self.env)
        self.assertFalse(self.path.exists())

    def test_skips_malformed_lines(self) -> None:
        vox_history.append("válido", self.env)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write("not json\n{\"text\": 3}\n[]\n")
        self.assertEqual(vox_history.last(self.env), "válido")

    def test_refuses_symlinks(self) -> None:
        target = self.root / "elsewhere"
        target.mkdir()
        (self.root / "vox").symlink_to(target)
        with self.assertRaises(RuntimeError):
            vox_history.append("texto", self.env)
        with self.assertRaises(RuntimeError):
            vox_history.last(self.env)

        (self.root / "vox").unlink()
        (self.root / "vox").mkdir()
        self.path.symlink_to(target / "file")
        with self.assertRaises(OSError):
            vox_history.last(self.env)

    def test_failed_write_keeps_previous_history(self) -> None:
        vox_history.append("primeiro", self.env)
        with mock.patch.object(vox_history.os, "replace", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                vox_history.append("segundo", self.env)
        self.assertEqual(vox_history.last(self.env), "primeiro")
        self.assertEqual(list(self.path.parent.iterdir()), [self.path])

    def test_clear(self) -> None:
        vox_history.append("texto", self.env)
        vox_history.clear(self.env)
        vox_history.clear(self.env)
        self.assertIsNone(vox_history.last(self.env))

    def test_main_exit_codes(self) -> None:
        def run(*args: str, env: dict[str, str] | None = None, stdin: bytes = b"") -> tuple[int, bytes]:
            stdout = io.TextIOWrapper(io.BytesIO())
            with (
                mock.patch.dict(os.environ, env or self.env, clear=True),
                mock.patch("sys.argv", ["vox_history.py", *args]),
                mock.patch("sys.stdin", io.TextIOWrapper(io.BytesIO(stdin))),
                mock.patch("sys.stdout", stdout),
                mock.patch("sys.stderr", io.StringIO()),
            ):
                code = vox_history.main()
            stdout.flush()
            return code, stdout.buffer.getvalue()

        self.assertEqual(run("last"), (vox_history.EXIT_EMPTY, b""))
        self.assertEqual(run("append", stdin="café\n".encode())[0], 0)
        self.assertEqual(run("last"), (0, "café\n".encode()))
        self.assertEqual(run("last", env={**self.env, "VOX_HISTORY": "0"})[0], vox_history.EXIT_DISABLED)
        self.assertEqual(run("append", stdin=b"")[0], 1)


if __name__ == "__main__":
    unittest.main()
