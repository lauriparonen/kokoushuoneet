from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import logging

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, OperationalError

from app.models import Booking
from app.schemas import BookingCreate, FINNISH_TZ
from app.exceptions import BookingNotFoundError, BookingConflictError, BookingValidationError

logger = logging.getLogger("booking_system")


class BookingService:
    def __init__(self, db: Session):
        self.db = db

    def create_booking(self, booking_data: BookingCreate) -> Booking:
        """Create a new booking after validation with race condition protection."""
        try:
            self._validate_not_in_past(booking_data.start_time)

            # Check for conflicts with row-level locking to prevent race conditions
            self._check_for_conflicts_with_lock(
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

            logger.info(
                f"Booking created: id={booking.id}, room={booking.room_id}, "
                f"user={booking.user_name}, time={booking.start_time} to {booking.end_time}"
            )
            return booking

        except (BookingConflictError, BookingValidationError):
            self.db.rollback()
            raise
        except IntegrityError as e:
            self.db.rollback()
            logger.warning(f"Integrity error during booking creation: {e}")
            raise BookingConflictError("Booking conflict detected (database constraint)")
        except OperationalError as e:
            self.db.rollback()
            logger.error(f"Database operational error during booking creation: {e}")
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Unexpected error creating booking: {e}", exc_info=True)
            raise

    def cancel_booking(self, booking_id: str) -> None:
        """Cancel (delete) a booking by ID."""
        try:
            booking = self.db.query(Booking).filter(Booking.id == booking_id).first()
            if not booking:
                raise BookingNotFoundError(f"Booking with id '{booking_id}' not found")

            logger.info(
                f"Canceling booking: id={booking.id}, room={booking.room_id}, "
                f"user={booking.user_name}"
            )
            self.db.delete(booking)
            self.db.commit()

        except BookingNotFoundError:
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error canceling booking {booking_id}: {e}", exc_info=True)
            raise

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
        """Validate that the booking start time is not in the past (Finnish time)."""
        now = datetime.now(FINNISH_TZ)

        # Ensure start_time is timezone-aware
        if start_time.tzinfo is None:
            start_time = start_time.replace(tzinfo=FINNISH_TZ)

        if start_time < now:
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

    def _check_for_conflicts_with_lock(
        self,
        room_id: str,
        start_time: datetime,
        end_time: datetime,
        exclude_booking_id: str | None = None,
    ) -> None:
        """Check for conflicts with row-level locking to prevent race conditions."""
        # Use FOR UPDATE to lock rows during the transaction
        # This prevents concurrent transactions from creating conflicting bookings
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
        ).with_for_update()

        if exclude_booking_id:
            query = query.filter(Booking.id != exclude_booking_id)

        conflicting = query.first()
        if conflicting:
            raise BookingConflictError(
                f"Booking conflicts with existing booking from "
                f"{conflicting.start_time} to {conflicting.end_time}"
            )
