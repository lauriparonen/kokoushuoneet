"""
Comprehensive test suite for edge cases in the booking system.
Tests timezone handling, race conditions, validation, and exception handling.

Note: This system uses Finnish timezone (Europe/Helsinki) as the default.
"""

import pytest
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import threading
import time

from app.main import app
from app.database import Base, get_db
from app.models import Booking
from app.schemas import BookingCreate, FINNISH_TZ
from app.services import BookingService
from app.exceptions import BookingConflictError, BookingValidationError


# Test database setup
TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override database dependency for testing."""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_database():
    """Create tables before each test and drop after."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session():
    """Provide a database session for direct testing."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# ============================================================================
# TIMEZONE HANDLING TESTS
# ============================================================================

class TestTimezoneHandling:
    """Test timezone normalization and UTC handling."""

    def test_naive_datetime_assumed_as_utc(self):
        """Test that naive datetime is assumed to be Finnish time."""
        future_time = datetime.now(FINNISH_TZ) + timedelta(days=30)
        response = client.post(
            "/bookings/",
            json={
                "room_id": "room-1",
                "start_time": future_time.replace(tzinfo=None).isoformat(),  # Naive datetime
                "end_time": (future_time + timedelta(hours=1)).replace(tzinfo=None).isoformat(),
                "user_name": "Test User"
            }
        )
        assert response.status_code == 201
        data = response.json()
        # Should have been stored with Finnish timezone info
        assert "start_time" in data
        assert "end_time" in data

    def test_utc_datetime_with_z_suffix(self):
        """Test datetime with Z suffix (UTC indicator)."""
        future_time = datetime.now(FINNISH_TZ) + timedelta(days=30)
        # Convert to UTC for the test
        future_utc = future_time.astimezone(timezone.utc)
        response = client.post(
            "/bookings/",
            json={
                "room_id": "room-1",
                "start_time": future_utc.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z"),
                "end_time": (future_utc + timedelta(hours=1)).replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z"),
                "user_name": "Test User"
            }
        )
        assert response.status_code == 201

    def test_datetime_with_timezone_offset(self):
        """Test datetime with explicit timezone offset."""
        future_time = datetime.now(FINNISH_TZ) + timedelta(days=30)
        response = client.post(
            "/bookings/",
            json={
                "room_id": "room-1",
                "start_time": future_time.isoformat(),  # Helsinki time with offset
                "end_time": (future_time + timedelta(hours=1)).isoformat(),
                "user_name": "Test User"
            }
        )
        assert response.status_code == 201

    def test_past_booking_rejected_with_utc(self):
        """Test that past bookings are rejected using proper UTC comparison."""
        past_time = datetime.now(FINNISH_TZ) - timedelta(hours=1)
        response = client.post(
            "/bookings/",
            json={
                "room_id": "room-1",
                "start_time": past_time.isoformat(),
                "end_time": (past_time + timedelta(hours=1)).isoformat(),
                "user_name": "Test User"
            }
        )
        assert response.status_code == 400
        assert "past" in response.json()["detail"].lower()

    def test_future_booking_accepted(self):
        """Test that future bookings are accepted."""
        future_time = datetime.now(FINNISH_TZ) + timedelta(days=30)
        response = client.post(
            "/bookings/",
            json={
                "room_id": "room-1",
                "start_time": future_time.isoformat(),
                "end_time": (future_time + timedelta(hours=1)).isoformat(),
                "user_name": "Test User"
            }
        )
        assert response.status_code == 201

    def test_booking_too_far_in_future_rejected(self):
        """Test that bookings more than 90 days in future are rejected."""
        far_future = datetime.now(FINNISH_TZ) + timedelta(days=91)
        response = client.post(
            "/bookings/",
            json={
                "room_id": "room-1",
                "start_time": far_future.isoformat(),
                "end_time": (far_future + timedelta(hours=1)).isoformat(),
                "user_name": "Test User"
            }
        )
        assert response.status_code == 422
        assert "90 days" in str(response.json())


# ============================================================================
# VALIDATION EDGE CASES
# ============================================================================

class TestValidationEdgeCases:
    """Test input validation and business rule edge cases."""

    def test_whitespace_only_room_id_rejected(self):
        """Test that whitespace-only room_id is rejected."""
        future_time = datetime.now(FINNISH_TZ) + timedelta(days=1)
        response = client.post(
            "/bookings/",
            json={
                "room_id": "   ",
                "start_time": future_time.isoformat(),
                "end_time": (future_time + timedelta(hours=1)).isoformat(),
                "user_name": "Test User"
            }
        )
        assert response.status_code == 422

    def test_whitespace_only_user_name_rejected(self):
        """Test that whitespace-only user_name is rejected."""
        future_time = datetime.now(FINNISH_TZ) + timedelta(days=1)
        response = client.post(
            "/bookings/",
            json={
                "room_id": "room-1",
                "start_time": future_time.isoformat(),
                "end_time": (future_time + timedelta(hours=1)).isoformat(),
                "user_name": "   "
            }
        )
        assert response.status_code == 422

    def test_whitespace_trimmed_from_inputs(self):
        """Test that leading/trailing whitespace is trimmed."""
        future_time = datetime.now(FINNISH_TZ) + timedelta(days=1)
        response = client.post(
            "/bookings/",
            json={
                "room_id": "  room-1  ",
                "start_time": future_time.isoformat(),
                "end_time": (future_time + timedelta(hours=1)).isoformat(),
                "user_name": "  Test User  "
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["room_id"] == "room-1"
        assert data["user_name"] == "Test User"

    def test_room_id_exceeds_max_length(self):
        """Test that room_id exceeding 50 characters is rejected."""
        future_time = datetime.now(FINNISH_TZ) + timedelta(days=1)
        long_room_id = "a" * 51  # 51 characters, exceeds max_length=50
        response = client.post(
            "/bookings/",
            json={
                "room_id": long_room_id,
                "start_time": future_time.isoformat(),
                "end_time": (future_time + timedelta(hours=1)).isoformat(),
                "user_name": "Test User"
            }
        )
        assert response.status_code == 422
        assert "at most 50 characters" in str(response.json()).lower() or "max_length" in str(response.json()).lower()

    def test_room_id_max_length_accepted(self):
        """Test that room_id with exactly 50 characters is accepted."""
        future_time = datetime.now(FINNISH_TZ) + timedelta(days=1)
        max_room_id = "a" * 50  # Exactly 50 characters
        response = client.post(
            "/bookings/",
            json={
                "room_id": max_room_id,
                "start_time": future_time.isoformat(),
                "end_time": (future_time + timedelta(hours=1)).isoformat(),
                "user_name": "Test User"
            }
        )
        assert response.status_code == 201

    def test_user_name_exceeds_max_length(self):
        """Test that user_name exceeding 100 characters is rejected."""
        future_time = datetime.now(FINNISH_TZ) + timedelta(days=1)
        long_user_name = "a" * 101  # 101 characters, exceeds max_length=100
        response = client.post(
            "/bookings/",
            json={
                "room_id": "room-1",
                "start_time": future_time.isoformat(),
                "end_time": (future_time + timedelta(hours=1)).isoformat(),
                "user_name": long_user_name
            }
        )
        assert response.status_code == 422
        assert "at most 100 characters" in str(response.json()).lower() or "max_length" in str(response.json()).lower()

    def test_user_name_max_length_accepted(self):
        """Test that user_name with exactly 100 characters is accepted."""
        future_time = datetime.now(FINNISH_TZ) + timedelta(days=1)
        max_user_name = "a" * 100  # Exactly 100 characters
        response = client.post(
            "/bookings/",
            json={
                "room_id": "room-1",
                "start_time": future_time.isoformat(),
                "end_time": (future_time + timedelta(hours=1)).isoformat(),
                "user_name": max_user_name
            }
        )
        assert response.status_code == 201

    def test_start_time_equals_end_time_rejected(self):
        """Test that zero-duration bookings are rejected."""
        future_time = datetime.now(FINNISH_TZ) + timedelta(days=1)
        response = client.post(
            "/bookings/",
            json={
                "room_id": "room-1",
                "start_time": future_time.isoformat(),
                "end_time": future_time.isoformat(),
                "user_name": "Test User"
            }
        )
        assert response.status_code == 422

    def test_very_short_booking_rejected(self):
        """Test that bookings shorter than 15 minutes are rejected."""
        future_time = datetime.now(FINNISH_TZ) + timedelta(days=1)
        response = client.post(
            "/bookings/",
            json={
                "room_id": "room-1",
                "start_time": future_time.isoformat(),
                "end_time": (future_time + timedelta(minutes=10)).isoformat(),
                "user_name": "Test User"
            }
        )
        assert response.status_code == 422
        assert "15 minutes" in str(response.json())

    def test_fifteen_minute_booking_accepted(self):
        """Test that exactly 15-minute bookings are accepted."""
        future_time = datetime.now(FINNISH_TZ) + timedelta(days=1)
        response = client.post(
            "/bookings/",
            json={
                "room_id": "room-1",
                "start_time": future_time.isoformat(),
                "end_time": (future_time + timedelta(minutes=15)).isoformat(),
                "user_name": "Test User"
            }
        )
        assert response.status_code == 201

    def test_extremely_long_booking_rejected(self):
        """Test that bookings longer than 4 hours are rejected."""
        future_time = datetime.now(FINNISH_TZ) + timedelta(days=1)
        response = client.post(
            "/bookings/",
            json={
                "room_id": "room-1",
                "start_time": future_time.isoformat(),
                "end_time": (future_time + timedelta(hours=5)).isoformat(),
                "user_name": "Test User"
            }
        )
        assert response.status_code == 422
        assert "4 hours" in str(response.json())

    def test_end_time_before_start_time_rejected(self):
        """Test that bookings with end before start are rejected."""
        future_time = datetime.now(FINNISH_TZ) + timedelta(days=1)
        response = client.post(
            "/bookings/",
            json={
                "room_id": "room-1",
                "start_time": future_time.isoformat(),
                "end_time": (future_time - timedelta(hours=1)).isoformat(),
                "user_name": "Test User"
            }
        )
        assert response.status_code == 422


# ============================================================================
# CONFLICT DETECTION TESTS
# ============================================================================

class TestConflictDetection:
    """Test booking conflict detection logic."""

    def test_overlapping_booking_rejected(self):
        """Test that overlapping bookings are rejected."""
        future_time = datetime.now(FINNISH_TZ) + timedelta(days=1)

        # Create first booking
        response1 = client.post(
            "/bookings/",
            json={
                "room_id": "room-1",
                "start_time": future_time.isoformat(),
                "end_time": (future_time + timedelta(hours=2)).isoformat(),
                "user_name": "User 1"
            }
        )
        assert response1.status_code == 201

        # Try to create overlapping booking
        response2 = client.post(
            "/bookings/",
            json={
                "room_id": "room-1",
                "start_time": (future_time + timedelta(hours=1)).isoformat(),
                "end_time": (future_time + timedelta(hours=3)).isoformat(),
                "user_name": "User 2"
            }
        )
        assert response2.status_code == 409
        assert "conflict" in response2.json()["detail"].lower()

    def test_edge_touching_bookings_allowed(self):
        """Test that bookings touching at edges are allowed."""
        future_time = datetime.now(FINNISH_TZ) + timedelta(days=1)

        # Create first booking
        response1 = client.post(
            "/bookings/",
            json={
                "room_id": "room-1",
                "start_time": future_time.isoformat(),
                "end_time": (future_time + timedelta(hours=1)).isoformat(),
                "user_name": "User 1"
            }
        )
        assert response1.status_code == 201

        # Create booking that starts exactly when first one ends
        response2 = client.post(
            "/bookings/",
            json={
                "room_id": "room-1",
                "start_time": (future_time + timedelta(hours=1)).isoformat(),
                "end_time": (future_time + timedelta(hours=2)).isoformat(),
                "user_name": "User 2"
            }
        )
        assert response2.status_code == 201

    def test_different_rooms_no_conflict(self):
        """Test that same time bookings in different rooms don't conflict."""
        future_time = datetime.now(FINNISH_TZ) + timedelta(days=1)

        # Create booking in room-1
        response1 = client.post(
            "/bookings/",
            json={
                "room_id": "room-1",
                "start_time": future_time.isoformat(),
                "end_time": (future_time + timedelta(hours=1)).isoformat(),
                "user_name": "User 1"
            }
        )
        assert response1.status_code == 201

        # Create booking in room-2 at same time
        response2 = client.post(
            "/bookings/",
            json={
                "room_id": "room-2",
                "start_time": future_time.isoformat(),
                "end_time": (future_time + timedelta(hours=1)).isoformat(),
                "user_name": "User 2"
            }
        )
        assert response2.status_code == 201

    def test_booking_completely_within_existing_rejected(self):
        """Test that a booking completely within another is rejected."""
        future_time = datetime.now(FINNISH_TZ) + timedelta(days=1)

        # Create first booking (2 hours)
        response1 = client.post(
            "/bookings/",
            json={
                "room_id": "room-1",
                "start_time": future_time.isoformat(),
                "end_time": (future_time + timedelta(hours=2)).isoformat(),
                "user_name": "User 1"
            }
        )
        assert response1.status_code == 201

        # Try to create booking completely within (30 min slot)
        response2 = client.post(
            "/bookings/",
            json={
                "room_id": "room-1",
                "start_time": (future_time + timedelta(minutes=30)).isoformat(),
                "end_time": (future_time + timedelta(hours=1)).isoformat(),
                "user_name": "User 2"
            }
        )
        assert response2.status_code == 409

    def test_booking_completely_encompasses_existing_rejected(self):
        """Test that a booking encompassing another is rejected."""
        future_time = datetime.now(FINNISH_TZ) + timedelta(days=1)

        # Create first booking (1 hour)
        response1 = client.post(
            "/bookings/",
            json={
                "room_id": "room-1",
                "start_time": (future_time + timedelta(hours=1)).isoformat(),
                "end_time": (future_time + timedelta(hours=2)).isoformat(),
                "user_name": "User 1"
            }
        )
        assert response1.status_code == 201

        # Try to create booking that encompasses it
        response2 = client.post(
            "/bookings/",
            json={
                "room_id": "room-1",
                "start_time": future_time.isoformat(),
                "end_time": (future_time + timedelta(hours=3)).isoformat(),
                "user_name": "User 2"
            }
        )
        assert response2.status_code == 409


