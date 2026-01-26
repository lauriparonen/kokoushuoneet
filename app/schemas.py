from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field, field_validator, model_validator

# Finnish timezone for the client (EET/EEST - UTC+2/UTC+3 with DST)
FINNISH_TZ = ZoneInfo("Europe/Helsinki")


class BookingCreate(BaseModel):
    room_id: str = Field(..., min_length=1, max_length=50, description="Room identifier")
    start_time: datetime = Field(..., description="Booking start time")
    end_time: datetime = Field(..., description="Booking end time")
    user_name: str = Field(..., min_length=1, max_length=100, description="Name of the person booking")

    @field_validator("start_time", "end_time", mode="before")
    @classmethod
    def normalize_to_finnish_time(cls, v):
        """Normalize all datetime inputs to timezone-aware Finnish time."""
        if isinstance(v, str):
            # Parse ISO format string
            dt = datetime.fromisoformat(v.replace('Z', '+00:00'))
        else:
            dt = v

        # If naive, assume Finnish timezone (Europe/Helsinki)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=FINNISH_TZ)
        else:
            # Convert to Finnish timezone
            dt = dt.astimezone(FINNISH_TZ)

        return dt

    @field_validator("room_id", "user_name")
    @classmethod
    def validate_not_whitespace(cls, v):
        """Ensure strings are not empty or whitespace-only."""
        if not v or not v.strip():
            raise ValueError("Field cannot be empty or whitespace-only")
        return v.strip()

    @model_validator(mode="after")
    def validate_time_range(self):
        """Validate that start_time is before end_time and bookings are reasonable."""
        if self.start_time >= self.end_time:
            raise ValueError("start_time must be before end_time")

        # Prevent extremely short bookings (less than 15 minutes)
        duration = self.end_time - self.start_time
        if duration < timedelta(minutes=15):
            raise ValueError("Booking duration must be at least 15 minutes")

        # Enforce maximum continuous duration (4 hours)
        if duration > timedelta(hours=4):
            raise ValueError("Booking duration cannot exceed 4 hours")

        # Prevent bookings too far in the future (more than 90 days)
        now = datetime.now(FINNISH_TZ)
        if self.start_time > now + timedelta(days=90):
            raise ValueError("Cannot create bookings more than 90 days in the future")

        return self


class BookingResponse(BaseModel):
    id: str
    room_id: str
    start_time: datetime
    end_time: datetime
    user_name: str
    created_at: datetime

    model_config = {"from_attributes": True}


class BookingListResponse(BaseModel):
    bookings: list[BookingResponse]
    count: int
