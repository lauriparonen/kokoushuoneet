class BookingError(Exception):
    """Base exception for booking errors."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class BookingNotFoundError(BookingError):
    """Raised when a booking is not found."""

    pass


class BookingConflictError(BookingError):
    """Raised when a booking conflicts with an existing one."""

    pass


class BookingValidationError(BookingError):
    """Raised when booking validation fails."""

    pass