# ============================================================================
# RACE CONDITION TESTS
# ============================================================================

class TestRaceConditions:
    """Test race condition prevention with concurrent requests."""

    def test_concurrent_booking_attempts_sequential(self, db_session):
        """Test that rapid sequential bookings for same slot result in conflicts."""
        # Note: True concurrent testing with SQLite in-memory database is limited
        # due to SQLite's threading restrictions. This test validates conflict detection
        # in rapid sequential requests which approximates concurrent access.
        future_time = datetime.now(FINNISH_TZ) + timedelta(days=1)

        # First booking should succeed
        response1 = client.post(
            "/bookings/",
            json={
                "room_id": "room-race-test",
                "start_time": future_time.isoformat(),
                "end_time": (future_time + timedelta(hours=1)).isoformat(),
                "user_name": "User 1"
            }
        )
        assert response1.status_code == 201

        # Subsequent attempts should be rejected due to conflict
        for i in range(2, 6):
            response = client.post(
                "/bookings/",
                json={
                    "room_id": "room-race-test",
                    "start_time": future_time.isoformat(),
                    "end_time": (future_time + timedelta(hours=1)).isoformat(),
                    "user_name": f"User {i}"
                }
            )
            assert response.status_code == 409, f"User {i} should have conflicted"
            assert "conflict" in response.json()["detail"].lower()

    def test_service_layer_with_locking(self, db_session):
        """Test that service layer conflict checking with locking works correctly."""
        # This test directly uses the service layer with row-level locking
        service = BookingService(db_session)
        future_time = datetime.now(FINNISH_TZ) + timedelta(days=1)

        # Create first booking
        booking1 = BookingCreate(
            room_id="room-lock-test",
            start_time=future_time,
            end_time=future_time + timedelta(hours=1),
            user_name="User 1"
        )
        result1 = service.create_booking(booking1)
        assert result1.id is not None

        # Try to create conflicting booking - should raise exception
        booking2 = BookingCreate(
            room_id="room-lock-test",
            start_time=future_time + timedelta(minutes=30),
            end_time=future_time + timedelta(hours=2),
            user_name="User 2"
        )

        with pytest.raises(BookingConflictError):
            service.create_booking(booking2)

        # Verify only one booking exists
        bookings = service.list_bookings("room-lock-test")
        assert len(bookings) == 1
        assert bookings[0].user_name == "User 1"


