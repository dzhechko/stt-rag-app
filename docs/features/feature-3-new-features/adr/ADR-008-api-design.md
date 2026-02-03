# ADR-008: REST API Design

## Status
Accepted

## Context
The application needs to expose REST API for external integrations:
- Developers building custom applications
- Enterprise customers integrating with internal systems
- Third-party services requiring programmatic access

**Related Requirements:**
- FR-006: API Access for Programmatic Access

## Decision Drivers
- Usability: Easy to understand and use
- Performance: Support rate-limited high throughput
- Security: API key authentication, request signing
- Documentation: Auto-generated from OpenAPI spec

## Considered Options

### Option 1: GraphQL
**Pros:**
- Flexible queries
- Single endpoint
- No over-fetching

**Cons:**
- Steeper learning curve
- Caching complexity
- Overkill for CRUD operations
- Less tooling support

### Option 2: gRPC
**Pros:**
- High performance
- Strong contracts
- Built-in streaming

**Cons:**
- Not browser-friendly
- Requires protobuf
- Less common for public APIs
- Harder to debug

### Option 3: REST + JSON
**Pros:**
- Simple and widely understood
- Excellent tooling
- Browser-native
- Easy caching
- OpenAPI ecosystem

**Cons:**
- Potential over-fetching
- Multiple endpoints

### Option 4: REST + JSON:API
**Pros:**
- Standardized format
- Built-in relationships

**Cons:**
- Complex spec
- Less adoption than basic REST

## Decision
**REST + JSON with OpenAPI 3.0** because it provides the best balance of simplicity, tooling support, and ecosystem compatibility.

## API Design Principles

### URL Structure
```
/api/v{version}/{resource}/{id}/{sub-resource}/{sub-id}
```

### HTTP Methods
| Method | Operation | Idempotent | Safe |
|---------|-----------|------------|------|
| GET | Read | Yes | Yes |
| POST | Create | No | No |
| PUT | Replace | Yes | No |
| PATCH | Update | Yes | No |
| DELETE | Delete | Yes | No |

### Status Codes
| Code | Usage |
|------|-------|
| 200 | Success (GET, PUT, PATCH) |
| 201 | Created (POST) |
| 204 | No Content (DELETE) |
| 400 | Bad Request |
| 401 | Unauthorized |
| 403 | Forbidden |
| 404 | Not Found |
| 409 | Conflict |
| 422 | Unprocessable Entity |
| 429 | Rate Limit Exceeded |
| 500 | Internal Server Error |

## API Endpoints

### Transcription
```yaml
POST /api/v1/transcribe
  Description: Start transcription for audio file
  Body: {fileUrl: string, language?: string, enableDiarization?: boolean}
  Response: 202 Accepted {jobId: string}

GET /api/v1/transcribe/{jobId}
  Description: Get transcription job status
  Response: 200 OK {status: string, transcriptId?: string}

GET /api/v1/transcripts/{id}
  Description: Get transcript by ID
  Response: 200 OK {transcript}

PATCH /api/v1/transcripts/{id}
  Description: Update transcript (edit segments)
  Body: {segments: [{id, text}]}
  Response: 200 OK {transcript}

DELETE /api/v1/transcripts/{id}
  Description: Delete transcript
  Response: 204 No Content
```

### Export
```yaml
POST /api/v1/transcripts/{id}/export
  Description: Request export
  Body: {format: 'srt'|'vtt'|'docx'|'txt'|'json', options: ExportOptions}
  Response: 202 Accepted {exportJobId: string}

GET /api/v1/export-jobs/{id}
  Description: Get export job status
  Response: 200 OK {status, fileUrl?}
```

### Search
```yaml
GET /api/v1/search
  Query Params: q=string, language?, dateFrom?, dateTo?, speaker?
  Response: 200 OK {results: [], totalCount, page, pageSize}
```

### Batch
```yaml
POST /api/v1/batch
  Description: Upload multiple files for batch processing
  Body: {fileUrls: string[], options: BatchOptions}
  Response: 202 Accepted {batchJobId: string}

GET /api/v1/batch/{id}
  Description: Get batch job status
  Response: 200 OK {status, items: []}
```

### Language Detection
```yaml
POST /api/v1/detect-language
  Description: Detect language from audio
  Body: {fileUrl: string}
  Response: 200 OK {language, confidence}
```

## Authentication

### API Key Scheme
```python
# Request header
Authorization: Bearer {api_key}

# Or query parameter (for simple integrations)
?api_key={api_key}
```

### API Key Generation
```python
import secrets

def generate_api_key() -> tuple[str, str]:
    """Generate API key and return (key, prefix)"""
    raw_key = secrets.token_urlsafe(32)
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    prefix = raw_key[:8]

    # Store only hash in database
    return raw_key, prefix
```

