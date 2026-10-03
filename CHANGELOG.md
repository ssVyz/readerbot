# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.0.4] - 2026-10-03

### Changed

- `minimenu` reworked so each menu returns one predictable type, with type
  hints throughout and PEP 8 names. This breaks the old API:
  - `Selection_menu` is now `SelectionMenu`; `present()` returns the chosen
    index (`int`) or `None` on quit, instead of a one-hot list or an index
    depending on a `simple` flag.
  - `Checkbox_menu` is now `CheckboxMenu`; `present()` returns the indices
    of the ticked items (`list[int]`) or `None`. Pre-tick items with
    `set_checked(indices)`, which replaces `update_checked()` and its list
    of 0/1 flags.
  - `select_file()` always returns an absolute `Path` (file or folder) or
    `None`, instead of a mix of `str`, `Path` and the folder passed in.
    Picking the current folder is now a `[select this folder]` entry at the
    top of the list, next to `cd ..`, instead of the `s` key.
  - `present()` raises `ValueError` for a menu with no items.
- Running `python minimenu.py` shows a short demo of all three menus.

### Removed

- The `s` key outside the file browser: it used to make every menu return
  the string `"select"`, which callers had to special-case.
- `Work_folder`, `decode_key()` and the other key/screen helpers from the
  public API. Use `select_file()` and the menu classes.

### Fixed

- On Windows, typing a capital H, P, K or M no longer moves the cursor as if
  an arrow key was pressed, and numpad arrows now work.
- On Linux, pressing Ctrl+C in a menu no longer leaves the terminal without
  echo afterwards.
- On Windows, Ctrl+C in a menu now raises `KeyboardInterrupt` as it does on
  Linux.
- The file browser no longer crashes on folders it cannot read, such as
  `C:\System Volume Information`; it stays put and shows why.
- `select_file()` starts in the current directory at call time, not the
  one that was current when `minimenu` was imported. Relative start folders
  no longer get stuck when going up with `cd ..`.
- Empty menus fail up front with a clear `ValueError` instead of crashing on
  the first keypress or returning index `-1`.
- `CheckboxMenu` no longer changes the list passed to it, and a result
  returned by `present()` no longer changes if the menu is shown again.

## [0.0.3] - 2026-10-03

### Changed

- `uv run main.py` now runs a single chat completion against the local
  Phi-3 model: it asks for a prompt, prints the model's reply, and exits.
  This is a quick end-to-end check that the model and runtime work; it
  expects `models/Phi-3-mini-4k-instruct-q4.gguf` to be present.

## [0.0.2] - 2026-10-03

### Added

- `llama-cpp-python` dependency for running local GGUF models (tested with
  Phi-3-mini-4k-instruct Q4 on CPU). It has no prebuilt wheel on PyPI, so
  `uv sync` compiles it from source: this needs a C++ toolchain (on Windows,
  Visual Studio with the "Desktop development with C++" workload) and takes
  about 5 minutes the first time. uv caches the built wheel afterwards.
- `uv.lock` to pin the resolved dependency set.

## [0.0.1] - 2026-10-03

### Added

- `CHANGELOG.md` to track changes.
- `CLAUDE.md` with repo rules and project notes.
- `.gitignore` exceptions so `CHANGELOG.md` and `CLAUDE.md` are tracked.

### Changed

- Initialized project version to `0.0.1` in `pyproject.toml`.
