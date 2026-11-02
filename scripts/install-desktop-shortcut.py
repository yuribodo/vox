#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import shlex
import sys
from pathlib import Path

import gi

gi.require_version("Gio", "2.0")
from gi.repository import Gio  # noqa: E402


ROOT_SCHEMA = "org.cinnamon.desktop.keybindings"
CUSTOM_SCHEMA = "org.cinnamon.desktop.keybindings.custom-keybinding"
SHORTCUTS = (
    ("vox-toggle", "Vox — ditado local", "<Super>v", ""),
    ("vox-toggle-fallback", "Vox — ditado local (reserva)", "<Control><Alt>space", ""),
    ("vox-paste-last", "Vox — colar último texto", "<Super><Shift>v", " --paste-last"),
)


def shortcut_command(command: Path, arguments: str) -> str:
    # Cinnamon splits the command with shell rules.
    return shlex.quote(str(command)) + arguments


def is_managed_command(existing: str, command: Path, arguments: str) -> bool:
    # Older installs stored the path unquoted; accept them so upgrades succeed.
    return existing in (shortcut_command(command, arguments), str(command) + arguments)


def custom_settings(shortcut_id: str) -> Gio.Settings:
    path = f"/org/cinnamon/desktop/keybindings/custom-keybindings/{shortcut_id}/"
    return Gio.Settings.new_with_path(CUSTOM_SCHEMA, path)


def ensure_cinnamon_schemas() -> None:
    source = Gio.SettingsSchemaSource.get_default()
    if source is None:
        raise RuntimeError("nenhum banco de schemas do GSettings foi encontrado")
    for schema in (ROOT_SCHEMA, CUSTOM_SCHEMA):
        if source.lookup(schema, True) is None:
            raise RuntimeError(f"schema do Cinnamon ausente: {schema}")


def install(command: Path) -> None:
    root = Gio.Settings.new(ROOT_SCHEMA)
    shortcut_ids = list(root.get_strv("custom-list"))
    managed_ids = {item[0] for item in SHORTCUTS}

    for shortcut_id, _name, _binding, arguments in SHORTCUTS:
        if shortcut_id not in shortcut_ids:
            continue
        existing_command = custom_settings(shortcut_id).get_string("command")
        if existing_command and not is_managed_command(existing_command, command, arguments):
            raise RuntimeError(
                f'o identificador de atalho "{shortcut_id}" já pertence a outro comando'
            )

    for shortcut_id in shortcut_ids:
        if shortcut_id in managed_ids:
            continue
        existing_bindings = custom_settings(shortcut_id).get_strv("binding")
        for _managed_id, _managed_name, binding, _arguments in SHORTCUTS:
            if binding in existing_bindings:
                name = custom_settings(shortcut_id).get_string("name") or shortcut_id
                raise RuntimeError(f'o atalho {binding} já pertence a "{name}"')

    unmanaged_ids = [shortcut_id for shortcut_id in shortcut_ids if shortcut_id not in managed_ids]
    root.set_strv("custom-list", unmanaged_ids)
    Gio.Settings.sync()

    for shortcut_id, name, binding, arguments in SHORTCUTS:
        shortcut = custom_settings(shortcut_id)
        shortcut.set_string("name", name)
        shortcut.set_string("command", shortcut_command(command, arguments))
        shortcut.set_strv("binding", [binding])

    root.set_strv("custom-list", [*unmanaged_ids, *(item[0] for item in SHORTCUTS)])
    Gio.Settings.sync()
    print(f"Atalhos instalados: Super + V, Ctrl + Alt + Espaço e Super + Shift + V (colar último) → {command}")


def remove() -> None:
    root = Gio.Settings.new(ROOT_SCHEMA)
    managed_ids = {item[0] for item in SHORTCUTS}
    shortcut_ids = [item for item in root.get_strv("custom-list") if item not in managed_ids]
    root.set_strv("custom-list", shortcut_ids)

    for shortcut_id in managed_ids:
        shortcut = custom_settings(shortcut_id)
        shortcut.reset("name")
        shortcut.reset("command")
        shortcut.reset("binding")
    Gio.Settings.sync()
    print("Atalhos do Vox removidos")


def main() -> int:
    parser = argparse.ArgumentParser(description="Instala o atalho global do Vox no Cinnamon")
    parser.add_argument("--remove", action="store_true", help="remove o atalho instalado")
    args = parser.parse_args()

    try:
        ensure_cinnamon_schemas()
        if args.remove:
            remove()
            return 0

        project_root = Path(__file__).resolve().parent.parent
        command = project_root / "scripts" / "vox-desktop-toggle.sh"
        if os.environ.get("XDG_CURRENT_DESKTOP", "").lower().find("cinnamon") == -1:
            raise RuntimeError("esta instalação automática requer uma sessão Cinnamon")
        if not command.is_file() or not os.access(command, os.X_OK):
            raise RuntimeError(f"controlador ausente ou sem permissão de execução: {command}")
        install(command)
        return 0
    except (RuntimeError, OSError) as error:
        print(f"vox: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
