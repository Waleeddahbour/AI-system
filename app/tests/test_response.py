import asyncio

from ..ai.nodes.preparation_node import preparation_node
from ..ai.nodes.response_node import response_node
from ..ai.schemas.graph_schema import ResponseOutput
from ..ai.schemas.tools_schema import SearchSource, WebSearchOutput


class FakeRaw:
    usage_metadata = {"input_tokens": 5, "output_tokens": 4}


class FakeStructuredLlm:
    def __init__(self, parsed):
        self.parsed = parsed

    async def ainvoke(self, messages):
        return {"parsed": self.parsed, "raw": FakeRaw(), "parsing_error": None}


class FakeLlm:
    def __init__(self, parsed):
        self.parsed = parsed

    def with_structured_output(self, *args, **kwargs):
        return FakeStructuredLlm(self.parsed)


def make_state():
    state = preparation_node("1", "What is OpenAI?", [])
    state["reasoning"] = "web_search was needed."
    state["tool_results"] = [
        WebSearchOutput(
            results=[
                SearchSource(
                    name="OpenAI",
                    url="https://example.com/openai",
                    snippet="OpenAI is an AI research company.",
                )
            ]
        )
    ]
    state["sources"] = [
        {"name": "OpenAI", "url": "https://example.com/openai"}
    ]
    return state


def test_response_node_returns_structured_graph_output():
    parsed = ResponseOutput(
        answer="Used web_search. OpenAI is an AI research company.",
        sources=[{"name": "OpenAI", "url": "https://example.com/openai"}],
    )

    result = asyncio.run(response_node(
        make_state(), FakeLlm(parsed), "prompt"))

    output = result["final_output"]
    assert output.answer.startswith("Used web_search")
    assert output.reasoning == "web_search was needed."
    assert output.sources[0].name == "OpenAI"
    assert output.tokens.total.input == 5


def test_response_node_filters_sources_to_tool_results():
    parsed = ResponseOutput(
        answer="Used web_search. Unsupported sources are not expected.",
        sources=[{"name": "OpenAI", "url": "https://example.com/openai"}],
    )

    result = asyncio.run(response_node(
        make_state(), FakeLlm(parsed), "prompt"))

    assert str(
        result["final_output"].sources[0].url) == "https://example.com/openai"


def test_response_node_explains_tool_errors():
    parsed = ResponseOutput(
        answer="Used web_search, but the tool failed.",
        sources=[],
    )
    state = preparation_node("1", "What is OpenAI?", [])
    state["reasoning"] = "web_search was needed."
    state["tool_results"] = [WebSearchOutput(
        results=[], error="web_search_failed")]

    result = asyncio.run(response_node(state, FakeLlm(parsed), "prompt"))

    assert "failed" in result["final_output"].answer
