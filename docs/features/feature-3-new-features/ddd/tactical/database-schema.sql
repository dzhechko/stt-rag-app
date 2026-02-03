-- Database Schema for Feature 3: New Features
-- PostgreSQL 15+
-- Version: 1.0.0
-- Date: 2026-02-03

-- ============================================================
-- EXTENSIONS
-- ============================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For full-text search

-- ============================================================
-- ENUMS
-- ============================================================

CREATE TYPE export_format_t AS ENUM ('srt', 'vtt', 'docx', 'txt', 'json');
CREATE TYPE job_status_t AS ENUM ('pending', 'processing', 'completed', 'failed');
CREATE TYPE edit_operation_t AS ENUM ('insert', 'delete', 'replace');
CREATE TYPE api_permission_t AS ENUM ('read', 'write', 'delete', 'admin');

-- ============================================================
-- TRANSCRIPT EDITING CONTEXT
-- ============================================================

-- Transcripts are the core entity, extended from existing system
CREATE TABLE IF NOT EXISTS transcripts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    audio_file_id UUID NOT NULL,
    user_id UUID NOT NULL,

    -- Language detection
    language_code VARCHAR(2) NOT NULL,  -- ISO 639-1
    language_confidence DECIMAL(3,2) DEFAULT 1.00,

    -- Metadata
    duration_seconds INTEGER NOT NULL,
    word_count INTEGER DEFAULT 0,
    segment_count INTEGER DEFAULT 0,

    -- Status
    status VARCHAR(50) NOT NULL DEFAULT 'processing',

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_edited_at TIMESTAMPTZ,

    -- Edit tracking
    is_edited BOOLEAN DEFAULT FALSE,
    edit_count INTEGER DEFAULT 0,

    CONSTRAINT fk_transcripts_user
        FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE CASCADE,

    CONSTRAINT valid_language_code
        CHECK (language_code ~ '^[a-z]{2}$'),

    CONSTRAINT valid_confidence
        CHECK (language_confidence BETWEEN 0 AND 1)
);

CREATE INDEX idx_transcripts_user_id ON transcripts(user_id);
CREATE INDEX idx_transcripts_language ON transcripts(language_code);
CREATE INDEX idx_transcripts_created_at ON transcripts(created_at DESC);
CREATE INDEX idx_transcripts_fulltext ON transcripts USING gin(to_tsvector('english', id::text)); -- Placeholder for content search

-- Transcript segments (time-aligned text units)
CREATE TABLE IF NOT EXISTS transcript_segments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    transcript_id UUID NOT NULL,

    -- Time alignment
    start_time DECIMAL(10,3) NOT NULL,  -- Seconds with millisecond precision
    end_time DECIMAL(10,3) NOT NULL,

    -- Content
    text TEXT NOT NULL,
    confidence DECIMAL(4,3),  -- ASR confidence score

    -- Speaker (optional, if diarization enabled)
    speaker_id VARCHAR(50),  -- SPEAKER_01, SPEAKER_02, or custom name

    -- Edit tracking
    is_edited BOOLEAN DEFAULT FALSE,
    original_text TEXT,

    -- Ordering
    sequence_number INTEGER NOT NULL,

    CONSTRAINT fk_segments_transcript
        FOREIGN KEY (transcript_id) REFERENCES transcripts(id)
        ON DELETE CASCADE,

    CONSTRAINT valid_time_range
        CHECK (end_time > start_time),

    CONSTRAINT valid_confidence
        CHECK (confidence IS NULL OR confidence BETWEEN 0 AND 1)
);

CREATE INDEX idx_segments_transcript_id ON transcript_segments(transcript_id);
CREATE INDEX idx_segments_speaker ON transcript_segments(speaker_id) WHERE speaker_id IS NOT NULL;
CREATE INDEX idx_segments_time_range ON transcript_segments(transcript_id, start_time, end_time);

-- ============================================================
-- LANGUAGE DETECTION CONTEXT
-- ============================================================

