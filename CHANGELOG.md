# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.0.12] - 2026-10-06

### Added

- New tool `summarize_section`: the agent names a `.md` file and a line
  range, and gets back a 2-4 sentence summary of those lines. The summary is
  written by a helper: the same model in a new conversation that sees only
  these lines, not the agent's conversation. So the agent can learn what a
  long section says while its own context grows by only the summary, which
  leaves room for many more steps on long manuscripts. It takes up to 24000
  characters per call (four times a `read_md` call; `SUMMARY_MAX_CHARS` in
  `config.py`) and, like `read_md`, says where it stopped if the range is
  longer. A summary of a 6000-8000 character section takes about 10 s on
  the laptop GPU.
- The model's cache of the agent's conversation is saved before a helper
  runs and restored afterwards. Without this, the step after each summary
  would have to read the whole conversation again (12 s instead of 1.5 s
  for a 6000-token conversation). While a helper runs, this takes extra
  RAM: roughly 0.1 MB per token of conversation with Qwen3-30B-A3B.

### Changed

- The system prompt now tells the agent to summarize sections that are too
  long for one `read_md` call instead of reading them, to get an overview
  of a long file from a few summaries, and to use `read_md` only for exact
  details, at most about 120 lines at a time. Answers may now be based on
  summaries, but numbers, names and quotes must still come from lines read
  with `read_md`.
- `outline_md` (and so `convert_docx`) now notes when sections are longer
  than one `read_md` call and points to `summarize_section`.
- When `read_md` stops at its size limit, it now offers `summarize_section`
  next to reading on. Before, it only suggested the next line range, which
  led the agent to read long sections piece after piece.
- Each tool call is now shown when it starts instead of when it has
  finished, because a summary takes a few seconds.

## [0.0.11] - 2026-10-06

### Added

- `outline_md` now also works for documents whose titles are formatted by
  hand instead of with Word's heading styles, which is common in
  manuscripts. pandoc only turns heading styles into Markdown headings, so
  such a document used to have no outline at all, and the agent fell back
  to searching and reading from the start. When a file has no Markdown
  headings, `outline_md` now lists the short lines that look like titles:
  lines in bold from start to end, and lines that start with a section
  number like 2.1 or 2.1.3 (level from the number: 2.1 is level 2). It says
  that these are guesses. Single numbers like "2." do not count, because
  numbered lists and hand-numbered references look like that.

### Changed

- `convert_docx` now returns the new file's outline, the same as
  `outline_md`, instead of its own list of headings. Before, a document
  without heading styles got "Headings: (none)", which led the agent to
  skip the outline altogether.

## [0.0.10] - 2026-10-06

### Added

- Optional GPU inference on NVIDIA GPUs. Set `GPU_LAYERS` in `config.py` to
  run that many model layers on the GPU (`-1` for all of them); it needs
  llama-cpp-python built with CUDA, and `README.md` explains the build. It is
  opt-in: the default `0` and the normal CPU build work exactly as before. If
  `GPU_LAYERS` is set but the build has no GPU support, readerbot says so at
  start-up and runs on the CPU. With Qwen3-30B-A3B Q3_K_M on an 8 GB laptop
  GPU, 20 layers read prompts about 3.8 times and write about 1.5 times as
  fast as the CPU alone, and need about 6 GB less system RAM.
- When `GPU_LAYERS` is set, start-up shows how many layers run on the GPU,
  for example `GPU: 20 of 48 layers`.

### Changed

- With a CUDA build, flash attention is now on. It saves about 2 GB of video
  memory at 32K context, which leaves room for more layers on the GPU, and
  reads prompts faster. CPU builds keep it off, as before.

## [0.0.9] - 2026-10-06

### Added

- `/ls` lists the files in the work folder: first exactly what the agent's
  `list_files` tool reports (with sizes, line counts and which `.docx`
  files are converted), then any other files, marked as invisible to the
  agent. The model does not see this listing.
- `/verbose <question>` asks a question as usual, but prints every tool
  result in full, exactly as the model gets it, instead of only its first
  line. Useful to see why the agent reads what it reads.

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
