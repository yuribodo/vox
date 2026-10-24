from __future__ import annotations

import datetime as dt
import importlib.util
import sys
import unittest
from pathlib import Path
from unittest import mock


def load_window():
    path = Path(__file__).with_name("vox-history-window.py")
    spec = importlib.util.spec_from_file_location("vox_history_window", path)
    module = importlib.util.module_from_spec(spec)
    # The pure helpers under test do not need GTK.
    with mock.patch.dict(sys.modules, {"gi": mock.MagicMock(), "gi.repository": mock.MagicMock()}):
        spec.loader.exec_module(module)
    return module


window = load_window()
BRT = dt.timezone(dt.timedelta(hours=-3))
NOW = dt.datetime(2026, 10, 23, 15, 30, 0, tzinfo=BRT)


class RelativeTimeTest(unittest.TestCase):
    def test_formats(self) -> None:
        cases = {
            "2026-10-23T15:29:31-03:00": "agora",
            "2026-10-23T15:05:00-03:00": "há 25 min",
            "2026-10-23T09:07:00-03:00": "hoje, 09:07",
            "2026-10-22T23:50:00-03:00": "ontem, 23:50",
            "2026-03-01T08:00:00-03:00": "01/03, 08:00",
            "2025-12-31T22:00:00-03:00": "31/12/2025, 22:00",
            # Other offsets are shown in local time.
            "2026-10-23T14:00:00+00:00": "hoje, 11:00",
            "garbage": "",
        }
        for timestamp, expected in cases.items():
            with self.subTest(timestamp=timestamp):
                self.assertEqual(window.relative_time(timestamp, NOW), expected)

    def test_future_timestamp_falls_back_to_clock(self) -> None:
        self.assertEqual(window.relative_time("2026-10-23T16:00:00-03:00", NOW), "hoje, 16:00")


def action(key, *, control=False, confirm_open=False, in_search=True, query="", selection=False):
    return window.key_action(
        key,
        control=control,
        confirm_open=confirm_open,
        in_search=in_search,
        query=query,
        search_has_selection=selection,
    )


class KeyActionTest(unittest.TestCase):
    def test_escape_cancels_confirm_before_closing(self) -> None:
        self.assertEqual(action("Escape"), "close")
        self.assertEqual(action("Escape", confirm_open=True), "cancel-confirm")

    def test_confirm_bar_leaves_other_keys_to_gtk(self) -> None:
        for key in ("Return", "Delete", "Down", "c"):
            with self.subTest(key=key):
                self.assertIsNone(action(key, control=key == "c", confirm_open=True))

    def test_navigation(self) -> None:
        self.assertEqual(action("Down"), "down")
        self.assertEqual(action("Up", query="abc"), "up")
        self.assertIsNone(action("a"))
        self.assertIsNone(action(None))

    def test_delete_edits_a_typed_query(self) -> None:
        self.assertEqual(action("Delete"), "delete")
        self.assertEqual(action("KP_Delete"), "delete")
        self.assertIsNone(action("Delete", query="aç"))
        self.assertEqual(action("Delete", query="aç", in_search=False), "delete")

    def test_copy_keeps_search_box_selection_copy(self) -> None:
        self.assertEqual(action("c", control=True), "copy")
        self.assertEqual(action("C", control=True), "copy")
        self.assertIsNone(action("c", control=True, selection=True))
        self.assertEqual(action("c", control=True, selection=True, in_search=False), "copy")
        self.assertIsNone(action("c"))


class PasteTest(unittest.TestCase):
    def make(self, *, target: str | None = "42", pasted: bool = True):
        history = object.__new__(window.HistoryWindow)
        history.target_window_id = target
        history.pasting = False
        history.window = mock.MagicMock()
        history.confirm = mock.MagicMock()
        history.confirm.get_visible.return_value = False
        history.selected = mock.MagicMock(return_value={"id": "a", "text": "olá"})
        history.flash = mock.MagicMock()
        history.present = mock.MagicMock()
        history.run_paste = mock.MagicMock(return_value=pasted)
        gtk = mock.patch.object(window, "Gtk")
        gtk.start().events_pending.return_value = False
        self.addCleanup(gtk.stop)
        return history

    def test_success_closes_the_window(self) -> None:
        history = self.make()
        history.paste()
        history.run_paste.assert_called_once_with("olá")
        history.window.hide.assert_called_once()
        history.window.destroy.assert_called_once()
        history.flash.assert_not_called()

    def test_failure_brings_the_window_back(self) -> None:
        history = self.make(pasted=False)
        history.paste()
        history.window.destroy.assert_not_called()
        history.window.show.assert_called_once()
        history.flash.assert_called_once_with("Não consegui colar: use Copiar")
        self.assertFalse(history.pasting)

    def test_helper_os_error_counts_as_failure(self) -> None:
        history = self.make()
        history.run_paste.side_effect = OSError("no python")
        with mock.patch("sys.stderr"):
            history.paste()
        history.window.destroy.assert_not_called()
        history.flash.assert_called_once()

    def test_no_target_never_pastes(self) -> None:
        history = self.make(target=None)
        history.paste()
        history.run_paste.assert_not_called()
        history.window.hide.assert_not_called()
        history.flash.assert_called_once_with("Sem janela de destino: use Copiar")

    def test_confirm_open_blocks_paste(self) -> None:
        history = self.make()
        history.confirm.get_visible.return_value = True
        history.paste()
        history.run_paste.assert_not_called()

    def test_focus_out_closes_except_while_pasting_or_confirming(self) -> None:
        history = self.make()
        history.on_focus_out()
        history.window.destroy.assert_called_once()

        for pasting, confirming in ((True, False), (False, True)):
            history = self.make()
            history.pasting = pasting
            history.confirm.get_visible.return_value = confirming
            history.on_focus_out()
            history.window.destroy.assert_not_called()


class PreviewTest(unittest.TestCase):
    def test_collapses_whitespace_and_caps_length(self) -> None:
        self.assertEqual(window.preview("  linha um\n\n\tlinha  dois \n"), "linha um linha dois")
        self.assertEqual(len(window.preview("palavra " * 10000)), window.PREVIEW_CHARS)


if __name__ == "__main__":
    unittest.main()
