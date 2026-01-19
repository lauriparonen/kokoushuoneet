from datetime import datetime

from pydantic import BaseModel, Field, field_validator, model_validator


class BookingCreate(BaseModel):
    room_id: str = Field(..., min_length=1, description="Room identifier")
    start_time: datetime = Field(..., description="Booking start time")
    end_time: datetime = Field(..., description="Booking end time")
    user_name: str = Field(..., min_length=1, description="Name of the person booking")

    @model_validator(mode="after")
    def validate_time_range(self):
        if self.start_time >= self.end_time:
            raise ValueError("start_time must be before end_time")
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
