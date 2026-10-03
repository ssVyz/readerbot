# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
