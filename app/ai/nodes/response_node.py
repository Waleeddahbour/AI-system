import json
import logging
import time

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from ..state import QAState
from ..schemas.graph_schema import GraphOutput, ResponseOutput


logger = logging.getLogger(__name__)


async def response_node(state: QAState, llm, response_prompt: str) -> QAState:
    question = state["question"]
    tool_results = state.get("tool_results", [])
    history = state.get("history", [])

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", "{response_prompt}"),
            MessagesPlaceholder("history"),
            (
                "human",
                "User question:\n{question}\n\nTool results:\n{tool_results}",
            ),
        ]
    )

    tool_results_payload = json.dumps(
        [result.model_dump(mode="json") for result in tool_results],
        indent=2,
        default=str,
    )

    messages = prompt.invoke(
        {
            "response_prompt": response_prompt,
            "history": history,
            "question": question,
            "tool_results": tool_results_payload,
        }
    ).to_messages()

    structured_llm = llm.with_structured_output(
        ResponseOutput, method="function_calling", include_raw=True)

    started_at = time.perf_counter()
    logger.info(
        "Response generation started",
        extra={
            "event": "response.started",
            "question_length": len(question),
            "history_count": len(history),
            "tool_count": len(tool_results),
        },
    )

    try:
        response = await structured_llm.ainvoke(messages)
    except Exception as exc:
        duration_ms = int((time.perf_counter() - started_at) * 1000)
        logger.exception(
            "Response LLM call failed",
            extra={
                "event": "response.llm_failed",
                "question_length": len(question),
                "history_count": len(history),
                "tool_count": len(tool_results),
                "duration_ms": duration_ms,
                "error_type": type(exc).__name__,
            },
        )
        state["error"] = f"Response LLM call failed: {exc}"
        return state

    duration_ms = int((time.perf_counter() - started_at) * 1000)

    parsed = response.get("parsed")
    raw = response.get("raw")
    parsing_error = response.get("parsing_error")

    if parsing_error:
        logger.error(
            "Response parsing failed",
            extra={
                "event": "response.parsing_failed",
                "question_length": len(question),
                "history_count": len(history),
                "tool_count": len(tool_results),
                "duration_ms": duration_ms,
                "parsing_error": str(parsing_error),
            },
        )
        state["error"] = f"Response parsing failed: {parsing_error}"
        return state

    if parsed is None:
        logger.error(
            "Response returned no parsed output",
            extra={
                "event": "response.parsed_missing",
                "question_length": len(question),
                "history_count": len(history),
                "tool_count": len(tool_results),
                "duration_ms": duration_ms,
            },
        )
        state["error"] = "Response returned no parsed output."
        return state

    answer = parsed.answer.strip()
    sources = parsed.sources

    step_latency = state["step_latency"]
    step_latency["llm"]["response"] = duration_ms
    step_latency["llm"]["total"] = (
        step_latency["llm"]["planner"] + step_latency["llm"]["response"]
    )
    total_latency = step_latency["retrieve"] + step_latency["llm"]["total"]

    usage = getattr(raw, "usage_metadata", None) or {}
    response_input_tokens = usage.get("input_tokens", 0)
    response_output_tokens = usage.get("output_tokens", 0)

    tokens = state["tokens"]
    tokens["response"] = {
        "input": response_input_tokens,
        "output": response_output_tokens,
    }
    tokens["total"] = {
        "input": tokens["planner"]["input"] + tokens["response"]["input"],
        "output": tokens["planner"]["output"] + tokens["response"]["output"],
    }

    final_output = GraphOutput(
        answer=answer,
        reasoning=state.get("reasoning", ""),
        sources=sources,
        latency_ms={
            "total": total_latency,
            "by_step": step_latency,
        },
        tokens=tokens,
    )

    state["answer"] = answer
    state["final_output"] = final_output
    state["step_latency"] = step_latency
    state["tokens"] = tokens
    logger.info(
        "Response generated",
        extra={
            "event": "response.completed",
            "duration_ms": duration_ms,
            "source_count": len(sources),
            "answer_length": len(answer),
            "input_tokens": response_input_tokens,
            "output_tokens": response_output_tokens,
        },
    )

    return state
