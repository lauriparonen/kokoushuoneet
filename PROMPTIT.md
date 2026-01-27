

## prompti 1 (Claude Code Cursorissa)
*create a fastapi application for a meeting room booking system.*

*requirements:*
- *endpoints for creating bookings, canceling bookings, and listing bookings for a room*
- *use sqlite in-memory database*
- *booking has: room_id, start_time, end_time, user_name/booking_id*
- *basic validation: no overlapping bookings, no past bookings, start before end*

*use sqlalchemy for db, pydantic for schemas. include basic error handling. ensure you employ software engineering best practices in the code you produce.*

### vastaus:
Update Todos

Create project structure and database models
Create Pydantic schemas for request/response validation
Implement booking service with business logic
Create FastAPI endpoints
Add error handling

Read e:\code\kokoushuoneet\requirements.txt
The requirements.txt already has the necessary dependencies. Let me create the FastAPI application with a clean structure.

[...agentti toteuttaa koodia, reflektiot jätetty pois]

I've created a FastAPI meeting room booking system. Here's the structure:

Project Structure:

app/
├── __init__.py
├── main.py          # FastAPI app with lifespan and error handlers
├── database.py      # SQLAlchemy setup with in-memory SQLite
├── models.py        # Booking SQLAlchemy model
├── schemas.py       # Pydantic request/response schemas
├── services.py      # Business logic layer
├── routes.py        # API endpoints
└── exceptions.py    # Custom exception classes
Endpoints:

POST /bookings/ - Create a booking
DELETE /bookings/{booking_id} - Cancel a booking
GET /bookings/room/{room_id} - List all bookings for a room
GET /bookings/{booking_id} - Get a specific booking
GET /health - Health check
Validations implemented:

Start time must be before end time (Pydantic model validator)
No bookings in the past (service layer)
No overlapping bookings for the same room (service layer)
Required fields with minimum length (Pydantic)
Key design decisions:

Separated concerns: routes → services → database
Custom exceptions mapped to HTTP status codes (404, 409, 400)
Dependency injection for database sessions and services
UUID-based booking IDs
Index on room_id and time range for efficient conflict queries
Run the app:

uvicorn app.main:app --reload
API docs will be available at http://localhost:8000/docs.

## prompti 2
*we're getting unhandled 500s because the database initialization isn't working:*
```
INFO:     127.0.0.1:54870 - "GET /bookings/test HTTP/1.1" 500 Internal Server Error
ERROR:    Exception in ASGI application
Traceback (most recent call last):
  File "E:\code\kokoushuoneet\venv\Lib\site-packages\sqlalchemy\engine\base.py", line 1967, in _exec_single_context
    self.dialect.do_execute(
    ~~~~~~~~~~~~~~~~~~~~~~~^
        cursor, str_statement, effective_parameters, context
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "E:\code\kokoushuoneet\venv\Lib\site-packages\sqlalchemy\engine\default.py", line 952, in do_execute
    cursor.execute(statement, parameters)
    ~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^
sqlite3.OperationalError: no such table: bookings
```

*how come?*
### vastaus:
The issue is that SQLite in-memory databases are connection-specific. Each new connection gets a fresh, empty database. Since SessionLocal creates new connections, the tables created by init_db() are lost.

The fix is to use a shared cache connection or a single persistent connection. Let me update the database configuration:

Read e:\code\kokoushuoneet\app\database.py
Edit e:\code\kokoushuoneet\app\database.py
Added 2 lines
The changes:

`?cache=shared` - Enables SQLite's shared cache mode, allowing multiple connections to access the same in-memory database
`"uri": True` - Required for SQLite to parse the URI-style connection string with query parameters
`pool_size=1, max_overflow=0` - Ensures connection pooling keeps the database alive (at least one connection always exists)
Restart the server and it should work now.

#### ! KOMMENTTI:
IDE-integroidun Claude Coden korjausehdotus ei toiminut, koska se hallusinoi SQLAlchemyn metodin `create_engine()` argumentin `max_overflow` ja kehitysserveri ei käynnistynyt enää: 

