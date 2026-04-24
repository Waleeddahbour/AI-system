from sqlalchemy.orm import Session
from typing import cast
from ..models import ChatMessages, SenderType


def save_message(
    db: Session, message: str, sender_type: SenderType, account_id: int, user_id: int
) -> ChatMessages:
    chat_message = ChatMessages(
        message=message, sender_type=sender_type, account_id=account_id, user_id=user_id
    )
    db.add(chat_message)
    db.commit()
    db.refresh(chat_message)
    return chat_message


def get_history(db: Session, account_id: int, user_id: int) -> list[dict[str, str]]:
    messages = (
        db.query(ChatMessages)
        .filter(
            ChatMessages.account_id == account_id,
            ChatMessages.user_id == user_id,
        )
        .order_by(ChatMessages.created_at.desc(), ChatMessages.id.desc())
        .limit(15)
        .all()
    )
    messages.reverse()

    role_map = {
        SenderType.USER: "user",
        SenderType.ASSISTANT: "assistant",
    }

    history: list[dict[str, str]] = []

    for message in messages:
        sender_type = cast(SenderType, message.sender_type)
        content = cast(str, message.message)

        history.append(
            {
                "role": role_map[sender_type],
                "content": content,
            }
        )

    return history
