import enum

from sqlalchemy import Column, ForeignKey, Integer, String, DateTime, Enum, func
from sqlalchemy.orm import relationship
from ..config.db import Base


class SenderType(enum.Enum):
    ASSISTANT = "ASSISTANT"
    USER = "USER"


class ChatMessages(Base):
    __tablename__ = "messages"

    # COLUMNS
    id = Column(Integer, primary_key=True, nullable=False)
    message = Column(String, nullable=False)
    sender_type = Column(Enum(SenderType), nullable=False,
                         default=SenderType.USER)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True),
                        server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(),
                        server_default=func.now(), nullable=False)

    # RELATIONSHIPS
    account = relationship("AccountModel", back_populates="messages")
    user = relationship("UserModel", back_populates="messages")
