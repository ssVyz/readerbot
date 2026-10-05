"""Everything the agent can do. The TOOLS registry at the end is the full list.

How a tool is built:
- It is a plain function ``(workspace, **args) -> str``.
- Its description and argument schema sit directly above it. Both are
  MODEL-FACING: they go into the system prompt, and the schema is also
  compiled into the grammar that constrains the model's replies.
- Every file name goes through ``workspace.vet`` before anything is read or
  written, so the agent only reaches .docx/.md files in the chosen folder.
- The result is MODEL-FACING too. Its first line is a one-line summary that
  is also shown to the user.
"""

import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import config
from workspace import WRITABLE, RefusedError, Workspace


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    parameters: dict[str, Any]
    function: Callable[..., str]


# --- Helpers ---

# Images loaded from elsewhere would make a Markdown preview contact that
# server, which could leak text from the documents. Local images are fine.
_REMOTE_IMAGE = re.compile(
    r"!\[[^\]]*\]\(\s*<?\s*(?:[a-z][a-z0-9+.-]*:)?//|<img\b", re.IGNORECASE
)

# A Markdown heading as pandoc writes it: one to six "#", then a space.
_HEADING = re.compile(r"(#{1,6})(?:\s|$)")


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        raise RefusedError(f"{path.name} is not UTF-8 text") from None


def _split_lines(text: str) -> list[str]:
    """Split on newlines only, so every tool numbers lines the same way."""
    lines = text.split("\n")
    if lines[-1] == "":
        lines.pop()
    return lines


def _char_count(lines: list[str], start: int, end: int) -> int:
    """Characters in lines start to end (counting from 1), with newlines."""
    return sum(len(line) + 1 for line in lines[start - 1:end])


def _check_new_text(text: str) -> None:
    if len(text) > config.WRITE_MAX_CHARS:
        raise RefusedError(
            f"too much text in one call ({len(text)} characters; "
            f"the limit is {config.WRITE_MAX_CHARS})"
        )
    if _REMOTE_IMAGE.search(text):
        raise RefusedError(
            "images from web addresses (![...](https://...) or "
            "<img>) are not allowed in files"
        )


def _with_newline(text: str) -> str:
    return text if text.endswith("\n") else text + "\n"


def _object_schema(**properties: str) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {name: {"type": kind}
                       for name, kind in properties.items()},
        "required": list(properties),
        "additionalProperties": False,
    }


# === TOOL: list_files ======================================================
# Access: lists the .docx and .md files in the folder; reads .md files to
# count their lines.

LIST_FILES_DESCRIPTION = (  # MODEL-FACING
    "List the .docx and .md files in the folder with their sizes. Call this "
    "first to learn the exact file names."
)
LIST_FILES_ARGS = _object_schema()  # MODEL-FACING


def list_files(workspace: Workspace) -> str:
    paths = workspace.files()
    if not paths:
        return "The folder has no .docx or .md files."
    rows = []
    for path in paths:
        if path.suffix.lower() == ".docx":
            kilobytes = max(1, round(path.stat().st_size / 1024))
            markdown = path.with_suffix(".md")
            status = (f"converted to {markdown.name}" if markdown.exists()
                      else "not converted yet")
            rows.append(f"{path.name} ({kilobytes} KB, {status})")
        else:
            try:
                count = len(_split_lines(_read_text(path)))
                rows.append(f"{path.name} ({count} lines)")
            except RefusedError:
                rows.append(f"{path.name} (not readable: not UTF-8 text)")
    count_text = "1 file" if len(paths) == 1 else f"{len(paths)} files"
    return f"{count_text}:\n" + "\n".join(rows)


# === TOOL: convert_docx ====================================================
# Access: reads one .docx; pandoc writes a new .md with the same name. Never
# overwrites a file and never changes the .docx.

CONVERT_DOCX_DESCRIPTION = (  # MODEL-FACING
    "Convert a .docx file to Markdown so that it can be read. Creates a .md "
    "file with the same name in the folder; the .docx is not changed. "
    "Returns the new file's length and headings. "
    'Example args: {"file": "Report.docx"}'
)
CONVERT_DOCX_ARGS = _object_schema(file="string")  # MODEL-FACING


