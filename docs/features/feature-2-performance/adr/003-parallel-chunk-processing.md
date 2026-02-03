# ADR-003: Parallel Chunk Processing for Large Files

**Status:** Accepted
**Date:** 2026-02-03
**Context:** Performance Optimization Feature

---

## Context

The STT application processes large audio files (>50MB) by splitting them into chunks. Currently, chunks are processed **sequentially**:

```
Chunk 1 (15s) → Chunk 2 (15s) → Chunk 3 (15s) → Chunk 4 (15s)
Total: 60 seconds
```

This sequential approach has significant drawbacks:

1. **Slow Processing:** 12-15 seconds per chunk adds up
2. **Poor Resource Utilization:** API and CPU idle during each chunk
3. **User Experience:** Long wait times for large files
4. **No Concurrency:** Single-threaded processing bottleneck

---

## Decision

Implement **parallel chunk processing** with controlled concurrency using asyncio.

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Parallel Orchestrator                       │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
        ┌───────────────────────────────────────────────┐
        │          Dynamic Chunk Sizer                  │
        │  Analyze file → Calculate optimal chunk size  │
        └───────────────────────────────────────────────┘
                            │
                            ▼
        ┌───────────────────────────────────────────────┐
        │            Audio Splitter                     │
        │  Split file into N chunks (10-25MB each)      │
        └───────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Concurrency Controller                        │
│  Semaphore(4) - Max 4 concurrent API calls                      │
└─────────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Chunk 1   │     │   Chunk 2   │     │   Chunk 3   │
│  Processing │     │  Processing │     │  Processing │
│  (12-15s)   │     │  (12-15s)   │     │  (12-15s)   │
└─────────────┘     └─────────────┘     └─────────────┘
        │                   │                   │
        └───────────────────┼───────────────────┘
                            ▼
        ┌───────────────────────────────────────────────┐
        │            Result Merger                      │
        │  Align timestamps → Combine text → Merge      │
        └───────────────────────────────────────────────┘
                            │
                            ▼
                      Final Transcript
        (Total time: 15-20s vs 60s sequential)
```

---

## Dynamic Chunk Sizing

Calculate optimal chunk size based on file characteristics:

```python
from dataclasses import dataclass
from typing import Optional
import os

@dataclass
class ChunkSizeConfig:
    """Chunk size configuration"""
    min_size_mb: int = 10
    max_size_mb: int = 25
    api_limit_mb: int = 25  # Cloud.ru limit

class DynamicChunkSizer:
    """Calculate optimal chunk size based on file characteristics"""

    def calculate_chunk_size(
        self,
        file_path: str,
        file_size_mb: Optional[int] = None
    ) -> int:
        """Calculate optimal chunk size in MB"""
        if file_size_mb is None:
            file_size_mb = os.path.getsize(file_path) / (1024 * 1024)

        # Base size on file size
        if file_size_mb < 50:
            base_size = 15  # Smaller files, smaller chunks
        elif file_size_mb < 100:
            base_size = 20  # Medium files, medium chunks
        else:
            base_size = 25  # Large files, max chunks

        # Adjust for audio quality (bitrate affects size)
        bitrate = self._get_bitrate(file_path)
        if bitrate > 320:  # High quality
            base_size = min(base_size + 5, self.config.max_size_mb)
        elif bitrate < 128:  # Low quality
            base_size = max(base_size - 5, self.config.min_size_mb)

        # Respect API limit
        return min(base_size, self.config.api_limit_mb)

    def estimate_num_chunks(
        self,
        file_path: str,
        chunk_size_mb: Optional[int] = None
    ) -> int:
        """Estimate number of chunks for file"""
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        chunk_size = chunk_size_mb or self.calculate_chunk_size(file_path)
        return max(1, int(file_size_mb / chunk_size))

    def _get_bitrate(self, file_path: str) -> int:
        """Get audio bitrate in kbps"""
        try:
            from pydub import AudioSegment
            audio = AudioSegment.from_file(file_path)
            # Rough bitrate calculation
            return audio.frame_rate * audio.frame_width * audio.channels * 8 / 1000
        except:
            return 128  # Default assumption
```

---

## Parallel Chunk Processing

```python
import asyncio
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class ChunkResult:
    """Result from processing a single chunk"""
    index: int
    text: str
    language: str
    segments: List[Dict]
    duration_ms: int
    from_cache: bool = False

