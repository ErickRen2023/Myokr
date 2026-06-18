from typing import Optional

from sqlalchemy import BigInteger, Boolean, SmallInteger, String, Text
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class KeyResult(Base, TimestampMixin):
    __tablename__ = "key_result"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    objective_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    description: Mapped[str] = mapped_column(String(1000), nullable=False)
    type: Mapped[int] = mapped_column(SmallInteger, nullable=False, comment="1=numeric 2=milestone 3=boolean")
    target: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    current_value: Mapped[Optional[float]] = mapped_column(nullable=True)
    is_achieved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0, comment="0=active 1=archived")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "description": self.description,
            "type": self.type,
            "target": self.target,
            "current_value": self.current_value,
            "is_achieved": self.is_achieved,
            "status": self.status,
        }