> TypeError: Invalid argument(s) 'max_overflow' sent to create_engine(), using configuration SQLiteDialect_pysqlite/SingletonThreadPool/Engine. Please check that the keyword arguments are appropriate for this combination of components.

Katsottuani SQLAlchemyn dokumentaatiota, jaoin tiedostot `models.py`, `main.py` sekä `database.py` Claudelle desktop-sovelluksessa. Tämä tunnisti saman ongelman (connection-specific in-memory database), mutta ehdotti toimivan korjausehdotuksen -  metodin StaticPool sisällyttäminen tietokannan luomiseen tiedostossa `database.py`:
``
``` 
from sqlalchemy.pool import StaticPool

DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False, "uri": True},
    echo=False,
    poolclass=StaticPool,
)
```

Näin serveri käynnistyi uudestaan, ja pääsin testaamaan toiminnallisuutta. En vielä ollu initialisoinut Git-repositoriota, koska ohjelman perusvaatimukset eivät olleet toteutuneet.

---

Tässä kohtaa olin tehnyt ensimmäisen commitin, kun rajapinnan perustoiminnallisuus oli kunnossa: tietokanta päivittyi kutsujen myötä, ja kaikista perustavanlaatuisin validaatio oli kunnossa. Tutustuin koodiin ja kirjasin itselleni ylös huomaamiani epäkohtia (esimerkiksi varausten aikarajausten määrittelyn puuttuminen, validaation alkeellisuus). Koska monen näkökulman kautta toimiminen on olennaista kokonaiskuvan kartoittamisen vuoksi, pyysin Claudea tutkimaan koodia ja kartoittamaan edge caset mitä se huomaisi, nähdäkseni kuinka paljon samoilla linjoilla minä olen sen kanssa. Modulaarisuus ja SoC oli ensimmäisen agentin jäljiltä jo verrattain hyvää, joten keskityin suoraan reunatapausten kartoitukseen. 
## prompti 3 (claude code cursorissa)
*look around this codebase suggest a map of edge cases the program is not handling. afterwards we will address these*

