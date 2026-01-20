from sqlalchemy import create_engine, Column, String, Text, Float, Integer, DateTime, Enum as SQLEnum, ForeignKey, ARRAY, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime
import enum

from app.config import settings

engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class TranscriptStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class JobType(str, enum.Enum):
    TRANSCRIPTION = "transcription"
    SUMMARIZATION = "summarization"


class JobStatus(str, enum.Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Transcript(Base):
    __tablename__ = "transcripts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    original_filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_size = Column(Integer, nullable=False)  # in bytes
    duration_seconds = Column(Float, nullable=True)
    language = Column(String, nullable=True)  # ISO-639-1 code
    status = Column(SQLEnum(TranscriptStatus), nullable=False, default=TranscriptStatus.PENDING)
    transcription_text = Column(Text, nullable=True)
    transcription_json = Column(JSON, nullable=True)  # verbose_json
    transcription_srt = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    extra_metadata = Column(JSON, nullable=True, default=dict)
    tags = Column(ARRAY(String), nullable=True, default=list)
    category = Column(String, nullable=True)
    
    # Relationships
    summaries = relationship("Summary", back_populates="transcript", cascade="all, delete-orphan")
    processing_jobs = relationship("ProcessingJob", back_populates="transcript", cascade="all, delete-orphan")


class Summary(Base):
    __tablename__ = "summaries"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    transcript_id = Column(UUID(as_uuid=True), ForeignKey("transcripts.id"), nullable=False)
    summary_text = Column(Text, nullable=False)
    summary_template = Column(String, nullable=True)
    summary_config = Column(JSON, nullable=True, default=dict)
    model_used = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    transcript = relationship("Transcript", back_populates="summaries")


class ProcessingJob(Base):
    __tablename__ = "processing_jobs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    transcript_id = Column(UUID(as_uuid=True), ForeignKey("transcripts.id"), nullable=False)
    job_type = Column(SQLEnum(JobType), nullable=False)
    status = Column(SQLEnum(JobStatus), nullable=False, default=JobStatus.QUEUED)
    progress = Column(Float, default=0.0, nullable=False)  # 0.0 to 1.0
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    transcript = relationship("Transcript", back_populates="processing_jobs")


class RAGSession(Base):
    __tablename__ = "rag_sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_name = Column(String, nullable=True)
    transcript_ids = Column(ARRAY(String), nullable=True, default=list)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    messages = relationship("RAGMessage", back_populates="session", cascade="all, delete-orphan")


class RAGMessage(Base):
    __tablename__ = "rag_messages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("rag_sessions.id"), nullable=True)  # Allow NULL for temporary messages
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    quality_score = Column(Float, nullable=True)
    retrieved_documents = Column(JSON, nullable=True, default=list)
    feedback_type = Column(String, nullable=True)  # "positive" or "negative"
    feedback_comment = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    session = relationship("RAGSession", back_populates="messages")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    Base.metadata.create_all(bind=engine)

