# CLAUDE.md

Guidance for Claude Code when working in this repository.

## Design rules

The design rules are hard boundaries for every design decision and code
change. Always follow them; if a task would break one, stop and ask.

@design_rules.md

## Project

`readerbot` — a Python 3.13 project managed with [uv](https://docs.astral.sh/uv/).

- `main.py` — entry point: start-up menus (model, then folder) and the REPL.
- `agent.py` — the model (chat template, output grammar) and the agent loop.
- `tools.py` — every tool the agent can use; its `TOOLS` registry is the
  complete list.
- `prompts.py` — all other model-facing text.
- `workspace.py` — the file boundary (`Workspace.vet`) and the pandoc call.
- `guard.py` — audit-hook tripwire against network use and stray programs.
- `config.py` — settings (context size, step limit, GPU layers, output caps).
- `ui.py` — console colours for user input, agent steps and answers.
- `minimenu.py` — vendored, self-contained tiny CLI menu library
  (`SelectionMenu`, `CheckboxMenu`, `select_file`; all return `None` when the
  user quits). Cross-platform key input via `msvcrt` on Windows and
  `termios`/`tty` on Linux. It is a copy/paste dependency, not a package —
  keep it standalone and dependency-free. `python minimenu.py` runs a demo.
- `models/` — local GGUF weights (git-ignored), e.g.
  `Qwen3-4B-Q4_K_M.gguf`, `Phi-3-mini-4k-instruct-q4.gguf`.
- `examples/` — sample documents for testing (git-ignored).
- `pyproject.toml` — project metadata; `version` is the single source of truth
  for the repo version.

The only dependency is `llama-cpp-python`, which builds from source on install
(needs the MSVC C++ toolchain on Windows). It is a CPU build unless built with
CUDA, which is opt-in (see `README.md`). With the CPU build and the default
`GPU_LAYERS = 0` in `config.py` the app must keep working as it does without a
GPU. pandoc must be on `PATH` to convert `.docx` files. No test suite yet.

## Repo rules

These are hard rules. Follow them without being reminded.

### Versioning

The repo version lives in `pyproject.toml` under `[project] version`.

- **Any code change is a patch bump.** Increment the third number
  (`0.0.1` → `0.0.2`) in `pyproject.toml` as part of the same change.
- **Minor and major versions are bumped only when a human asks.** Never raise
  the second or first number on your own initiative — not for a new feature,
  not for a breaking change. Make the patch bump and mention it if you think a
  larger bump is warranted.

### Changelog

- **Any code change gets a `CHANGELOG.md` entry**, in the same change as the
  code and the patch bump.
- Format is [Keep a Changelog](https://keepachangelog.com/en/1.1.0/): add a new
  `## [X.Y.Z] - YYYY-MM-DD` section at the top (below `## [Unreleased]`) with
  the entry grouped under `Added`, `Changed`, `Deprecated`, `Removed`, `Fixed`,
  or `Security`.
- Write entries for a human reader: what changed and why it matters, not a
  restatement of the diff.
- Docs-only or comment-only edits do not need a version bump or an entry.

### Git

- **Humans do the git submits.** Do not run `git commit`, `git push`,
  `git merge`, `git rebase`, `git tag`, or anything else that writes to history
  or a remote — not even when the work is finished and obviously commit-ready.
- Read-only git commands (`status`, `diff`, `log`, `show`) are fine.
- Do not change .gitignore, this is done by humans.

## Conventions

- Run the app with `uv run main.py`.
