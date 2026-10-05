"""Minimenu: tiny keyboard-driven menus for the terminal.

Copy this file into a project. It only uses the standard library and works
on Windows (msvcrt) and on Linux and macOS (termios).

- ``SelectionMenu(items).present()`` returns the index of the chosen item.
- ``CheckboxMenu(items).present()`` returns the indices of the ticked items.
- ``select_file()`` browses the file system and returns the chosen ``Path``;
  ``select_file(folders_only=True)`` lists folders only.

All three return ``None`` when the user quits with ``q``.

Keys: up/down move the cursor, Enter confirms, q quits. In a checkbox menu,
right ticks the current item and left unticks it. In a selection menu,
left/right move the cursor like up/down.
"""

import subprocess
import sys
from collections.abc import Iterable
from pathlib import Path
from typing import Literal

__all__ = ["CheckboxMenu", "Menu", "SelectionMenu", "select_file"]

Key = Literal["up", "down", "left", "right", "enter", "quit"]


# --- Menus ---

class Menu:
    """Item list, drawing and key loop shared by the menus. Subclass it."""

    def __init__(
        self,
        items: Iterable[str] = (),
        header: str | None = None,
        footer: str | None = None,
        padding: int = 0,
    ) -> None:
        self.header = header
        self.footer = footer
        self.padding = padding
        self._items: list[str] = []
        self._cursor = 0
        self.load_list(items)

    def add_item(self, item: str) -> None:
        """Append one item to the end of the menu."""
        if not isinstance(item, str):
            raise TypeError(
                f"menu items must be str, not {type(item).__name__}"
            )
        self._items.append(item)

    def load_list(self, items: Iterable[str]) -> None:
        """Replace all items. The menu keeps a copy, not your list."""
        self._items = []
        for item in items:
            self.add_item(item)

    def _run(self) -> bool:
        """Show the menu until Enter (True) or q (False) is pressed."""
        if not self._items:
            raise ValueError("menu has no items to show")
        self._cursor = min(self._cursor, len(self._items) - 1)
        while True:
            self._draw()
            key = _read_key()
            if key == "enter":
                return True
            if key == "quit":
                return False
            if key is not None:
                self._on_key(key)

    def _on_key(self, key: Key) -> None:
        """Move the cursor. Subclasses decide what left/right do."""
        if key == "up":
            self._cursor = max(self._cursor - 1, 0)
        elif key == "down":
            self._cursor = min(self._cursor + 1, len(self._items) - 1)

    def _label(self, index: int) -> str:
        """Return the text shown for the item at ``index``."""
        return self._items[index]

    def _draw(self) -> None:
        _clear_screen()
        print()
        if self.header is not None:
            print(self.header)
            print()
        for index in range(len(self._items)):
            self._print_padding()
            arrow = " --> " if index == self._cursor else "     "
            print(f"{arrow} {self._label(index)}")
        print()
        self._print_padding()
        if self.footer is not None:
            print(self.footer)
            print()

    def _print_padding(self) -> None:
        for _ in range(self.padding):
            print()


class SelectionMenu(Menu):
    """Pick one item."""

    def present(self) -> int | None:
        """Show the menu and return the chosen index, or None on quit.

        Raises ValueError if the menu has no items.
        """
        return self._cursor if self._run() else None

    def _on_key(self, key: Key) -> None:
        if key == "left":
            key = "up"
        elif key == "right":
            key = "down"
        super()._on_key(key)


class CheckboxMenu(Menu):
    """Tick any number of items. Right ticks an item, left unticks it."""

    _checked: list[bool]

    def add_item(self, item: str) -> None:
        super().add_item(item)
        self._checked.append(False)

    def load_list(self, items: Iterable[str]) -> None:
        """Replace all items and untick everything."""
        self._checked = []
        super().load_list(items)

    def set_checked(self, indices: Iterable[int]) -> None:
        """Tick exactly the items at ``indices`` and untick the rest."""
        checked = [False] * len(self._items)
        for index in indices:
            if not 0 <= index < len(self._items):
                raise IndexError(f"no menu item at index {index}")
            checked[index] = True
        self._checked = checked

    def present(self) -> list[int] | None:
        """Show the menu and return the ticked indices, or None on quit.

        Raises ValueError if the menu has no items.
        """
        if not self._run():
            return None
        return [index for index, ticked in enumerate(self._checked) if ticked]

    def _on_key(self, key: Key) -> None:
        if key == "right":
            self._checked[self._cursor] = True
        elif key == "left":
            self._checked[self._cursor] = False
        else:
            super()._on_key(key)

    def _label(self, index: int) -> str:
        box = "[X]" if self._checked[index] else "[ ]"
        return f" {box}  {self._items[index]}"


