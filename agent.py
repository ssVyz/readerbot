"""The model and the agent loop.

A question starts a turn. In each step the model replies with one JSON
object, forced by a grammar built from tools.TOOLS: either a tool call,
which is run and its result sent back, or the answer, which ends the turn.
"""

import json
import time
from pathlib import Path
from typing import Any, cast

from llama_cpp import Llama, llama_supports_gpu_offload
from llama_cpp.llama_chat_format import Jinja2ChatFormatter
from llama_cpp.llama_grammar import LlamaGrammar

import config
import prompts
import tools
import ui
from workspace import Workspace

Message = dict[str, str]

_PROBE = "readerbot-system-probe"


class Model:
    """A local GGUF model, prompted through its own chat template."""

    def __init__(self, path: Path) -> None:
        self.name = path.name
        # Layers on the GPU (-1: all); 0 when llama.cpp has no GPU support.
        self.gpu_layers = (config.GPU_LAYERS if llama_supports_gpu_offload()
                           else 0)
        self.llm = _load(path, self.gpu_layers)
        architecture = self.llm.metadata.get("general.architecture", "")
        self.layer_count = int(self.llm.metadata.get(
            f"{architecture}.block_count", 0))
        self.context_tokens = self.llm.n_ctx()
        self.max_step_tokens = min(config.STEP_MAX_TOKENS,
                                   self.context_tokens // 4)

        template = self.llm.metadata.get("tokenizer.chat_template")
        if not template:
            raise ValueError(f"{path.name} has no chat template")
        self._formatter = Jinja2ChatFormatter(
            template=template,
            eos_token=self._token_text(self.llm.token_eos()),
            bos_token=self._token_text(self.llm.token_bos()),
        )
        probe = self._formatter(messages=[
            {"role": "system", "content": _PROBE},
            {"role": "user", "content": "hello"},
        ])
        self._stop = probe.stop
        self.has_system_role = _PROBE in probe.prompt

    def render(self, messages: list[Message]) -> str:
        """Return the exact prompt text the model sees for ``messages``."""
        if (not self.has_system_role and len(messages) > 1
                and messages[0]["role"] == "system"
                and messages[1]["role"] == "user"):
            folded = prompts.SYSTEM_FOLDED.format(
                system=messages[0]["content"], user=messages[1]["content"])
            messages = [{"role": "user", "content": folded}, *messages[2:]]
        # enable_thinking=False switches off Qwen3's long "thinking" blocks;
        # templates that do not know the flag ignore it.
        result = self._formatter(messages=cast(Any, messages),
                                 enable_thinking=False)
        return result.prompt

    def count_tokens(self, prompt: str) -> int:
        return len(self._tokenize(prompt))

    def complete(self, prompt: str, grammar: LlamaGrammar) -> tuple[str, bool]:
        """Generate one reply. Returns the text and whether it was cut off."""
        result = self.llm.create_completion(
            self._tokenize(prompt),
            grammar=grammar,
            max_tokens=self.max_step_tokens,
            temperature=config.TEMPERATURE,
            stop=self._stop,
        )
        choice = result["choices"][0]  # type: ignore[index]
        return choice["text"], choice["finish_reason"] == "length"

    def _tokenize(self, prompt: str) -> list[int]:
        # The rendered template already holds any begin-of-text token.
        return self.llm.tokenize(prompt.encode("utf-8"), add_bos=False,
                                 special=True)

    def _token_text(self, token: int) -> str:
        if token < 0:
            return ""
        return self.llm.detokenize([token], special=True).decode(
            "utf-8", "replace")


def _load(path: Path, gpu_layers: int) -> Llama:
    # A first, small load reads how much context the model was trained for.
    # Asking for more makes llama.cpp warn and the output degrade. It stays
    # on the CPU, so the weights are copied to the GPU only once.
    probe = Llama(model_path=str(path), n_ctx=512, verbose=False)
    architecture = probe.metadata.get("general.architecture", "")
    trained = int(probe.metadata.get(f"{architecture}.context_length",
                                     config.CONTEXT_TOKENS))
    probe.close()
    # With a GPU build, flash attention makes the GPU's scratch memory for
    # attention much smaller, leaving room for more layers. llama-cpp-python
    # turns it off unless asked; CPU builds keep it off as before.
    return Llama(model_path=str(path),
                 n_ctx=min(config.CONTEXT_TOKENS, trained),
                 n_gpu_layers=gpu_layers,
                 flash_attn=llama_supports_gpu_offload(), verbose=False)


class Agent:
    """One conversation with the model about the files in one workspace."""

    def __init__(self, model: Model, workspace: Workspace) -> None:
        self.model = model
        self.workspace = workspace
        self.tool_list = "\n".join(
            prompts.TOOL_ENTRY.format(
                name=tool.name,
                description=tool.description,
                args=json.dumps({key: spec["type"] for key, spec
                                 in tool.parameters["properties"].items()}),
            )
            for tool in tools.TOOLS
        )
        self.system_prompt = prompts.SYSTEM.format(tools=self.tool_list)
        self._step_grammar = _grammar(_step_schema(answer_only=False))
        self._answer_grammar = _grammar(_step_schema(answer_only=True))
        self.messages: list[Message] = []
        self.reset()

    def reset(self) -> None:
        """Forget the conversation."""
        self.messages = [{"role": "system", "content": self.system_prompt}]

    def ask(self, question: str, *, verbose: bool = False) -> str | None:
        """Run one turn, printing each step. Returns the answer, or None.

        With ``verbose``, each tool result is printed in full, exactly as
        the model gets it, instead of only its first line.

        If the turn is interrupted (Ctrl+C) or fails, the conversation goes
        back to where it was before the question. Files already written
        stay.
        """
        start = len(self.messages)
        try:
            return self._turn(question, verbose)
        except BaseException:
            del self.messages[start:]
            raise

    def _turn(self, question: str, verbose: bool) -> str | None:
        self.messages.append({"role": "user", "content": question})
        for step in range(1, config.MAX_STEPS + 1):
            last_step = step == config.MAX_STEPS
            if last_step:
                self.messages.append({"role": "user",
                                      "content": prompts.STEP_LIMIT})
            prompt = self.model.render(self.messages)
            needed = (self.model.count_tokens(prompt)
                      + self.model.max_step_tokens)
            if needed > self.model.context_tokens:
                print("  The conversation no longer fits the model's "
                      "context. Type /reset to start over.")
                return None

            _show(f"  step {step} ...", end="")
            started = time.perf_counter()
            grammar = self._answer_grammar if last_step else self._step_grammar
            raw, cut_off = self.model.complete(prompt, grammar)
            seconds = time.perf_counter() - started
            if cut_off:
                _show(f"\r  step {step} ({seconds:.1f} s): reply too long, "
                      "cut off and ignored")
                self.messages.append({"role": "user",
                                      "content": prompts.REPLY_CUT_OFF})
                continue

            try:
                # strict=False: the grammar lets models put raw newlines
                # inside strings, which plain JSON does not allow.
                reply: dict[str, Any] = json.loads(raw, strict=False)
            except json.JSONDecodeError:
                _show(f"\r  step {step} ({seconds:.1f} s): reply was not "
                      "valid JSON and was ignored")
                self.messages.append({"role": "user",
                                      "content": prompts.REPLY_INVALID})
                continue
            self.messages.append({"role": "assistant", "content": raw})
            _show(f"\r  step {step} ({seconds:.1f} s): {reply['thought']}")
            if "answer" in reply:
                return str(reply["answer"])

            name, args = reply["tool"], reply["args"]
            result = tools.run_tool(self.workspace, name, args)
            message = prompts.TOOL_RESULT.format(name=name, result=result)
            _show(f"    -> {name}({_format_args(args)})")
            if verbose:
                print(message, flush=True)
            else:
                _show(f"    <- {result.splitlines()[0] if result else ''}")
            self.messages.append({"role": "user", "content": message})
        print("  Stopped: the model did not answer within the step limit.")
        return None


def _step_schema(answer_only: bool) -> dict[str, Any]:
    """The JSON shapes a model reply may take; compiled into a grammar."""
    answer = {
        "type": "object",
        "properties": {"thought": {"type": "string"},
                       "answer": {"type": "string"}},
        "required": ["thought", "answer"],
        "additionalProperties": False,
    }
    if answer_only:
        return answer
    calls = [
        {
            "type": "object",
            "properties": {"thought": {"type": "string"},
                           "tool": {"const": tool.name},
                           "args": tool.parameters},
            "required": ["thought", "tool", "args"],
            "additionalProperties": False,
        }
        for tool in tools.TOOLS
    ]
    return {"anyOf": [*calls, answer]}


def _grammar(schema: dict[str, Any]) -> LlamaGrammar:
    return LlamaGrammar.from_json_schema(json.dumps(schema), verbose=False)


def _show(text: str, *, end: str = "\n") -> None:
    """Print a line of the agent's progress in the step colour."""
    print(ui.paint(text, ui.STEP), end=end, flush=True)


def _format_args(args: dict[str, Any]) -> str:
    parts = []
    for key, value in args.items():
        text = repr(value)
        if len(text) > 60:
            text = text[:57] + "..."
        parts.append(f"{key}={text}")
    return ", ".join(parts)
