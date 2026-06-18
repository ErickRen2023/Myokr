from datetime import date

from sqlalchemy import BigInteger, Date, Integer, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Cycle(Base, TimestampMixin):
    __tablename__ = "cycle"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    type: Mapped[int] = mapped_column(SmallInteger, nullable=False, comment="1=monthly 2=bimonthly 3=quarterly 4=half_year 5=yearly")
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0, comment="0=active 1=completed")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "start_date": str(self.start_date),
            "end_date": str(self.end_date),
            "status": self.status,
        }
