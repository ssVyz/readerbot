# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.0.8] - 2026-10-05

### Changed

- Choosing the work folder at start-up now lists only folders, not files,
  so it is easier to find your way around. Pick a folder with
  "[select this folder]". `minimenu.select_file` has a new
  `folders_only` option for this; without it, it works as before.

## [0.0.7] - 2026-10-05

### Added

- New tool `outline_md`: shows a `.md` file's headings, each with the line
  range and size (in characters) of its section. The agent now gets a map
  of a long manuscript first and reads only the sections it needs, instead
  of working through the file from line 1 and using up its steps and
  context. For very long outlines it leaves out the deepest heading levels
  (at most 50 headings, set in `config.py`).

### Changed

- The system prompt and the `read_md` description now tell the agent to
  call `outline_md` before reading and not to read a long file from the
  start. The `read_md` example no longer suggests reading lines 1-40, which
  models tended to copy.
- `convert_docx` now points the agent to `outline_md` when the `.md` file
  already exists. Before, it only said to read the file, so after the first
  session the agent had no headings to go by.
- Context doubled to 32768 tokens, so a question has room for about twice as
  many reads before the conversation is full.
- At most 8000 characters per `create_md`/`append_md`/`edit_md` call (was
  20000). One model reply is capped at 2048 tokens, so longer text could
  never arrive in a single call anyway.

## [0.0.6] - 2026-10-04

### Added

- Colours in the console, so the conversation is easy to follow: what you
  type is cyan, the agent's steps and tool calls are yellow, and its final
  answer is green. Colours switch off when the output is not a terminal or
  when the `NO_COLOR` environment variable is set. Change them in `ui.py`.

## [0.0.5] - 2026-10-04

### Added

- readerbot is now an agent you talk to. `uv run main.py` asks which model
  to load (any `.gguf` in `models/`) and which folder to work in, then
  answers questions about the documents there in a REPL. Commands: `/help`,
  `/tools`, `/prompt` (the system prompt as the model gets it), `/reset`,
  `/quit`; Ctrl+C stops a running answer.
- The agent's tools, all in `tools.py`:
  - `list_files`: the `.docx` and `.md` files in the folder.
  - `convert_docx`: turns a `.docx` into a `.md` of the same name with
    pandoc, and lists its headings. It never overwrites an existing `.md`
    and says when that file is older than the `.docx`.
  - `read_md`: a numbered line range, capped at about 6000 characters.
  - `search_md`: the lines that contain all of the given words, in any
    order (not case-sensitive), with snippets.
  - `create_md`: a new `.md` file; it never overwrites.
  - `append_md`: adds text to the end of a `.md` file.
  - `edit_md`: replaces one exact passage in a `.md` file.
- Every file access is vetted before it happens. The agent only sees
  `.docx` and `.md` files directly in the chosen folder, can only write
  `.md` files, and is refused paths, links, reserved Windows names and
  anything outside the folder. Written files may not load images from the
  web, which a Markdown preview could use to leak document text.
- A tripwire (`guard.py`) stops the program if anything tries to use the
  network or start a program other than pandoc.
- The model's replies are forced into a fixed JSON format, so it can only
  call the tools above, with well-formed arguments. This works with any
  model that has a chat template. Tested with Qwen3-4B and Phi-3-mini.
  Phi-3's template has no system role, so the instructions are put in
  front of the first question instead.

### Changed

- `main.py` no longer runs a one-shot test completion; it starts the REPL.

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