def convert_docx(workspace: Workspace, file: str) -> str:
    source = workspace.vet(file, (".docx",), exists=True)
    target = workspace.vet(source.with_suffix(".md").name, WRITABLE,
                           exists=None)
    if target.exists():
        stale = ""
        if target.stat().st_mtime < source.stat().st_mtime:
            stale = (" It is older than the .docx and may be out of date; "
                     "tell the user.")
        return (f"{target.name} already exists, so nothing was converted. "
                f"See its sections with outline_md.{stale}")
    workspace.convert_docx(source, target)
    lines = _split_lines(_read_text(target))
    headings = [f"  line {number}: {line}"
                for number, line in enumerate(lines, start=1)
                if line.startswith("#")]
    shown = "\n".join(headings[:30]) or "  (none)"
    more = (f"\n  ... and {len(headings) - 30} more"
            if len(headings) > 30 else "")
    return (f"Created {target.name} ({len(lines)} lines).\n"
            f"Headings:\n{shown}{more}")


# === TOOL: outline_md ======================================================
# Access: reads one .md file.

OUTLINE_MD_DESCRIPTION = (  # MODEL-FACING
    "Show the outline of a .md file: its headings, each with the line range "
    "and size in characters of its section (a section includes its "
    "subsections). Call this before reading a file, then read only the "
    "sections you need with read_md. "
    'Example args: {"file": "Report.md"}'
)
OUTLINE_MD_ARGS = _object_schema(file="string")  # MODEL-FACING


def outline_md(workspace: Workspace, file: str) -> str:
    path = workspace.vet(file, (".md",), exists=True)
    lines = _split_lines(_read_text(path))
    total = len(lines)
    if total == 0:
        return f"{path.name} is empty."
    headings = [(number, len(match.group(1)), line)
                for number, line in enumerate(lines, start=1)
                if (match := _HEADING.match(line))]
    count_text = ("1 heading" if len(headings) == 1
                  else f"{len(headings)} headings")
    header = (f"Outline of {path.name}: {total} lines, "
              f"{_char_count(lines, 1, total)} characters, {count_text}.")
    if not headings:
        return header + "\nFind the parts you need with search_md."

    # Too many headings: leave out the deepest levels until the rest fit.
    cap = config.OUTLINE_MAX_HEADINGS
    depth = max(level for _, level, _ in headings)
    while depth > 1 and sum(level <= depth for _, level, _ in headings) > cap:
        depth -= 1
    shown = [index for index, (_, level, _) in enumerate(headings)
             if level <= depth]

    rows = []
    first = headings[0][0]
    if any(line.strip() for line in lines[:first - 1]):
        rows.append(f"  lines 1-{first - 1} "
                    f"({_char_count(lines, 1, first - 1)} characters): "
                    "text before the first heading")
    width = config.SNIPPET_CHARS
    for index in shown[:cap]:
        start, level, line = headings[index]
        # A section ends before the next heading of the same or a higher level.
        end = next((number - 1 for number, other, _ in headings[index + 1:]
                    if other <= level), total)
        title = line[:width] + "..." if len(line) > width else line
        rows.append(f"  lines {start}-{end} "
                    f"({_char_count(lines, start, end)} characters): {title}")
    notes = ""
    if depth < max(level for _, level, _ in headings):
        notes += (f"\n[Only headings down to {'#' * depth} are listed, to "
                  "keep this short. read_md shows the subheadings.]")
    if len(shown) > cap:
        rest = headings[shown[cap]][0]
        notes += (f"\n[Stopped after {cap} headings. The rest starts at line "
                  f"{rest}; find parts there with search_md.]")
    return header + "\n" + "\n".join(rows) + notes


# === TOOL: read_md =========================================================
# Access: reads one .md file.

READ_MD_DESCRIPTION = (  # MODEL-FACING
    "Read lines start_line to end_line (inclusive, counting from 1) of a .md "
    "file. Each line comes with its number. At most about "
    f"{config.READ_MAX_CHARS} characters are returned per call. Take the "
    "line range of the section you need from outline_md; do not read a long "
    "file from the start. "
    'Example args: {"file": "Report.md", "start_line": 120, "end_line": 185}'
)
READ_MD_ARGS = _object_schema(  # MODEL-FACING
    file="string", start_line="integer", end_line="integer"
)


