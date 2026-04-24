from typing import TypedDict, NotRequired, Literal, List

from .schemas.graph_schema import GraphOutput, Source
from .schemas.tools_schema import ToolCall, WeatherOutput, WebSearchOutput

ToolName = Literal["weather", "web_search"]
ToolResult = WebSearchOutput | WeatherOutput


class LlmLatencyState(TypedDict):
    planner: int
    response: int
    total: int


class StepLatencyState(TypedDict):
    retrieve: int
    llm: LlmLatencyState


class TokenUsageState(TypedDict):
    input: int
    output: int


class TokenState(TypedDict):
    planner: TokenUsageState
    response: TokenUsageState
    total: TokenUsageState


class QAState(TypedDict):
    # input
    user_id: str
    question: str
    history: list[dict[str, str,]]

    # planner
    need_tool: NotRequired[bool]
    direct_answer: NotRequired[str | None]
    reasoning: NotRequired[str]
    tool_calls: NotRequired[List[ToolCall]]
    tool_results: NotRequired[List[ToolResult]]
    sources: NotRequired[list[Source]]

    # response
    answer: NotRequired[str]
    final_output: NotRequired[GraphOutput]

    # metrics
    step_latency: NotRequired[StepLatencyState]
    tokens: NotRequired[TokenState]
    error: NotRequired[str]
