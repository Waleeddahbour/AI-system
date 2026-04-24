from sqlalchemy import Column, String, Integer, DateTime, func
from sqlalchemy.orm import relationship

from ..config.db import Base


class AccountModel(Base):
    __tablename__ = 'accounts'

    # COLUMNS
    id = Column(Integer, primary_key=True, nullable=False)
    name = Column(String(255), nullable=False, unique=True)
    created_at = Column(DateTime(timezone=True),
                        server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(),
                        onupdate=func.now(), nullable=False)

    # RELATIONSHIPS
    users = relationship("UserModel", back_populates="account",
                         cascade="all, delete-orphan")
    messages = relationship(
        "ChatMessages", back_populates="account", cascade="all, delete-orphan")
