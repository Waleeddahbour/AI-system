import asyncio

import httpx

from ..ai.nodes.preparation_node import preparation_node
from ..ai.nodes import tool_node as tool_node_module
from ..ai.nodes.tool_node import run_tool_call, tool_node
from ..ai.schemas.tools_schema import (
    WeatherInput,
    WeatherToolCall,
    WebSearchInput,
    WebSearchToolCall,
)
from ..ai.tools.tools import weather_tool, web_search_tool


class FakeResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return {
            "AbstractURL": "https://example.com/openai",
            "AbstractText": "OpenAI is an AI research company.",
            "Heading": "OpenAI",
            "RelatedTopics": [],
        }


class FakeAsyncClient:
    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def get(self, *args, **kwargs):
        return FakeResponse()


class FailingAsyncClient(FakeAsyncClient):
    attempts = 0

    async def get(self, *args, **kwargs):
        FailingAsyncClient.attempts += 1
        raise httpx.RequestError("network failed")


def test_weather_tool_returns_supported_city_weather():
    result = asyncio.run(weather_tool(WeatherInput(city="Dubai")))

    assert result.temp_c == 34.0
    assert result.error is None


def test_weather_tool_marks_unsupported_city_as_error():
    result = asyncio.run(weather_tool(WeatherInput(city="Atlantis")))

    assert result.error == "unsupported_city"


def test_web_search_tool_returns_sources_from_duckduckgo_response(monkeypatch):
    monkeypatch.setattr(
        "app.ai.tools.tools.httpx.AsyncClient", FakeAsyncClient)

    result = asyncio.run(web_search_tool(WebSearchInput(query="OpenAI")))

    assert result.error is None
    assert result.results[0].name == "OpenAI"
    assert str(result.results[0].url) == "https://example.com/openai"


def test_web_search_tool_retries_and_returns_error_on_failure(monkeypatch):
    FailingAsyncClient.attempts = 0
    monkeypatch.setattr(
        "app.ai.tools.tools.httpx.AsyncClient", FailingAsyncClient)

    result = asyncio.run(web_search_tool(WebSearchInput(query="OpenAI")))

    assert FailingAsyncClient.attempts == 3
    assert result.results == []
    assert result.error.startswith("web_search_failed")


def test_tool_node_uses_cache_for_repeated_tool_calls(monkeypatch):
    calls = {"count": 0}

    async def fake_handler(args):
        calls["count"] += 1
        return await weather_tool(args)

    monkeypatch.setitem(
        tool_node_module.TOOL_REGISTRY,
        "weather",
        {
            "input_model": WeatherInput,
            "handler": fake_handler,
            "cache_ttl_seconds": 300,
        },
    )
    tool_node_module._tool_cache.clear()
    tool_call = WeatherToolCall(
        tool_name="weather",
        arguments=WeatherInput(city="Dubai"),
    )

    asyncio.run(run_tool_call(tool_call))
    asyncio.run(run_tool_call(tool_call))

    assert calls["count"] == 1


def test_tool_node_handles_partial_tool_failures(monkeypatch):
    async def failing_handler(args):
        raise RuntimeError("failed")

    monkeypatch.setitem(
        tool_node_module.TOOL_REGISTRY,
        "web_search",
        {
            "input_model": WebSearchInput,
            "handler": failing_handler,
            "cache_ttl_seconds": 0,
        },
    )
    state = preparation_node("1", "tools", [])
    state["tool_calls"] = [
        WeatherToolCall(
            tool_name="weather",
            arguments=WeatherInput(city="Dubai"),
        ),
        WebSearchToolCall(
            tool_name="web_search",
            arguments=WebSearchInput(query="OpenAI"),
        ),
    ]

    result = asyncio.run(tool_node(state))

    assert "error" not in result
    assert len(result["tool_results"]) == 1
