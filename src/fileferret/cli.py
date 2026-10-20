"""Command-line entry point: `fileferret ask "question" [--root PATH ...]` and `fileferret cache`."""

import argparse
import sys
from pathlib import Path

from dotenv import find_dotenv, load_dotenv

from fileferret.agent.answer import Answer
from fileferret.agent.loop import run
from fileferret.extractors import cache
from fileferret.llm import PROVIDERS, LLMClient, ToolCall, get_client
from fileferret.llm.ollama_client import OllamaClient
from fileferret.tools.common import describe_size
from fileferret.workspace import AskPermission, Workspace, default_roots


def main(argv: list[str] | None = None) -> int:
    # Read settings/keys from a .env file (current folder or above); real env vars win.
    load_dotenv(find_dotenv(usecwd=True))

    parser = argparse.ArgumentParser(prog="fileferret")
    sub = parser.add_subparsers(dest="command", required=True)

    ask = sub.add_parser("ask", help="Ask a question about your files")
    ask.add_argument("question")
    ask.add_argument("--root", type=Path, action="append",
                     help="Folder to search; repeat for several. Default: FILEFERRET_ROOTS, "
                          "else your user folder")
    ask.add_argument("--max-steps", type=int, default=20, help="Max model calls before giving up")
    ask.add_argument("--provider", choices=PROVIDERS, help="Model backend (default: anthropic)")
    ask.add_argument("--model", help="Model name, e.g. claude-opus-5-5 or llama3.1")
    ask.add_argument("-v", "--verbose", action="store_true", help="Show each tool call")

    cache_cmd = sub.add_parser("cache", help="Show or clear the cache of extracted PDF text")
    cache_cmd.add_argument("--clear", action="store_true", help="Delete the cache")

    args = parser.parse_args(argv)

    if args.command == "cache":
        return _cache_command(args.clear)

    if args.command == "ask":
        if args.verbose:
            cache.on_extract = lambda p: print(f"  (reading {p.name} for the first time)", file=sys.stderr)
        roots = default_roots(args.root)
        for root in roots:
            if not root.is_dir():
                print(f"error: {root} is not a folder", file=sys.stderr)
                return 1
        try:
            client = get_client(args.provider, args.model)
            ws = Workspace(roots, _permission_prompt(client))
            if args.verbose:
                print(f"[{type(client).__name__}:{client.model}] searching "
                      + "; ".join(str(r) for r in ws.roots), file=sys.stderr)
            answer = run(args.question, ws, client, args.max_steps,
                         on_step=_print_step if args.verbose else None)
        except Exception as e:
            if args.verbose:
                raise
            print(f"error: {e}", file=sys.stderr)
            return 1
        _print_answer(answer)
    return 0


def _cache_command(clear: bool) -> int:
    location = cache.cache_dir()
    if clear:
        cache.clear()
        print(f"Cleared {location}")
        return 0
    count, size = cache.stats()
    print(f"Cache: {location}\n{count} file(s), {describe_size(size)}\n"
          "It holds plain-text copies of PDFs you've searched; delete it with: fileferret cache --clear")
    return 0


def _permission_prompt(client: LLMClient) -> AskPermission | None:
    """y/N prompt for folders outside the roots; None (always deny) when nobody can answer."""
    if not sys.stdin.isatty():
        return None
    cloud = not isinstance(client, OllamaClient)

    def ask(folder: Path) -> bool:
        print(f"\nFileFerret wants to search outside the allowed folders:\n  {folder}", file=sys.stderr)
        if folder.parent == folder:
            print("  warning: this is an entire drive", file=sys.stderr)
        if cloud:
            print(f"  note: contents it reads there are sent to {type(client).__name__} "
                  f"({client.model})", file=sys.stderr)
        print("Allow for this run? [y/N] ", end="", file=sys.stderr, flush=True)
        answer = sys.stdin.readline()
        return answer.strip().lower() in ("y", "yes")

    return ask


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
