import asyncio
import logging
import time
import json
import os


from ..state import QAState
from ..schemas.graph_schema import Source
from ..schemas.tools_schema import WeatherOutput, WebSearchOutput
from ..tools.tools import TOOL_REGISTRY


logger = logging.getLogger(__name__)

_tool_cache: dict[str, tuple[float, object]] = {}
_tool_semaphore = asyncio.Semaphore(
    int(os.getenv("TOOL_CONCURRENCY_LIMIT", "5"))
)


def make_tool_cache_key(tool_name: str, arguments) -> str:
    if hasattr(arguments, "model_dump"):
        payload = arguments.model_dump(mode="json")
    else:
        payload = arguments

    return json.dumps(
        {"tool_name": tool_name, "arguments": payload},
        sort_keys=True,
        default=str,
    )


def extract_sources(result: WebSearchOutput | WeatherOutput) -> list[Source]:
    if isinstance(result, WebSearchOutput):
        return [Source(name=item.name, url=item.url) for item in result.results]

    if isinstance(result, WeatherOutput):
        return [Source(name=result.source_name, url=result.source_url)]

    return []


async def run_tool_call(tool_call):
    async with _tool_semaphore:
        tool_name = tool_call.tool_name
        started_at = time.perf_counter()
        logger.info(
            "Tool call started",
            extra={"event": "tool.started", "tool_name": tool_name},
        )
        tool_entry = TOOL_REGISTRY.get(tool_name)
        if tool_entry is None:
            raise ValueError(f"Unsupported tool: {tool_name}")

        input_model = tool_entry["input_model"]
        handler = tool_entry["handler"]
        arguments = tool_call.arguments
        if hasattr(arguments, "model_dump"):
            arguments = arguments.model_dump()
        validated_args = input_model(**arguments)

        cache_ttl = tool_entry.get("cache_ttl_seconds")
        cache_key = make_tool_cache_key(tool_name, validated_args)

        if cache_ttl:
            cached = _tool_cache.get(cache_key)
            if cached:
                expires_at, cached_result = cached
                if time.time() < expires_at:
                    logger.info(
                        "Tool cache hit",
                        extra={
                            "event": "tool.cache_hit",
                            "tool_name": tool_name,
                        },
                    )
                    return cached_result
                del _tool_cache[cache_key]

        result = await handler(validated_args)

        if cache_ttl and not getattr(result, "error", None):
            _tool_cache[cache_key] = (time.time() + cache_ttl, result)

        duration_ms = int((time.perf_counter() - started_at) * 1000)
        logger.info(
            "Tool call completed",
            extra={
                "event": "tool.completed",
                "tool_name": tool_name,
                "duration_ms": duration_ms,
                "source_count": len(extract_sources(result)),
            },
        )
        return result


async def tool_node(state: QAState) -> QAState:
    tool_calls = state.get("tool_calls")
    if not tool_calls:
        state["error"] = "No tools calls found in state"
        logger.error(
            "Tool execution skipped because no tool calls were provided",
            extra={"event": "tools.missing"},
        )
        return state

    sources = []
    started_at = time.perf_counter()
    logger.info(
        "Parallel tool execution started",
        extra={"event": "tools.started", "tool_count": len(tool_calls)},
    )

    tool_results = await asyncio.gather(
        *(run_tool_call(tool_call) for tool_call in tool_calls),
        return_exceptions=True,
    )

    successful_results = []

    for result in tool_results:
        if isinstance(result, Exception):
            logger.error(
                "Tool execution failed",
                extra={
                    "event": "tool.failed",
                    "error_type": type(result).__name__,
                },
                exc_info=result,
            )
            continue

        successful_results.append(result)
        sources.extend(extract_sources(result))

    if not successful_results:
        state["error"] = "All tool calls failed."
        duration_ms = int((time.perf_counter() - started_at) * 1000)
        logger.error(
            "All tool calls failed",
            extra={
                "event": "tools.failed",
                "tool_count": len(tool_calls),
                "duration_ms": duration_ms,
            },
        )
        return state

    duration_ms = int((time.perf_counter() - started_at) * 1000)

    state["tool_results"] = successful_results
    state["sources"] = sources
    state["step_latency"]["retrieve"] = duration_ms
    logger.info(
        "Parallel tool execution completed",
        extra={
            "event": "tools.completed",
            "tool_count": len(successful_results),
            "source_count": len(sources),
            "duration_ms": duration_ms,
        },
    )
    return state
