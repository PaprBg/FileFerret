from fileferret.agent.loop import execute, run
from fileferret.llm import LLMResponse, ToolCall


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