# ============================================================================
# EXCEPTION HANDLING TESTS
# ============================================================================

class TestExceptionHandling:
    """Test that exceptions are properly caught and returned with correct status codes."""

    def test_booking_not_found_returns_404(self):
        """Test that non-existent booking returns 404."""
        response = client.get("/bookings/non-existent-id")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_cancel_non_existent_booking_returns_404(self):
        """Test that canceling non-existent booking returns 404."""
        response = client.delete("/bookings/non-existent-id")
        assert response.status_code == 404

    def test_invalid_json_returns_422(self):
        """Test that invalid JSON returns 422."""
        response = client.post(
            "/bookings/",
            json={
                "room_id": "room-1",
                # Missing required fields
            }
        )
        assert response.status_code == 422
        assert "errors" in response.json()

    def test_malformed_datetime_returns_422(self):
        """Test that malformed datetime returns validation error."""
        response = client.post(
            "/bookings/",
            json={
                "room_id": "room-1",
                "start_time": "not-a-datetime",
                "end_time": "also-not-a-datetime",
                "user_name": "Test User"
            }
        )
        assert response.status_code == 422

    def test_validation_error_has_detailed_messages(self):
        """Test that validation errors include field-specific details."""
        response = client.post(
            "/bookings/",
            json={
                "room_id": "",  # Empty string
                "start_time": "2026-12-01T10:00:00",
                "end_time": "2026-12-01T09:00:00",  # Before start
                "user_name": "Test"
            }
        )
        assert response.status_code == 422
        data = response.json()
        assert "errors" in data or "detail" in data


