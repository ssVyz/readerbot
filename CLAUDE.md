# CLAUDE.md

Guidance for Claude Code when working in this repository.

## Project

`readerbot` — a Python 3.13 project managed with [uv](https://docs.astral.sh/uv/).

- `main.py` — entry point.
- `minimenu.py` — vendored, self-contained tiny CLI menu library (`Selection_menu`,
  `Checkbox_menu`, `Work_folder`, `select_file`). Cross-platform key input via
  `msvcrt` on Windows and `termios`/`tty` on Linux. It is a copy/paste
  dependency, not a package — keep it standalone and dependency-free.
- `pyproject.toml` — project metadata; `version` is the single source of truth
  for the repo version.

No dependencies and no test suite yet.

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
- Leave finished work in the working tree and say what is ready to commit.

## Conventions

- Keep `*.md` out of git unless it is explicitly un-ignored in `.gitignore` —
  the repo ignores markdown by default (`README.md`, `CHANGELOG.md`, and
  `CLAUDE.md` are the current exceptions).
- Run the app with `uv run main.py`.