### vastaus
```
Edge Case Analysis Map
Based on my exploration of your meeting room booking system, here's a comprehensive map of edge cases that aren't currently being handled:

1. Time and Timezone Issues 🕐
Location: services.py:62, models.py:18

Timezone awareness: The system uses datetime.utcnow() but accepts naive datetime objects from API requests, creating timezone confusion
End time in the past: Only validates start_time isn't in the past, but end_time could theoretically be in the past if the booking is extremely short
Zero-duration bookings: While schema validates start_time < end_time, a booking could be 1 microsecond long (e.g., same second)
Extremely long bookings: No maximum duration limit (could book for years)
Edge-touching bookings: If Booking A ends at 14:00 and Booking B starts at 14:00, are they conflicting? Current logic allows them (good), but this isn't documented
2. Input Validation Gaps 📝
Location: schemas.py:7-10, routes.py

Empty/whitespace strings: room_id and user_name require min_length=1 but don't validate against whitespace-only strings (e.g., " ")
String length limits: No maximum length validation for room_id or user_name (could cause database issues or DoS)
Special characters: room_id could contain path traversal characters, SQL-like syntax, or other problematic characters
Invalid UUID format: booking_id in routes accepts any string, no UUID format validation
Case sensitivity: room_id is case-sensitive, so "Room-A" and "room-a" are different rooms (may or may not be intended)
3. Database and Concurrency Issues 💾
Location: services.py:15-33, database.py

Race conditions: Between checking for conflicts (line 18-22) and creating booking (line 30-31), another request could create a conflicting booking
Database transaction rollback: No explicit transaction management or error handling for database failures during commit
In-memory database volatility: Using SQLite in-memory means all data is lost on server restart (no persistence warning to users)
Connection pool exhaustion: While using StaticPool, no limits or timeout handling for database connections
Concurrent modification: No optimistic locking or versioning to handle simultaneous updates
4. Business Logic Edge Cases 🏢
Location: services.py

Booking cancellation timing: Can cancel bookings that are currently ongoing or already past (no time-based restrictions)
Same user multiple bookings: No limit on how many times the same user can book the same room or different rooms
Room existence: System doesn't validate if a room actually exists (can book non-existent rooms)
Booking modification: No update/edit endpoint exists, users must cancel and recreate (could lose the slot to another user)
Historical bookings: Past bookings accumulate forever with no archival or cleanup strategy
5. API Response and Error Handling 🚨
Location: main.py:25-46, routes.py

Unhandled exceptions: Only custom BookingError subclasses are caught; database errors, validation errors from Pydantic, or other exceptions would return default FastAPI 500 errors
Partial error messages: Generic Pydantic validation errors might not be user-friendly
Missing CORS configuration: No Cross-Origin Resource Sharing headers configured
No rate limiting: API endpoints are unprotected from abuse
No authentication/authorization: Anyone can create, view, or cancel any booking
6. Query and Filtering Limitations 🔍
Location: services.py:44-51, routes.py:34-41

No pagination: list_bookings() returns all bookings for a room (could be thousands)
No time filtering: Cannot filter bookings by date range (e.g., "show me next week's bookings")
No sorting options: Always sorted by start_time, no other sort options
No search functionality: Cannot search by user_name or other criteria
No status filtering: Cannot differentiate between upcoming, ongoing, and past bookings
7. Data Integrity Issues 🔐
Location: models.py:10-18

UUID collision: While extremely unlikely, no handling for UUID generation collision
Orphaned data: No foreign key constraints or referential integrity checks
Data truncation: No validation that datetime values are within database column constraints
NULL handling: While columns are marked nullable=False, no explicit validation at the model level
8. Performance and Scalability ⚡
Location: services.py:73-88

N+1 query pattern: Not currently an issue, but no eager loading strategy documented
Missing indexes: Only one composite index; queries by user_name or created_at would be slow
No caching: Every request hits the database even for frequently accessed data
No query timeout: Long-running queries could hang indefinitely
9. Observability and Logging 📊
Location: Entire application

No logging: No logs for booking creation, cancellation, or conflicts
No metrics: No instrumentation for monitoring booking patterns or API performance
No request tracing: Cannot track individual requests through the system
No audit trail: Cannot see who canceled a booking or when
10. Edge Cases in Conflict Detection ⚔️
Location: services.py:65-93

Inclusive vs exclusive boundaries: The conflict query uses < and >, so exact same start/end times would be allowed
DST transitions: During daylight saving time transitions, bookings could overlap or have gaps
Leap seconds: Edge case where leap seconds could cause unexpected time comparisons
Parameter exclude_booking_id: Is implemented but never used (dead code for potential update feature)
11. API Design Issues 🎯
Location: routes.py

No bulk operations: Cannot create multiple bookings at once
No partial responses: Always returns full booking objects
No ETag/conditional requests: No support for caching or conditional GET requests
Inconsistent resource naming: /room/{room_id} vs /{booking_id} (mixing resource types in the same router)
12. Datetime Handling Specifics 📅
Location: models.py:24-28

ISO format parsing: The validator converts strings to datetime but doesn't specify timezone handling
Microsecond precision: Different clients might send different precision levels
Date-only bookings: Cannot book "all day" without specifying exact times
Recurring bookings: No support for recurring meetings
Priority Assessment
Critical (Must Fix)
Race conditions in booking creation
Timezone handling inconsistencies
Unhandled database exceptions
Missing authentication/authorization
High (Should Fix)
Input validation (whitespace, length limits, special characters)
Pagination for list endpoints
Request ID validation (UUID format)
Logging and audit trail
Medium (Nice to Have)
Maximum booking duration limits
Room existence validation
Booking modification endpoint
Time-based filtering
Low (Future Enhancements)
Rate limiting
Caching
Bulk operations
Recurring bookings
Would you like me to start addressing these edge cases? I recommend we prioritize them based on criticality and start with the most impactful ones first.
```

Annoin agentin suorittaa kriittisimmät korjaukset eli validaation ja päällekkäisyyksien eston; pyysin sitä myös tekemään perinpohjaisen testikokoelman reunatapauksille. Pyysin siltä suunnitelman, jonka hyväksyin sen luettuani:

## prompti 4
_yes let's start from the most critical ones. start from the race conditions, timezone handling inconsistencies and unhandled exceptions. authentication and authorization is not yet important at this phase. draft a plan for addressing the three first critical ones you outlined_

