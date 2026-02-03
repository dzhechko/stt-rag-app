# Pseudocode: Parallel Chunk Processing

**Feature:** Performance Optimizations
**Algorithm:** Parallel Audio Chunk Processing with Controlled Concurrency

---

## Overview

Process audio file chunks in parallel while respecting API rate limits and maintaining result order.

---

## Algorithm: Parallel Chunk Processing

```
FUNCTION process_file_parallel(file_path, language, concurrency_limit=4):
    INPUT:
        file_path: Path to audio file
        language: Target language (or "auto" for detection)
        concurrency_limit: Max concurrent API calls (default: 4)

    OUTPUT:
        transcript: Merged transcript with text and timestamps

    # Step 1: Calculate optimal chunk size
    chunk_size_mb = calculate_optimal_chunk_size(file_path)

    # Step 2: Split file into chunks
    chunks = split_file_into_chunks(file_path, chunk_size_mb)
    num_chunks = length(chunks)

    LOG "Processing file with {num_chunks} chunks ({chunk_size_mb}MB each)"

    # Step 3: Process chunks in parallel with semaphore control
    results = parallel_map_with_semaphore(
        items=chunks,
        func=process_single_chunk,
        concurrency_limit=concurrency_limit,
        progress_callback=update_progress
    )

    # Step 4: Merge results in order
    transcript = merge_chunk_results(results)

    RETURN transcript


FUNCTION process_single_chunk(chunk, index, language, progress_callback):
    INPUT:
        chunk: Audio chunk data
        index: Chunk index (for ordering)
        language: Target language
        progress_callback: Function to report progress

    OUTPUT:
        result: Chunk transcription result

    # Step 1: Generate cache key
    chunk_hash = sha256(chunk.data)
    cache_key = "transcript:{chunk_hash}:{language}"

    # Step 2: Check cache (L1 → L2 → L3)
    cached_result = cache_get(cache_key)
    IF cached_result EXISTS:
        LOG "Cache hit for chunk {index + 1}"
        result = cached_result
        result.from_cache = TRUE
    ELSE:
        # Step 3: Transcribe via API with retry
        result = transcribe_with_retry(
            chunk=chunk,
            language=language,
            max_retries=3
        )

        # Step 4: Cache result (L1, L2, L3)
        cache_put(cache_key, result, ttl=86400)  # 24 hours
        result.from_cache = FALSE

    # Step 5: Update progress
    progress = (index + 1) / total_chunks
    progress_callback(progress)

    RETURN result


FUNCTION transcribe_with_retry(chunk, language, max_retries=3):
    INPUT:
        chunk: Audio chunk to transcribe
        language: Target language
        max_retries: Maximum retry attempts

    OUTPUT:
        result: Transcription result

    FOR attempt FROM 0 TO max_retries - 1:
        TRY:
            LOG "Transcribing chunk (attempt {attempt + 1}/{max_retries})"

            # Call Cloud.ru Whisper API
            result = api_client.transcribe(
                audio_data=chunk.data,
                model="whisper-large-v3",
                language=language
            )

            RETURN result

        CATCH TransientError AS error:
            IF attempt < max_retries - 1:
                # Exponential backoff
                wait_time = 2 ^ attempt  # 1s, 2s, 4s
                LOG "Retry in {wait_time}s: {error.message}"
                sleep(wait_time)
            ELSE:
                LOG "Max retries exceeded"
                THROW error


FUNCTION parallel_map_with_semaphore(items, func, concurrency_limit, progress_callback):
    INPUT:
        items: List of items to process
        func: Function to apply to each item
        concurrency_limit: Max concurrent executions
        progress_callback: Progress reporting function

    OUTPUT:
        results: List of results in original order

    # Create semaphore for concurrency control
    semaphore = Semaphore(concurrency_limit)

    # Create async tasks for all items
    tasks = []
    FOR EACH item WITH index IN items:
        task = async_task(process_with_semaphore, item, index, semaphore, func, progress_callback)
        tasks.append(task)

    # Wait for all tasks to complete
    raw_results = await gather(tasks)

    # Sort by index to maintain order
    results = sort(raw_results, key="index")

    RETURN results


FUNCTION process_with_semaphore(item, index, semaphore, func, progress_callback):
    INPUT:
        item: Item to process
        index: Item index
        semaphore: Concurrency control semaphore
        func: Processing function
        progress_callback: Progress callback

    OUTPUT:
        result: Processing result with index

    # Acquire semaphore (blocks if limit reached)
    semaphore.acquire()

    TRY:
        # Process the item
        result = func(item, index, progress_callback)
        result.index = index
        RETURN result

    FINALLY:
        # Always release semaphore
        semaphore.release()


FUNCTION merge_chunk_results(results):
    INPUT:
        results: List of chunk results

    OUTPUT:
        transcript: Merged transcript

    # Sort results by index (should already be sorted)
    sorted_results = sort(results, key="index")

    # Combine text
    combined_text = ""
    FOR EACH result IN sorted_results:
        combined_text += " " + result.text

    # Merge segments with timestamp adjustment
    all_segments = []
    time_offset_ms = 0

    FOR EACH result IN sorted_results:
        FOR EACH segment IN result.segments:
            adjusted_segment = copy(segment)
            adjusted_segment.start += time_offset_ms / 1000
            adjusted_segment.end += time_offset_ms / 1000
            all_segments.append(adjusted_segment)

        time_offset_ms += result.duration_ms

    # Detect language (most common across chunks)
    languages = [result.language FOR result IN results IF result.language EXISTS]
    detected_language = mode(languages) IF languages NOT EMPTY ELSE "auto"

    RETURN {
        "text": combined_text.strip(),
        "language": detected_language,
        "segments": all_segments,
        "total_duration_ms": time_offset_ms
    }


FUNCTION calculate_optimal_chunk_size(file_path):
    INPUT:
        file_path: Path to audio file

    OUTPUT:
        chunk_size_mb: Optimal chunk size in MB

    file_size_mb = get_file_size(file_path) / (1024 * 1024)

    # Base size on file size
    IF file_size_mb < 50:
        base_size = 15  # Smaller files, smaller chunks
    ELSE IF file_size_mb < 100:
        base_size = 20  # Medium files, medium chunks
    ELSE:
        base_size = 25  # Large files, max chunks

    # Adjust for audio bitrate
    bitrate = get_audio_bitrate(file_path)
    IF bitrate > 320:  # High quality
        base_size = min(base_size + 5, 25)
    ELSE IF bitrate < 128:  # Low quality
        base_size = max(base_size - 5, 10)

    # Respect API limit
    RETURN min(base_size, 25)


FUNCTION split_file_into_chunks(file_path, chunk_size_mb):
    INPUT:
        file_path: Path to audio file
        chunk_size_mb: Target chunk size in MB

    OUTPUT:
        chunks: List of AudioChunk objects

    # Load audio file
    audio = load_audio_file(file_path)
    duration_ms = audio.duration_ms
    file_size_mb = audio.size_bytes / (1024 * 1024)

    # Calculate chunk duration
    bytes_per_ms = file_size_mb / duration_ms
    chunk_duration_ms = (chunk_size_mb * 1024 * 1024) / bytes_per_ms

    # Split into chunks
    chunks = []
    start_ms = 0
    index = 0

    WHILE start_ms < duration_ms:
        end_ms = min(start_ms + chunk_duration_ms, duration_ms)
        chunk_audio = audio.slice(start_ms, end_ms)

        chunks.append(AudioChunk(
            index=index,
            audio=chunk_audio,
            start_ms=start_ms,
            end_ms=end_ms,
            duration_ms=end_ms - start_ms
        ))

        start_ms = end_ms
        index += 1

    RETURN chunks
```

