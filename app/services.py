from datetime import datetime

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.models import Booking
from app.schemas import BookingCreate
from app.exceptions import BookingNotFoundError, BookingConflictError, BookingValidationError


class BookingService:
    def __init__(self, db: Session):
        self.db = db

    def create_booking(self, booking_data: BookingCreate) -> Booking:
        """Create a new booking after validation."""
        self._validate_not_in_past(booking_data.start_time)
        self._check_for_conflicts(
            room_id=booking_data.room_id,
            start_time=booking_data.start_time,
            end_time=booking_data.end_time,
        )

        booking = Booking(
            room_id=booking_data.room_id,
            start_time=booking_data.start_time,
            end_time=booking_data.end_time,
            user_name=booking_data.user_name,
        )
        self.db.add(booking)
        self.db.commit()
        self.db.refresh(booking)
        return booking

    def cancel_booking(self, booking_id: str) -> None:
        """Cancel (delete) a booking by ID."""
        booking = self.db.query(Booking).filter(Booking.id == booking_id).first()
        if not booking:
            raise BookingNotFoundError(f"Booking with id '{booking_id}' not found")

        self.db.delete(booking)
        self.db.commit()

    def list_bookings(self, room_id: str) -> list[Booking]:
        """List all bookings for a specific room."""
        return (
            self.db.query(Booking)
            .filter(Booking.room_id == room_id)
            .order_by(Booking.start_time)
            .all()
        )

    def get_booking(self, booking_id: str) -> Booking:
        """Get a single booking by ID."""
        booking = self.db.query(Booking).filter(Booking.id == booking_id).first()
        if not booking:
            raise BookingNotFoundError(f"Booking with id '{booking_id}' not found")
        return booking

    def _validate_not_in_past(self, start_time: datetime) -> None:
        """Validate that the booking start time is not in the past."""
        if start_time < datetime.utcnow():
            raise BookingValidationError("Cannot create bookings in the past")

    def _check_for_conflicts(
        self,
        room_id: str,
        start_time: datetime,
        end_time: datetime,
        exclude_booking_id: str | None = None,
    ) -> None:
        """Check if the proposed booking conflicts with existing bookings."""
        query = self.db.query(Booking).filter(
            and_(
                Booking.room_id == room_id,
                or_(
                    and_(
                        Booking.start_time < end_time,
                        Booking.end_time > start_time,
                    ),
                ),
            )
        )

        if exclude_booking_id:
            query = query.filter(Booking.id != exclude_booking_id)

        conflicting = query.first()
        if conflicting:
            raise BookingConflictError(
                f"Booking conflicts with existing booking from "
                f"{conflicting.start_time} to {conflicting.end_time}"
            )
