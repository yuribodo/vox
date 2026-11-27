from __future__ import annotations

import importlib.util
import io
import os
import runpy
import shlex
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
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


class ShortcutReinstallTest(unittest.TestCase):
    def test_moved_checkout_requires_explicit_removal_before_reinstall(self) -> None:
        bindings = {
            "vox-toggle": ("<Super>v", []),
            "vox-toggle-fallback": ("<Control><Alt>space", []),
            "vox-paste-last": ("<Super><Shift>v", ["--paste-last"]),
            "vox-history": ("<Super><Alt>v", ["--history"]),
        }
        unrelated = {"name": "Editor", "command": "/usr/bin/editor", "binding": ["<Super>e"]}
        custom = {"my-editor": deepcopy(unrelated)}
        ids = ["my-editor"]
        root = mock.Mock()
        root.get_strv.side_effect = lambda _key: ids.copy()
        root.set_strv.side_effect = lambda _key, value: ids.__setitem__(slice(None), value)
        gio = mock.Mock()
        gio.Settings.new.return_value = root
        opened_settings = []

        def settings_for(_schema, path):
            shortcut_id = Path(path).name
            settings = mock.Mock()
            settings.get_string.side_effect = lambda key: custom.get(shortcut_id, {}).get(key, "")
            settings.get_strv.side_effect = lambda key: custom.get(shortcut_id, {}).get(key, [])

            def write(key, value):
                custom.setdefault(shortcut_id, {})[key] = value

            settings.set_string.side_effect = write
            settings.set_strv.side_effect = write
            settings.reset.side_effect = lambda key: custom.get(shortcut_id, {}).pop(key, None)
            opened_settings.append(settings)
            return settings

        gio.Settings.new_with_path.side_effect = settings_for

        def run_cli(script, *args):
            stderr = io.StringIO()
            with (
                mock.patch.dict(sys.modules, {
                    "gi": mock.Mock(),
                    "gi.repository": mock.Mock(Gio=gio),
                }),
                mock.patch.dict(os.environ, {"XDG_CURRENT_DESKTOP": "X-Cinnamon"}),
                mock.patch.object(sys, "argv", [str(script), *args]),
                redirect_stdout(io.StringIO()),
                redirect_stderr(stderr),
                self.assertRaises(SystemExit) as exit_,
            ):
                runpy.run_path(str(script), run_name="__main__")
            return exit_.exception.code, stderr.getvalue()

        def check_registration(wrapper):
            self.assertEqual(ids, ["my-editor", *bindings])
            self.assertEqual(custom["my-editor"], unrelated)
            for shortcut_id, (key, args) in bindings.items():
                with self.subTest(shortcut=shortcut_id, checkout=wrapper.parent.parent.name):
                    entry = custom[shortcut_id]
                    self.assertEqual(entry["binding"], [key])
                    self.assertEqual(shlex.split(entry["command"]), [str(wrapper), *args])

        with tempfile.TemporaryDirectory() as temp_dir:
            old_root = Path(temp_dir) / "old-vox"
            new_root = Path(temp_dir) / "tester's Vox"
            scripts = old_root / "scripts"
            scripts.mkdir(parents=True)
            source = Path(__file__).with_name("install-desktop-shortcut.py")
            script = Path(shutil.copyfile(source, scripts / source.name))
            wrapper = scripts / "vox-desktop-toggle.sh"
            wrapper.touch(mode=0o700)
            self.assertEqual(run_cli(script), (0, ""))
            check_registration(wrapper)

            old_entries = deepcopy(custom)
            old_ids = ids.copy()
            shutil.move(old_root, new_root)
            script = new_root / script.relative_to(old_root)
            wrapper = new_root / wrapper.relative_to(old_root)
            root.reset_mock()
            gio.Settings.sync.reset_mock()
            opened_settings.clear()

            exit_code, stderr = run_cli(script)
            self.assertEqual(exit_code, 1)
            self.assertIn("já pertence a outro comando", stderr)
            self.assertEqual(custom, old_entries)
            self.assertEqual(ids, old_ids)
            root.set_strv.assert_not_called()
            gio.Settings.sync.assert_not_called()
            for settings in opened_settings:
                settings.set_string.assert_not_called()
                settings.set_strv.assert_not_called()
                settings.reset.assert_not_called()

            self.assertEqual(run_cli(script, "--remove"), (0, ""))
            self.assertEqual(ids, ["my-editor"])
            self.assertEqual(custom["my-editor"], unrelated)
            self.assertTrue(all(not custom[shortcut_id] for shortcut_id in bindings))

            self.assertEqual(run_cli(script), (0, ""))
            check_registration(wrapper)


if __name__ == "__main__":
    unittest.main()