# --- File browser ---

_SELECT_FOLDER = "[select this folder]"
_PARENT_FOLDER = "cd .."
_BROWSER_FOOTER = (
    "Arrow keys move, Enter opens a folder or picks a file, q quits."
)
_FOLDER_BROWSER_FOOTER = "Arrow keys move, Enter opens a folder, q quits."


def select_file(
    start_folder: str | Path | None = None, *, folders_only: bool = False
) -> Path | None:
    """Browse the file system and return the chosen file or folder.

    Enter on a folder opens it, Enter on a file picks it, and the
    "[select this folder]" entry picks the folder being shown. With
    ``folders_only``, files are not listed, so only a folder can be picked.
    Starts in ``start_folder`` if it is a readable folder, otherwise in the
    current working directory.

    Returns an absolute ``Path``, or ``None`` if the user quits.
    """
    if start_folder is None:
        folder = Path.cwd()
    else:
        folder = Path(start_folder).resolve()
    try:
        entries = _list_folder(folder, folders_only)
    except OSError:
        folder = Path.cwd()
        entries = _list_folder(folder, folders_only)

    if folders_only:
        prompt, footer = "Select a folder", _FOLDER_BROWSER_FOOTER
    else:
        prompt, footer = "Select a file or folder", _BROWSER_FOOTER
    notice = ""
    while True:
        header = f"Current folder: {folder}\n{prompt}"
        if notice:
            header += f"\n\n{notice}"
        labels = [_SELECT_FOLDER, _PARENT_FOLDER]
        labels += [entry.name for entry in entries]
        choice = SelectionMenu(labels, header, footer).present()

        if choice is None:
            return None
        if choice == 0:
            return folder
        target = folder.parent if choice == 1 else entries[choice - 2]
        if not folders_only and not target.is_dir():
            return target
        try:
            entries = _list_folder(target, folders_only)
        except OSError as error:
            notice = f"Cannot open {target}: {error.strerror}"
        else:
            folder, notice = target, ""


def _list_folder(folder: Path, folders_only: bool) -> list[Path]:
    """Return the entries of ``folder``; raises OSError if it is unreadable."""
    entries = list(folder.iterdir())
    if folders_only:
        entries = [entry for entry in entries if entry.is_dir()]
    return entries


# --- Keyboard and screen ---

if sys.platform == "win32":
    import msvcrt

    _ARROWS: dict[bytes, Key] = {
        b"H": "up", b"P": "down", b"K": "left", b"M": "right",
    }
    _KEYS: dict[bytes, Key] = {b"\r": "enter", b"q": "quit"}

    def _read_key() -> Key | None:
        """Wait for a keypress and return its name, or None if unmapped."""
        while msvcrt.kbhit():  # drop keys pressed during the last redraw
            msvcrt.getch()
        key = msvcrt.getch()
        if key in (b"\x00", b"\xe0"):  # prefix byte of arrow/function keys
            return _ARROWS.get(msvcrt.getch())
        if key == b"\x03":
            raise KeyboardInterrupt
        return _KEYS.get(key)

else:
    import termios
    import tty

    _ARROWS: dict[str, Key] = {
        "\x1b[A": "up", "\x1b[B": "down", "\x1b[C": "right", "\x1b[D": "left",
    }
    _KEYS: dict[str, Key] = {"\n": "enter", "\r": "enter", "q": "quit"}

    def _read_key() -> Key | None:
        """Wait for a keypress and return its name, or None if unmapped."""
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setcbreak(fd)
            # drop keys pressed during the last redraw
            termios.tcflush(fd, termios.TCIFLUSH)
            key = sys.stdin.read(1)
            if key == "\x1b":
                return _ARROWS.get(key + sys.stdin.read(2))
            return _KEYS.get(key)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def _clear_screen() -> None:
    command = "cls" if sys.platform == "win32" else "clear"
    subprocess.run(command, shell=True, check=False)


# --- Demo: python minimenu.py ---

if __name__ == "__main__":
    fruit = ["apple", "banana", "cherry"]
    footer = "Arrow keys move, Enter confirms, q quits."
    choice = SelectionMenu(fruit, "Pick a fruit", footer).present()
    ticked = CheckboxMenu(fruit, "Tick some fruit", footer).present()
    path = select_file()
    print(f"SelectionMenu: {choice}")
    print(f"CheckboxMenu:  {ticked}")
    print(f"select_file:   {path}")
