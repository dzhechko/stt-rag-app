# ADR-001: Export Service Architecture

## Status
Accepted

## Context
The application needs to export transcripts in multiple formats (SRT, VTT, DOCX, TXT, JSON) for different use cases:
- Content creators need subtitle files for video platforms
- Business users need documents for meeting notes
- Developers need JSON for API integration

**Related Requirements:**
- FR-001: Multi-format Export (SRT, VTT)
- FR-008: Additional Export Formats (DOCX, TXT, JSON)

## Decision Drivers
- Performance: Export must complete in <10 seconds for 10K-word transcripts
- Maintainability: Support 5+ formats without code duplication
- Testability: Each format converter independently testable
- Extensibility: Easy to add new export formats

## Considered Options

### Option 1: External Service (e.g., CloudConvert)
**Pros:**
- No implementation complexity
- Supports many formats out-of-the-box

**Cons:**
- Cost increases with usage
- Data privacy concerns (sending transcripts externally)
- Latency from external API calls
- Vendor lock-in

### Option 2: Single Monolithic Export Function
**Pros:**
- Simple to implement
- Centralized logic

**Cons:**
- Hard to maintain with 5+ formats
- Code duplication inevitable
- Difficult to test individually

### Option 3: Strategy Pattern with Format Converters
**Pros:**
- Each format is independent converter
- Easy to add new formats
- Testable in isolation
- Clear separation of concerns

**Cons:**
- Slightly more initial code
- Requires interface design

## Decision
**Strategy Pattern with Format Converters** because it provides the best balance of maintainability, extensibility, and testability while keeping data in-house.

## Architecture

```python
# Converter interface
class ExportConverter(ABC):
    @abstractmethod
    def convert(self, transcript: Transcript, options: ExportOptions) -> bytes:
        pass

# Implementations
class SrtConverter(ExportConverter):
    def convert(self, transcript: Transcript, options: ExportOptions) -> bytes:
        # SRT-specific logic
        pass

class VttConverter(ExportConverter):
    def convert(self, transcript: Transcript, options: ExportOptions) -> bytes:
        # VTT-specific logic
        pass

# Factory
class ExportConverterFactory:
    _converters = {
        ExportFormat.SRT: SrtConverter(),
        ExportFormat.VTT: VttConverter(),
        # ...
    }

    @classmethod
    def get_converter(cls, format: ExportFormat) -> ExportConverter:
        return cls._converters[format]

# Service
class ExportService:
    async def export(self, request: ExportRequest) -> ExportResult:
        converter = ExportConverterFactory.get_converter(request.format)
        content = converter.convert(request.transcript, request.options)
        return ExportResult(content, self._generate_filename(request))
```

## Consequences

### Positive
- Each format converter can be developed and tested independently
- Adding new formats only requires implementing the interface
- ExportService is decoupled from format-specific logic
- Easy to mock for testing

### Negative
- Slightly more code than monolithic approach
- Requires maintenance of converter registry

### Risks
- **Risk:** Format converters may have duplicate logic (e.g., timecode formatting)
- **Mitigation:** Extract common utilities to helper module

- **Risk:** Large transcripts may cause memory issues
- **Mitigation:** Implement streaming for formats >100MB

## Implementation Details

### Timecode Handling
```python
class TimecodeFormatter:
    @staticmethod
    def to_srt(seconds: float) -> str:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"

    @staticmethod
    def to_vtt(seconds: float) -> str:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02}:{minutes:02}:{secs:02}.{millis:03}"
```

### Export Job Tracking
- Store export jobs in database for async processing
- Track status: pending -> processing -> completed/failed
- Retain files for 24 hours, then delete

## Performance Considerations
- SRT/VTT: O(n) where n = segment count
- DOCX: O(n) with library overhead
- JSON: O(n) with fast serialization
- TXT: O(n), simplest format

## Related ADRs
- ADR-008: REST API Design (export endpoints)
- ADR-005: Batch Processing (batch export)
