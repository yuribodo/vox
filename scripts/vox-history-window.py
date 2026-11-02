#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import re
import subprocess
import sys
import time
from pathlib import Path

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("GdkX11", "3.0")
gi.require_version("Pango", "1.0")
from gi.repository import Gdk, GdkX11, Gtk, Pango  # noqa: E402

import vox_history  # noqa: E402

APPLICATION_ID = "io.github.yuribodo.Vox.History"
PREVIEW_CHARS = 280
HINT = "Enter colar · Ctrl+C copiar · Del apagar · Esc fechar"

CSS = b"""
#vox-history { background-color: transparent; }
#vox-history-surface {
    background-color: rgba(14, 15, 18, 0.97);
    border: 1px solid rgba(255, 255, 255, 0.13);
    border-radius: 18px;
    color: rgba(235, 233, 237, 1);
}
#vox-history-surface label { color: rgba(235, 233, 237, 1); }
#vox-history-surface .dim { color: rgba(148, 146, 156, 1); }
#vox-history-surface .title { font-weight: 600; font-size: 13px; }
#vox-history-surface entry {
    background: rgba(255, 255, 255, 0.06);
    color: rgba(235, 233, 237, 1);
    border: 1px solid rgba(255, 255, 255, 0.10);
    border-radius: 10px;
    box-shadow: none;
    min-height: 34px;
}
#vox-history-surface entry:focus { border-color: rgba(158, 143, 255, 0.70); }
#vox-history-surface scrolledwindow,
#vox-history-surface list { background: transparent; border: none; }
#vox-history-surface row { border-radius: 10px; padding: 8px 10px; }
#vox-history-surface row:hover { background-color: rgba(255, 255, 255, 0.05); }
#vox-history-surface row:selected { background-color: rgba(158, 143, 255, 0.20); }
#vox-history-surface button {
    background: rgba(255, 255, 255, 0.06);
    background-image: none;
    color: rgba(235, 233, 237, 1);
    border: none;
    border-radius: 9px;
    box-shadow: none;
    text-shadow: none;
    padding: 4px 12px;
}
#vox-history-surface button:hover { background: rgba(255, 255, 255, 0.12); }
#vox-history-surface button:focus { box-shadow: inset 0 0 0 1px rgba(158, 143, 255, 0.80); }
#vox-history-surface button:disabled label { color: rgba(148, 146, 156, 0.6); }
#vox-history-surface .danger label { color: rgba(255, 148, 79, 1); }
#vox-history-confirm {
    background-color: rgba(255, 148, 79, 0.10);
    border-radius: 10px;
    padding: 6px 10px;
}
"""


def preview(text: str) -> str:
    # Pango ellipsizes to two lines; capping first keeps a 1 MiB entry cheap to lay out.
    return " ".join(text.split())[:PREVIEW_CHARS]


def relative_time(timestamp: str, now: dt.datetime) -> str:
    try:
        when = dt.datetime.fromisoformat(timestamp).astimezone(now.tzinfo)
    except (TypeError, ValueError):
        return ""
    seconds = (now - when).total_seconds()
    if 0 <= seconds < 60:
        return "agora"
    if 0 <= seconds < 3600:
        return f"há {int(seconds // 60)} min"
    clock = when.strftime("%H:%M")
    days = (now.date() - when.date()).days
    if days == 0:
        return f"hoje, {clock}"
    if days == 1:
        return f"ontem, {clock}"
    if when.year == now.year:
        return when.strftime("%d/%m, %H:%M")
    return when.strftime("%d/%m/%Y, %H:%M")


def key_action(
    key: str | None,
    *,
    control: bool,
    confirm_open: bool,
    in_search: bool,
    query: str,
    search_has_selection: bool,
) -> str | None:
    """Map a key name to a window action, or None to let GTK handle the key."""
    if key == "Escape":
        return "cancel-confirm" if confirm_open else "close"
    if confirm_open:
        return None
    if key in ("Down", "Up"):
        return key.lower()
    if control and key in ("c", "C"):
        return None if in_search and search_has_selection else "copy"
    if key in ("Delete", "KP_Delete"):
        # With a query typed, Delete edits the search text instead.
        return None if in_search and query else "delete"
    return None


def label(text: str, *classes: str) -> Gtk.Label:
    widget = Gtk.Label(label=text, xalign=0)
    for name in classes:
        widget.get_style_context().add_class(name)
    return widget