-- Language detection results
CREATE TABLE IF NOT EXISTS language_detections (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    audio_file_id UUID NOT NULL UNIQUE,
    transcript_id UUID,

    -- Detection result
    detected_language VARCHAR(2) NOT NULL,
    language_name VARCHAR(50) NOT NULL,
    confidence DECIMAL(3,2) NOT NULL,

    -- Detection metadata
    detection_duration_seconds DECIMAL(6,3),
    sample_analyzed_seconds DECIMAL(6,3),
    detection_method VARCHAR(50) DEFAULT 'cloudru_whisper',

    -- Fallback
    is_fallback BOOLEAN DEFAULT FALSE,
    fallback_reason TEXT,

    -- Timestamps
    detected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_detections_transcript
        FOREIGN KEY (transcript_id) REFERENCES transcripts(id)
        ON DELETE SET NULL,

    CONSTRAINT valid_detection_confidence
        CHECK (confidence BETWEEN 0 AND 1)
);

CREATE INDEX idx_detections_audio_file ON language_detections(audio_file_id);
CREATE INDEX idx_detections_language ON language_detections(detected_language);

-- ============================================================
-- SPEAKER DIARIZATION CONTEXT
-- ============================================================

-- Speaker profiles (learned speaker characteristics)
CREATE TABLE IF NOT EXISTS speaker_profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,

    -- Identification
    name VARCHAR(100) NOT NULL,  -- SPEAKER_01, SPEAKER_02, or custom name
    is_custom_name BOOLEAN DEFAULT FALSE,

    -- Learned characteristics
    embeddings VECTOR(128),  -- Voice embedding
    avg_pitch DECIMAL(6,2),
    avg_speaking_rate DECIMAL(6,2),

    -- Appearance tracking
    appearance_count INTEGER DEFAULT 1,
    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_profiles_user
        FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE CASCADE,

    CONSTRAINT unique_user_name
        UNIQUE (user_id, name)
);

CREATE INDEX idx_speaker_profiles_user ON speaker_profiles(user_id);

-- Speaker segments (diarization results)
CREATE TABLE IF NOT EXISTS speaker_segments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    transcript_id UUID NOT NULL,
    segment_id UUID NOT NULL UNIQUE,

    -- Speaker assignment
    speaker_profile_id UUID,
    speaker_label VARCHAR(100) NOT NULL,  -- Denormalized for performance

    -- Confidence
    confidence DECIMAL(3,2),

    CONSTRAINT fk_speaker_segments_transcript
        FOREIGN KEY (transcript_id) REFERENCES transcripts(id)
        ON DELETE CASCADE,

    CONSTRAINT fk_speaker_segments_profile
        FOREIGN KEY (speaker_profile_id) REFERENCES speaker_profiles(id)
        ON DELETE SET NULL,

    CONSTRAINT fk_speaker_segments_segment
        FOREIGN KEY (segment_id) REFERENCES transcript_segments(id)
        ON DELETE CASCADE
);

CREATE INDEX idx_speaker_segments_transcript ON speaker_segments(transcript_id);
CREATE INDEX idx_speaker_segments_profile ON speaker_segments(speaker_profile_id);

-- ============================================================
-- EXPORT CONTEXT
-- ============================================================

-- Export jobs
CREATE TABLE IF NOT EXISTS export_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    transcript_id UUID NOT NULL,
    user_id UUID NOT NULL,

    -- Export specification
    format export_format_t NOT NULL,
    options JSONB NOT NULL DEFAULT '{}',
        -- {includeTimestamps: bool, includeSpeakers: bool, includeMetadata: bool}

    -- Processing
    status job_status_t NOT NULL DEFAULT 'pending',
    error_message TEXT,

    -- Result
    file_url TEXT,
    file_size_bytes BIGINT,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,

    CONSTRAINT fk_export_jobs_transcript
        FOREIGN KEY (transcript_id) REFERENCES transcripts(id)
        ON DELETE CASCADE,

    CONSTRAINT fk_export_jobs_user
        FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE CASCADE
);

CREATE INDEX idx_export_jobs_transcript ON export_jobs(transcript_id);
CREATE INDEX idx_export_jobs_user ON export_jobs(user_id);
CREATE INDEX idx_export_jobs_status ON export_jobs(status);
CREATE INDEX idx_export_jobs_created_at ON export_jobs(created_at DESC);

