from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from functools import lru_cache

from ..ai.agent import Agent
from ..ai.handleDB import get_history, save_message
from ..ai.history_cache import history_cache
from ..ai.schemas.graph_schema import GraphOutput
from ..config.db import get_db
from ..models import SenderType

router = APIRouter(prefix="/chat", tags=["chat"])


@lru_cache(maxsize=1)
def get_agent() -> Agent:
    return Agent()


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1)
    account_id: int
    user_id: int


@router.post("", response_model=GraphOutput)
async def chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
    agent: Agent = Depends(get_agent),
):
    try:
        question = request.question.strip()
        if not question:
            raise HTTPException(
                status_code=400, detail="Question cannot be empty")

        cache_key = f"history:{request.account_id}:{request.user_id}"

        history = history_cache.get(cache_key)
        if history is None:
            history = get_history(db, request.account_id,
                                  request.user_id) or []
            history_cache.set(cache_key, history)

        save_message(
            db=db,
            message=question,
            sender_type=SenderType.USER,
            account_id=request.account_id,
            user_id=request.user_id,
        )

        history = (history + [{"role": "user", "content": question}])[-15:]
        history_cache.set(cache_key, history)

        result = await agent.run(
            user_id=str(request.user_id),
            question=question,
            history=history,
        )

        save_message(
            db=db,
            message=result.answer,
            sender_type=SenderType.ASSISTANT,
            account_id=request.account_id,
            user_id=request.user_id,
        )

        history = (
            history + [{"role": "assistant", "content": result.answer}])[-15:]
        history_cache.set(cache_key, history)

        return result

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
