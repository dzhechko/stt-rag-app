from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID


class TranscriptCreate(BaseModel):
    original_filename: str
    language: Optional[str] = None  # ISO-639-1 code, None for auto-detect


class TranscriptResponse(BaseModel):
    id: UUID
    original_filename: str
    file_path: str
    file_size: int
    duration_seconds: Optional[float] = None
    language: Optional[str] = None
    status: str
    transcription_text: Optional[str] = None
    transcription_json: Optional[Dict[str, Any]] = None
    transcription_srt: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    extra_metadata: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    category: Optional[str] = None
    
    class Config:
        from_attributes = True


class TranscriptListResponse(BaseModel):
    transcripts: List[TranscriptResponse]
    total: int


class ProcessingJobResponse(BaseModel):
    id: UUID
    transcript_id: UUID
    job_type: str
    status: str
    progress: float
    error_message: Optional[str] = None
    retry_count: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class SummaryCreate(BaseModel):
    transcript_id: UUID
    template: Optional[str] = None  # meeting, interview, lecture, podcast
    custom_prompt: Optional[str] = None
    fields_config: Optional[Dict[str, bool]] = None  # participants, decisions, deadlines, topics
    model: Optional[str] = None  # GigaChat/GigaChat-2-Max, Qwen/Qwen3-235B-A22B-Instruct-2507, etc.


class SummaryResponse(BaseModel):
    id: UUID
    transcript_id: UUID
    summary_text: str
    summary_template: Optional[str] = None
    summary_config: Optional[Dict[str, Any]] = None
    model_used: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class TranscriptUpdate(BaseModel):
    transcription_text: Optional[str] = None
    tags: Optional[List[str]] = None
    category: Optional[str] = None
    extra_metadata: Optional[Dict[str, Any]] = None


class RAGSessionCreate(BaseModel):
    session_name: Optional[str] = None
    transcript_ids: Optional[List[str]] = None


class RAGSessionResponse(BaseModel):
    id: UUID
    session_name: Optional[str] = None
    transcript_ids: Optional[List[str]] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class RAGQuestionRequest(BaseModel):
    question: str
    transcript_ids: Optional[List[str]] = None
    top_k: Optional[int] = 5  # Number of chunks to retrieve
    model: Optional[str] = None  # Model for answer generation
    temperature: Optional[float] = 0.3  # Temperature for generation
    use_reranking: Optional[bool] = True  # Enable reranking
    use_query_expansion: Optional[bool] = True  # Enable query expansion
    use_multi_hop: Optional[bool] = False  # Enable multi-hop reasoning
    use_hybrid_search: Optional[bool] = False  # Enable hybrid search (BM25 + Vector)
    use_advanced_grading: Optional[bool] = False  # Enable advanced quality grading
    reranker_model: Optional[str] = "ms-marco-MiniLM-L-6-v2"  # Reranker model name


class RAGMessageResponse(BaseModel):
    id: UUID
    session_id: UUID
    question: str
    answer: str
    quality_score: Optional[float] = None
    retrieved_documents: Optional[List[Dict[str, Any]]] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class QualityMetrics(BaseModel):
    groundedness: float  # 0.0-1.0
    completeness: float  # 0.0-1.0
    relevance: float  # 0.0-1.0
    overall_score: float  # 0.0-5.0


class RAGAnswerResponse(BaseModel):
    answer: str
    sources: List[Dict[str, Any]]
    quality_score: float
    retrieved_chunks: List[Dict[str, Any]]
    message_id: Optional[str] = None  # For feedback tracking
    quality_metrics: Optional[QualityMetrics] = None  # Advanced quality metrics


class RAGFeedbackRequest(BaseModel):
    feedback_type: str  # "positive" or "negative"
    comment: Optional[str] = None


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
