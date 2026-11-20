"""Serve only the static export under its production /vox base path, on loopback."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory


def main():
    export = Path(__file__).resolve().parents[1] / "out"
    if not (export / "index.html").is_file():
        raise SystemExit("Missing static export: build with NEXT_PUBLIC_BASE_PATH=/vox")
    with TemporaryDirectory(prefix="vox-smoke-") as root:
        (Path(root) / "vox").symlink_to(export, target_is_directory=True)
        handler = partial(SimpleHTTPRequestHandler, directory=root)
        with ThreadingHTTPServer(("127.0.0.1", 4173), handler) as server:
            server.serve_forever()


if __name__ == "__main__":
    main()
