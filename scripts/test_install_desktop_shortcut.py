from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path
from unittest import mock


def load_installer():
    path = Path(__file__).with_name("install-desktop-shortcut.py")
    spec = importlib.util.spec_from_file_location("install_desktop_shortcut", path)
    module = importlib.util.module_from_spec(spec)
    # The pure helpers under test do not need GSettings.
    with mock.patch.dict(sys.modules, {"gi": mock.MagicMock(), "gi.repository": mock.MagicMock()}):
        spec.loader.exec_module(module)
    return module


installer = load_installer()


class ShortcutCommandTest(unittest.TestCase):
    def test_quotes_paths_for_cinnamon(self) -> None:
        self.assertEqual(installer.shortcut_command(Path("/opt/vox/t.sh"), ""), "/opt/vox/t.sh")
        self.assertEqual(
            installer.shortcut_command(Path("/home/joão/my vox/t.sh"), " --paste-last"),
            "'/home/joão/my vox/t.sh' --paste-last",
        )

    def test_accepts_current_and_legacy_unquoted_commands(self) -> None:
        command = Path("/home/joão/vox/t.sh")
        self.assertTrue(installer.is_managed_command("'/home/joão/vox/t.sh'", command, ""))
        self.assertTrue(installer.is_managed_command("/home/joão/vox/t.sh", command, ""))
        self.assertTrue(
            installer.is_managed_command("/home/joão/vox/t.sh --paste-last", command, " --paste-last")
        )

    def test_rejects_other_commands(self) -> None:
        command = Path("/home/joão/vox/t.sh")
        self.assertFalse(installer.is_managed_command("/usr/bin/other", command, ""))
        self.assertFalse(installer.is_managed_command("/home/joão/vox/t.sh", command, " --paste-last"))


if __name__ == "__main__":
    unittest.main()