## Rate Limiting

### Strategy
```python
from collections import defaultdict
from time import time

class RateLimiter:
    def __init__(self, redis):
        self.redis = redis
        self.limits = {
            'free': (10, 60),      # 10 requests/minute
            'premium': (100, 60),  # 100 requests/minute
            'enterprise': (1000, 60)
        }

    async def check_limit(self, api_key_id: str, tier: str) -> bool:
        limit, window = self.limits[tier]
        key = f"ratelimit:{api_key_id}"

        current = await self.redis.incr(key)
        if current == 1:
            await self.redis.expire(key, window)

        return current <= limit
```

### Response on Limit Exceeded
```json
{
  "type": "https://api.example.com/errors/rate-limit-exceeded",
  "title": "Rate Limit Exceeded",
  "status": 429,
  "detail": "Rate limit of 100 requests/minute exceeded. Retry after 60 seconds.",
  "instance": "/api/v1/transcribe",
  "retryAfter": 60
}
```

## Request/Response Validation

### Request Validation
```python
from pydantic import BaseModel, Field, validator

class TranscribeRequest(BaseModel):
    fileUrl: str = Field(..., regex=r'^https?://')
    language: Optional[str] = Field(None, regex=r'^[a-z]{2}$')
    enableDiarization: bool = False

    @validator('language')
    def validate_language(cls, v):
        if v and v not in SUPPORTED_LANGUAGES:
            raise ValueError(f"Language {v} not supported")
        return v
```

### Error Response Format (RFC 7807)
```python
class ProblemDetail(BaseModel):
    type: str  # Error type URI
    title: str  # Short title
    status: int  # HTTP status code
    detail: str  # Detailed message
    instance: str  # Request path
    errors: Optional[Dict[str, List[str]]] = None  # Validation errors

@app.exception_handler(ValidationError)
async def validation_error_handler(request, exc):
    return JSONResponse(
        status_code=422,
        content=ProblemDetail(
            type="https://api.example.com/errors/validation",
            title="Validation Error",
            status=422,
            detail=str(exc),
            instance=str(request.url),
            errors=exc.errors()
        ).dict()
    )
```

## OpenAPI Specification

### Base Configuration
```yaml
openapi: 3.0.0
info:
  title: STT Application API
  version: 1.0.0
  description: Speech-to-Text application API
  contact:
    name: API Support
    email: api@example.com

servers:
  - url: https://api.stt-app.com/v1
    description: Production

security:
  - ApiKeyAuth: []

components:
  securitySchemes:
    ApiKeyAuth:
      type: apiKey
      in: header
      name: Authorization
      description: "Format: Bearer {api_key}"
```

## Versioning Strategy

### URL Path Versioning
```
/api/v1/transcripts/{id}
/api/v2/transcripts/{id}  # Future major version
```

**Benefits:**
- Clear version separation
- Easy to deprecate old versions
- Browser cache friendly

### Deprecation Policy
- Support N-1 versions (v1 supported when v2 released)
- 6-month deprecation notice
- Sunset date in response headers

## Consequences

### Positive
- Simple, well-understood API
- Excellent tooling support (Swagger, Postman)
- Easy to consume from any language
- Auto-generated documentation

### Negative
- More endpoints than GraphQL
- Potential over-fetching
- Version management overhead

### Risks
- **Risk:** Breaking changes affect clients
- **Mitigation:** Semantic versioning, deprecation policy

- **Risk:** Rate limiting abuse detection
- **Mitigation:** Multiple tiers, burst allowance

## Documentation

### Swagger UI
```python
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

app = FastAPI()

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="STT Application API",
        version="1.0.0",
        routes=app.routes,
    )
    openapi_schema["info"]["contact"] = {
        "name": "API Support",
        "email": "api@example.com"
    }
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi
```

## Client SDKs

### Python SDK
```python
# Example SDK structure
class STTClient:
    def __init__(self, api_key: str, base_url: str = "https://api.stt-app.com"):
        self.api_key = api_key
        self.base_url = base_url

    async def transcribe(
        self,
        file_url: str,
        language: Optional[str] = None
    ) -> Transcript:
        response = await self._post(
            "/v1/transcribe",
            json={"fileUrl": file_url, "language": language}
        )
        return Transcript(**response)

    async def _post(self, path, **kwargs):
        return await self._request("POST", path, **kwargs)
```

## Related ADRs
- ADR-010: Security Architecture
- ADR-005: Batch Processing (batch endpoints)
- ADR-004: Search Architecture (search endpoint)