class ParallelChunkProcessor:
    """Process audio chunks in parallel with controlled concurrency"""

    def __init__(
        self,
        concurrency_limit: int = 4,
        cache: Optional[MultiLevelCache] = None
    ):
        self.concurrency_limit = concurrency_limit
        self.cache = cache
        self.semaphore = asyncio.Semaphore(concurrency_limit)

    async def process_file(
        self,
        file_path: str,
        language: Optional[str] = None,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """Process file with parallel chunk execution"""
        # Calculate optimal chunk size
        sizer = DynamicChunkSizer()
        chunk_size_mb = sizer.calculate_chunk_size(file_path)
        num_chunks = sizer.estimate_num_chunks(file_path, chunk_size_mb)

        logger.info(
            f"Processing file with {num_chunks} chunks "
            f"({chunk_size_mb}MB each)"
        )

        # Split file into chunks
        chunks = self._split_file(file_path, chunk_size_mb)

        # Process chunks in parallel
        results = await self._process_chunks_parallel(
            chunks=chunks,
            language=language,
            progress_callback=progress_callback
        )

        # Merge results
        merged = self._merge_results(results)

        return {
            "text": merged["text"],
            "language": merged["language"],
            "segments": merged["segments"],
            "processing_time": merged["total_time"],
            "chunks_processed": len(results),
            "cache_hits": sum(1 for r in results if r.from_cache)
        }

    async def _process_chunks_parallel(
        self,
        chunks: List[AudioChunk],
        language: Optional[str],
        progress_callback: Optional[callable]
    ) -> List[ChunkResult]:
        """Process chunks with controlled concurrency"""
        tasks = [
            self._process_single_chunk(
                chunk=chunk,
                index=i,
                total_chunks=len(chunks),
                language=language,
                progress_callback=progress_callback
            )
            for i, chunk in enumerate(chunks)
        ]

        # Execute with semaphore limiting concurrency
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle exceptions
        valid_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Chunk {i} failed: {result}")
                # Retry logic could be added here
            else:
                valid_results.append(result)

        return valid_results

    async def _process_single_chunk(
        self,
        chunk: AudioChunk,
        index: int,
        total_chunks: int,
        language: Optional[str],
        progress_callback: Optional[callable]
    ) -> ChunkResult:
        """Process single chunk (async wrapper)"""
        # Acquire semaphore (limits concurrency)
        async with self.semaphore:
            logger.info(f"Processing chunk {index + 1}/{total_chunks}")

            # Check cache first
            if self.cache:
                cache_key = CacheKey.for_transcript(
                    chunk.hash,
                    language or "auto"
                )
                cached = self.cache.get(cache_key)
                if cached:
                    logger.info(f"Cache hit for chunk {index + 1}")
                    if progress_callback:
                        progress = (index + 1) / total_chunks
                        progress_callback(progress)
                    return ChunkResult.from_cache(
                        cached["value"],
                        index
                    )

            # Process via API
            try:
                # Run blocking API call in thread pool
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None,
                    self._transcribe_chunk,
                    chunk,
                    language
                )

                # Cache result
                if self.cache:
                    self.cache.put(
                        key=cache_key,
                        value=result,
                        cache_type="transcript",
                        ttl_seconds=86400
                    )

                # Update progress
                if progress_callback:
                    progress = (index + 1) / total_chunks
                    progress_callback(progress)

                return ChunkResult(
                    index=index,
                    text=result["text"],
                    language=result.get("language", language),
                    segments=result.get("segments", []),
                    duration_ms=chunk.duration_ms,
                    from_cache=False
                )

            except Exception as e:
                logger.error(f"Error processing chunk {index}: {e}")
                raise

    def _transcribe_chunk(
        self,
        chunk: AudioChunk,
        language: Optional[str]
    ) -> Dict[str, Any]:
        """Blocking transcription call (runs in thread pool)"""
        # Use existing transcription service
        with tempfile.NamedTemporaryFile(delete=False) as temp:
            chunk.save(temp.name)
            result = self.transcription_service.transcribe_file(
                file_path=temp.name,
                language=language
            )
            os.unlink(temp.name)
            return result

    def _merge_results(self, results: List[ChunkResult]) -> Dict[str, Any]:
        """Merge chunk results into final transcript"""
        # Sort by index to ensure correct order
        sorted_results = sorted(results, key=lambda r: r.index)

        # Combine text
        combined_text = " ".join(r.text for r in sorted_results)

        # Combine segments with timestamp adjustment
        all_segments = []
        time_offset_ms = 0
        for result in sorted_results:
            for segment in result.segments:
                adjusted_segment = segment.copy()
                adjusted_segment["start"] += time_offset_ms / 1000.0
                adjusted_segment["end"] += time_offset_ms / 1000.0
                all_segments.append(adjusted_segment)
            time_offset_ms += result.duration_ms

        # Detect language (use most common)
        languages = [r.language for r in sorted_results if r.language]
        detected_language = max(set(languages), key=languages.count) if languages else "auto"

        return {
            "text": combined_text,
            "language": detected_language,
            "segments": all_segments,
            "total_time": sum(r.duration_ms for r in sorted_results)
        }

    def _split_file(
        self,
        file_path: str,
        chunk_size_mb: int
    ) -> List[AudioChunk]:
        """Split audio file into chunks"""
        try:
            from pydub import AudioSegment

            audio = AudioSegment.from_file(file_path)
            duration_ms = len(audio)
            chunk_size_ms = int(
                (chunk_size_mb * 1024 * 1024) /
                (os.path.getsize(file_path) / duration_ms)
            )

            chunks = []
            start_ms = 0
            index = 0

            while start_ms < duration_ms:
                end_ms = min(start_ms + chunk_size_ms, duration_ms)
                chunk_audio = audio[start_ms:end_ms]

                chunks.append(AudioChunk(
                    index=index,
                    audio=chunk_audio,
                    start_ms=start_ms,
                    end_ms=end_ms
                ))

                start_ms = end_ms
                index += 1

            return chunks

        except ImportError:
            raise NotImplementedError(
                "Parallel processing requires pydub. "
                "Install with: pip install pydub"
            )
