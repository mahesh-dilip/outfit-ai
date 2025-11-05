# Error Handling & Logging

## Overview

Outfit AI now has a comprehensive logging and error handling system for better debugging, monitoring, and production reliability.

## Components

### 1. Structured Logging (`logging_config.py`)

**Features:**
- JSON format for log aggregation (production)
- Standard format for development (human-readable)
- Configurable log levels
- File and console output
- Silencing of noisy third-party libraries

**Configuration:**
```python
# Environment variables
LOG_LEVEL=INFO          # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_FORMAT=standard     # standard or json
```

**Usage:**
```python
from logging_config import get_logger, log_event

logger = get_logger(__name__)

# Basic logging
logger.info("User logged in")
logger.error("Failed to upload file", exc_info=True)

# Event logging with structured data
log_event(logger, "ITEM_CREATED", user_id=123, item_id=456)
```

### 2. Custom Exceptions (`exceptions.py`)

All custom exceptions inherit from `OutfitAIException` with:
- Custom error codes
- HTTP status codes
- Additional details/context
- Automatic error logging

**Available Exceptions:**
```python
# Authentication & Authorization
AuthenticationError(message, details)     # 401
AuthorizationError(message, details)      # 403

# Resources
ResourceNotFoundError(resource, id)       # 404

# Validation
ValidationError(message, field, details)  # 400

# Operations
GCSUploadError(message, details)          # 500
VectorDBError(message, details)           # 500
AIGenerationError(message, details)       # 500
DatabaseError(message, details)           # 500
```

**Usage Example:**
```python
from exceptions import ResourceNotFoundError, ValidationError

# Raise specific exceptions
if not user:
    raise ResourceNotFoundError("User", user_id)

if not image_file:
    raise ValidationError("Image file is required", field="image")

# Exceptions are automatically caught and logged
```

### 3. Error Handler Middleware

Catches all `OutfitAIException` instances and:
- Logs the error with full context
- Returns consistent error response
- Includes error code, message, and details

**Error Response Format:**
```json
{
  "error_code": "RESOURCE_NOT_FOUND",
  "message": "User with id 123 not found",
  "details": {
    "resource": "User",
    "id": 123
  }
}
```

## Log Formats

### Standard Format (Development)
```
2025-11-05 14:30:00 - app_server - INFO - User 123 logged in successfully
2025-11-05 14:30:05 - app_server - ERROR - Failed to upload image: Connection timeout
```

### JSON Format (Production)
```json
{
  "timestamp": "2025-11-05T14:30:00.123456",
  "level": "INFO",
  "logger": "app_server",
  "message": "User logged in successfully",
  "module": "app_server",
  "function": "login",
  "line": 245,
  "event": "AUTH_SUCCESS",
  "user_id": 123
}
```

## Pre-defined Log Events

Structured events for important actions:
- `AUTH_SUCCESS` / `AUTH_FAILURE`
- `ITEM_CREATED` / `ITEM_DELETED`
- `RECOMMENDATION_GENERATED` / `RECOMMENDATION_FAILED`
- `GCS_UPLOAD_SUCCESS` / `GCS_UPLOAD_FAILED`
- `VECTOR_INDEX_UPDATED`
- `DATABASE_ERROR`

## Application Lifecycle

The application logs important lifecycle events:

```
🚀 Outfit AI API starting up...
Database URL: sqlite:///./outfitai.db
CORS origins: ['http://localhost:5173']
...
👋 Outfit AI API shutting down...
```

## Best Practices

### 1. Use Appropriate Log Levels
```python
logger.debug("Detailed diagnostic information")
logger.info("Normal operations")
logger.warning("Warning - may cause issues")
logger.error("Error occurred but app continues")
logger.critical("Critical error - app may stop")
```

### 2. Include Context
```python
# Good - includes context
logger.error(f"Failed to create item for user {user_id}: {error}")

# Better - structured context
logger.error(
    "Failed to create item",
    extra={"extra_fields": {
        "user_id": user_id,
        "error": str(error),
        "item_title": title
    }}
)
```

### 3. Use Custom Exceptions
```python
# Good - provides context
raise ResourceNotFoundError("User", user_id)

# Good - includes additional details
raise ValidationError(
    "Invalid email format",
    field="email",
    details={"provided": email, "expected": "email@example.com"}
)
```

### 4. Log Important Events
```python
# Log successful operations
log_event(logger, "ITEM_CREATED", user_id=user.id, item_id=item.id)

# Log failures
log_event(logger, "GCS_UPLOAD_FAILED", filename=file.filename, error=str(e))
```

## Production Configuration

### Enable JSON Logging
```bash
# .env
LOG_LEVEL=INFO
LOG_FORMAT=json
```

### Log to File
```python
# In app startup
setup_logging(
    level="INFO",
    json_format=True,
    log_file="/var/log/outfit-ai/app.log"
)
```

### Integrate with Log Aggregation

#### Option 1: File-based (Datadog, Splunk)
- Configure file logging
- Point log aggregator to log file
- JSON format enables structured queries

#### Option 2: Sentry Integration
```bash
pip install sentry-sdk
```

```python
import sentry_sdk

sentry_sdk.init(
    dsn="your-sentry-dsn",
    traces_sample_rate=1.0,
)
```

## Monitoring & Alerts

### Key Metrics to Monitor
- Error rate (errors per minute)
- Authentication failures
- AI generation failures
- GCS upload failures
- Response times
- Database errors

### Example Queries (JSON logs)

**Find all errors:**
```
level="ERROR"
```

**Authentication failures:**
```
event="AUTH_FAILURE"
```

**Slow operations:**
```
message contains "slow" OR duration > 1000
```

## Debugging

### Enable Debug Logging
```bash
# Temporary for debugging
LOG_LEVEL=DEBUG python app_server.py
```

### View Specific Module Logs
```python
logging.getLogger("app_server").setLevel(logging.DEBUG)
logging.getLogger("vector_db").setLevel(logging.DEBUG)
```

### Check Logs in Real-time
```bash
# Standard logs
tail -f logs/app.log

# JSON logs (pretty print)
tail -f logs/app.log | jq .
```

## Testing

### Unit Tests
```python
import logging
from logging_config import setup_logging

def test_user_creation():
    setup_logging(level="DEBUG")
    # Your test code
    # Logs will show detailed execution
```

### Integration Tests
```python
# Check logs for specific events
with caplog.at_level(logging.INFO):
    create_user(...)
    assert "User created" in caplog.text
```

## Migration Notes

### Removed
- All `print()` statements replaced with `logger` calls
- Manual error handling replaced with custom exceptions

### Added
- Structured logging with JSON support
- Custom exception hierarchy
- Error handler middleware
- Startup/shutdown logging
- Event-based logging

---

**Last Updated:** November 5, 2025  
**Python Logging Docs:** https://docs.python.org/3/library/logging.html

