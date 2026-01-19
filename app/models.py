import uuid
from datetime import datetime

from sqlalchemy import Column, String, DateTime, Index
from sqlalchemy.orm import validates

from app.database import Base


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    room_id = Column(String, nullable=False, index=True)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    user_name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_bookings_room_time", "room_id", "start_time", "end_time"),
    )

    @validates("start_time", "end_time")
    def validate_times(self, key, value):
        if isinstance(value, str):
            return datetime.fromisoformat(value)
        return value

    def __repr__(self):
        return f"<Booking(id={self.id}, room={self.room_id}, user={self.user_name})>"
