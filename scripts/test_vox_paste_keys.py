from __future__ import annotations

import os
import unittest
from unittest import mock

import vox_paste_keys
from vox_paste_keys import parse_wm_class, paste_key_for_classes, prepare_paste, terminal_safe_text


class PasteKeyTest(unittest.TestCase):
    def test_parse_wm_class(self) -> None:
        output = 'WM_CLASS(STRING) = "org.gnome.Terminal", "Gnome-terminal"\n'
        self.assertEqual(parse_wm_class(output), ("org.gnome.Terminal", "Gnome-terminal"))

    def test_parse_wm_class_without_property(self) -> None:
        self.assertEqual(parse_wm_class("WM_CLASS:  not found.\n"), ())

    def test_terminals_use_ctrl_shift_v(self) -> None:
        for classes in [
            ("kitty", "kitty"),
            ("Alacritty", "Alacritty"),
            ("org.gnome.Terminal", "Gnome-terminal"),
            ("konsole", "konsole"),
        ]:
            with self.subTest(classes=classes):
                self.assertEqual(paste_key_for_classes(classes), "ctrl+shift+v")

    def test_other_windows_use_ctrl_v(self) -> None:
        self.assertEqual(paste_key_for_classes(("Navigator", "firefox")), "ctrl+v")
        self.assertEqual(paste_key_for_classes(("orca", "Orca")), "ctrl+v")
        self.assertEqual(paste_key_for_classes(()), "ctrl+v")

    def test_override(self) -> None:
        self.assertEqual(paste_key_for_classes(("kitty",), "shift+Insert"), "shift+Insert")

    def test_override_rejects_invalid_keys(self) -> None:
        with self.assertRaises(ValueError):
            paste_key_for_classes((), "ctrl+v; rm")


class TerminalSafeTextTest(unittest.TestCase):
    def test_newlines_become_spaces(self) -> None:
        self.assertEqual(terminal_safe_text("first line\nsecond\r\nthird\n"), "first line second third")

    def test_escape_sequences_cannot_end_bracketed_paste(self) -> None:
        text = "safe\x1b[201~rm -rf ~\n"
        result = terminal_safe_text(text)
        self.assertNotIn("\x1b", result)
        self.assertNotIn("\n", result)

    def test_control_characters_and_unicode_separators(self) -> None:
        self.assertEqual(terminal_safe_text("a\tb\x7fc\x85d\u2028e\u2029f"), "a b c d e f")

    def test_preserves_unicode_text(self) -> None:
        self.assertEqual(terminal_safe_text("olá café 🚀"), "olá café 🚀")


class PreparePasteTest(unittest.TestCase):
    def prepare(self, classes: tuple[str, ...], text: str, env: dict[str, str] | None = None) -> tuple[str, str]:
        with mock.patch.object(vox_paste_keys, "window_classes", return_value=classes), mock.patch.dict(
            os.environ, env or {}, clear=False
        ):
            if env is None:
                os.environ.pop("VOX_PASTE_KEY", None)
            return prepare_paste("123", text)

    def test_terminal_gets_shortcut_and_flattened_text(self) -> None:
        self.assertEqual(self.prepare(("kitty", "kitty"), "a\nb"), ("ctrl+shift+v", "a b"))

    def test_regular_window_keeps_exact_multiline_text(self) -> None:
        self.assertEqual(self.prepare(("Navigator", "firefox"), "a\nb"), ("ctrl+v", "a\nb"))

    def test_override_is_treated_as_terminal(self) -> None:
        self.assertEqual(
            self.prepare(("unknown",), "a\nb", {"VOX_PASTE_KEY": "shift+Insert"}),
            ("shift+Insert", "a b"),
        )


if __name__ == "__main__":
    unittest.main()