-- Export templates (for custom export formats)
CREATE TABLE IF NOT EXISTS export_templates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,

    -- Template definition
    name VARCHAR(100) NOT NULL,
    description TEXT,
    format export_format_t NOT NULL,

    -- Template configuration
    template_config JSONB NOT NULL,
        -- {header: string, segmentFormat: string, footer: string, variables: []}

    -- Sharing
    is_public BOOLEAN DEFAULT FALSE,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_export_templates_user
        FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE CASCADE,

    CONSTRAINT unique_user_template_name
        UNIQUE (user_id, name)
);

CREATE INDEX idx_export_templates_user ON export_templates(user_id);
CREATE INDEX idx_export_templates_public ON export_templates(is_public) WHERE is_public = TRUE;

-- ============================================================
-- GLOBAL SEARCH CONTEXT
-- ============================================================

-- Search queries (for analytics)
CREATE TABLE IF NOT EXISTS search_queries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,

    -- Query
    search_term TEXT NOT NULL,
    filters JSONB DEFAULT '{}',
        -- {language: string, dateRange: {start, end}, duration: {min, max}, speakers: []}

    -- Results
    result_count INTEGER NOT NULL DEFAULT 0,
    execution_time_ms INTEGER,

    -- Timestamp
    executed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_search_queries_user
        FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE CASCADE
);

CREATE INDEX idx_search_queries_user ON search_queries(user_id);
CREATE INDEX idx_search_queries_term ON search_queries USING gin(to_tsvector('english', search_term));

-- ============================================================
-- VERSION HISTORY CONTEXT
-- ============================================================

-- Transcript versions
CREATE TABLE IF NOT EXISTS transcript_versions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    transcript_id UUID NOT NULL,
    version_number INTEGER NOT NULL,

    -- Content snapshot (full or diff)
    content_snapshot JSONB NOT NULL,
        -- Stores full state or diff based on retention policy
    content_hash VARCHAR(64) NOT NULL,  -- SHA-256

    -- Metadata
    change_summary TEXT,
    created_by UUID NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_versions_transcript
        FOREIGN KEY (transcript_id) REFERENCES transcripts(id)
        ON DELETE CASCADE,

    CONSTRAINT fk_versions_user
        FOREIGN KEY (created_by) REFERENCES users(id),

    CONSTRAINT unique_transcript_version
        UNIQUE (transcript_id, version_number)
);

CREATE INDEX idx_versions_transcript ON transcript_versions(transcript_id);
CREATE INDEX idx_versions_created_at ON transcript_versions(created_at DESC);

-- ============================================================
-- BATCH PROCESSING CONTEXT
-- ============================================================

-- Batch jobs
CREATE TABLE IF NOT EXISTS batch_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,

    -- Batch metadata
    item_count INTEGER NOT NULL,
    total_file_size_bytes BIGINT NOT NULL,

    -- Processing
    status job_status_t NOT NULL DEFAULT 'pending',

    -- Statistics
    successful_count INTEGER DEFAULT 0,
    failed_count INTEGER DEFAULT 0,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,

    CONSTRAINT fk_batch_jobs_user
        FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE CASCADE
);

CREATE INDEX idx_batch_jobs_user ON batch_jobs(user_id);
CREATE INDEX idx_batch_jobs_status ON batch_jobs(status);
CREATE INDEX idx_batch_jobs_created_at ON batch_jobs(created_at DESC);

-- Batch items
CREATE TABLE IF NOT EXISTS batch_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    batch_job_id UUID NOT NULL,
    audio_file_id UUID NOT NULL,

    -- Processing type
    processing_type VARCHAR(50) NOT NULL,  -- 'detection', 'transcription', 'diarization'

    -- Status
    status job_status_t NOT NULL DEFAULT 'pending',
    error_message TEXT,

    -- Result
    result_transcript_id UUID,

    -- Ordering
    sequence_number INTEGER NOT NULL,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,

    CONSTRAINT fk_batch_items_job
        FOREIGN KEY (batch_job_id) REFERENCES batch_jobs(id)
        ON DELETE CASCADE,

    CONSTRAINT fk_batch_items_result
        FOREIGN KEY (result_transcript_id) REFERENCES transcripts(id)
        ON DELETE SET NULL
);

