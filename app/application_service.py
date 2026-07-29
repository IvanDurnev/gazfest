import re
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.max_webapp_auth import MaxMiniAppUser
from app.models import FestivalUser, ParticipationApplication


class DuplicateApplicationError(ValueError):
    pass


class ParticipationApplicationRequest(BaseModel):
    activity: Literal["ride", "stars"]
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    age: int | None = Field(default=None, ge=6, le=100)
    equipment: Literal["bicycle", "rollers", "skate", "other"] | None = None
    equipment_other: str | None = Field(default=None, max_length=100)
    phone: str | None = Field(default=None, max_length=32)
    performance_description: str | None = Field(default=None, max_length=2000)

    @field_validator("first_name", "last_name")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("field cannot be empty")
        return value

    @field_validator(
        "equipment_other",
        "phone",
        "performance_description",
    )
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        return value.strip() if value else None

    @model_validator(mode="after")
    def validate_activity_fields(self):
        if self.activity == "ride":
            if self.age is None or self.equipment is None:
                raise ValueError("age and equipment are required for ride")
            if self.equipment == "other" and not self.equipment_other:
                raise ValueError("custom equipment is required")
        else:
            phone_digits = re.sub(r"\D", "", self.phone or "")
            if not 10 <= len(phone_digits) <= 15:
                raise ValueError("valid phone is required")
            if not self.performance_description:
                raise ValueError("performance description is required")

        return self


def create_participation_application(
    data: ParticipationApplicationRequest,
    *,
    max_user: MaxMiniAppUser,
) -> ParticipationApplication:
    user = db.session.get(FestivalUser, max_user.user_id)
    if user is None:
        started_at = datetime.fromtimestamp(max_user.auth_date, tz=UTC)
        user = FestivalUser(
            max_user_id=max_user.user_id,
            chat_id=max_user.chat_id or max_user.user_id,
            first_name=max_user.first_name,
            last_name=max_user.last_name,
            username=max_user.username,
            first_started_at=started_at,
            last_started_at=started_at,
        )
        db.session.add(user)

    application = ParticipationApplication(
        max_user_id=max_user.user_id,
        activity=data.activity,
        first_name=data.first_name,
        last_name=data.last_name,
        age=data.age if data.activity == "ride" else None,
        equipment=data.equipment if data.activity == "ride" else None,
        equipment_other=(
            data.equipment_other
            if data.activity == "ride" and data.equipment == "other"
            else None
        ),
        phone=data.phone if data.activity == "stars" else None,
        performance_description=(
            data.performance_description if data.activity == "stars" else None
        ),
    )
    db.session.add(application)

    try:
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        raise DuplicateApplicationError from exc
    except Exception:
        db.session.rollback()
        raise

    return application


def list_participation_applications(
    max_user_id: int,
) -> list[ParticipationApplication]:
    return list(
        db.session.scalars(
            select(ParticipationApplication)
            .where(ParticipationApplication.max_user_id == max_user_id)
            .order_by(ParticipationApplication.created_at.desc())
        )
    )