def read_md(workspace: Workspace, file: str, start_line: int,
            end_line: int) -> str:
    path = workspace.vet(file, (".md",), exists=True)
    lines = _split_lines(_read_text(path))
    total = len(lines)
    if total == 0:
        return f"{path.name} is empty."
    if start_line < 1 or end_line < start_line:
        raise RefusedError(
            "start_line must be 1 or more, and end_line must not "
            "be smaller than start_line"
        )
    if start_line > total:
        raise RefusedError(f"{path.name} has only {total} lines")
    end_line = min(end_line, total)

    cap = config.READ_MAX_CHARS
    rows: list[str] = []
    used = 0
    note = ""
    for number in range(start_line, end_line + 1):
        row = f"{number:>5} | {lines[number - 1]}"
        if rows and used + len(row) > cap:
            note = (f"\n[Stopped after line {number - 1} to stay under {cap} "
                    f"characters. Continue with start_line={number}.]")
            break
        if len(row) > cap:
            row = row[:cap] + " [rest of this line cut]"
        rows.append(row)
        used += len(row) + 1
    last = start_line + len(rows) - 1
    header = f"{path.name}, lines {start_line}-{last} of {total}:"
    return header + "\n" + "\n".join(rows) + note


# === TOOL: search_md =======================================================
# Access: reads one .md file.

SEARCH_MD_DESCRIPTION = (  # MODEL-FACING
    "Find the lines of a .md file that contain all of the given words, in "
    "any order (plain text, not case-sensitive, no wildcards). Use one or "
    "two key words. Returns the line numbers with a snippet of each line, "
    f"at most {config.SEARCH_MAX_HITS} lines. "
    'Example args: {"file": "Report.md", "words": "climate"}'
)
SEARCH_MD_ARGS = _object_schema(  # MODEL-FACING
    file="string", words="string"
)


