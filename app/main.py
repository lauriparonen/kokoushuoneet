from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import IntegrityError, OperationalError, DatabaseError, DataError

from app.database import init_db
from app.routes import router
from app.exceptions import BookingNotFoundError, BookingConflictError, BookingValidationError
from app.logging_config import logger
from app.schemas import FINNISH_TZ


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


@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError):
    """Handle database integrity constraint violations."""
    logger.warning(f"Database integrity error: {exc}")
    return JSONResponse(
        status_code=409,
        content={"detail": "Database integrity constraint violated"},
    )


@app.exception_handler(OperationalError)
async def operational_error_handler(request: Request, exc: OperationalError):
    """Handle database connection and operational issues."""
    logger.error(f"Database operational error: {exc}")
    return JSONResponse(
        status_code=503,
        content={"detail": "Database temporarily unavailable"},
    )


@app.exception_handler(DataError)
async def data_error_handler(request: Request, exc: DataError):
    """Handle invalid data for database operations."""
    logger.warning(f"Database data error: {exc}")
    return JSONResponse(
        status_code=400,
        content={"detail": "Invalid data format for database operation"},
    )


@app.exception_handler(DatabaseError)
async def database_error_handler(request: Request, exc: DatabaseError):
    """Handle general database errors."""
    logger.error(f"Database error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Database error occurred"},
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    """Handle Pydantic request validation errors with detailed messages."""
    errors = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"][1:]) if len(error["loc"]) > 1 else str(error["loc"][0])
        errors.append({
            "field": field,
            "message": error["msg"],
            "type": error["type"]
        })
    logger.warning(f"Request validation error: {errors}")
    return JSONResponse(
        status_code=422,
        content={"detail": "Validation error", "errors": errors},
    )


@app.exception_handler(Exception)
async def generic_error_handler(request: Request, exc: Exception):
    """Catch-all handler for unexpected errors."""
    logger.exception(f"Unexpected error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred"},
    )


app.include_router(router)


@app.get("/health")
def health_check():
    """Health check endpoint with database connectivity test."""
    from sqlalchemy import text
    from app.database import get_db

    try:
        # Test database connection
        db = next(get_db())
        db.execute(text("SELECT 1"))
        return {
            "status": "healthy",
            "database": "connected",
            "timestamp": datetime.now(FINNISH_TZ).isoformat(),
            "timezone": "Europe/Helsinki"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "database": "disconnected",
                "timestamp": datetime.now(FINNISH_TZ).isoformat(),
                "timezone": "Europe/Helsinki"
            }
        )