---

## Complexity Analysis

### Time Complexity

- **Best Case (All cache hits):** O(n) - Parallel lookup, minimal API calls
- **Average Case (Mixed):** O(n/k) - k = concurrency limit
- **Worst Case (All cache misses):** O(n/k) - Limited by concurrency

### Space Complexity

- **Audio Chunks:** O(n * chunk_size) - Temporary chunk storage
- **Results:** O(n) - Store all chunk results before merge
- **Total:** O(n * chunk_size)

### Parallel Speedup

```
Speedup = min(n, k) / k_eff

Where:
  n = number of chunks
  k = concurrency limit
  k_eff = effective concurrency (considering cache hits)

Theoretical maximum: k (when n >= k)
Realistic: 2-4x for typical workloads
```

---

## Example Execution

### Input
- File: 100MB audio file
- Language: Russian
- Concurrency: 4

### Execution Flow

```
1. Calculate chunk size: 20MB
2. Split into 5 chunks
3. Process in parallel (max 4 concurrent):

Time 0s:
  ├─ Chunk 0: Processing (API call started)
  ├─ Chunk 1: Processing (API call started)
  ├─ Chunk 2: Processing (API call started)
  └─ Chunk 3: Processing (API call started)
  └─ Chunk 4: Waiting (semaphore)

Time 15s:
  ├─ Chunk 0: Complete
  ├─ Chunk 1: Complete
  ├─ Chunk 2: Complete
  ├─ Chunk 3: Complete
  └─ Chunk 4: Processing (started)

Time 30s:
  └─ Chunk 4: Complete

Total: 30s (vs 75s sequential = 2.5x speedup)
```

---

## Edge Cases

### 1. Single Chunk (Small File)

```
IF num_chunks == 1:
    # No parallelism needed
    RETURN process_single_chunk(chunks[0], language)
```

### 2. API Rate Limit

```
IF api_rate_limit_exceeded():
    # Reduce concurrency
    new_limit = max(1, concurrency_limit // 2)
    RETURN process_file_parallel(file_path, language, new_limit)
```

### 3. Failed Chunk

```
IF chunk_result IS ERROR:
    # Retry failed chunk only
    RETRY chunk with exponential backoff
    IF still fails:
        MARK transcript as PARTIAL
        INCLUDE error in result
```

### 4. Memory Limit

```
IF available_memory < (num_chunks * chunk_size):
    # Reduce chunk size, increase count
    new_chunk_size = (available_memory * 0.8) / num_chunks
    RETURN process_file_parallel(file_path, language, new_chunk_size)
```

---

**Document Control**

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-03 | Performance Team | Initial pseudocode |
