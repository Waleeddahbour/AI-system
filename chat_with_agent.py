import asyncio
import json
import time

from app.ai.handleDB import get_history, save_message
from app.ai.history_cache import history_cache
from app.ai.agent import Agent
from app.config.db import sessionLocal
from app.models import SenderType


ACCOUNT_ID = 1
USER_ID = 1


def print_result(result, wall_ms: int) -> None:
    payload = result.model_dump(mode="json")
    payload["manual_wall_ms"] = wall_ms
    print(json.dumps(payload, indent=2))


async def main() -> None:
    agent = Agent()
    db = sessionLocal()
    cache_key = f"history:{ACCOUNT_ID}:{USER_ID}"

    print("Manual agent chat test. Type 'exit' to stop. Ctrl+D or Ctrl+C also exits.")
    print(f"Using account_id={ACCOUNT_ID}, user_id={USER_ID}")

    try:
        while True:
            try:
                question = input("\nYou: ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break

            if question.lower() in {"exit", "quit"}:
                break
            if not question:
                continue

            started_at = time.perf_counter()
            try:
                history = history_cache.get(cache_key)
                if history is None:
                    history = get_history(db, ACCOUNT_ID, USER_ID) or []
                    history_cache.set(cache_key, history)

                save_message(
                    db=db,
                    message=question,
                    sender_type=SenderType.USER,
                    account_id=ACCOUNT_ID,
                    user_id=USER_ID,
                )

                history = (
                    history + [{"role": "user", "content": question}])[-15:]
                history_cache.set(cache_key, history)

                result = await agent.run(
                    user_id=str(USER_ID),
                    question=question,
                    history=history,
                )

                save_message(
                    db=db,
                    message=result.answer,
                    sender_type=SenderType.ASSISTANT,
                    account_id=ACCOUNT_ID,
                    user_id=USER_ID,
                )

                history = (
                    history + [{"role": "assistant", "content": result.answer}]
                )[-15:]
                history_cache.set(cache_key, history)
            except Exception as exc:
                print(f"\nAgent error: {type(exc).__name__}: {exc}")
                continue

            wall_ms = int((time.perf_counter() - started_at) * 1000)

            print("\nAgent:")
            print_result(result, wall_ms=wall_ms)
    finally:
        db.close()


try:
    asyncio.run(main())
except KeyboardInterrupt:
    print()