### vastaus:
```
Implementation Plan: Critical Edge Cases
Here's a comprehensive plan to address the three critical issues:

1. Race Conditions in Booking Creation 🔒
Problem Analysis
In services.py:15-33, there's a time gap between:

Checking for conflicts (line 18-22)
Creating the booking (line 30-31)
During this gap, another concurrent request could create a conflicting booking, bypassing validation.

Solution: Database-Level Constraint + Proper Transaction Isolation
Approach A: Optimistic Locking with Database Constraint (Recommended)
Changes needed:

Add unique constraint at database level (models.py)

Use PostgreSQL's exclusion constraint or SQLite's trigger
For SQLite: Create a trigger that validates no overlapping bookings on insert
This provides database-level protection against race conditions
Update service layer (services.py)

Wrap booking creation in explicit transaction with appropriate isolation level
Catch IntegrityError from database constraint violations
Convert to user-friendly BookingConflictError
Add row-level locking for conflict check

Use SELECT FOR UPDATE when checking conflicts
This locks rows until transaction completes
Code changes:


# models.py - Add check constraint (SQLite limitation workaround)
# Note: SQLite doesn't support exclusion constraints, so we'll use:
# - Application-level locking with SELECT FOR UPDATE
# - Or move to PostgreSQL for EXCLUDE constraints

# services.py - Transaction with row locking
from sqlalchemy.exc import IntegrityError

def create_booking(self, booking_data: BookingCreate) -> Booking:
    try:
        # Start explicit transaction
        self._validate_not_in_past(booking_data.start_time)
        
        # Lock the room's booking records for this time range
        self._check_for_conflicts_with_lock(...)
        
        booking = Booking(...)
        self.db.add(booking)
        self.db.commit()
        self.db.refresh(booking)
        return booking
    except IntegrityError as e:
        self.db.rollback()
        raise BookingConflictError("Booking conflict detected")
Approach B: Application-Level Distributed Lock
Use Redis or similar for distributed locking
Acquire lock on room_id before validation
More complex but works with any database
Recommendation: Start with Approach A (database-level protection with row locking)

2. Timezone Handling Inconsistencies 🌍
Problem Analysis
services.py:62 uses datetime.utcnow() (naive UTC)
models.py:18 uses func.now() (database server time)
API accepts naive datetime objects from clients
No timezone information preserved or validated
Solution: Enforce UTC Throughout + Add Timezone Awareness
Implementation Strategy:
Standardize on UTC everywhere

All datetime objects stored as UTC
All API requests/responses use ISO 8601 with timezone
Database stores UTC timestamps
Make datetimes timezone-aware

Code changes:


# schemas.py - Validate and normalize to UTC
from datetime import datetime, timezone

class BookingCreate(BaseModel):
    # ... existing fields ...
    
    @field_validator("start_time", "end_time", mode="before")
    @classmethod
    def normalize_to_utc(cls, v):
        if isinstance(v, str):
            dt = datetime.fromisoformat(v.replace('Z', '+00:00'))
        else:
            dt = v
            
        # If naive, assume UTC
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            # Convert to UTC
            dt = dt.astimezone(timezone.utc)
            
        return dt

# services.py - Use timezone-aware comparison
def _validate_not_in_past(self, start_time: datetime) -> None:
    now = datetime.now(timezone.utc)
    # Ensure start_time is timezone-aware
    if start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=timezone.utc)
    
    if start_time < now:
        raise BookingValidationError("Cannot create bookings in the past")

# models.py - Already using func.now() which is good
# Keep as-is: created_at = Column(DateTime, default=func.now())
Update response serialization

Return ISO 8601 format with UTC indicator (Z suffix)
Ensure consistent timezone in all responses
Add validation for reasonable time ranges

Reject bookings more than X years in the future
Prevent extremely long bookings (add max duration check)
3. Unhandled Database and System Exceptions ⚠️
Problem Analysis
Only custom BookingError exceptions have handlers (main.py:25-46)
Database errors, SQLAlchemy exceptions, and system errors return generic 500 responses
No graceful degradation or user-friendly error messages
Solution: Comprehensive Exception Handling Strategy
Implementation Strategy:
Add global exception handlers
Code changes:


# main.py - Add comprehensive exception handlers

from sqlalchemy.exc import (
    IntegrityError, 
    OperationalError, 
    DatabaseError,
    DataError
)
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

# Database exception handlers
@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError):
    # Could be constraint violation, duplicate key, etc.
    return JSONResponse(
        status_code=409,
        content={"detail": "Database integrity constraint violated"},
    )

@app.exception_handler(OperationalError)
async def operational_error_handler(request: Request, exc: OperationalError):
    # Database connection issues, lock timeouts, etc.
    # Log the actual error but don't expose internals
    logger.error(f"Database operational error: {exc}")
    return JSONResponse(
        status_code=503,
        content={"detail": "Database temporarily unavailable"},
    )

@app.exception_handler(DataError)
async def data_error_handler(request: Request, exc: DataError):
    # Invalid data for database column type
    return JSONResponse(
        status_code=400,
        content={"detail": "Invalid data format for database"},
    )

# Pydantic validation errors
@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    # Format validation errors nicely
    errors = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"][1:])
        errors.append({
            "field": field,
            "message": error["msg"],
            "type": error["type"]
        })
    return JSONResponse(
        status_code=422,
        content={"detail": "Validation error", "errors": errors},
    )

# Catch-all for unexpected errors
@app.exception_handler(Exception)
async def generic_error_handler(request: Request, exc: Exception):
    # Log the full error for debugging
    logger.exception(f"Unexpected error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred"},
    )
Add explicit transaction management in services

# services.py - Add rollback handling

def create_booking(self, booking_data: BookingCreate) -> Booking:
    try:
        self._validate_not_in_past(booking_data.start_time)
        self._check_for_conflicts(...)
        
        booking = Booking(...)
        self.db.add(booking)
        self.db.commit()
        self.db.refresh(booking)
        return booking
    except (BookingConflictError, BookingValidationError):
        self.db.rollback()
        raise  # Re-raise our custom exceptions
    except Exception as e:
        self.db.rollback()
        # Log unexpected error
        logger.error(f"Unexpected error creating booking: {e}")
        raise
Add basic logging infrastructure

# Add to requirements.txt (or use built-in logging)
# python-json-logger  # For structured logging

# Create app/logging_config.py
import logging
import sys

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    return logging.getLogger("booking_system")

# Use in main.py and services.py
logger = setup_logging()
Add health check improvements

# main.py - Enhanced health check
@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    """Health check with database connectivity test."""
    try:
        # Test database connection
        db.execute("SELECT 1")
        return {
            "status": "healthy",
            "database": "connected",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "database": "disconnected",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
Implementation Order & Files to Modify
Phase 1: Timezone Handling (Safest, No Breaking Changes)
✏️ schemas.py - Add timezone validators
✏️ services.py - Update time comparisons to use UTC
✅ Test with various timezone inputs
Phase 2: Exception Handling (Improves Reliability)
✏️ Create app/logging_config.py - New file
✏️ main.py - Add exception handlers
✏️ services.py - Add transaction rollbacks
✏️ requirements.txt - Add logging dependencies (if needed)
✅ Test error scenarios
Phase 3: Race Condition Prevention (Most Complex)
✏️ services.py - Add row-level locking in conflict check
✏️ services.py - Add IntegrityError handling
✏️ database.py - Adjust transaction isolation level
✅ Write concurrent booking tests to verify fix
Testing Strategy
For each fix:

Timezone Tests:

Submit bookings with various timezone formats
Verify all stored as UTC
Test past booking validation with different timezones
Exception Tests:

Trigger database errors
Send invalid data
Verify error responses are user-friendly
Race Condition Tests:

Use threading/asyncio to simulate concurrent requests
Attempt to create conflicting bookings simultaneously
Verify only one succeeds
Dependencies to Add

# requirements.txt additions
python-json-logger==2.0.7  # Optional: for structured logging
This plan addresses all three critical issues systematically. Should I proceed with implementation starting from Phase 1 (timezone handling)?
```

