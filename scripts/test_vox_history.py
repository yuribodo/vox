from __future__ import annotations

import io
import json
import multiprocessing
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

    def files(self) -> list[str]:
        return sorted(item.name for item in self.path.parent.iterdir())

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
        self.assertEqual(set(first), {"id", "timestamp", "text"})
        self.assertIn("T", first["timestamp"])
        self.assertEqual(self.files(), ["history.jsonl", "history.lock"])
        self.assertEqual(stat.S_IMODE((self.path.parent / "history.lock").stat().st_mode), 0o600)

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
        self.assertEqual(self.files(), ["history.jsonl", "history.lock"])

    def test_clear(self) -> None:
        vox_history.clear(self.env)
        self.assertFalse(self.path.parent.exists())
        vox_history.append("texto", self.env)
        vox_history.clear(self.env)
        vox_history.clear(self.env)
        self.assertIsNone(vox_history.last(self.env))

    def test_list_is_newest_first_with_unique_ids(self) -> None:
        self.assertEqual(vox_history.list_entries(self.env), [])
        for text in ["um", "dois", "três"]:
            vox_history.append(text, self.env)
        entries = vox_history.list_entries(self.env)
        self.assertEqual([entry["text"] for entry in entries], ["três", "dois", "um"])
        self.assertEqual(len({entry["id"] for entry in entries}), 3)
        with self.assertRaises(vox_history.HistoryDisabled):
            vox_history.list_entries({**self.env, "VOX_HISTORY": "0"})

    def test_delete_by_id_survives_interleaved_append(self) -> None:
        vox_history.append("manter", self.env)
        vox_history.append("apagar", self.env)
        target = vox_history.list_entries(self.env)[0]["id"]
        vox_history.append("novo", self.env)  # shifts every index; the id still points at "apagar"
        self.assertTrue(vox_history.delete(target, self.env))
        self.assertFalse(vox_history.delete(target, self.env))
        self.assertEqual([e["text"] for e in vox_history.list_entries(self.env)], ["novo", "manter"])
        self.assertEqual(stat.S_IMODE(self.path.stat().st_mode), 0o600)

    def test_delete_missing_history(self) -> None:
        self.assertFalse(vox_history.delete("nada", self.env))
        self.assertFalse(self.path.parent.exists())

    def test_legacy_entries_get_stable_ids(self) -> None:
        self.path.parent.mkdir(mode=0o700)
        self.path.write_text('{"timestamp": "2026-01-01T10:00:00-03:00", "text": "antigo"}\n')
        self.path.chmod(0o600)
        legacy_id = vox_history.list_entries(self.env)[0]["id"]
        self.assertEqual(vox_history.list_entries(self.env)[0]["id"], legacy_id)
        vox_history.append("novo", self.env)
        self.assertEqual(self.entries()[0]["id"], legacy_id)
        self.assertTrue(vox_history.delete(legacy_id, self.env))
        self.assertEqual(vox_history.last(self.env), "novo")

    def test_concurrent_appends_are_not_lost(self) -> None:
        context = multiprocessing.get_context("fork")
        workers = [
            context.Process(target=append_many, args=(self.env, worker)) for worker in range(8)
        ]
        for worker in workers:
            worker.start()
        for worker in workers:
            worker.join(30)
            self.assertEqual(worker.exitcode, 0)
        self.assertEqual(len(self.entries()), 40)

    def test_matches_ignores_case_and_accents(self) -> None:
        folded = vox_history.normalize("Uma AÇÃO rápida")
        self.assertEqual(folded, "uma acao rapida")
        self.assertTrue(vox_history.matches("acao", folded))
        self.assertTrue(vox_history.matches("RAPIDA Úma", folded))
        self.assertTrue(vox_history.matches("  ", folded))
        self.assertFalse(vox_history.matches("acao lenta", folded))

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

        code, output = run("list")
        entries = json.loads(output)
        self.assertEqual((code, [entry["text"] for entry in entries]), (0, ["café\n"]))
        self.assertEqual(run("delete", entries[0]["id"]), (0, b""))
        self.assertEqual(run("delete", entries[0]["id"])[0], 1)
        self.assertEqual(run("list"), (0, b"[]\n"))


def append_many(env: dict[str, str], worker: int) -> None:
    for index in range(5):
        vox_history.append(f"processo {worker} texto {index}", env)


if __name__ == "__main__":
    unittest.main()
