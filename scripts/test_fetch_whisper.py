"""Network-free tests of the Whisper setup preflight."""

import pathlib
import shutil
import subprocess
import tempfile
import unittest


SCRIPT = pathlib.Path(__file__).with_name("fetch-whisper.sh")


class FetchWhisperPreflightTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = pathlib.Path(directory.name)
        self.cache = self.root / ".local"
        self.tools = self.root / "bin"
        self.tools.mkdir()
        self.log = self.root / "commands"
        self.script = self.root / "scripts" / SCRIPT.name
        self.script.parent.mkdir()
        self.bash = shutil.which("bash")
        source = SCRIPT.read_text()
        for name in ("gcc-15", "g++-15"):
            # Redirect only the two pinned compiler paths in the script copy.
            fixture_path = self.tools / name
            source = source.replace(f'"/usr/bin/{name}"', f'"{fixture_path}"')
            self.stub(fixture_path, "exit 79")
        self.script.write_text(source)
        for name in ("dirname", "mkdir"):
            (self.tools / name).symlink_to(shutil.which(name))
        for name in ("curl", "git", "nproc", "sha256sum", "tar"):
            self.stub(self.tools / name, f'echo {name} >> "$COMMAND_LOG"\nexit 79')

    def stub(self, entry, body):
        entry.parent.mkdir(parents=True, exist_ok=True)
        entry.write_text(f"#!{self.bash}\n{body}\n")
        entry.chmod(0o755)

    def run_script(self, **settings):
        return subprocess.run(
            [self.bash, self.script],
            env={"PATH": str(self.tools), "COMMAND_LOG": str(self.log), **settings},
            capture_output=True,
            text=True,
            timeout=5,
        )

    def prime_bootstrap(self, cmake_body):
        archive = self.cache / "downloads/cmake-4.1.0-linux-x86_64.tar.gz"
        archive.parent.mkdir(parents=True)
        archive.touch()
        (self.cache / "src/whisper.cpp-v1.9.1/.git").mkdir(parents=True)
        self.stub(self.cache / "tools/cmake-4.1.0-linux-x86_64/bin/cmake", cmake_body)
        self.stub(self.tools / "sha256sum", 'echo sha256sum >> "$COMMAND_LOG"')
        self.stub(
            self.tools / "git",
            'echo "git:$3" >> "$COMMAND_LOG"\n'
            'case "$3" in\n'
            'rev-parse) echo f049fff95a089aa9969deb009cdd4892b3e74916;;\n'
            'status) exit 0;;\n'
            '*) exit 79;;\n'
            'esac',
        )

    def test_missing_tools_or_fixed_compilers_stop_before_download(self):
        for name in ("git", "sha256sum", "nproc", "curl", "tar", "gcc-15", "g++-15"):
            with self.subTest(name=name):
                entry = self.tools / name
                original = entry.read_bytes()
                entry.unlink()
                result = self.run_script()
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertIn(name, result.stderr)
                self.assertIn("stopped before downloading anything", result.stderr)
                self.assertFalse(self.log.exists())
                self.assertFalse(self.cache.exists())
                entry.write_bytes(original)
                entry.chmod(0o755)

    def test_valid_preflight_reaches_first_bootstrap_download(self):
        result = self.run_script()
        self.assertEqual(result.returncode, 79, result.stderr)
        self.assertEqual(self.log.read_text().splitlines(), ["curl"])

    def test_configuration_failure_stops_before_model_downloads(self):
        self.prime_bootstrap(
            'echo "cmake:$1:$CMAKE_GENERATOR:$CUDACXX" >> "$COMMAND_LOG"\nexit 42'
        )
        nvcc = str(self.root / "custom-cuda/bin/nvcc")
        result = self.run_script(CMAKE_GENERATOR="Ninja", CUDACXX=nvcc)
        self.assertEqual(result.returncode, 42, result.stderr)
        self.assertIn("configuration failed before model downloads", result.stderr)
        self.assertEqual(
            self.log.read_text().splitlines(),
            ["sha256sum", "git:rev-parse", "git:status", f"cmake:-S:Ninja:{nvcc}"],
        )

    def test_cached_run_needs_neither_curl_nor_tar_and_verifies_models(self):
        self.prime_bootstrap('echo "cmake:$1" >> "$COMMAND_LOG"')
        for relative in (
            "models/whisper-large-v3-turbo-q8_0/ggml-large-v3-turbo-q8_0.bin",
            "models/whisper-vad/ggml-silero-v6.2.0.bin",
        ):
            model = self.cache / relative
            model.parent.mkdir(parents=True)
            model.touch()
        (self.tools / "curl").unlink()
        (self.tools / "tar").unlink()
        self.stub(self.tools / "nproc", "echo 1")
        result = self.run_script()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            self.log.read_text().splitlines(),
            ["sha256sum", "git:rev-parse", "git:status", "cmake:-S",
             "sha256sum", "sha256sum", "cmake:--build"],
        )


if __name__ == "__main__":
    unittest.main()
