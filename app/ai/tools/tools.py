import os
from dotenv import load_dotenv
import httpx
import asyncio
import logging
from pydantic import HttpUrl, TypeAdapter
from ..schemas.tools_schema import (
    WeatherInput,
    WeatherOutput,
    WebSearchInput,
    WebSearchOutput,
    SearchSource,
)

load_dotenv()
DUCKDUCKGO_URL = os.getenv("DUCKDUCKGO_URL", "https://api.duckduckgo.com/")
http_url_adapter = TypeAdapter(HttpUrl)
logger = logging.getLogger(__name__)


async def web_search_tool(args: WebSearchInput) -> WebSearchOutput:
    data = None
    last_error: Exception | None = None

    for attempt in range(3):
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    DUCKDUCKGO_URL,
                    params={
                        "q": args.query,
                        "format": "json",
                        "no_html": 1,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                break

        except (httpx.RequestError, httpx.HTTPStatusError, ValueError) as exc:
            last_error = exc
            logger.warning(
                "Web search request failed",
                extra={
                    "event": "web_search.retry",
                    "attempt": attempt + 1,
                    "error_type": type(exc).__name__,
                },
            )
            if attempt < 2:
                await asyncio.sleep(0.25 * (2 ** attempt))

    if data is None:
        logger.error(
            "Web search failed after retries",
            extra={
                "event": "web_search.failed",
                "error_type": type(last_error).__name__ if last_error else None,
            },
        )
        return WebSearchOutput(
            results=[],
            error=f"web_search_failed: {type(last_error).__name__}",
        )

    results: list[SearchSource] = []
    seen_urls: set[str] = set()

    def add_result(name: str, url: str, snippet: str) -> None:
        if not url or url in seen_urls:
            return

        try:
            validated_url = http_url_adapter.validate_python(url)
        except Exception:
            return

        seen_urls.add(url)
        results.append(
            SearchSource(
                name=name[:60] if name else "DuckDuckGo",
                url=validated_url,
                snippet=snippet,
            )
        )

    abstract_url = data.get("AbstractURL")
    abstract_text = data.get("AbstractText")
    heading = data.get("Heading")
    if abstract_url and abstract_text:
        add_result(heading or "DuckDuckGo", abstract_url, abstract_text)

    related_topics = data.get("RelatedTopics", [])
    if isinstance(related_topics, list):
        for topic in related_topics:
            if not isinstance(topic, dict):
                continue

            first_url = topic.get("FirstURL")
            text = topic.get("Text")
            if first_url and text:
                add_result(text, first_url, text)
                continue

            subtopics = topic.get("Topics", [])
            if isinstance(subtopics, list):
                for subtopic in subtopics:
                    if not isinstance(subtopic, dict):
                        continue
                    first_url = subtopic.get("FirstURL")
                    text = subtopic.get("Text")
                    if first_url and text:
                        add_result(text, first_url, text)

    results = results[:5]
    logger.info(
        "Web search completed",
        extra={"event": "web_search.completed", "source_count": len(results)},
    )
    return WebSearchOutput(results=results)


async def weather_tool(args: WeatherInput) -> WeatherOutput:
    # a dummy weather tool for now
    fake_weather = {
        "dubai": {"temp_c": 34.0, "condition": "Sunny"},
        "abu dhabi": {"temp_c": 33.0, "condition": "Hot and clear"},
        "doha": {"temp_c": 31.0, "condition": "Windy"},
        "london": {"temp_c": 15.0, "condition": "Cloudy"},
    }

    city_key = args.city.strip().lower()
    weather = fake_weather.get(
        city_key,
        {"temp_c": 0.0, "condition": "Unsupported city in dummy weather tool"}
    )
    if city_key not in fake_weather:
        logger.info(
            "Weather lookup returned unsupported city",
            extra={"event": "weather.unsupported_city"},
        )

    return WeatherOutput(
        city=args.city,
        temp_c=weather['temp_c'],
        condition=weather['condition'],
        source_name='Dummy Weather Tool',
        source_url='https://example.com/dummy-weather',
        error="unsupported_city" if city_key not in fake_weather else None,

    )


TOOL_REGISTRY = {
    "web_search": {
        "description": "Search the web for factual or recent information",
        "input_model": WebSearchInput,
        "handler": web_search_tool,
        "cache_ttl_seconds": 300,
    },
    "weather": {
        "description": "Get current weather for a city using a dummy weather tool",
        "input_model": WeatherInput,
        "handler": weather_tool,
        "cache_ttl_seconds": 600,
    },
}