```

---

## Progress Tracking

```python
class ProgressTracker:
    """Track and report processing progress"""

    def __init__(self, total_chunks: int):
        self.total_chunks = total_chunks
        self.completed_chunks = 0
        self.start_time = None

    def update(self, chunk_index: int, status: str) -> float:
        """Update progress and return current percentage"""
        if status == "completed":
            self.completed_chunks += 1

        progress = self.completed_chunks / self.total_chunks
        logger.info(f"Progress: {progress:.1%} ({self.completed_chunks}/{self.total_chunks})")

        return progress

    def get_eta(self) -> Optional[float]:
        """Get estimated time remaining in seconds"""
        if not self.start_time or self.completed_chunks == 0:
            return None

        elapsed = time.time() - self.start_time
        avg_time_per_chunk = elapsed / self.completed_chunks
        remaining_chunks = self.total_chunks - self.completed_chunks

        return avg_time_per_chunk * remaining_chunks
```

---

## Usage Example

```python
# backend/app/main.py

@app.post("/api/transcripts/upload")
async def upload_file(
    file: UploadFile = File(...),
    language: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    # Save file
    file_path = file_service.save_uploaded_file(await file.read(), file.filename)

    # Create transcript record
    transcript = Transcript(
        original_filename=file.filename,
        file_path=file_path,
        status=TranscriptStatus.PROCESSING
    )
    db.add(transcript)
    db.commit()

    # Process with parallel chunks
    processor = ParallelChunkProcessor(
        concurrency_limit=4,
        cache=cache_service
    )

    # Progress callback
    def update_progress(progress: float):
        transcript.progress = progress
        db.commit()

    # Process file
    result = await processor.process_file(
        file_path=file_path,
        language=language,
        progress_callback=update_progress
    )

    # Update transcript
    transcript.transcription_text = result["text"]
    transcript.transcription_json = {"segments": result["segments"]}
    transcript.status = TranscriptStatus.COMPLETED
    db.commit()

    return result
```

---

## Performance Comparison

### Sequential (Current)
- 100MB file = 4 chunks
- 15 seconds per chunk
- **Total: 60 seconds**

### Parallel (New)
- 100MB file = 4 chunks
- 4 concurrent API calls
- **Total: 15-20 seconds** (3-4x speedup)

### Scaling

| File Size | Chunks | Sequential | Parallel (4x) | Speedup |
|-----------|--------|------------|---------------|---------|
| 25MB | 1 | 15s | 15s | 1x |
| 50MB | 2 | 30s | 15s | 2x |
| 100MB | 4 | 60s | 20s | 3x |
| 200MB | 8 | 120s | 40s | 3x |
| 500MB | 20 | 300s | 120s | 2.5x |

---

## Configuration

```python
# backend/app/config.py

class ProcessingConfig:
    # Parallel processing
    MAX_CONCURRENT_CHUNKS: int = 4
    CHUNK_SIZE_MIN_MB: int = 10
    CHUNK_SIZE_MAX_MB: int = 25
    API_RATE_LIMIT_PER_MINUTE: int = 20

    # Retry
    MAX_CHUNK_RETRIES: int = 3
    CHUNK_RETRY_DELAY_SECONDS: int = 5

    # Progress
    PROGRESS_UPDATE_INTERVAL_SECONDS: int = 1
```

---

## Consequences

### Positive

1. **Speed:** 3-4x faster for multi-chunk files
2. **Resource Efficiency:** Better API and CPU utilization
3. **Scalability:** Linear speedup with concurrency
4. **UX:** Faster results for large files

### Negative

1. **Complexity:** Async code is harder to debug
2. **Memory:** More memory usage for concurrent tasks
3. **API Limits:** Need to respect rate limits
4. **Error Handling:** Partial failures require handling

### Mitigations

- Configurable concurrency limit
- Semaphore to prevent overload
- Graceful degradation on errors
- Comprehensive logging

---

## Alternatives Considered

### 1. Sequential (Current)

**Pros:** Simple, predictable
**Cons:** Slow, poor resource use
**Decision:** Being replaced

### 2. Multi-Processing

**Pros:** True parallelism across CPUs
**Cons:** High memory, complex IPC
**Decision:** Not needed (I/O bound)

### 3. Distributed (Multiple Workers)

**Pros:** Horizontal scaling
**Cons:** Network overhead, complexity
**Decision:** Future enhancement

---

## References

- AsyncIO Concurrency: https://docs.python.org/3/library/asyncio.html
- pydub Audio Splitting: https://github.com/jiaaro/pydub

---

**Document Control**

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-03 | Performance Team | Initial ADR |