CREATE INDEX idx_batch_items_job ON batch_items(batch_job_id);
CREATE INDEX idx_batch_items_status ON batch_items(status);

-- ============================================================
-- API ACCESS CONTEXT
-- ============================================================

-- API clients (applications)
CREATE TABLE IF NOT EXISTS api_clients (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,

    -- Client information
    name VARCHAR(100) NOT NULL,
    description TEXT,
    website_url TEXT,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_api_clients_user
        FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE CASCADE
);

CREATE INDEX idx_api_clients_user ON api_clients(user_id);

-- API keys
CREATE TABLE IF NOT EXISTS api_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    client_id UUID NOT NULL,

    -- Key (hashed)
    key_hash VARCHAR(64) NOT NULL UNIQUE,  -- SHA-256 hash
    key_prefix VARCHAR(8) NOT NULL,  -- First 8 chars for identification

    -- Permissions
    permissions JSONB NOT NULL DEFAULT '["read"]',
        -- Array of api_permission_t

    -- Rate limiting
    rate_limit_per_minute INTEGER DEFAULT 100,

    -- Status
    is_active BOOLEAN DEFAULT TRUE,

    -- Expiration (optional)
    expires_at TIMESTAMPTZ,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_used_at TIMESTAMPTZ,

    CONSTRAINT fk_api_keys_client
        FOREIGN KEY (client_id) REFERENCES api_clients(id)
        ON DELETE CASCADE
);

CREATE INDEX idx_api_keys_client ON api_keys(client_id);
CREATE INDEX idx_api_keys_prefix ON api_keys(key_prefix);
CREATE INDEX idx_api_keys_active ON api_keys(is_active) WHERE is_active = TRUE;

-- API requests (for rate limiting and analytics)
CREATE TABLE IF NOT EXISTS api_requests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    api_key_id UUID NOT NULL,

    -- Request
    endpoint VARCHAR(255) NOT NULL,
    method VARCHAR(10) NOT NULL,
    path_parameters JSONB DEFAULT '{}',
    query_parameters JSONB DEFAULT '{}',

    -- Response
    status_code INTEGER NOT NULL,
    response_time_ms INTEGER,

    -- Timestamp
    requested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_api_requests_key
        FOREIGN KEY (api_key_id) REFERENCES api_keys(id)
        ON DELETE CASCADE
);

CREATE INDEX idx_api_requests_key ON api_requests(api_key_id);
CREATE INDEX idx_api_requests_requested_at ON api_requests(requested_at DESC);

-- Partition by month for performance
-- CREATE TABLE api_requests_2024_01 PARTITION OF api_requests
-- FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');

-- ============================================================
-- INDEXES FOR PERFORMANCE
-- ============================================================

-- Full-text search on transcript content
-- Note: This is a placeholder. Actual implementation may use Qdrant.
CREATE INDEX idx_transcripts_content_search ON transcripts
USING gin(to_tsvector('simple', COALESCE(
    (SELECT string_agg(text, ' ') FROM transcript_segments WHERE transcript_id = transcripts.id),
    ''
)));

-- Composite index for common queries
CREATE INDEX idx_transcripts_user_language ON transcripts(user_id, language_code);
CREATE INDEX idx_transcripts_user_created ON transcripts(user_id, created_at DESC);

-- ============================================================
-- TRIGGERS
-- ============================================================

-- Update transcript updated_at timestamp
CREATE OR REPLACE FUNCTION update_transcript_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_transcript_updated_at
    BEFORE UPDATE ON transcripts
    FOR EACH ROW
    EXECUTE FUNCTION update_transcript_updated_at();

