import asyncio

from ..ai.nodes.planner_node import planner_node
from ..ai.nodes.preparation_node import preparation_node
from ..ai.schemas.tools_schema import PlannerOutput


class FakeRaw:
    usage_metadata = {"input_tokens": 3, "output_tokens": 2}


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


def test_planner_routes_weather_questions_to_weather_tool():
    parsed = PlannerOutput(
        need_tool=True,
        tool_calls=[{"tool_name": "weather", "arguments": {"city": "Dubai"}}],
        direct_answer=None,
        reasoning="Weather lookup is needed.",
    )
    state = preparation_node("1", "weather in Dubai", [])

    result = asyncio.run(planner_node(state, FakeLlm(parsed), "prompt"))

    assert result["need_tool"] is True
    assert result["tool_calls"][0].tool_name == "weather"
    assert result["reasoning"] == "Weather lookup is needed."


def test_planner_routes_factual_questions_to_web_search_tool():
    parsed = PlannerOutput(
        need_tool=True,
        tool_calls=[
            {"tool_name": "web_search", "arguments": {"query": "OpenAI CEO"}}
        ],
        direct_answer=None,
        reasoning="Web search is needed.",
    )
    state = preparation_node("1", "Who is the CEO of OpenAI?", [])

    result = asyncio.run(planner_node(state, FakeLlm(parsed), "prompt"))

    assert result["need_tool"] is True
    assert result["tool_calls"][0].tool_name == "web_search"


def test_planner_answers_simple_questions_directly():
    parsed = PlannerOutput(
        need_tool=False,
        tool_calls=[],
        direct_answer="Hello.",
        reasoning="No tool is needed.",
    )
    state = preparation_node("1", "hello", [])

    result = asyncio.run(planner_node(state, FakeLlm(parsed), "prompt"))

    assert result["need_tool"] is False
    assert result["tool_calls"] == []
    assert result["direct_answer"] == "Hello."
