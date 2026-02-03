# Ubiquitous Language - Feature 3: New Features

**Version:** 1.0.0
**Date:** 2026-02-03

## Overview

This document defines the ubiquitous language shared across all teams working on Feature 3. These terms must be used consistently in code, documentation, and conversations.

## Core Domain Terms

### Transcript
The complete text representation of an audio file, including all segments, timestamps, and metadata.

**Contexts:** All contexts

**Properties:**
- `id`: Unique identifier
- `audioFileId`: Source audio reference
- `language`: Detected or specified language
- `segments`: Time-aligned text units
- `duration`: Audio length in seconds
- `wordCount`: Total words
- `createdAt`: Creation timestamp
- `status`: Processing state

---

### Segment
A time-aligned unit of text within a transcript, typically representing a continuous speech segment.

**Contexts:** Transcript Editing, Export, Speaker Diarization

**Properties:**
- `id`: Unique identifier
- `transcriptId`: Parent transcript
- `startTime`: Beginning timestamp (seconds)
- `endTime`: Ending timestamp (seconds)
- `text`: Spoken words
- `speakerId`: Speaker reference (optional)
- `confidence`: Recognition accuracy (0-1)

---

### Language
The identified spoken language in audio, represented as ISO 639-1 code.

**Contexts:** Language Detection, Global Search, Transcript Editing

**Properties:**
- `code`: ISO 639-1 code (e.g., "en", "ru", "es")
- `name`: Full name (e.g., "English", "Russian")
- `confidence`: Detection probability (0-1)
- `detectedAt`: When detection occurred

**Supported Languages:**
- English (en)
- Russian (ru)
- Spanish (es)
- French (fr)
- German (de)
- Portuguese (pt)
- Italian (it)
- Dutch (nl)
- Polish (pl)
- Chinese (zh)

---

## Context-Specific Terms

### Export Context

#### Export
The process of converting a transcript into an external file format.

**Properties:**
- `format`: Target format (SRT, VTT, DOCX, TXT, JSON)
- `includeMetadata`: Boolean flag
- `includeTimestamps`: Boolean flag
- `includeSpeakers`: Boolean flag

---

#### Timecode
A timestamp representation indicating when a segment starts or ends.

**Formats:**
- **SRT:** `HH:MM:SS,mmm` (e.g., `00:01:23,456`)
- **VTT:** `HH:MM:SS.mmm` (e.g., `00:01:23.456`)
- **JSON:** Unix timestamp seconds (e.g., `83.456`)

---

#### Export Format
The target file format for transcript export.

| Format | Extension | Description |
|--------|-----------|-------------|
| SRT | .srt | SubRip subtitle format |
| VTT | .vtt | WebVTT format for HTML5 video |
| DOCX | .docx | Microsoft Word document |
| TXT | .txt | Plain text without formatting |
| JSON | .json | Structured data with metadata |

---

### Language Detection Context

#### Auto-detection
Automatic identification of the spoken language from audio content before transcription.

**Process:**
1. Extract audio sample (first 30 seconds)
2. Analyze audio features
3. Compare against language models
4. Return language with confidence score

---

#### Confidence Score
A probability value (0-1) indicating the accuracy of language detection.

**Thresholds:**
- `>= 0.95`: Auto-confirm without warning
- `0.70 - 0.94`: Auto-confirm with warning
- `< 0.70`: Require manual selection

---

#### Fallback Language
The default language used when auto-detection fails or confidence is low.

**Default:** User's preferred language or English

---

### Speaker Diarization Context

#### Speaker
A distinct individual identified in an audio recording.

**Properties:**
- `id`: Unique identifier (e.g., "SPEAKER_01", custom name)
- `segments`: List of time ranges where speaker talks
- `profileId`: Reference to learned characteristics
- `totalDuration`: Cumulative speaking time

---

#### Diarization
The process of identifying who spoke when in an audio recording.

