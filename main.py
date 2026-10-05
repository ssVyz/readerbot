"""readerbot: ask a local model about the documents in one folder.

Start-up: pick a model from models/, pick the folder, then type questions.
"""

import io
import shutil
import sys
from pathlib import Path

import config
import guard
import ui
from agent import Agent, Model
from minimenu import SelectionMenu, select_file
from workspace import Workspace

HELP = """\
Commands:
  /tools   list the tools the model can use
  /prompt  show the system prompt the model gets
  /reset   forget the conversation (files are not touched)
  /quit    leave readerbot
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
        elif line == "/tools":
            print(agent.tool_list)
        elif line == "/prompt":
            print(agent.system_prompt)
        elif line == "/reset":
            agent.reset()
            print("The conversation was cleared.")
        elif line.startswith("/"):
            print(f"Unknown command {line}. Type /help for the commands.")
        else:
            try:
                answer = agent.ask(line)
            except KeyboardInterrupt:
                print("\nStopped. The question was dropped from the "
                      "conversation; files already written stay.")
                continue
            except Exception as error:  # a bug must not end the session
                print(f"\nInternal error: {error!r}. The question was "
                      "dropped from the conversation.")
                continue
            if answer is not None:
                print("\n" + ui.paint(answer, ui.ANSWER))


if __name__ == "__main__":
    main()
