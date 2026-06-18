from sqlalchemy import BigInteger, Boolean, Integer, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Milestone(Base, TimestampMixin):
    __tablename__ = "milestone"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    key_result_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_deleted: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0, comment="0=not deleted 1=deleted")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "description": self.description,
            "completed": self.completed,
            "sort_order": self.sort_order,
            "is_deleted": self.is_deleted,
        }
