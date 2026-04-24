import enum

from sqlalchemy import Column, Enum, ForeignKey, Integer, String, DateTime, func
from sqlalchemy.orm import relationship
from ..config.db import Base


class UserRole(enum.Enum):
    SUPER_ADMIN = "SUPER_ADMIN"
    ADMIN = "ADMIN"
    USER = "USER"


class UserModel(Base):
    __tablename__ = "users"

    # COLUMNS
    id = Column(Integer, primary_key=True, nullable=False)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    username = Column(String, nullable=False, unique=True)
    email = Column(String, nullable=False, unique=True)
    password = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), nullable=False,
                  server_default=UserRole.USER.value)
    created_at = Column(DateTime(timezone=True),
                        server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(),
                        server_default=func.now(), nullable=False)

    # RELATIONSHIPS
    account = relationship("AccountModel", back_populates="users")
    messages = relationship(
        "ChatMessages", back_populates="user", cascade="all, delete-orphan")