**Output:**
- Speaker count (2-10 speakers)
- Segment assignments (each segment has speaker)
- Speaker labels (default or custom names)

---

#### Speaker Profile
Learned characteristics of a speaker for identification across recordings.

**Properties:**
- `id`: Unique identifier
- `name`: Custom name (optional)
- `embeddings`: Voice characteristics
- `appearanceCount`: How many times seen

---

### Global Search Context

#### Query
A user's search input for finding content across transcripts.

**Types:**
- **Simple:** Single word or phrase
- **Boolean:** With AND, OR, NOT operators
- **Phrase:** Exact phrase in quotes
- **Proximity:** Words within N distance

---

#### Filter
A constraint applied to search results.

**Filter Types:**
- `dateRange`: Start and end dates
- `language`: Specific language code
- `duration`: Min/max audio duration
- `speaker`: Specific speaker ID
- `tags`: Array of tags

---

#### Relevance Score
A ranking metric (0-1) indicating how well a result matches the query.

**Factors:**
- Term frequency (TF)
- Inverse document frequency (IDF)
- Match position (earlier = higher)
- Context matches (more = higher)

---

#### Context Snippet
The text surrounding a matched term, typically 50 characters before and after.

**Purpose:** Show match context in search results

---

### Batch Processing Context

#### Batch
A group of audio files uploaded together for processing.

**Properties:**
- `id`: Unique identifier
- `items`: Array of batch items (max 10)
- `status`: Pending, Processing, Completed, Failed
- `createdAt`: Upload timestamp
- `completedAt`: Finish timestamp

---

#### Queue
An ordered list of jobs waiting to be processed.

**Properties:**
- `type`: Job type (detection, transcription, diarization)
- `priority`: Numeric priority (higher = first)
- `maxConcurrency`: Limit on simultaneous jobs

---

#### Item Status
The processing state of an individual file in a batch.

| Status | Description |
|--------|-------------|
| `pending` | Waiting in queue |
| `processing` | Currently being processed |
| `completed` | Successfully finished |
| `failed` | Processing failed with error |

---

### Transcript Editing Context

#### Edit
A modification to transcript text content.

**Types:**
- `insert`: Add new text
- `delete`: Remove text
- `replace`: Replace existing text

---

#### Playback Sync
The alignment between transcript text position and audio playback position.

**Behaviors:**
- Click text -> Jump to audio position
- Playback -> Auto-scroll text
- Edit -> Preserve timestamp

---

#### Auto-scroll
Automatic scrolling of transcript text during audio playback to keep current segment visible.

**Behavior:** Scroll when playback enters new segment

---

#### Edited Flag
A visual indicator marking segments that have been modified from original transcription.

**Purpose:** Show users what they've changed

---

### Version History Context

#### Version
A snapshot of a transcript at a specific point in time.

**Properties:**
- `id`: Unique identifier
- `transcriptId`: Parent transcript
- `number`: Sequential version number
- `content`: Full transcript state
- `changeSummary`: Description of changes
- `createdAt`: Snapshot timestamp
- `createdBy`: User or system

---

#### Diff
A comparison between two transcript versions showing differences.

**Output:**
- Added text (highlighted green)
- Deleted text (highlighted red)
- Modified text (highlighted yellow)

---

#### Restore
The act of reverting a transcript to a previous version state.

**Behavior:** Creates new version with restored content

---

#### Retention Policy
The maximum number of versions to keep per transcript.

**Default:** 50 versions
**Action:** Delete oldest versions when limit exceeded

---

### API Access Context

#### API Key
A unique token used to authenticate API requests from external applications.

**Properties:**
- `key`: Secure random token
- `clientId`: Associated application
- `permissions`: Allowed operations
- `rateLimit`: Max requests per minute
- `createdAt`: Creation timestamp
- `expiresAt`: Expiration date (optional)

---

#### Endpoint
A specific URL path exposed by the API for a system operation.

**Format:** `/api/v1/{resource}/{id}/{action}`

