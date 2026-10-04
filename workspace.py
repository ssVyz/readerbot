"""The file boundary: the one folder the agent works in.

The user picks the folder at start-up. Every tool gets its file paths from
``Workspace.vet``, which runs before anything is read or written: a name
passes only if it is a bare file name with an allowed extension that
resolves to a regular file directly inside that folder. pandoc, the only
external program, is also run from here, on vetted paths only.
"""

import os
import subprocess
import sys
from pathlib import Path

import config

VISIBLE = (".docx", ".md")  # the only files the agent can see
WRITABLE = (".md",)  # the only files it can create or change
MAX_NAME_CHARS = 120
_FORBIDDEN_CHARS = frozenset('<>:"/\\|?*') | {chr(code) for code in range(32)}


class RefusedError(Exception):
    """A request was refused. The message is shown to the model and user."""


class Workspace:
    """The folder the user picked, and the only way to reach files in it."""

    def __init__(self, folder: Path, pandoc: str | None) -> None:
        self.folder = folder.resolve(strict=True)
        self.pandoc = pandoc  # absolute path to pandoc, or None if missing

    def vet(
        self, name: object, allowed: tuple[str, ...], *, exists: bool | None
    ) -> Path:
        """Return the path for file ``name``, or raise RefusedError.

        ``allowed`` lists the permitted extensions. ``exists`` says whether
        the file must already exist (True), must not exist yet (False), or
        may be either (None).
        """
        if not isinstance(name, str) or not name:
            raise RefusedError("a file name must be a non-empty string")
        if len(name) > MAX_NAME_CHARS:
            raise RefusedError(
                f"file names are limited to {MAX_NAME_CHARS} "
                "characters"
            )
        if (any(char in _FORBIDDEN_CHARS for char in name)
                or name != name.strip() or name.endswith(".")):
            raise RefusedError(
                f"{name!r} is not a plain file name; use a name "
                "from list_files, without any folder"
            )
        if sys.platform == "win32" and os.path.isreserved(name):
            raise RefusedError(f"{name!r} is a reserved name on Windows")
        if Path(name).suffix.lower() not in allowed:
            raise RefusedError(
                f"{name!r}: only {' and '.join(allowed)} files "
                "are allowed here"
            )

        path = self.folder / name
        if path.resolve().parent != self.folder:
            raise RefusedError(f"{name!r} is outside the folder")
        if path.is_symlink() or path.is_junction():
            raise RefusedError(f"{name!r} is a link; links are not followed")
        if exists and not path.is_file():
            raise RefusedError(
                f"{name!r} does not exist; call list_files to "
                "see the files"
            )
        if exists is False and path.exists():
            raise RefusedError(f"{name!r} already exists")
        return path

    def files(self) -> list[Path]:
        """The files the agent may see (each one passes vet()), by name."""
        found = []
        for entry in self.folder.iterdir():
            try:
                found.append(self.vet(entry.name, VISIBLE, exists=True))
            except RefusedError:
                continue
        return sorted(found, key=lambda path: path.name.lower())

    def convert_docx(self, source: Path, target: Path) -> None:
        """Convert a vetted .docx into a vetted new .md file with pandoc."""
        if self.pandoc is None:
            raise RefusedError(
                "pandoc is not installed, so .docx files cannot "
                "be converted"
            )
        # Fixed arguments only. The paths are absolute, so a file name that
        # starts with "-" cannot be mistaken for an option.
        command = [
            self.pandoc,
            "--sandbox",
            "--from=docx",
            "--to=markdown",
            "--wrap=none",
            "--track-changes=accept",
            f"--output={target}",
            str(source),
        ]
        try:
            subprocess.run(
                command,
                check=True,
                capture_output=True,
                timeout=config.PANDOC_TIMEOUT_SECONDS,
            )
        except subprocess.CalledProcessError as error:
            message = error.stderr.decode("utf-8", "replace").strip()
            raise RefusedError(
                "pandoc could not convert the file: "
                f"{message[:500]}"
            ) from None
        except subprocess.TimeoutExpired:
            raise RefusedError(
                "pandoc took too long and was stopped"
            ) from None
