"""readerbot: ask a local model about the documents in one folder.

Start-up: pick a model from models/, pick the folder, then type questions.
"""

import io
import shutil
import sys
from pathlib import Path

import config
import guard
import tools
import ui
from agent import Agent, Model
from minimenu import SelectionMenu, select_file
from workspace import Workspace

HELP = """\
Commands:
  /ls              list the files in the folder
  /context         show how much of the model's context the conversation
                   fills
  /verbose <text>  ask as usual, and show every tool result in full,
                   exactly as the model gets it
  /tools           list the tools the model can use
  /prompt          show the system prompt the model gets
  /reset           forget the conversation (files are not touched)
  /quit            leave readerbot
Anything else is sent to the model. Ctrl+C stops a running answer."""


def main() -> None:
    if isinstance(sys.stdout, io.TextIOWrapper):
        # Model answers can hold any character; never crash on printing.
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    try:
        model_path = choose_model()
        if model_path is None:
            return
        folder = choose_folder()
        if folder is None:
            return
        pandoc = shutil.which("pandoc")
        # After the menus: they clear the screen by starting a program,
        # which the guard would block.
        guard.install(allowed_program=pandoc)
        ui.enable()

        print(f"Loading {model_path.name} ...")
        model = Model(model_path)
        agent = Agent(model, Workspace(folder, pandoc))
    except KeyboardInterrupt:
        print()
        return

    print(f"Model:  {model.name} ({model.context_tokens} tokens of context)")
    if config.GPU_LAYERS:
        print(f"GPU:    {gpu_status(model)}")
    print(f"Folder: {agent.workspace.folder}")
    if pandoc is None:
        print("pandoc was not found, so .docx files cannot be converted.")
    print("Type a question, or /help.")
    repl(agent)


def choose_model() -> Path | None:
    models = sorted(config.MODELS_DIR.glob("*.gguf"),
                    key=lambda path: path.name.lower())
    if not models:
        print(f"No .gguf model files in {config.MODELS_DIR}")
        return None
    labels = [f"{path.name}  ({path.stat().st_size / 2**30:.1f} GB)"
              for path in models]
    choice = SelectionMenu(
        labels,
        header="Which model should readerbot load?",
        footer="Arrow keys move, Enter loads the model, q quits.",
    ).present()
    return None if choice is None else models[choice]


def gpu_status(model: Model) -> str:
    """For the start-up summary: how much of the model runs on the GPU."""
    if model.gpu_layers == 0:
        return ("not used, because this llama-cpp-python build has no GPU "
                "support (see README.md)")
    total = model.layer_count
    on_gpu = total if model.gpu_layers < 0 else min(model.gpu_layers, total)
    return f"{on_gpu} of {total} layers"


def choose_folder() -> Path | None:
    """Ask for the folder; only folders are listed, not files."""
    return select_file(folders_only=True)


def repl(agent: Agent) -> None:
    while True:
        try:
            line = ui.read_line("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if not line:
            continue
        if line in ("/quit", "/exit"):
            return
        if line == "/help":
            print(HELP)
        elif line == "/ls":
            print(list_folder(agent.workspace))
        elif line == "/context":
            print(context_status(agent))
        elif line == "/tools":
            print(agent.tool_list)
        elif line == "/prompt":
            print(agent.system_prompt)
        elif line == "/reset":
            agent.reset()
            print("The conversation was cleared.")
        elif line == "/verbose" or line.startswith("/verbose "):
            question = line.removeprefix("/verbose").strip()
            if question:
                ask(agent, question, verbose=True)
            else:
                print("Type the question after /verbose, for example: "
                      "/verbose What is chapter 2 about?")
        elif line.startswith("/"):
            print(f"Unknown command {line}. Type /help for the commands.")
        else:
            ask(agent, line)


def ask(agent: Agent, question: str, *, verbose: bool = False) -> None:
    """Send one question to the agent and print its answer."""
    try:
        answer = agent.ask(question, verbose=verbose)
    except KeyboardInterrupt:
        print("\nStopped. The question was dropped from the "
              "conversation; files already written stay.")
        return
    except Exception as error:  # a bug must not end the session
        print(f"\nInternal error: {error!r}. The question was "
              "dropped from the conversation.")
        return
    if answer is not None:
        print("\n" + ui.paint(answer, ui.ANSWER))


def context_status(agent: Agent) -> str:
    """For /context: how much of the model's context the conversation fills,
    and how much is left for the next question."""
    use = agent.context_use()
    used = sum(tokens for _, tokens in use.values())
    size = agent.model.context_tokens
    rows = [f"Context: {used:,} of {size:,} tokens used ({used / size:.0%})."]
    for kind, (count, tokens) in use.items():
        label = kind if count is None else f"{kind} ({count})"
        rows.append(f"  {tokens:>7,}  {label}")
    reserve = agent.model.max_step_tokens
    left = size - used - reserve
    if left > 0:
        rows.append(f"Left for new messages: {left:,} ({reserve:,} more are "
                    "kept free for each reply).")
    else:
        rows.append("The conversation is full. Type /reset to start over.")
    return "\n".join(rows)


def list_folder(workspace: Workspace) -> str:
    """For /ls: the files as the agent's list_files shows them, then the
    other files in the folder, which the agent cannot see."""
    listing = tools.run_tool(workspace, "list_files", {})
    try:
        visible = {path.name for path in workspace.files()}
        others = sorted((entry.name for entry in workspace.folder.iterdir()
                         if entry.is_file() and entry.name not in visible),
                        key=str.lower)
    except OSError:
        return listing
    if others:
        listing += ("\nOther files (the agent cannot see these):\n"
                    + "\n".join(others))
    return listing


if __name__ == "__main__":
    main()
