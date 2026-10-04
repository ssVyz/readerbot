"""Tripwire against network access and stray programs.

``install()`` adds a Python audit hook (it cannot be removed again) that
raises ``GuardError`` whenever anything in this process tries to use the
network or to start a program other than pandoc. It backs up the "Local
only" rules in design_rules.md for our own code and our dependencies.

It is not a sandbox: model output is never executed, so the model never
gets to run Python in the first place.
"""

import subprocess
import sys
from typing import Any

_NETWORK_EVENTS = frozenset({
    "socket.bind",
    "socket.connect",
    "socket.getaddrinfo",
    "socket.gethostbyaddr",
    "socket.gethostbyname",
    "socket.getnameinfo",
    "socket.sendmsg",
    "socket.sendto",
    "urllib.Request",
    "webbrowser.open",
})
_PROGRAM_EVENTS = frozenset({
    "os.exec",
    "os.posix_spawn",
    "os.spawn",
    "os.startfile",
    "os.system",
})


class GuardError(RuntimeError):
    """Something tried to reach the network or start a program."""


def install(allowed_program: str | None) -> None:
    """Block network use and every program except ``allowed_program``.

    ``allowed_program`` must be the exact path later passed to subprocess
    (pandoc). ``None`` blocks all programs.
    """

    def hook(event: str, args: tuple[Any, ...]) -> None:
        if event in _NETWORK_EVENTS:
            raise GuardError(f"blocked network access ({event})")
        if event in _PROGRAM_EVENTS:
            raise GuardError(f"blocked program start ({event})")
        if event == "subprocess.Popen":
            executable, command = args[0], args[1]
            if not _starts(allowed_program, executable, command):
                raise GuardError(
                    f"blocked program start ({executable or command})"
                )

    sys.addaudithook(hook)


def _starts(allowed: str | None, executable: object, command: object) -> bool:
    """Whether a subprocess.Popen call would start the allowed program."""
    if allowed is None:
        return False
    if executable is not None:  # set explicitly, or cmd.exe for shell=True
        return str(executable) == allowed
    if isinstance(command, (list, tuple)):
        return bool(command) and str(command[0]) == allowed
    # On Windows the arguments are already joined into one command line.
    quoted = subprocess.list2cmdline([allowed])
    return command == quoted or str(command).startswith(quoted + " ")
