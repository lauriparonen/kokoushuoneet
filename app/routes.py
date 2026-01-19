from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import BookingCreate, BookingResponse, BookingListResponse
from app.services import BookingService

router = APIRouter(prefix="/bookings", tags=["bookings"])


def get_booking_service(db: Session = Depends(get_db)) -> BookingService:
    return BookingService(db)


@router.post("/", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
def create_booking(
    booking_data: BookingCreate,
    service: BookingService = Depends(get_booking_service),
):
    """Create a new room booking."""
    booking = service.create_booking(booking_data)
    return booking


@router.delete("/{booking_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_booking(
    booking_id: str,
    service: BookingService = Depends(get_booking_service),
):
    """Cancel an existing booking."""
    service.cancel_booking(booking_id)


@router.get("/room/{room_id}", response_model=BookingListResponse)
def list_bookings(
    room_id: str,
    service: BookingService = Depends(get_booking_service),
):
    """List all bookings for a specific room."""
    bookings = service.list_bookings(room_id)
    return BookingListResponse(bookings=bookings, count=len(bookings))


@router.get("/{booking_id}", response_model=BookingResponse)
def get_booking(
    booking_id: str,
    service: BookingService = Depends(get_booking_service),
):
    """Get a specific booking by ID."""
    return service.get_booking(booking_id)