# ============================================================================
# SERVICE LAYER TESTS
# ============================================================================

class TestServiceLayer:
    """Test service layer directly to ensure transaction handling."""

    def test_service_rollback_on_conflict(self, db_session):
        """Test that failed bookings are rolled back properly."""
        service = BookingService(db_session)
        future_time = datetime.now(FINNISH_TZ) + timedelta(days=1)

        # Create first booking
        booking1 = BookingCreate(
            room_id="room-1",
            start_time=future_time,
            end_time=future_time + timedelta(hours=1),
            user_name="User 1"
        )
        service.create_booking(booking1)

        # Try to create conflicting booking
        booking2 = BookingCreate(
            room_id="room-1",
            start_time=future_time + timedelta(minutes=30),
            end_time=future_time + timedelta(hours=2),
            user_name="User 2"
        )

        with pytest.raises(BookingConflictError):
            service.create_booking(booking2)

        # Verify only one booking exists
        bookings = service.list_bookings("room-1")
        assert len(bookings) == 1

    def test_service_rollback_on_validation_error(self, db_session):
        """Test that validation errors cause rollback."""
        service = BookingService(db_session)
        past_time = datetime.now(FINNISH_TZ) - timedelta(hours=1)

        booking = BookingCreate(
            room_id="room-1",
            start_time=past_time,
            end_time=past_time + timedelta(hours=1),
            user_name="User 1"
        )

        with pytest.raises(BookingValidationError):
            service.create_booking(booking)

        # Verify no booking was created
        bookings = service.list_bookings("room-1")
        assert len(bookings) == 0


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestEndToEndScenarios:
    """Test complete end-to-end scenarios."""

    def test_complete_booking_lifecycle(self):
        """Test creating, retrieving, and canceling a booking."""
        future_time = datetime.now(FINNISH_TZ) + timedelta(days=1)

        # Create booking
        create_response = client.post(
            "/bookings/",
            json={
                "room_id": "room-1",
                "start_time": future_time.isoformat(),
                "end_time": (future_time + timedelta(hours=1)).isoformat(),
                "user_name": "Test User"
            }
        )
        assert create_response.status_code == 201
        booking_id = create_response.json()["id"]

        # Retrieve booking
        get_response = client.get(f"/bookings/{booking_id}")
        assert get_response.status_code == 200
        assert get_response.json()["id"] == booking_id

        # List bookings
        list_response = client.get("/bookings/room/room-1")
        assert list_response.status_code == 200
        assert list_response.json()["count"] == 1

        # Cancel booking
        delete_response = client.delete(f"/bookings/{booking_id}")
        assert delete_response.status_code == 204

        # Verify it's gone
        get_after_delete = client.get(f"/bookings/{booking_id}")
        assert get_after_delete.status_code == 404

    def test_multiple_sequential_bookings(self):
        """Test creating multiple bookings in sequence."""
        base_time = datetime.now(FINNISH_TZ) + timedelta(days=1)

        for i in range(5):
            start = base_time + timedelta(hours=i * 2)
            response = client.post(
                "/bookings/",
                json={
                    "room_id": "room-sequential",
                    "start_time": start.isoformat(),
                    "end_time": (start + timedelta(hours=1)).isoformat(),
                    "user_name": f"User {i}"
                }
            )
            assert response.status_code == 201

        # Verify all bookings exist
        list_response = client.get("/bookings/room/room-sequential")
        assert list_response.status_code == 200
        assert list_response.json()["count"] == 5

    def test_health_check_endpoint(self):
        """Test health check returns correct status."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["database"] == "connected"
        assert "timestamp" in data
