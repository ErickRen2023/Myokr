from sqlalchemy import BigInteger, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class CycleReview(Base, TimestampMixin):
    __tablename__ = "cycle_review"

    cycle_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    highlights: Mapped[str] = mapped_column(Text, nullable=False, default="")
    blockers: Mapped[str] = mapped_column(Text, nullable=False, default="")
    learnings: Mapped[str] = mapped_column(Text, nullable=False, default="")
    next_steps: Mapped[str] = mapped_column(Text, nullable=False, default="")

    def to_dict(self) -> dict:
        return {
            "cycle_id": self.cycle_id,
            "summary": self.summary,
            "highlights": self.highlights,
            "blockers": self.blockers,
            "learnings": self.learnings,
            "next_steps": self.next_steps,
            "updated_at": self.update_time.isoformat() if self.update_time else None,
        }
