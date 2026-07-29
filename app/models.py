from datetime import datetime
from typing import Literal

from pydantic import BaseModel
from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db


class Sender(BaseModel):
    user_id: int
    first_name: str | None = None
    last_name: str | None = None
    username: str | None = None
    is_bot: bool = False
    last_activity_time: int | None = None


class Recipient(BaseModel):
    chat_id: int | None = None
    chat_type: str


class MessageBody(BaseModel):
    mid: str
    text: str | None = None


class Message(BaseModel):
    sender: Sender | None = None
    recipient: Recipient
    body: MessageBody


class MessageCreatedUpdate(BaseModel):
    update_type: Literal["message_created"]
    timestamp: int
    message: Message


class BotStartedUpdate(BaseModel):
    update_type: Literal["bot_started"]
    timestamp: int
    chat_id: int
    user: Sender


class FestivalUser(db.Model):
    __tablename__ = "users"

    max_user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    first_name: Mapped[str | None] = mapped_column(String(255))
    last_name: Mapped[str | None] = mapped_column(String(255))
    username: Mapped[str | None] = mapped_column(
        String(255),
        unique=True,
        index=True,
    )
    first_started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    last_started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )


class ParticipationApplication(db.Model):
    __tablename__ = "participation_applications"
    __table_args__ = (
        UniqueConstraint(
            "max_user_id",
            "activity",
            name="uq_participation_application_user_activity",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    max_user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.max_user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    activity: Mapped[str] = mapped_column(String(32), nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    age: Mapped[int | None] = mapped_column(Integer)
    equipment: Mapped[str | None] = mapped_column(String(32))
    equipment_other: Mapped[str | None] = mapped_column(String(100))
    phone: Mapped[str | None] = mapped_column(String(32))
    performance_description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="new",
        server_default="new",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