-- Update speaker profile last_seen_at
CREATE OR REPLACE FUNCTION update_speaker_profile_last_seen()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE speaker_profiles
    SET last_seen_at = NOW(),
        appearance_count = appearance_count + 1
    WHERE id = NEW.speaker_profile_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_speaker_profile_last_seen
    AFTER INSERT ON speaker_segments
    FOR EACH ROW
    WHEN (NEW.speaker_profile_id IS NOT NULL)
    EXECUTE FUNCTION update_speaker_profile_last_seen();

-- ============================================================
-- VIEWS
-- ============================================================

-- Transcript summary view (for dashboard)
CREATE OR REPLACE VIEW transcript_summary AS
SELECT
    t.id,
    t.user_id,
    t.language_code,
    t.duration_seconds,
    t.word_count,
    t.status,
    t.is_edited,
    t.created_at,
    COUNT(DISTINCT ts.speaker_id) as speaker_count,
    COUNT(ts.id) as segment_count
FROM transcripts t
LEFT JOIN transcript_segments ts ON ts.transcript_id = t.id
GROUP BY t.id;

-- Batch job summary view
CREATE OR REPLACE VIEW batch_job_summary AS
SELECT
    bj.id,
    bj.user_id,
    bj.item_count,
    bj.successful_count,
    bj.failed_count,
    bj.status,
    bj.created_at,
    bj.completed_at,
    CASE
        WHEN bj.completed_at IS NOT NULL THEN
            EXTRACT(EPOCH FROM (bj.completed_at - bj.created_at))
        ELSE NULL
    END as total_duration_seconds
FROM batch_jobs bj;

-- ============================================================
-- FUNCTIONS
-- ============================================================

-- Get transcript with full content
CREATE OR REPLACE FUNCTION get_transcript_full(p_transcript_id UUID)
RETURNS TABLE (
    id UUID,
    audio_file_id UUID,
    language_code VARCHAR(2),
    duration_seconds INTEGER,
    segments JSONB
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        t.id,
        t.audio_file_id,
        t.language_code,
        t.duration_seconds,
        jsonb_agg(
            jsonb_build_object(
                'id', ts.id,
                'startTime', ts.start_time,
                'endTime', ts.end_time,
                'text', ts.text,
                'speakerId', ts.speaker_id,
                'isEdited', ts.is_edited
            ) ORDER BY ts.sequence_number
        ) as segments
    FROM transcripts t
    LEFT JOIN transcript_segments ts ON ts.transcript_id = t.id
    WHERE t.id = p_transcript_id
    GROUP BY t.id;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- ROW LEVEL SECURITY (Optional)
-- ============================================================

-- Enable RLS on sensitive tables
ALTER TABLE transcripts ENABLE ROW LEVEL SECURITY;
ALTER TABLE transcript_segments ENABLE ROW LEVEL SECURITY;
ALTER TABLE export_jobs ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only access their own transcripts
CREATE POLICY transcripts_user_policy ON transcripts
    FOR ALL
    USING (user_id = current_setting('app.user_id')::UUID);

CREATE POLICY segments_user_policy ON transcript_segments
    FOR ALL
    USING (
        transcript_id IN (
            SELECT id FROM transcripts WHERE user_id = current_setting('app.user_id')::UUID
        )
    );

-- ============================================================
-- COMMENTS
-- ============================================================

COMMENT ON TABLE transcripts IS 'Core transcript entity with language detection and edit tracking';
COMMENT ON TABLE transcript_segments IS 'Time-aligned text units within transcripts';
COMMENT ON TABLE language_detections IS 'Language auto-detection results from audio analysis';
COMMENT ON TABLE speaker_profiles IS 'Learned speaker characteristics for identification';
COMMENT ON TABLE speaker_segments IS 'Speaker assignments for transcript segments';
COMMENT ON TABLE export_jobs IS 'Export job tracking for various output formats';
COMMENT ON TABLE transcript_versions IS 'Version history snapshots of transcript edits';
COMMENT ON TABLE batch_jobs IS 'Batch processing job tracking for multiple uploads';
COMMENT ON TABLE api_keys IS 'API authentication keys with rate limiting';

-- ============================================================
-- SEED DATA (Optional for development)
-- ============================================================

-- No seed data for this schema - all data is user-generated
