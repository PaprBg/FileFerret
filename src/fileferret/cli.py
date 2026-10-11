"""Command-line entry point: `fileferret ask "question" --root PATH`."""

import argparse
import sys
from pathlib import Path

from dotenv import find_dotenv, load_dotenv

from fileferret.agent.answer import Answer
from fileferret.agent.loop import run
from fileferret.llm import PROVIDERS, ToolCall, get_client


def main(argv: list[str] | None = None) -> int:
    # Read settings/keys from a .env file (current folder or above); real env vars win.
    load_dotenv(find_dotenv(usecwd=True))

    parser = argparse.ArgumentParser(prog="fileferret")
    sub = parser.add_subparsers(dest="command", required=True)

    ask = sub.add_parser("ask", help="Ask a question about your files")
    ask.add_argument("question")
    ask.add_argument("--root", type=Path, default=Path.cwd(), help="Folder to search")
    ask.add_argument("--max-steps", type=int, default=20, help="Max model calls before giving up")
    ask.add_argument("--provider", choices=PROVIDERS, help="Model backend (default: anthropic)")
    ask.add_argument("--model", help="Model name, e.g. claude-opus-5-5 or llama3.1")
    ask.add_argument("-v", "--verbose", action="store_true", help="Show each tool call")

    args = parser.parse_args(argv)

    if args.command == "ask":
        if not args.root.is_dir():
            print(f"error: {args.root} is not a folder", file=sys.stderr)
            return 1
        try:
            client = get_client(args.provider, args.model)
            if args.verbose:
                print(f"[{type(client).__name__}:{client.model}] searching {args.root.resolve()}",
                      file=sys.stderr)
            answer = run(args.question, args.root, client, args.max_steps,
                         on_step=_print_step if args.verbose else None)
        except Exception as e:
            if args.verbose:
                raise
            print(f"error: {e}", file=sys.stderr)
            return 1
        _print_answer(answer)
    return 0


def _print_step(call: ToolCall, result: str, is_error: bool) -> None:
    arguments = ", ".join(f"{k}={v!r}" for k, v in call.arguments.items())
    lines = result.splitlines()
    summary = lines[0] if is_error or len(lines) <= 1 else f"{len(lines)} lines of output"
    print(f"  -> {call.name}({arguments})  {summary}", file=sys.stderr)


def _print_answer(answer: Answer) -> None:
    print(answer.text)
    if not answer.citations:
        return
    print("\nSources:")
    for c in answer.citations:
        if c.verified:
            first_line = c.quote.splitlines()[0] if c.quote else ""
            print(f"  {c.location()}  \"{first_line[:120]}\"")
        else:
            print(f"  {c.location()}  (could not verify: file or lines not found)")


if __name__ == "__main__":
    raise SystemExit(main())
