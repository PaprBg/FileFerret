"""Run the search -> read -> refine loop.

1. Send the system prompt, question, and tool list to the model.
2. The model asks for one or more tools; run them and append calls + results to the history.
3. Call the model again with the full history; repeat.
4. Stop when the model answers without calling a tool, refuses, or max_steps is reached.
5. Check the answer's citations against the real files.

The model is passed in as an LLMClient, so the loop works with any provider in fileferret.llm.
"""

import inspect
import platform
from collections.abc import Callable
from pathlib import Path

from fileferret.agent.answer import Answer
from fileferret.agent.citations import extract_citations
from fileferret.agent.prompts import SYSTEM_PROMPT
from fileferret.extractors import SUPPORTED_SUFFIXES, ExtractionError
from fileferret.llm import LLMClient, ToolCall
from fileferret.tools import SCHEMAS, TOOLS, ToolError
from fileferret.workspace import Workspace, known_folders

# Called after each tool runs with (call, result, is_error); used by the CLI's --verbose.
OnStep = Callable[[ToolCall, str, bool], None]


def run(question: str, ws: Workspace, client: LLMClient, max_steps: int = 20,
        on_step: OnStep | None = None) -> Answer:
    system = SYSTEM_PROMPT.format(
        environment=describe_environment(ws),
        base=ws.base,
        supported=", ".join(SUPPORTED_SUFFIXES),
    )
    messages: list[dict] = [{"role": "user", "content": question}]

    for step in range(1, max_steps + 1):
        response = client.chat(system, messages, SCHEMAS)
        messages.append(response.to_message())

        if response.refused:
            return Answer(response.text or "The model declined to answer.", steps=step)
        if not response.tool_calls:
            text = response.text.strip() or "(The model returned an empty answer.)"
            return Answer(text, extract_citations(text, ws), steps=step)

        for call in response.tool_calls:
            result, is_error = execute(call, ws)
            if on_step:
                on_step(call, result, is_error)
            messages.append({
                "role": "tool",
                "tool_call_id": call.id,
                "name": call.name,
                "content": result,
                "is_error": is_error,
            })

    return Answer(f"Stopped after {max_steps} steps without a final answer. "
                  "Try a more specific question or a higher --max-steps.", steps=max_steps)


def describe_environment(ws: Workspace) -> str:
    """Tell the model where things are, like Claude Code's environment info."""
    lines = [
        f"- Operating system: {platform.system()} {platform.release()}",
        f"- User folder: {Path.home()}",
    ]
    lines += [f"- {name}: {path}" for name, path in known_folders()]
    lines.append("- Allowed folders (no approval needed): " + "; ".join(str(r) for r in ws.roots))
    return "\n".join(lines)


def execute(call: ToolCall, ws: Workspace) -> tuple[str, bool]:
    """Run one tool call. Problems go back to the model as error results instead of crashing."""
    handler = TOOLS.get(call.name)
    if handler is None:
        return f"Error: unknown tool {call.name!r}. Available: {', '.join(TOOLS)}", True

    # Small models often send null for optional arguments; treat that as "not given".
    arguments = {k: v for k, v in call.arguments.items() if v is not None}
    try:
        inspect.signature(handler).bind(ws, **arguments)
    except TypeError as e:
        return f"Error: bad arguments for {call.name}: {e}", True

    try:
        return handler(ws, **arguments), False
    except (ToolError, ExtractionError) as e:
        return f"Error: {e}", True
    except OSError as e:
        return f"Error: {e.strerror or e}", True
