"""Console colours, so the user's input, the agent's steps and its answers
are easy to tell apart.

Plain ANSI escape codes. They stay off when the output is not a terminal,
when the NO_COLOR environment variable is set, or when the Windows console
cannot show them. Change the colours here.
"""

import os
import sys

USER = "\033[96m"  # bright cyan: what the user types
STEP = "\033[33m"  # yellow: the agent's steps and tool calls
ANSWER = "\033[92m"  # bright green: the agent's final answer
_RESET = "\033[0m"

_enabled = False


def enable() -> None:
    """Switch colours on if the console can show them."""
    global _enabled
    if os.environ.get("NO_COLOR") or not sys.stdout.isatty():
        return
    _enabled = _windows_console_ready()


def paint(text: str, colour: str) -> str:
    """Return ``text`` in ``colour`` (unchanged while colours are off)."""
    return f"{colour}{text}{_RESET}" if _enabled else text


def read_line(prompt: str) -> str:
    """Like input(), with the prompt and the typed text in USER colour."""
    if not _enabled:
        return input(prompt)
    try:
        return input(f"{USER}{prompt}")
    finally:
        sys.stdout.write(_RESET)
        sys.stdout.flush()


def _windows_console_ready() -> bool:
    """Turn on ANSI code handling in the Windows console (Windows 10 has
    it, but off by default outside Windows Terminal)."""
    if sys.platform != "win32":
        return True
    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.windll.kernel32
    handle = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
    mode = wintypes.DWORD()
    if not kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
        return False
    enable_virtual_terminal_processing = 0x0004
    return bool(kernel32.SetConsoleMode(
        handle, mode.value | enable_virtual_terminal_processing))
