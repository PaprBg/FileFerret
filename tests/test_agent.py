from fileferret.agent.loop import execute, run
from fileferret.llm import LLMResponse, ToolCall
from fileferret.workspace import Workspace


class FakeClient:
    """Plays back scripted responses and records what the loop sent."""

    model = "fake"

    def __init__(self, *responses):
        self.responses = list(responses)
        self.sent = []

    def chat(self, system, messages, tools):
        self.sent.append(list(messages))
        return self.responses.pop(0)


def tool_call(name, **arguments):
    return LLMResponse("", [ToolCall(f"call_{name}", name, arguments)])


def test_loop_searches_then_answers_with_verified_citation(docs):
    client = FakeClient(
        tool_call("grep_text", pattern="wifi password"),
        LLMResponse("The WiFi password is hunter2 [notes/wifi.md:L4]."),
    )
    answer = run("what is my wifi password?", docs, client)

    assert answer.steps == 2
    tool_result = client.sent[1][-1]
    assert tool_result["role"] == "tool" and "notes/wifi.md:L4" in tool_result["content"]
    [citation] = answer.citations
    assert citation.verified and citation.quote == "WiFi password: hunter2"


STORY = "Downloads/The_Lighthouse_Keepers_Last_Lantern.txt"


def test_marguerite_question_takes_three_calls(docs):
    # Real failure: flash-lite only searched file names; flash needed 7 calls.
    client = FakeClient(
        tool_call("grep_text", pattern="Marguerite", paths=["Desktop", "Downloads"], files_only=True),
        tool_call("read_file", path=STORY),
        LLMResponse(f"It's the lighthouse tale about Marguerite [{STORY}:L1] [{STORY}:L3]."),
    )
    answer = run("find the file with a story about a character named Marguerite", docs, client)

    grep_result = client.sent[1][-1]["content"]
    assert STORY in grep_result and "Desktop/lexicon.txt" in grep_result
    assert answer.steps == 3
    assert [c.verified for c in answer.citations] == [True, True]


def test_kind_of_content_question_uses_preview(docs):
    # Real failure: the file never says "story", so name and keyword searches can't find it.
    client = FakeClient(
        tool_call("preview_files", path="Downloads"),
        tool_call("read_file", path=STORY),
        LLMResponse(f"The story is 'The Lighthouse Keeper's Last Lantern' [{STORY}:L1]."),
    )
    answer = run("find the file that tells a story", docs, client)

    assert "THE LIGHTHOUSE KEEPER'S LAST LANTERN" in client.sent[1][-1]["content"]
    [citation] = answer.citations
    assert citation.verified and citation.quote == "THE LIGHTHOUSE KEEPER'S LAST LANTERN"


def test_pdf_answer_with_page_citation(docs):
    client = FakeClient(
        tool_call("grep_text", pattern="revenue", files_only=True),
        tool_call("read_file", path="docs/report.pdf", page=2),
        LLMResponse("Revenue grew 12% [docs/report.pdf:p2:L1]."),
    )
    answer = run("how much did revenue grow?", docs, client)
    [citation] = answer.citations
    assert citation.page == 2 and citation.verified
    assert citation.quote == "Quarterly revenue grew 12%"
    assert citation.location() == "docs/report.pdf:p2:L1"


def test_prompt_explains_tool_choice(docs):
    client = FakeClient(LLMResponse("done"))
    systems = []
    original = client.chat
    client.chat = lambda system, messages, tools: systems.append(system) or original(system, messages, tools)
    run("q", docs, client)
    assert "find_files searches file NAMES only" in systems[0]
    assert "preview_files" in systems[0] and "files_only=true" in systems[0]


def test_wrong_citation_is_flagged(docs):
    client = FakeClient(LLMResponse("It's in [notes/wifi.md:L99] and [missing.md:L1-L2]."))
    answer = run("q", docs, client)
    assert [c.verified for c in answer.citations] == [False, False]


def test_stops_at_max_steps(docs):
    client = FakeClient(*[tool_call("list_dir") for _ in range(3)])
    answer = run("q", docs, client, max_steps=3)
    assert answer.steps == 3 and "Stopped after 3 steps" in answer.text


def test_tool_problems_go_back_to_model_as_errors(docs):
    assert execute(ToolCall("1", "nope", {}), docs)[1] is True
    assert execute(ToolCall("1", "read_file", {"wrong": 1}), docs)[1] is True
    result, is_error = execute(ToolCall("1", "grep_text", {"pattern": "(bad"}), docs)
    assert is_error and "invalid regex" in result
    # null optional arguments are ignored rather than rejected
    assert execute(ToolCall("1", "grep_text", {"pattern": "milk", "glob": None}), docs)[1] is False


def test_prompt_tells_model_the_environment(docs):
    client = FakeClient(LLMResponse("done"))
    captured = {}
    original = client.chat

    def chat(system, messages, tools):
        captured["system"] = system
        return original(system, messages, tools)

    client.chat = chat
    run("q", docs, client)
    assert "User folder:" in captured["system"]
    assert str(docs.base) in captured["system"]


def test_outside_folder_approved_then_cited(docs, outside):
    ws = Workspace(docs.roots, lambda folder: True)
    secret = (outside / "secret.md").as_posix()
    client = FakeClient(
        tool_call("grep_text", pattern="secret", path=str(outside)),
        LLMResponse(f"It is 42 [{secret}:L2]."),
    )
    answer = run("what's the secret?", ws, client)
    tool_result = client.sent[1][-1]
    assert not tool_result["is_error"] and f"{secret}:L2" in tool_result["content"]
    [citation] = answer.citations
    assert citation.verified and citation.quote == "the secret is 42"


def test_outside_folder_denied_goes_back_as_error(docs, outside):
    ws = Workspace(docs.roots, lambda folder: False)
    result, is_error = execute(ToolCall("1", "read_file", {"path": str(outside / "secret.md")}), ws)
    assert is_error and "denied" in result
