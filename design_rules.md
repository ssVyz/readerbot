# Design rules

Hard boundaries for readerbot. They apply to every design decision and every
change. If a task seems to need breaking one, stop and ask a human.

readerbot is a local REPL in which a local LLM agent reads manuscripts
(.docx converted to Markdown), answers questions about them and writes
derivative files.

## Local only

- No network access at runtime: no HTTP, sockets, telemetry, update checks
  or model downloads. Models load from local files only.
- Do not use llama-cpp-python features that can reach the network:
  `Llama.from_pretrained`, multimodal chat handlers (they fetch image URLs),
  JSON schemas with remote `$ref`, the `llama_cpp.server` module.
- The only external program is pandoc: a fixed argument list including
  `--sandbox`, no shell, no Lua filters, called from code — never from a
  string the model wrote.
- Dependencies: standard library and llama-cpp-python. Any new dependency
  needs human approval.
- Manuscript content (converted files, outputs, notes, logs, transcripts)
  stays in the chosen folder and is never committed. A chosen folder inside
  this repo must be git-ignored (like `examples/`).

## Files

- The agent works in one folder, picked by the user at start-up. It sees
  only the `.docx` and `.md` files directly in that folder, nothing else.
- `.docx` files are read-only sources. Nothing writes, renames, moves or
  deletes them; pandoc only reads them.
- `.md` files in the folder are the agent's working files: it may create,
  edit and append to them, including ones the user put there. Creating
  never overwrites a file, and the agent never deletes files.
- Every read and write is vetted first. Tools take bare file names, never
  paths. Validate a name before touching the file system (no separators,
  drive letters, `..` or `:`), then check that the resolved path is inside
  the folder. This also blocks UNC paths (`\\server\share`), which open a
  network connection on Windows.
- All text I/O sets `encoding="utf-8"` explicitly.

## Tools (everything the agent can do)

- All agent tools live in `tools.py`. Its `TOOLS` registry is the complete
  list of what the agent can do. No tools are defined, loaded or registered
  anywhere else, and none at runtime.
- One tool = one plain function, with its model-facing description and
  argument schema directly beside it, marked as model-facing.
- Never a tool, now or later: shell or subprocess access, code execution,
  network access, file deletion, writing outside the work folder, editing
  source documents.
- Assume document text can take over the model (prompt injection). Every
  tool must be safe with any arguments: validate them in code.
- Model output is only ever parsed as data (tool name and arguments) or
  shown to the user. It is never executed.
- Tool output is size-capped and says when it was cut and how to get more.
- Every tool call is shown to the user as it happens.
- Adding or changing a tool needs human review and a CHANGELOG entry that
  names the tool.

## Prompts

- All model-facing text lives in `prompts.py` as named constants, each with
  a comment saying when it is sent. Tool descriptions live beside their tool
  in `tools.py`. No model-facing strings anywhere else.

## Simplicity

- A few small modules of plain functions. No agent frameworks, plugin
  systems or hidden registration (decorators, auto-discovery).
- Code does the mechanical work (finding, counting, splitting, file
  handling); the model reads and judges.
- Never send a whole document to the model. It works through bounded
  pieces.