**Examples:**
- `POST /api/v1/transcribe` - Start transcription
- `GET /api/v1/transcripts/{id}` - Get transcript
- `POST /api/v1/transcripts/{id}/export` - Export transcript
- `GET /api/v1/search` - Search transcripts

---

#### Rate Limit
The maximum number of API requests allowed per time period.

**Default:** 100 requests/minute per API key
**Enforcement:** Return 429 status when exceeded

---

## Anti-Patterns to Avoid

### Don't Use These Terms

| Anti-Pattern | Correct Term | Reason |
|--------------|--------------|--------|
| "Subtitle" | Segment | Subtitle is export format, segment is domain entity |
| "Caption" | Segment | Caption is display concept, segment is data |
| "Speech-to-Text" | Transcription | STT is process, Transcript is entity |
| "Voice" | Speaker | Voice is physical, Speaker is domain concept |
| "Clip" | Segment | Clip is editing concept, Segment is domain |
| "Language Detection" | Auto-detection | Full phrase, avoid abbreviation |
| "Convert" | Export | Export is domain term, convert is generic |
| "Search Result" | SearchResult | Use consistent capitalization |
| "User" | ApiClient | In API context, use ApiClient not User |

### Language Rules

1. **Be Explicit:** Use "Transcript" not "Document" or "Text"
2. **Be Consistent:** Use "Segment" everywhere, not "Segment" vs "Subtitle"
3. **Be Domain-Driven:** Use business language, not technical
4. **Be Precise:** "Language Detection" not "Language ID" or "Lang Detect"

## Code Examples

### Python (Backend)
```python
# CORRECT: Use ubiquitous language
transcript = Transcript(
    id=transcript_id,
    language=DetectedLanguage(code="en", confidence=0.98),
    segments=[
        Segment(
            id=segment_id,
            start_time=0.0,
            end_time=4.5,
            text="Hello world"
        )
    ]
)

# INCORRECT: Generic terms
document = {
    "text": "Hello world",
    "lang": "en"
}
```

### TypeScript (Frontend)
```typescript
// CORRECT: Use ubiquitous language
interface Transcript {
  id: string;
  language: DetectedLanguage;
  segments: Segment[];
}

interface Segment {
  id: string;
  startTime: number;
  endTime: number;
  text: string;
  speakerId?: string;
}

// INCORRECT: Generic terms
interface Document {
  content: string;
  lang: string;
}
```

## Communication Examples

### Daily Standup
- "The `Transcript` entity now stores the `DetectedLanguage` value object"
- "I'm working on the `Export` context, adding SRT format support"
- "The `Language Detection` service is returning low `confidence` scores"

### Code Review
- "Rename `convert()` to `export()` to match ubiquitous language"
- "Use `Segment` instead of `Subtitle` in this component"
- "The `Speaker` entity should have a `profileId`, not `voiceId`"

### Documentation
- "When a `Batch` is created, each `BatchItem` is enqueued for processing"
- "The `Auto-detection` process returns a `DetectedLanguage` with `confidence` score"
- "Users can `restore` a transcript to any previous `Version`"

## Glossary Index

| Term | Context | Definition |
|------|---------|------------|
| Auto-detection | Language Detection | Automatic language identification |
| Batch | Batch Processing | Group of files for processing |
| Confidence Score | Language Detection | Detection probability |
| Context Snippet | Global Search | Text around match |
| Diff | Version History | Version comparison |
| Diarization | Speaker Diarization | Speaker identification |
| Edit | Transcript Editing | Text modification |
| Export | Export | Format conversion |
| Language | All | Spoken language ISO code |
| Query | Global Search | Search input |
| Relevance Score | Global Search | Match quality ranking |
| Restore | Version History | Revert to previous version |
| Segment | Editing, Export | Time-aligned text unit |
| Speaker | Diarization, Editing | Identified person |
| Timecode | Export | Timestamp representation |
| Transcript | All | Complete audio text representation |
| Version | Version History | Transcript snapshot |
