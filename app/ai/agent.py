import logging
import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

from ..config.logging import configure_logging
from .nodes.planner_node import planner_node
from .nodes.preparation_node import preparation_node
from .nodes.response_node import response_node
from .nodes.tool_node import tool_node
from .prompt import PLANNER_PROMPT, RESPONSE_PROMPT
from .schemas.graph_schema import GraphOutput
from .state import QAState


load_dotenv()
configure_logging()
logger = logging.getLogger(__name__)


def create_llm() -> ChatOpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY is missing")

    model = os.getenv("OPENAI_MODEL") or "gpt-4o-mini"

    return ChatOpenAI(
        model=model,
        api_key=api_key,
        temperature=0,
    )


class Agent:
    def __init__(self, llm: ChatOpenAI | None = None):
        self.llm = llm or create_llm()

    async def run(
        self,
        user_id: str,
        question: str,
        history: list[dict[str, str]] | None = None,
    ) -> GraphOutput:
        logger.info(
            "Agent run started",
            extra={"event": "agent.start", "user_id": user_id},
        )
        state = preparation_node(
            user_id=user_id,
            question=question,
            history=history or [],
        )

        state = await planner_node(state, self.llm, PLANNER_PROMPT)
        self._raise_if_error(state)

        if not state.get("need_tool", False):
            direct_answer = state.get("direct_answer")
            if direct_answer is None or not direct_answer.strip():
                state["error"] = "Planner returned no direct answer."
                self._raise_if_error(state)

            step_latency = state["step_latency"]
            total_latency = step_latency["retrieve"] + \
                step_latency["llm"]["total"]
            tokens = state["tokens"]

            final_output = GraphOutput(
                answer=direct_answer,
                reasoning=state.get("reasoning", ""),
                sources=state.get("sources", []),
                latency_ms={
                    "total": total_latency,
                    "by_step": step_latency,
                },
                tokens=tokens,
            )

            state["answer"] = direct_answer
            state["final_output"] = final_output
        else:
            state = await tool_node(state)
            self._raise_if_error(state)

            state = await response_node(state, self.llm, RESPONSE_PROMPT)
            self._raise_if_error(state)

        final_output = state["final_output"]
        logger.info(
            "Agent run completed",
            extra={
                "event": "agent.completed",
                "user_id": user_id,
                "duration_ms": final_output.latency_ms.total,
                "source_count": len(final_output.sources),
            },
        )

        return final_output

    @staticmethod
    def _raise_if_error(state: QAState) -> None:
        if state.get("error"):
            logger.error("Agent run failed", extra={"event": "agent.error"})
            raise RuntimeError(state["error"])
