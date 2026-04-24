import logging
import time

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder


from ..state import QAState
from ..schemas.tools_schema import PlannerOutput


logger = logging.getLogger(__name__)


async def planner_node(state: QAState, llm, planner_prompt: str) -> QAState:
    question = state["question"]
    history = state.get("history", [])

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", "{planner_prompt}"),
            MessagesPlaceholder("history"),
            ("human", "{question}"),
        ]
    )
    messages = prompt.invoke(
        {
            "planner_prompt": planner_prompt,
            "history": history,
            "question": question,
        }
    ).to_messages()

    structured_llm = llm.with_structured_output(
        PlannerOutput, method="function_calling", include_raw=True)

    started_at = time.perf_counter()

    logger.info(
        "Planner started",
        extra={
            "event": "planner.started",
            "question_length": len(question),
            "history_count": len(history),
        },
    )

    try:
        response = await structured_llm.ainvoke(messages)
    except Exception as exc:
        duration_ms = int((time.perf_counter() - started_at) * 1000)
        logger.exception(
            "Planner LLM call failed",
            extra={
                "event": "planner.llm_failed",
                "question_length": len(question),
                "history_count": len(history),
                "duration_ms": duration_ms,
                "error_type": type(exc).__name__,
            },
        )
        state["error"] = f"Planner LLM call failed: {exc}"
        return state
    duration_ms = int((time.perf_counter() - started_at) * 1000)

    parsed = response.get("parsed")
    raw = response.get("raw")
    parsing_error = response.get("parsing_error")

    if parsing_error:
        logger.error(
            "Planner parsing failed",
            extra={
                "event": "planner.parsing_failed",
                "question_length": len(question),
                "history_count": len(history),
                "duration_ms": duration_ms,
                "parsing_error": str(parsing_error),
            },
        )
        state["error"] = f"Planner parsing failed: {parsing_error}"
        return state
    if parsed is None:
        logger.error(
            "Planner returned no parsed output",
            extra={
                "event": "planner.parsed_missing",
                "question_length": len(question),
                "history_count": len(history),
                "duration_ms": duration_ms,
            },
        )
        state["error"] = "Planner returned no parsed output."
        return state

    state["need_tool"] = parsed.need_tool
    state["direct_answer"] = parsed.direct_answer
    state["reasoning"] = parsed.reasoning
    state["tool_calls"] = parsed.tool_calls if parsed.need_tool else []

    usage = getattr(raw, "usage_metadata", None) or {}
    planner_input_tokens = usage.get("input_tokens", 0)
    planner_output_tokens = usage.get("output_tokens", 0)

    step_latency = state["step_latency"]
    step_latency["llm"]["planner"] = duration_ms
    step_latency["llm"]["total"] = (
        step_latency["llm"]["planner"] + step_latency["llm"]["response"]
    )
    state["step_latency"] = step_latency

    tokens = state["tokens"]
    tokens["planner"] = {
        "input": planner_input_tokens,
        "output": planner_output_tokens,
    }
    tokens["total"] = {
        "input": tokens["planner"]["input"] + tokens["response"]["input"],
        "output": tokens["planner"]["output"] + tokens["response"]["output"],
    }

    state["tokens"] = tokens
    logger.info(
        "Planner completed",
        extra={
            "event": "planner.completed",
            "need_tool": parsed.need_tool,
            "tool_count": len(state["tool_calls"]),
            "duration_ms": duration_ms,
            "input_tokens": planner_input_tokens,
            "output_tokens": planner_output_tokens,
        },
    )

    return state
