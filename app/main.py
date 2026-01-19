from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.database import init_db
from app.routes import router
from app.exceptions import BookingNotFoundError, BookingConflictError, BookingValidationError


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Meeting Room Booking System",
    description="API for managing meeting room bookings",
    version="1.0.0",
    lifespan=lifespan,
)


@app.exception_handler(BookingNotFoundError)
async def booking_not_found_handler(request: Request, exc: BookingNotFoundError):
    return JSONResponse(
        status_code=404,
        content={"detail": exc.message},
    )


@app.exception_handler(BookingConflictError)
async def booking_conflict_handler(request: Request, exc: BookingConflictError):
    return JSONResponse(
        status_code=409,
        content={"detail": exc.message},
    )


@app.exception_handler(BookingValidationError)
async def booking_validation_handler(request: Request, exc: BookingValidationError):
    return JSONResponse(
        status_code=400,
        content={"detail": exc.message},
    )


app.include_router(router)


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