def button(text: str, tooltip: str, callback, *classes: str) -> Gtk.Button:
    widget = Gtk.Button(label=text)
    widget.set_tooltip_text(tooltip)
    widget.set_focus_on_click(False)
    widget.connect("clicked", lambda _button: callback())
    for name in classes:
        widget.get_style_context().add_class(name)
    return widget


class HistoryWindow:
    def __init__(self, application: Gtk.Application, target_window_id: str | None) -> None:
        self.target_window_id = target_window_id
        self.paste_script = Path(__file__).with_name("paste-x11.py")
        self.entries: list[dict[str, str]] = []
        # Folded text per entry id, so a keystroke never re-normalizes 1 MiB entries.
        self.folded: dict[str, str] = {}
        self.pasting = False
        self.visible: list[dict[str, str]] = []
        self.load_error: str | None = None

        self.window = Gtk.ApplicationWindow(application=application, title="Vox — histórico")
        self.window.set_name("vox-history")
        self.window.set_decorated(False)
        self.window.set_keep_above(True)
        self.window.set_type_hint(Gdk.WindowTypeHint.DIALOG)
        self.window.set_position(Gtk.WindowPosition.CENTER_ALWAYS)
        self.window.set_default_size(580, 500)
        self.window.set_app_paintable(True)
        visual = self.window.get_screen().get_rgba_visual()
        if visual is not None:
            self.window.set_visual(visual)

        css = Gtk.CssProvider()
        css.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_screen(
            self.window.get_screen(), css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        surface = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        surface.set_name("vox-history-surface")
        for side in ("start", "end", "top", "bottom"):
            getattr(surface, f"set_margin_{side}")(1)
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        content.set_border_width(14)
        surface.pack_start(content, True, True, 0)

        header = Gtk.Box(spacing=8)
        header.pack_start(label("Histórico do Vox", "title"), False, False, 0)
        self.clear_button = button("Limpar tudo", "Apagar todo o histórico", self.ask_clear, "danger")
        header.pack_end(self.clear_button, False, False, 0)
        content.pack_start(header, False, False, 0)

        self.search = Gtk.SearchEntry()
        self.search.set_placeholder_text("Buscar no histórico…")
        # "changed" instead of the debounced "search-changed", so Enter right after typing pastes a filtered row.
        self.search.connect("changed", lambda _entry: self.render())
        self.search.connect("activate", lambda _entry: self.paste())
        content.pack_start(self.search, False, False, 0)

        self.confirm = Gtk.Box(spacing=8)
        self.confirm.set_name("vox-history-confirm")
        question = label("Apagar todo o histórico? Não dá para desfazer.")
        question.set_line_wrap(True)
        self.confirm.pack_start(question, True, True, 0)
        self.confirm_cancel = Gtk.Button(label="Cancelar")
        self.confirm_cancel.connect("clicked", lambda _button: self.hide_confirm())
        confirm_ok = Gtk.Button(label="Apagar tudo")
        confirm_ok.get_style_context().add_class("danger")
        confirm_ok.connect("clicked", lambda _button: self.clear_all())
        self.confirm.pack_end(confirm_ok, False, False, 0)
        self.confirm.pack_end(self.confirm_cancel, False, False, 0)
        self.confirm.set_no_show_all(True)
        content.pack_start(self.confirm, False, False, 0)

        self.list = Gtk.ListBox()
        self.list.set_can_focus(False)
        self.list.set_activate_on_single_click(False)
        self.list.connect("row-activated", lambda _list, _row: self.paste())
        self.list.connect("row-selected", lambda _list, _row: self.update_buttons())
        self.scroller = Gtk.ScrolledWindow()
        self.scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.scroller.add(self.list)
        self.empty = label("", "dim")
        self.empty.set_xalign(0.5)
        self.empty.set_justify(Gtk.Justification.CENTER)
        self.empty.set_line_wrap(True)
        self.stack = Gtk.Stack()
        self.stack.add_named(self.scroller, "list")
        self.stack.add_named(self.empty, "empty")
        content.pack_start(self.stack, True, True, 0)

        footer = Gtk.Box(spacing=8)
        self.paste_button = button("Colar", "Colar na janela anterior (Enter)", self.paste)
        self.copy_button = button("Copiar", "Copiar para a área de transferência (Ctrl+C)", self.copy)
        self.delete_button = button("Apagar", "Apagar este texto (Delete)", self.delete, "danger")
        for widget in (self.paste_button, self.copy_button, self.delete_button):
            footer.pack_start(widget, False, False, 0)
        self.hint = label(HINT, "dim")
        self.hint.set_ellipsize(Pango.EllipsizeMode.END)
        footer.pack_end(self.hint, True, True, 0)
        self.hint.set_xalign(1)
        content.pack_start(footer, False, False, 0)

        self.window.add(surface)
        self.window.connect("key-press-event", self.on_key)
        self.window.connect("focus-out-event", self.on_focus_out)
        self.window.show_all()
        # After show_all: a GtkStack ignores a hidden child, so the empty or
        # disabled message would never show on the first render.
        self.reload()
        self.present()

    def present(self) -> None:
        # A server timestamp lets Muffin's focus-stealing prevention accept a
        # window launched from a global shortcut.
        gdk_window = self.window.get_window()
        if isinstance(gdk_window, GdkX11.X11Window):
            self.window.present_with_time(GdkX11.x11_get_server_time(gdk_window))
        else:
            self.window.present()
        self.search.grab_focus()

    def reload(self) -> None:
        try:
            self.entries = vox_history.list_entries()
            self.load_error = None
        except vox_history.HistoryDisabled:
            self.entries = []
            self.load_error = "Histórico desativado (VOX_HISTORY=0).\nNenhum texto é salvo."
        except (OSError, RuntimeError) as error:
            print(f"vox: {error}", file=sys.stderr)
            self.entries = []
            self.load_error = "Não consegui ler o histórico."
        for entry in self.entries:
            if entry["id"] not in self.folded:
                self.folded[entry["id"]] = vox_history.normalize(entry["text"])
        self.render()

    def render(self) -> None:
        selected = self.selected()
        for row in self.list.get_children():
            self.list.remove(row)
        query = self.search.get_text()
        self.visible = [e for e in self.entries if vox_history.matches(query, self.folded[e["id"]])]
        now = dt.datetime.now().astimezone()
        for entry in self.visible:
            when = label(relative_time(entry.get("timestamp", ""), now), "dim")
            text = label(preview(entry["text"]))
            text.set_line_wrap(True)
            text.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
            text.set_lines(2)
            text.set_ellipsize(Pango.EllipsizeMode.END)
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
            box.pack_start(when, False, False, 0)
            box.pack_start(text, False, False, 0)
            row = Gtk.ListBoxRow()
            row.set_can_focus(False)
            row.add(box)
            self.list.add(row)
        self.list.show_all()

        if self.visible:
            index = self.visible.index(selected) if selected in self.visible else 0
            self.list.select_row(self.list.get_row_at_index(index))
            self.stack.set_visible_child_name("list")
        else:
            if self.load_error:
                self.empty.set_text(self.load_error)
            elif self.entries:
                self.empty.set_text(f"Nada encontrado para “{query.strip()}”.")
            else:
                self.empty.set_text("Nenhum texto salvo ainda.\nDite com Super + V e ele aparece aqui.")
            self.stack.set_visible_child_name("empty")
        self.clear_button.set_sensitive(bool(self.entries))
        self.update_buttons()

    def selected(self) -> dict[str, str] | None:
        row = self.list.get_selected_row()
        if row is None or row.get_index() >= len(self.visible):
            return None
        return self.visible[row.get_index()]

    def update_buttons(self) -> None:
        has_entry = self.selected() is not None
        self.paste_button.set_sensitive(has_entry and self.target_window_id is not None)
        self.copy_button.set_sensitive(has_entry)
        self.delete_button.set_sensitive(has_entry)

    def move_selection(self, step: int) -> None:
        row = self.list.get_selected_row()
        index = (row.get_index() if row else -1) + step
        target = self.list.get_row_at_index(max(0, min(index, len(self.visible) - 1)))
        if target is not None:
            self.list.select_row(target)
            allocation = target.get_allocation()
            self.scroller.get_vadjustment().clamp_page(allocation.y, allocation.y + allocation.height)

    def flash(self, message: str) -> None:
        self.hint.set_text(message)

    def paste(self) -> None:
        entry = self.selected()
        if entry is None or self.confirm.get_visible():
            return
        if self.target_window_id is None:
            self.flash("Sem janela de destino: use Copiar")
            return
        self.pasting = True
        self.window.hide()
        while Gtk.events_pending():
            Gtk.main_iteration_do(False)
        try:
            pasted = self.run_paste(entry["text"])
        except OSError as error:
            print(f"vox: {error}", file=sys.stderr)
            pasted = False
        if pasted:
            self.window.destroy()
            return
        self.window.show()
        self.present()
        self.pasting = False
        self.flash("Não consegui colar: use Copiar")

    def run_paste(self, text: str) -> bool:
        process = subprocess.Popen(
            (sys.executable, str(self.paste_script), "--window-id", self.target_window_id),
            stdin=subprocess.PIPE,
        )
        try:
            with process.stdin:
                process.stdin.write(text.encode("utf-8"))
        except BrokenPipeError:
            process.wait()
            return False
        # Keep serving X11 events: after a Copy this process owns the clipboard,
        # and the helper asks the owner for it before pasting.
        deadline = time.monotonic() + 15
        while process.poll() is None:
            if time.monotonic() > deadline:
                # SIGTERM lets the helper restore the user's clipboard first.
                process.terminate()
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
                return False
            while Gtk.events_pending():
                Gtk.main_iteration_do(False)
            time.sleep(0.01)
        return process.returncode == 0

    def copy(self) -> None:
        entry = self.selected()
        if entry is None:
            return
        clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        clipboard.set_text(entry["text"], -1)
        # Hand the text to the clipboard manager so it outlives this window.
        clipboard.store()
        self.flash("Copiado")

    def delete(self) -> None:
        entry = self.selected()
        if entry is None:
            return
        try:
            vox_history.delete(entry["id"])
        except (OSError, RuntimeError, vox_history.HistoryDisabled) as error:
            print(f"vox: {error}", file=sys.stderr)
            self.flash("Não consegui apagar")
            return
        index = self.visible.index(entry)
        self.reload()
        row = self.list.get_row_at_index(min(index, len(self.visible) - 1))
        if row is not None:
            self.list.select_row(row)
        self.flash("Apagado")

    def ask_clear(self) -> None:
        if not self.entries:
            return
        self.confirm.set_no_show_all(False)
        self.confirm.show_all()
        self.confirm_cancel.grab_focus()

    def hide_confirm(self) -> None:
        self.confirm.hide()
        self.search.grab_focus_without_selecting()

    def clear_all(self) -> None:
        try:
            vox_history.clear()
        except (OSError, RuntimeError) as error:
            print(f"vox: {error}", file=sys.stderr)
            self.flash("Não consegui limpar")
        self.hide_confirm()
        self.reload()

    def on_focus_out(self, *_args: object) -> bool:
        # Closing keeps the paste target from going stale: reopening captures
        # the window focused now. Paste hides the window on purpose, and the
        # confirmation bar must survive a stray focus change.
        if not self.pasting and not self.confirm.get_visible():
            self.window.destroy()
        return False

    def on_key(self, _window: Gtk.Window, event: Gdk.EventKey) -> bool:
        action = key_action(
            Gdk.keyval_name(event.keyval),
            control=bool(event.state & Gdk.ModifierType.CONTROL_MASK),
            confirm_open=self.confirm.get_visible(),
            in_search=self.search.has_focus(),
            query=self.search.get_text(),
            search_has_selection=bool(self.search.get_selection_bounds()),
        )
        if action is None:
            return False
        {
            "close": self.window.destroy,
            "cancel-confirm": self.hide_confirm,
            "down": lambda: self.move_selection(1),
            "up": lambda: self.move_selection(-1),
            "copy": self.copy,
            "delete": self.delete,
        }[action]()
        return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Janela de histórico do Vox")
    parser.add_argument("--window-id", help="janela X11 que recebe o texto colado")
    args = parser.parse_args()
    target = args.window_id
    if target is not None and not re.fullmatch(r"[0-9]+", target):
        print(f"vox: invalid X11 window id: {target!r}", file=sys.stderr)
        target = None

    # A second launch only activates the running instance and brings it to the
    # front. It cannot hold a stale target: the window closes on focus-out.
    application = Gtk.Application(application_id=APPLICATION_ID)
    windows: list[HistoryWindow] = []

    def activate(_application: Gtk.Application) -> None:
        if windows and windows[0].window.get_visible():
            windows[0].present()
        elif not windows:
            windows.append(HistoryWindow(application, target))

    application.connect("activate", activate)
    return application.run(sys.argv[:1])


if __name__ == "__main__":
    raise SystemExit(main())