## prompti 5
*yeah go ahead and implement them, using your recommendations. also after you have added these, curate a test suite which simulates scenarios where the validation fails and the system catches the errors correctly ie the right exceptions are thrown*

<agentti työskentelee...>

Agentti lisäsi ihmeelliset aikajanat huoneiden varaukseen (esim. 365 päivän maksimipituus). Korjasin tilanteen käsin, olettamalla 15 minuutin minimivarauksen sekä neljän tunnin maksimivarauksen.

Tämän jälkeen kävin läpi agentin tuottamaa koodia, ajoin testit ja kokeilin rajapintaa käsin Swaggerin kautta. Manuaalista prosessia nopeuttaakseni pyysin Cursorilta keskeisimmät pyynnöt eri skenaarioihin:
### prompti 6
_give me a handful of API commands that i can test by hand in swagger so i can verify the actual api also works
based on the test suite @test_edge_cases.py_

### vastaus
```
Based on the test suite, here are some practical API commands you can test in Swagger:
1. Health Check (easiest first test)
GET /health
2. Create a Valid Booking
POST /bookings/
Body:
{  "room_id": "room-1",  "start_time": "2026-02-15T10:00:00",  "end_time": "2026-02-15T11:00:00",  "user_name": "John Doe"}
Expected: 201 Created
3. List Bookings for a Room
GET /bookings/room/room-1
Expected: 200 OK (should show the booking you just created)
4. Test Overlapping Booking (Conflict)
POST /bookings/
Body:
{  "room_id": "room-1",  "start_time": "2026-02-15T10:30:00",  "end_time": "2026-02-15T11:30:00",  "user_name": "Jane Smith"}
Expected: 409 Conflict - overlaps with the first booking
5. Test Edge-Touching Booking (Should Succeed)
POST /bookings/
Body:
{  "room_id": "room-1",  "start_time": "2026-02-15T11:00:00",  "end_time": "2026-02-15T12:00:00",  "user_name": "Jane Smith"}
Expected: 201 Created - starts exactly when previous ends
6. Test Past Booking (Should Fail)
POST /bookings/
Body:
{  "room_id": "room-2",  "start_time": "2026-01-20T10:00:00",  "end_time": "2026-01-20T11:00:00",  "user_name": "Time Traveler"}
Expected: 400 Bad Request - booking in the past
7. Test Booking Too Long (Should Fail)
POST /bookings/
Body:
{  "room_id": "room-3",  "start_time": "2026-02-20T09:00:00",  "end_time": "2026-02-20T15:00:00",  "user_name": "Marathon Booker"}
Expected: 422 Validation Error - exceeds 4 hour maximum
8. Test Booking Too Short (Should Fail)
POST /bookings/
Body:
{  "room_id": "room-3",  "start_time": "2026-02-20T10:00:00",  "end_time": "2026-02-20T10:10:00",  "user_name": "Quick Chat"}
Expected: 422 Validation Error - less than 15 minute minimum
9. Get Specific Booking
First create a booking, note the id from the response, then:
GET /bookings/{id}
Expected: 200 OK
10. Cancel a Booking
Using the same booking ID:
DELETE /bookings/{id}
Expected: 204 No Content

```

Kokeilin näistä jokaisen käsin, ja vastaukset olivat kuten piti. 

---

Tässä kohtaa sovelluksen keskeisin toimintalogiikka oli mielestäni tähän vaiheeseen katsottuna riittävän perusteellisesti katsastettua. Keskustelin projektista toisen Claude-instanssin kanssa, joka ehdotti projektin kontitusta. En ole aiemmin käyttänyt Dockeria, joten minulle tämä oli mahtavan konkreettinen tapa tutustua siihen - Pythonin dependenssien kanssa säätäminen on inhottavaa; kontittamalla niin tehtävän tarkastaja, minä itse, kuin kuka hyvänsä projektin työstettäväkseen tulevaisuudessa ottava henkilö pääsee helpommalla. Asensin Dockerin ja pyysin Claude Codea luomaan Dockerfilen ja testasin, että se toimii. Tämän tein niin monessa instanssissa, että jätän promptit jakamatta selkeyden vuoksi.