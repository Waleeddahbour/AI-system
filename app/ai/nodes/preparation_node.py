from ..state import QAState


def preparation_node(user_id: str, question: str, history: list[dict[str, str]]) -> QAState:
    cleaned_question = question.strip()

    if not cleaned_question:
        raise ValueError("question cannot be empty")

    return {
        "user_id": user_id,
        "question": cleaned_question,
        "history": history or [],
        "need_tool": False,
        "direct_answer": "",
        "reasoning": "",
        "tool_calls": [],
        "tool_results": [],
        "sources": [],
        "step_latency": {
            "retrieve": 0,
            "llm": {
                "planner": 0,
                "response": 0,
                "total": 0,
            },
        },
        "tokens": {
            "planner": {
                "input": 0,
                "output": 0,
            },
            "response": {
                "input": 0,
                "output": 0,
            },
            "total": {
                "input": 0,
                "output": 0,
            },
        },
    }