def search_md(workspace: Workspace, file: str, words: str) -> str:
    path = workspace.vet(file, (".md",), exists=True)
    if len(words) > 200:
        raise RefusedError("words are limited to 200 characters")
    needles = words.lower().split()
    if not needles:
        raise RefusedError("words must not be empty")
    wanted = " and ".join(repr(needle) for needle in needles)
    hits = [(number, line)
            for number, line in enumerate(
                _split_lines(_read_text(path)), start=1)
            if all(needle in line.lower() for needle in needles)]
    if not hits:
        return f"No lines in {path.name} contain {wanted}."

    width = config.SNIPPET_CHARS
    rows = []
    for number, line in hits[:config.SEARCH_MAX_HITS]:
        first = min(line.lower().index(needle) for needle in needles)
        begin = max(0, first - width // 3)
        snippet = line[begin:begin + width]
        if begin > 0:
            snippet = "..." + snippet
        if begin + width < len(line):
            snippet += "..."
        rows.append(f"{number:>5} | {snippet}")
    shown = (f", showing the first {config.SEARCH_MAX_HITS}"
             if len(hits) > config.SEARCH_MAX_HITS else "")
    return (f"{len(hits)} lines in {path.name} contain {wanted}{shown}:\n"
            + "\n".join(rows))


# === TOOL: create_md =======================================================
# Access: creates one new .md file. Never overwrites an existing file.

CREATE_MD_DESCRIPTION = (  # MODEL-FACING
    "Create a new .md file with the given content. Fails if the file "
    "already exists; use edit_md or append_md to change existing files. "
    'Example args: {"file": "summary.md", "content": "# Summary\\n..."}'
)
CREATE_MD_ARGS = _object_schema(  # MODEL-FACING
    file="string", content="string"
)


def create_md(workspace: Workspace, file: str, content: str) -> str:
    path = workspace.vet(file, WRITABLE, exists=False)
    _check_new_text(content)
    text = _with_newline(content)
    with path.open("x", encoding="utf-8") as handle:  # "x": never overwrite
        handle.write(text)
    return f"Created {path.name} ({len(_split_lines(text))} lines)."


# === TOOL: append_md =======================================================
# Access: adds text to the end of one existing .md file.

APPEND_MD_DESCRIPTION = (  # MODEL-FACING
    "Add text to the end of an existing .md file. "
    'Example args: {"file": "notes.md", "text": "- another point"}'
)
APPEND_MD_ARGS = _object_schema(  # MODEL-FACING
    file="string", text="string"
)


def append_md(workspace: Workspace, file: str, text: str) -> str:
    path = workspace.vet(file, WRITABLE, exists=True)
    _check_new_text(text)
    if not text.strip():
        raise RefusedError("text must not be empty")
    existing = _read_text(path)
    addition = _with_newline(text)
    if existing and not existing.endswith("\n"):
        addition = "\n" + addition
    with path.open("a", encoding="utf-8") as handle:
        handle.write(addition)
    total = len(_split_lines(existing + addition))
    return (f"Appended {len(_split_lines(addition))} lines to {path.name}; "
            f"it now has {total} lines.")


# === TOOL: edit_md =========================================================
# Access: rewrites one existing .md file with one passage replaced.

EDIT_MD_DESCRIPTION = (  # MODEL-FACING
    "Replace one passage in an existing .md file. old_text must be copied "
    "exactly from the file (without the line numbers that read_md adds) and "
    "must occur exactly once; new_text replaces it. "
    'Example args: {"file": "summary.md", "old_text": "Draft", '
    '"new_text": "Final"}'
)
EDIT_MD_ARGS = _object_schema(  # MODEL-FACING
    file="string", old_text="string", new_text="string"
)


def edit_md(workspace: Workspace, file: str, old_text: str,
            new_text: str) -> str:
    path = workspace.vet(file, WRITABLE, exists=True)
    if not old_text:
        raise RefusedError("old_text must not be empty")
    _check_new_text(new_text)
    text = _read_text(path)
    count = text.count(old_text)
    if count == 0:
        raise RefusedError(
            f"old_text was not found in {path.name}. Read the "
            "lines again and copy the text exactly, without the "
            "line numbers."
        )
    if count > 1:
        raise RefusedError(
            f"old_text occurs {count} times in {path.name}; "
            "include more of the surrounding text so that it "
            "matches only once."
        )
    line = text.count("\n", 0, text.index(old_text)) + 1
    path.write_text(text.replace(old_text, new_text, 1), encoding="utf-8")
    return f"Edited {path.name} at line {line}."


# === REGISTRY: everything the agent can do =================================

TOOLS = [
    Tool("list_files", LIST_FILES_DESCRIPTION, LIST_FILES_ARGS, list_files),
    Tool("convert_docx", CONVERT_DOCX_DESCRIPTION, CONVERT_DOCX_ARGS,
         convert_docx),
    Tool("outline_md", OUTLINE_MD_DESCRIPTION, OUTLINE_MD_ARGS, outline_md),
    Tool("read_md", READ_MD_DESCRIPTION, READ_MD_ARGS, read_md),
    Tool("search_md", SEARCH_MD_DESCRIPTION, SEARCH_MD_ARGS, search_md),
    Tool("create_md", CREATE_MD_DESCRIPTION, CREATE_MD_ARGS, create_md),
    Tool("append_md", APPEND_MD_DESCRIPTION, APPEND_MD_ARGS, append_md),
    Tool("edit_md", EDIT_MD_DESCRIPTION, EDIT_MD_ARGS, edit_md),
]

_TOOLS_BY_NAME = {tool.name: tool for tool in TOOLS}
_ARG_TYPES = {"string": (str, "a string"), "integer": (int, "an integer")}


def run_tool(workspace: Workspace, name: str, args: object) -> str:
    """Run one tool call from the model; errors come back as text."""
    try:
        tool = _TOOLS_BY_NAME.get(name)
        if tool is None:
            raise RefusedError(f"there is no tool called {name!r}")
        return tool.function(workspace, **_checked_args(tool, args))
    except RefusedError as error:
        return f"ERROR: {error}"
    except OSError as error:
        return f"ERROR: {error.strerror or error}"


def _checked_args(tool: Tool, args: object) -> dict[str, Any]:
    """Check the arguments in code too; the grammar alone is not trusted."""
    if not isinstance(args, dict):
        raise RefusedError("args must be a JSON object")
    properties = tool.parameters["properties"]
    unknown = sorted(set(args) - set(properties))
    missing = sorted(set(tool.parameters["required"]) - set(args))
    if unknown or missing:
        raise RefusedError(
            f"{tool.name} takes exactly these args: "
            f"{', '.join(properties) or 'none'}"
        )
    for key, value in args.items():
        kind, wording = _ARG_TYPES[properties[key]["type"]]
        if not isinstance(value, kind) or isinstance(value, bool):
            raise RefusedError(f"{key} must be {wording}")
    return args
