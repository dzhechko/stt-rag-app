import os
import logging
import time
import threading
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
from typing import List, Optional
from uuid import UUID

from app.config import settings
from app.database import get_db, init_db, Transcript, TranscriptStatus, ProcessingJob, JobType, JobStatus
from app.models import (
    TranscriptResponse,
    TranscriptListResponse,
    ProcessingJobResponse,
    ErrorResponse,
    SummaryCreate,
    SummaryResponse,
    TranscriptUpdate,
    RAGSessionCreate,
    RAGSessionResponse,
    RAGQuestionRequest,
    RAGAnswerResponse,
    RAGMessageResponse,
    RAGFeedbackRequest
)
from app.services.transcription_service import TranscriptionService
from app.services.file_service import FileService
from app.services.summarization_service import SummarizationService
from app.services.rag_service import RAGService
from app.services.rag_qa_service import RAGQAService

# Initialize services (singleton instances)
transcription_service = TranscriptionService()
file_service = FileService()
summarization_service = SummarizationService()
rag_service = RAGService()
rag_qa_service = RAGQAService()
from app.database import Summary, RAGSession, RAGMessage
from app.monitoring import (
    setup_monitoring,
    transcription_requests,
    transcription_duration,
    summarization_requests,
    rag_queries,
    rag_query_duration,
    active_transcriptions,
    active_summarizations
)


def create_translated_json(original_json: dict, translated_text: str) -> dict:
    """
    Создает переведенный JSON из оригинального JSON и переведенного текста.
    Сохраняет структуру сегментов и таймкоды, заменяя только текстовые поля.
    
    Args:
        original_json: Оригинальный JSON транскрипта с сегментами
        translated_text: Переведенный текст (цельный)
    
    Returns:
        Новый JSON с переведенными сегментами
    """
    if not original_json or not translated_text:
        return original_json
    
    # Создаем копию оригинального JSON
    translated_json = original_json.copy()
    
    # Обновляем корневое поле text
    translated_json["text"] = translated_text
    
    # Если есть сегменты, обновляем их
    if "segments" in original_json and isinstance(original_json["segments"], list):
        segments = original_json["segments"]
        if not segments:
            return translated_json
        
        # Собираем оригинальный текст из сегментов для расчета пропорций
        original_segments_text = []
        for seg in segments:
            if isinstance(seg, dict) and "text" in seg:
                original_segments_text.append(seg.get("text", ""))
        
        original_full_text = " ".join(original_segments_text)
        
        if not original_full_text:
            return translated_json
        
        # Разбиваем переведенный текст на сегменты пропорционально длине оригинальных
        translated_segments = []
        total_original_length = len(original_full_text)
        
        if total_original_length == 0:
            # Если оригинальный текст пуст, возвращаем оригинальный JSON
            return translated_json
        
        translated_text_pos = 0
        for i, seg in enumerate(segments):
            if not isinstance(seg, dict):
                translated_segments.append(seg)
                continue
            
            # Копируем сегмент
            new_seg = seg.copy()
            
            # Вычисляем длину оригинального текста сегмента
            original_seg_text = seg.get("text", "")
            original_seg_length = len(original_seg_text)
            
            if original_seg_length == 0:
                new_seg["text"] = ""
                translated_segments.append(new_seg)
                continue
            
            # Вычисляем пропорцию этого сегмента в общем тексте
            segment_ratio = original_seg_length / total_original_length
            
            # Вычисляем соответствующую длину в переведенном тексте
            translated_seg_length = int(len(translated_text) * segment_ratio)
            
            # Для последнего сегмента берем весь оставшийся текст
            if i == len(segments) - 1:
                new_seg["text"] = translated_text[translated_text_pos:].strip()
            else:
                if translated_seg_length == 0:
                    translated_seg_length = 1
                end_pos = min(translated_text_pos + translated_seg_length, len(translated_text))
                new_seg["text"] = translated_text[translated_text_pos:end_pos].strip()
                translated_text_pos = end_pos
            
            translated_segments.append(new_seg)
        
        translated_json["segments"] = translated_segments
    
    # Удаляем или очищаем words, так как они специфичны для оригинального языка
    if "words" in translated_json:
        translated_json["words"] = []
    
    return translated_json

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    force=True  # Force reconfiguration to ensure logs go to stdout
)
# Ensure logs are flushed immediately to stdout/stderr
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)
handler = logging.StreamHandler()
handler.setLevel(getattr(logging, settings.log_level))
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logging.root.addHandler(handler)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="STT App API",
    description="Speech-to-Text application with transcription, summarization, and RAG",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
transcription_service = TranscriptionService()
file_service = FileService()
summarization_service = SummarizationService()
rag_service = RAGService()
rag_qa_service = RAGQAService()


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    init_db()
    setup_monitoring(app)
    logger.info("Application started")


@app.get("/")
async def root():
    return {"message": "STT App API", "version": "1.0.0"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.post("/api/transcripts/upload", response_model=TranscriptResponse, status_code=201)
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    language: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Upload and transcribe audio file
    """
    try:
        # Validate file type
        allowed_extensions = {".mp3", ".mp4", ".mpeg", ".mpga", ".m4a", ".wav", ".webm"}
        file_extension = os.path.splitext(file.filename)[1].lower()
        
        if file_extension not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"File type {file_extension} not supported. Allowed: {', '.join(allowed_extensions)}"
            )
        
        # Read file content
        file_content = await file.read()
        file_size = len(file_content)
        
        # Note: Large files will be automatically split into chunks during transcription
        # No need to reject them here
        
        # Save uploaded file
        saved_file_path = file_service.save_uploaded_file(file_content, file.filename)
        
        # Create transcript record
        transcript = Transcript(
            original_filename=file.filename,
            file_path=saved_file_path,
            file_size=file_size,
            language=language,
            status=TranscriptStatus.PENDING
        )
        db.add(transcript)
        db.commit()
        db.refresh(transcript)
        
        # Create processing job
        job = ProcessingJob(
            transcript_id=transcript.id,
            job_type=JobType.TRANSCRIPTION,
            status=JobStatus.QUEUED
        )
        db.add(job)
        db.commit()
        
        # Start transcription in background
        background_tasks.add_task(
            process_transcription,
            transcript.id,
            saved_file_path,
            language
        )
        
        logger.info(f"File uploaded and queued for transcription: {transcript.id}")
        return TranscriptResponse.from_orm(transcript)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading file: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error uploading file: {str(e)}")


async def process_transcription(
    transcript_id: UUID,
    file_path: str,
    language: Optional[str]
):
    """Background task to process transcription"""
    from app.database import SessionLocal
    
    db = SessionLocal()
    try:
        transcript = db.query(Transcript).filter(Transcript.id == transcript_id).first()
        if not transcript:
            logger.error(f"Transcript not found: {transcript_id}")
            return
        
        # Update status
        transcript.status = TranscriptStatus.PROCESSING
        job = db.query(ProcessingJob).filter(
            ProcessingJob.transcript_id == transcript_id,
            ProcessingJob.job_type == JobType.TRANSCRIPTION
        ).first()
        if job:
            job.status = JobStatus.PROCESSING
            job.progress = 0.1
        db.commit()
        
        # Get file size for progress emulation
        file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
        file_size_mb = file_size / (1024 * 1024)
        max_file_size = settings.max_file_size_mb * 1024 * 1024
        
        # Callback function for updating progress
        progress_stop_event = threading.Event()
        
        def update_progress(progress: float):
            """Callback for updating progress in database"""
            try:
                # Get fresh job from database to avoid session issues
                fresh_job = db.query(ProcessingJob).filter(
                    ProcessingJob.transcript_id == transcript_id,
                    ProcessingJob.job_type == JobType.TRANSCRIPTION
                ).first()
                if fresh_job:
                    fresh_job.progress = min(max(progress, 0.0), 1.0)  # Clamp between 0 and 1
                    db.commit()
                    logger.debug(f"Progress updated to {progress:.2%} for transcript {transcript_id}")
            except Exception as e:
                logger.error(f"Error updating progress: {str(e)}", exc_info=True)
        
        # Emulate progress for regular files (not chunked)
        def emulate_progress():
            """Emulate progress based on file size and time"""
            if file_size <= max_file_size:
                # Estimate expected duration based on file size
                if file_size_mb < 5:
                    # Small files: ~15-20 seconds
                    time_to_50 = 5   # быстрее вывести движение
                    time_to_90 = 10
                elif file_size_mb < 15:
                    # Medium files: ~40-60 seconds
                    time_to_50 = 10
                    time_to_90 = 25
                else:
                    # Large files (but not chunked): ~90-120 seconds
                    time_to_50 = 20
                    time_to_90 = 50
                
                # Update to 0.5 after time_to_50
                if not progress_stop_event.wait(time_to_50):
                    update_progress(0.5)
                
                # Update to 0.9 after time_to_90
                if not progress_stop_event.wait(time_to_90 - time_to_50):
                    update_progress(0.9)
        
        # Start progress emulation thread for regular files
        progress_thread = None
        if file_size <= max_file_size:
            progress_thread = threading.Thread(target=emulate_progress, daemon=True)
            progress_thread.start()
        
        # Transcribe
        try:
            active_transcriptions.inc()
            start_time = time.time()
            
            # Normalize and validate language parameter
            # If language is explicitly set, force it (especially for Russian)
            normalized_language = None
            if language and language.strip():
                normalized_language = language.strip().lower()
                # Map common variations to ISO-639-1 codes
                lang_map = {
                    "ru": "ru",
                    "russian": "ru",
                    "русский": "ru",
                    "en": "en",
                    "english": "en",
                    "английский": "en"
                }
                normalized_language = lang_map.get(normalized_language, normalized_language)
                logger.info(f"Using normalized language: {normalized_language} (original: {language})")
            
            result = transcription_service.transcribe_file(
                file_path=file_path,
                language=normalized_language,
                response_format="json",  # Evolution Cloud.ru supports: json, text
                progress_callback=update_progress if file_size > max_file_size else None  # Only for chunked files
            )
            
            # Stop progress emulation when transcription completes
            if progress_thread:
                progress_stop_event.set()
                progress_thread.join(timeout=1.0)
            
            duration = time.time() - start_time
            transcription_duration.observe(duration)
            transcription_requests.labels(status="success").inc()
            
            # Update transcript with results
            detected_language = result.get("language", language)
            transcription_text = result["text"]
            original_english_text = None
            
            # Check if translation is needed: requested Russian but got English
            if normalized_language and normalized_language.lower() == "ru" and detected_language and detected_language.lower() == "en":
                logger.warning(
                    f"Language mismatch for transcript {transcript_id}: "
                    f"requested=ru, detected=en. Attempting automatic translation to Russian..."
                )
                try:
                    original_english_text = transcription_text
                    transcription_text = summarization_service.translate_text(
                        text=transcription_text,
                        source_language="en",
                        target_language="ru"
                    )
                    detected_language = "ru"
                    logger.info(f"Successfully translated transcript {transcript_id} from English to Russian")
                except Exception as e:
                    logger.error(
                        f"Failed to translate transcript {transcript_id}: {str(e)}. "
                        f"Using original English transcription.",
                        exc_info=True
                    )
                    # Keep original English text if translation fails
                    transcription_text = original_english_text or transcription_text
            
            transcript.transcription_text = transcription_text
            transcript.transcription_json = result.get("full_response", {})
            transcript.language = detected_language
            transcript.status = TranscriptStatus.COMPLETED
            
            # Store original English text in metadata if translation was performed
            if original_english_text:
                if not transcript.extra_metadata:
                    transcript.extra_metadata = {}
                transcript.extra_metadata["original_english_text"] = original_english_text
                transcript.extra_metadata["translated"] = True
            
            # Log language detection result
            if normalized_language and normalized_language.strip() and normalized_language.strip() != detected_language:
                if not (normalized_language.lower() == "ru" and detected_language.lower() == "en"):
                    logger.warning(
                        f"Language mismatch for transcript {transcript_id}: "
                        f"requested={normalized_language}, detected={detected_language}. "
                        f"Consider explicitly setting language='{detected_language}' for better results."
                    )
            elif not normalized_language or not normalized_language.strip():
                logger.info(
                    f"Auto-detected language for transcript {transcript_id}: {detected_language}. "
                    f"To force a specific language, set the language parameter during upload."
                )
            else:
                logger.info(f"Transcription completed with requested language: {detected_language}")
            
            # Save transcript files (use translated text if available)
            file_service.save_transcript(
                transcript_id=str(transcript_id),
                text=transcription_text,
                json_data=result.get("full_response"),
                srt=None  # Can be generated from verbose_json if needed
            )
            
            # Stop progress emulation
            if progress_thread:
                progress_stop_event.set()
            
            # Update job
            if job:
                job.status = JobStatus.COMPLETED
                job.progress = 1.0
                update_progress(1.0)  # Ensure final progress is set
            
            db.commit()
            logger.info(f"Transcription completed for {transcript_id}")
            
            # Note: RAG indexing is now done on-demand via /api/transcripts/{id}/reindex endpoint
            # This allows users to control when indexing happens and see progress
            
            # Cleanup original file if configured
            file_service.cleanup_original_file(file_path)
        
        except Exception as e:
            logger.error(f"Error in transcription: {str(e)}", exc_info=True)
            transcription_requests.labels(status="error").inc()
            transcript.status = TranscriptStatus.FAILED
            if job:
                job.status = JobStatus.FAILED
                job.error_message = str(e)
                job.retry_count += 1
            db.commit()
        finally:
            active_transcriptions.dec()
    
    finally:
        db.close()


@app.get("/api/transcripts", response_model=TranscriptListResponse)
async def list_transcripts(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    language: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List all transcripts with optional filtering"""
    query = db.query(Transcript)
    
    # Filter by status (ignore empty strings)
    if status and status.strip():
        try:
            status_enum = TranscriptStatus(status.strip())
            query = query.filter(Transcript.status == status_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
    
    # Filter by language (ignore empty strings)
    if language and language.strip():
        query = query.filter(Transcript.language == language.strip())
    
    total = query.count()
    transcripts = query.order_by(Transcript.created_at.desc()).offset(skip).limit(limit).all()
    
    return TranscriptListResponse(
        transcripts=[TranscriptResponse.from_orm(t) for t in transcripts],
        total=total
    )


@app.get("/api/transcripts/{transcript_id}", response_model=TranscriptResponse)
async def get_transcript(
    transcript_id: UUID,
    db: Session = Depends(get_db)
):
    """Get transcript by ID"""
    transcript = db.query(Transcript).filter(Transcript.id == transcript_id).first()
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript not found")
    return TranscriptResponse.from_orm(transcript)


@app.delete("/api/transcripts/{transcript_id}", status_code=204)
async def delete_transcript(
    transcript_id: UUID,
    db: Session = Depends(get_db)
):
    """Delete transcript and associated files"""
    transcript = db.query(Transcript).filter(Transcript.id == transcript_id).first()
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript not found")
    
    # Delete files
    file_service.delete_file(transcript.file_path)
    file_service.delete_transcript_files(str(transcript_id))
    
    # Delete from database
    db.delete(transcript)
    db.commit()
    
    logger.info(f"Deleted transcript: {transcript_id}")
    return None


@app.get("/api/jobs/{job_id}", response_model=ProcessingJobResponse)
async def get_job(
    job_id: UUID,
    db: Session = Depends(get_db)
):
    """Get processing job status"""
    job = db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return ProcessingJobResponse.from_orm(job)


@app.get("/api/transcripts/{transcript_id}/jobs", response_model=List[ProcessingJobResponse])
async def get_transcript_jobs(
    transcript_id: UUID,
    db: Session = Depends(get_db)
):
    """Get all jobs for a transcript"""
    jobs = db.query(ProcessingJob).filter(
        ProcessingJob.transcript_id == transcript_id
    ).order_by(ProcessingJob.created_at.desc()).all()
    return [ProcessingJobResponse.from_orm(job) for job in jobs]


@app.put("/api/transcripts/{transcript_id}", response_model=TranscriptResponse)
async def update_transcript(
    transcript_id: UUID,
    update_data: TranscriptUpdate,
    db: Session = Depends(get_db)
):
    """Update transcript (edit text, tags, category, metadata)"""
    transcript = db.query(Transcript).filter(Transcript.id == transcript_id).first()
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript not found")
    
    if update_data.transcription_text is not None:
        transcript.transcription_text = update_data.transcription_text
    if update_data.tags is not None:
        transcript.tags = update_data.tags
    if update_data.category is not None:
        transcript.category = update_data.category
    if update_data.extra_metadata is not None:
        transcript.extra_metadata = update_data.extra_metadata
    
    db.commit()
    db.refresh(transcript)
    
    logger.info(f"Updated transcript: {transcript_id}")
    return TranscriptResponse.from_orm(transcript)


@app.post("/api/summaries", response_model=SummaryResponse, status_code=201)
async def create_summary(
    summary_data: SummaryCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Create summary for a transcript"""
    transcript = db.query(Transcript).filter(Transcript.id == summary_data.transcript_id).first()
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript not found")
    
    if not transcript.transcription_text:
        raise HTTPException(status_code=400, detail="Transcript has no text to summarize")
    
    if transcript.status != TranscriptStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Transcript is not completed")
    
    # Create summary record
    summary = Summary(
        transcript_id=summary_data.transcript_id,
        summary_text="",  # Will be filled by background task
        summary_template=summary_data.template,
        summary_config=summary_data.fields_config or {},
        model_used=summary_data.model or summarization_service.default_model
    )
    db.add(summary)
    db.commit()
    db.refresh(summary)
    
    # Create processing job
    job = ProcessingJob(
        transcript_id=summary_data.transcript_id,
        job_type=JobType.SUMMARIZATION,
        status=JobStatus.QUEUED
    )
    db.add(job)
    db.commit()
    
    # Start summarization in background
    background_tasks.add_task(
        process_summarization,
        summary.id,
        summary_data.transcript_id,
        summary_data.template,
        summary_data.custom_prompt,
        summary_data.fields_config,
        summary_data.model
    )
    
    logger.info(f"Summary job queued for transcript: {summary_data.transcript_id}")
    return SummaryResponse.from_orm(summary)


async def process_summarization(
    summary_id: UUID,
    transcript_id: UUID,
    template: Optional[str],
    custom_prompt: Optional[str],
    fields_config: Optional[dict],
    model: Optional[str]
):
    """Background task to process summarization"""
    from app.database import SessionLocal
    
    db = SessionLocal()
    try:
        summary = db.query(Summary).filter(Summary.id == summary_id).first()
        transcript = db.query(Transcript).filter(Transcript.id == transcript_id).first()
        
        if not summary or not transcript:
            logger.error(f"Summary or transcript not found: {summary_id}, {transcript_id}")
            return
        
        # Update job status
        job = db.query(ProcessingJob).filter(
            ProcessingJob.transcript_id == transcript_id,
            ProcessingJob.job_type == JobType.SUMMARIZATION
        ).order_by(ProcessingJob.created_at.desc()).first()
        
        if job:
            job.status = JobStatus.PROCESSING
            job.progress = 0.1
        db.commit()
        
        # Summarize
        try:
            active_summarizations.inc()
            result = summarization_service.summarize(
                text=transcript.transcription_text,
                template=template,
                custom_prompt=custom_prompt,
                fields_config=fields_config,
                model=model
            )
            summarization_requests.labels(status="success").inc()
            
            # Update summary
            summary.summary_text = result["summary_text"]
            summary.summary_config = result.get("fields_config", {})
            
            if job:
                job.status = JobStatus.COMPLETED
                job.progress = 1.0
            
            db.commit()
            logger.info(f"Summarization completed for transcript: {transcript_id}")
        
        except Exception as e:
            logger.error(f"Error in summarization: {str(e)}", exc_info=True)
            summarization_requests.labels(status="error").inc()
            if job:
                job.status = JobStatus.FAILED
                job.error_message = str(e)
                job.retry_count += 1
            db.commit()
        finally:
            active_summarizations.dec()
    
    finally:
        db.close()


@app.get("/api/transcripts/{transcript_id}/summaries", response_model=List[SummaryResponse])
async def get_transcript_summaries(
    transcript_id: UUID,
    db: Session = Depends(get_db)
):
    """Get all summaries for a transcript"""
    summaries = db.query(Summary).filter(
        Summary.transcript_id == transcript_id
    ).order_by(Summary.created_at.desc()).all()
    return [SummaryResponse.from_orm(s) for s in summaries]


@app.get("/api/summaries/{summary_id}", response_model=SummaryResponse)
async def get_summary(
    summary_id: UUID,
    db: Session = Depends(get_db)
):
    """Get summary by ID"""
    summary = db.query(Summary).filter(Summary.id == summary_id).first()
    if not summary:
        raise HTTPException(status_code=404, detail="Summary not found")
    return SummaryResponse.from_orm(summary)


# RAG Endpoints

@app.post("/api/rag/sessions", response_model=RAGSessionResponse, status_code=201)
async def create_rag_session(
    session_data: RAGSessionCreate,
    db: Session = Depends(get_db)
):
    """Create a new RAG session"""
    session = RAGSession(
        session_name=session_data.session_name,
        transcript_ids=[str(tid) for tid in (session_data.transcript_ids or [])]
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return RAGSessionResponse.from_orm(session)


@app.get("/api/rag/sessions", response_model=List[RAGSessionResponse])
async def list_rag_sessions(
    db: Session = Depends(get_db)
):
    """List all RAG sessions"""
    sessions = db.query(RAGSession).order_by(RAGSession.created_at.desc()).all()
    return [RAGSessionResponse.from_orm(s) for s in sessions]


@app.get("/api/rag/sessions/{session_id}", response_model=RAGSessionResponse)
async def get_rag_session(
    session_id: UUID,
    db: Session = Depends(get_db)
):
    """Get RAG session by ID"""
    session = db.query(RAGSession).filter(RAGSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return RAGSessionResponse.from_orm(session)


@app.post("/api/rag/ask", response_model=RAGAnswerResponse)
async def ask_question(
    question_data: RAGQuestionRequest,
    db: Session = Depends(get_db)
):
    """Ask a question using RAG"""
    try:
        start_time = time.time()
        # Convert transcript_ids to strings if provided
        transcript_ids_str = None
        if question_data.transcript_ids:
            transcript_ids_str = [str(tid) for tid in question_data.transcript_ids]
            logger.info(f"Answering question with transcript filter: {transcript_ids_str}")
            
            # Check if transcripts are indexed, if not, try to index them
            for tid in question_data.transcript_ids:
                transcript = db.query(Transcript).filter(Transcript.id == tid).first()
                if transcript and transcript.status == TranscriptStatus.COMPLETED and transcript.transcription_text:
                    # Check if indexed by trying a small search
                    test_chunks = rag_service.search(
                        query="test",
                        transcript_ids=[str(tid)],
                        top_k=1
                    )
                    if not test_chunks:
                        logger.info(f"Transcript {tid} not indexed, attempting to index...")
                        try:
                            rag_service.index_transcript(
                                transcript_id=str(tid),
                                text=transcript.transcription_text,
                                metadata={"original_filename": transcript.original_filename, "language": transcript.language}
                            )
                            logger.info(f"Successfully indexed transcript {tid}")
                        except Exception as e:
                            logger.warning(f"Failed to auto-index transcript {tid}: {str(e)}")
        
        result = rag_qa_service.answer_question(
            question=question_data.question,
            transcript_ids=transcript_ids_str,
            model=question_data.model or None,
            top_k=question_data.top_k or 5,
            temperature=question_data.temperature or 0.3,
            use_reranking=question_data.use_reranking if question_data.use_reranking is not None else True,
            use_query_expansion=question_data.use_query_expansion if question_data.use_query_expansion is not None else True,
            use_multi_hop=question_data.use_multi_hop if question_data.use_multi_hop is not None else False,
            use_hybrid_search=question_data.use_hybrid_search if question_data.use_hybrid_search is not None else False,
            use_advanced_grading=question_data.use_advanced_grading if question_data.use_advanced_grading is not None else False,
            reranker_model=question_data.reranker_model or "ms-marco-MiniLM-L-6-v2"
        )
        duration = time.time() - start_time
        rag_query_duration.observe(duration)
        rag_queries.labels(status="success").inc()
        # For non-session queries, create a temporary message to enable feedback
        # This allows users to provide feedback even without a session
        # Find or create a temporary session for feedback
        temp_session = db.query(RAGSession).filter(RAGSession.session_name == "Temporary Feedback Session").first()
        if not temp_session:
            temp_session = RAGSession(session_name="Temporary Feedback Session")
            db.add(temp_session)
            db.flush()
        
        temp_message = RAGMessage(
            session_id=temp_session.id,
            question=question_data.question,
            answer=result["answer"],
            quality_score=result["quality_score"],
            retrieved_documents=result["sources"]
        )
        db.add(temp_message)
        db.commit()
        db.refresh(temp_message)
        result["message_id"] = str(temp_message.id)
        return RAGAnswerResponse(**result)
    except ConnectionError as e:
        logger.error(f"Connection error answering question: {str(e)}", exc_info=True)
        rag_queries.labels(status="error").inc()
        raise HTTPException(status_code=503, detail=f"Connection error: {str(e)}")
    except Exception as e:
        logger.error(f"Error answering question: {str(e)}", exc_info=True)
        rag_queries.labels(status="error").inc()
        raise HTTPException(status_code=500, detail=f"Error answering question: {str(e)}")


@app.post("/api/rag/sessions/{session_id}/ask", response_model=RAGAnswerResponse)
async def ask_question_in_session(
    session_id: UUID,
    question_data: RAGQuestionRequest,
    db: Session = Depends(get_db)
):
    """Ask a question in a RAG session and save the message"""
    session = db.query(RAGSession).filter(RAGSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Use session's transcript_ids if not provided
    transcript_ids = question_data.transcript_ids or session.transcript_ids
    
    # Convert to strings
    transcript_ids_str = None
    if transcript_ids:
        transcript_ids_str = [str(tid) for tid in transcript_ids]
        logger.info(f"Answering question in session with transcript filter: {transcript_ids_str}")
    
    # Fetch conversation history from the session (last 10 messages)
    previous_messages = db.query(RAGMessage).filter(
        RAGMessage.session_id == session_id
    ).order_by(RAGMessage.created_at.desc()).limit(10).all()
    
    # Convert to format expected by answer_question (reverse to chronological order)
    conversation_history = [
        {"question": msg.question, "answer": msg.answer}
        for msg in reversed(previous_messages)
    ]
    
    if conversation_history:
        logger.info(f"Including {len(conversation_history)} previous messages from session {session_id}")
    
    try:
        result = rag_qa_service.answer_question(
            question=question_data.question,
            transcript_ids=transcript_ids_str,
            conversation_history=conversation_history,
            model=question_data.model or None,
            top_k=question_data.top_k or 5,
            temperature=question_data.temperature or 0.3,
            use_reranking=question_data.use_reranking if question_data.use_reranking is not None else True,
            use_query_expansion=question_data.use_query_expansion if question_data.use_query_expansion is not None else True,
            use_multi_hop=question_data.use_multi_hop if question_data.use_multi_hop is not None else False,
            use_hybrid_search=question_data.use_hybrid_search if question_data.use_hybrid_search is not None else False,
            use_advanced_grading=question_data.use_advanced_grading if question_data.use_advanced_grading is not None else False,
            reranker_model=question_data.reranker_model or "ms-marco-MiniLM-L-6-v2"
        )
        
        # Save message
        message = RAGMessage(
            session_id=session_id,
            question=question_data.question,
            answer=result["answer"],
            quality_score=result["quality_score"],
            retrieved_documents=result["sources"]
        )
        db.add(message)
        db.commit()
        db.refresh(message)
        
        # Return answer response with message_id for feedback
        return RAGAnswerResponse(
            answer=result["answer"],
            sources=result["sources"],
            quality_score=result["quality_score"],
            retrieved_chunks=result["retrieved_chunks"],
            message_id=str(message.id)
        )
    
    except ConnectionError as e:
        logger.error(f"Connection error answering question in session: {str(e)}", exc_info=True)
        raise HTTPException(status_code=503, detail=f"Connection error: {str(e)}")
    except Exception as e:
        logger.error(f"Error answering question in session: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error answering question: {str(e)}")


@app.get("/api/rag/sessions/{session_id}/messages", response_model=List[RAGMessageResponse])
async def get_session_messages(
    session_id: UUID,
    db: Session = Depends(get_db)
):
    """Get all messages in a RAG session"""
    messages = db.query(RAGMessage).filter(
        RAGMessage.session_id == session_id
    ).order_by(RAGMessage.created_at.asc()).all()
    return [RAGMessageResponse.from_orm(m) for m in messages]


@app.delete("/api/rag/sessions/{session_id}", status_code=204)
async def delete_rag_session(
    session_id: UUID,
    db: Session = Depends(get_db)
):
    """Delete a RAG session and all its messages"""
    session = db.query(RAGSession).filter(RAGSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Cascade delete will handle messages automatically due to relationship
    db.delete(session)
    db.commit()
    return None


@app.post("/api/transcripts/{transcript_id}/reindex")
async def reindex_transcript(
    transcript_id: UUID,
    db: Session = Depends(get_db)
):
    """Reindex a transcript in the RAG system"""
    transcript = db.query(Transcript).filter(Transcript.id == transcript_id).first()
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript not found")
    
    if not transcript.transcription_text:
        raise HTTPException(status_code=400, detail="Transcript has no text to index")
    
    if transcript.status != TranscriptStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Transcript is not completed")
    
    # Create processing job for indexing
    job = ProcessingJob(
        transcript_id=transcript_id,
        job_type=JobType.INDEXING,
        status=JobStatus.PROCESSING,
        progress=0.0
    )
    db.add(job)
    print(f"[REINDEX] Creating indexing job for transcript {transcript_id}, job_type={JobType.INDEXING}, job_type.value={JobType.INDEXING.value}", flush=True)
    try:
        db.commit()
        db.refresh(job)
        print(f"[REINDEX] Indexing job created successfully: {job.id}", flush=True)
    except Exception as e:
        print(f"[REINDEX] Error creating indexing job: {str(e)}", flush=True)
        db.rollback()
        raise
    
    try:
        # Callback function for updating indexing progress
        def update_indexing_progress(progress: float):
            """Callback for updating indexing progress in database"""
            try:
                # Get fresh job from database to avoid session issues
                fresh_job = db.query(ProcessingJob).filter(
                    ProcessingJob.transcript_id == transcript_id,
                    ProcessingJob.job_type == JobType.INDEXING
                ).order_by(ProcessingJob.created_at.desc()).first()
                if fresh_job:
                    fresh_job.progress = min(max(progress, 0.0), 1.0)  # Clamp between 0 and 1
                    db.commit()
                    logger.debug(f"Indexing progress updated to {progress:.2%} for transcript {transcript_id}")
            except Exception as e:
                logger.error(f"Error updating indexing progress: {str(e)}", exc_info=True)
        
        num_chunks = rag_service.index_transcript(
            transcript_id=str(transcript_id),
            text=transcript.transcription_text,
            metadata={"original_filename": transcript.original_filename, "language": transcript.language},
            progress_callback=update_indexing_progress
        )
        # Update job to completed
        job.status = JobStatus.COMPLETED
        job.progress = 1.0
        update_indexing_progress(1.0)
        db.commit()
        
        if num_chunks == 0:
            # Check if it's because embeddings are not available
            return {
                "message": "Cannot index transcript: Embeddings API is not available. Evolution Cloud.ru does not support embeddings endpoint. RAG features are disabled.",
                "chunks_indexed": 0,
                "error": "embeddings_not_available",
                "reason": "Evolution Cloud.ru does not support embeddings API endpoint (/v1/embeddings)"
            }
        return {
            "message": f"Successfully reindexed transcript {transcript_id}",
            "chunks_indexed": num_chunks
        }
    except ValueError as e:
        if "not available" in str(e) or "Embeddings API" in str(e):
            logger.warning(f"Embeddings not available for transcript {transcript_id}: {str(e)}")
            if job:
                job.status = JobStatus.FAILED
                job.error_message = str(e)
                db.commit()
            return {
                "message": "Cannot index transcript: Embeddings API is not available. Evolution Cloud.ru does not support embeddings endpoint.",
                "chunks_indexed": 0,
                "error": "embeddings_not_available",
                "reason": "Evolution Cloud.ru does not support embeddings API endpoint"
            }
        raise
    except Exception as e:
        logger.error(f"Error reindexing transcript {transcript_id}: {str(e)}", exc_info=True)
        if job:
            job.status = JobStatus.FAILED
            job.error_message = str(e)
            db.commit()
        raise HTTPException(status_code=500, detail=f"Error reindexing transcript: {str(e)}")


@app.post("/api/transcripts/{transcript_id}/translate")
async def translate_transcript(
    transcript_id: UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    target_language: str = "ru",
    model: Optional[str] = None
):
    """Manually translate a transcript to target language (async)"""
    transcript = db.query(Transcript).filter(Transcript.id == transcript_id).first()
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript not found")
    
    if not transcript.transcription_text:
        raise HTTPException(status_code=400, detail="Transcript has no text to translate")
    
    if transcript.status != TranscriptStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Transcript is not completed")
    
    # Check if already translated
    if transcript.extra_metadata and transcript.extra_metadata.get("translated") and target_language == "ru":
        return {
            "message": "Transcript is already translated to Russian",
            "transcript_id": str(transcript_id),
            "already_translated": True
        }
    
    # Determine source language
    source_language = "en"
    if transcript.language and transcript.language.lower() == "ru":
        source_language = "ru"
        # If translating Russian to Russian, return current text
        if target_language == "ru":
            return {
                "message": "Transcript is already in Russian",
                "transcript_id": str(transcript_id),
                "already_translated": True
            }
    
    # Create processing job for translation
    job = ProcessingJob(
        transcript_id=transcript_id,
        job_type=JobType.TRANSLATION,
        status=JobStatus.QUEUED,
        progress=0.0
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    
    # Start translation in background
    background_tasks.add_task(
        process_translation,
        transcript_id,
        target_language,
        source_language,
        job.id,
        model
    )
    
    logger.info(f"Translation job queued for transcript {transcript_id} from {source_language} to {target_language}")
    
    return {
        "message": f"Translation started. Progress will be available in processing jobs.",
        "transcript_id": str(transcript_id),
        "job_id": str(job.id),
        "status": "queued"
    }


async def process_translation(
    transcript_id: UUID,
    target_language: str,
    source_language: str,
    job_id: UUID,
    model: Optional[str] = None
):
    """Background task to process translation"""
    from app.database import SessionLocal
    
    db = SessionLocal()
    try:
        transcript = db.query(Transcript).filter(Transcript.id == transcript_id).first()
        if not transcript:
            logger.error(f"Transcript not found: {transcript_id}")
            return
        
        job = db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
        if not job:
            logger.error(f"Translation job not found: {job_id}")
            return
        
        # Update job status to processing
        job.status = JobStatus.PROCESSING
        job.progress = 0.0
        db.commit()
        
        # Track translation start time
        translation_start_time = time.time()
        
        # Callback function for updating translation progress
        def update_translation_progress(progress: float):
            """Callback for updating translation progress in database"""
            try:
                # Get fresh job from database to avoid session issues
                fresh_job = db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
                if fresh_job:
                    fresh_job.progress = min(max(progress, 0.0), 1.0)  # Clamp between 0 and 1
                    db.commit()
                    logger.debug(f"Translation progress updated to {progress:.2%} for transcript {transcript_id}")
            except Exception as e:
                logger.error(f"Error updating translation progress: {str(e)}", exc_info=True)
        
        # Get original text (if already translated, use original from metadata)
        text_to_translate = transcript.transcription_text
        if transcript.extra_metadata and transcript.extra_metadata.get("original_english_text"):
            # If we're translating back to English, use original
            if target_language == "en":
                text_to_translate = transcript.extra_metadata.get("original_english_text")
        
        # Update progress to indicate translation started
        update_translation_progress(0.1)
        
        # Translate using SummarizationService (use global instance) with progress callback
        translated_text = summarization_service.translate_text(
            text=text_to_translate,
            source_language=source_language,
            target_language=target_language,
            model=model,
            progress_callback=update_translation_progress
        )
        
        # Save original text and translated JSON if translating from English to Russian
        if target_language == "ru" and source_language == "en":
            if not transcript.extra_metadata:
                transcript.extra_metadata = {}
            transcript.extra_metadata["original_english_text"] = text_to_translate
            transcript.extra_metadata["translated"] = True
            transcript.extra_metadata["translation_duration_seconds"] = int(time.time() - translation_start_time)
            
            # Create translated JSON if original JSON exists
            if transcript.transcription_json:
                try:
                    translated_json = create_translated_json(
                        original_json=transcript.transcription_json,
                        translated_text=translated_text
                    )
                    transcript.extra_metadata["translated_transcription_json"] = translated_json
                    # Mark JSON field as modified so SQLAlchemy persists nested changes
                    flag_modified(transcript, "extra_metadata")
                    logger.info(f"Created translated JSON for transcript {transcript_id}")
                except Exception as e:
                    logger.warning(f"Failed to create translated JSON for transcript {transcript_id}: {str(e)}")
                    # Continue without translated JSON - frontend will fallback to original
        
        # Update transcript
        transcript.transcription_text = translated_text
        transcript.language = target_language
        db.commit()
        db.refresh(transcript)
        
        # Update job to completed
        job.status = JobStatus.COMPLETED
        job.progress = 1.0
        update_translation_progress(1.0)
        db.commit()
        
        logger.info(f"Successfully translated transcript {transcript_id} from {source_language} to {target_language}")
    
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error translating transcript {transcript_id}: {error_msg}", exc_info=True)
        
        # Update job to failed
        try:
            job = db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
            if job:
                job.status = JobStatus.FAILED
                job.error_message = error_msg
                db.commit()
        except Exception as job_error:
            logger.error(f"Error updating job status to failed: {str(job_error)}", exc_info=True)
    
    finally:
        db.close()


@app.get("/api/rag/status")
async def get_rag_status():
    """Get RAG system status and diagnostics"""
    status = {
        "qdrant_available": rag_service.qdrant_client is not None,
        "collection_name": rag_service.collection_name,
        "embeddings_available": False
    }
    
    if rag_service.qdrant_client is None:
        status["error"] = "Qdrant client is not available. Check if Qdrant container is running."
        return status
    
    try:
        # Check Qdrant connection
        collections = rag_service.qdrant_client.get_collections().collections
        collection_names = [c.name for c in collections]
        status["collections"] = collection_names
        status["target_collection_exists"] = rag_service.collection_name in collection_names
        
        # Check embeddings
        try:
            test_embedding = rag_service.embeddings.embed_query("test")
            status["embeddings_available"] = True
            status["embedding_dimension"] = len(test_embedding)
        except Exception as e:
            status["embeddings_error"] = str(e)
        
        # Get collection info if exists
        if status["target_collection_exists"]:
            try:
                collection_info = rag_service.qdrant_client.get_collection(rag_service.collection_name)
                status["collection_points_count"] = collection_info.points_count
            except Exception as e:
                status["collection_info_error"] = str(e)
        
    except Exception as e:
        status["error"] = f"Error checking RAG status: {str(e)}"
        logger.error(f"Error in RAG status check: {str(e)}", exc_info=True)
    
    return status


@app.get("/api/transcripts/{transcript_id}/index-status")
async def get_transcript_index_status(
    transcript_id: UUID,
    db: Session = Depends(get_db)
):
    """Check if a transcript is indexed in RAG system"""
    transcript = db.query(Transcript).filter(Transcript.id == transcript_id).first()
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript not found")
    
    if not transcript.transcription_text:
        return {
            "indexed": False,
            "reason": "Transcript has no text"
        }
    
    if transcript.status != TranscriptStatus.COMPLETED:
        return {
            "indexed": False,
            "reason": f"Transcript status is {transcript.status}, not completed"
        }
    
    # Check if indexed by trying a small search
    try:
        test_chunks = rag_service.search(
            query="test",
            transcript_ids=[str(transcript_id)],
            top_k=1
        )
        return {
            "indexed": len(test_chunks) > 0,
            "transcript_id": str(transcript_id),
            "has_text": bool(transcript.transcription_text),
            "text_length": len(transcript.transcription_text) if transcript.transcription_text else 0
        }
    except Exception as e:
        logger.error(f"Error checking index status: {str(e)}", exc_info=True)
        return {
            "indexed": False,
            "error": str(e),
            "transcript_id": str(transcript_id)
        }


@app.post("/api/rag/messages/{message_id}/feedback")
async def submit_rag_feedback(
    message_id: UUID,
    feedback_data: RAGFeedbackRequest,
    db: Session = Depends(get_db)
):
    """Submit feedback for a RAG answer"""
    message = db.query(RAGMessage).filter(RAGMessage.id == message_id).first()
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    if feedback_data.feedback_type not in ["positive", "negative"]:
        raise HTTPException(status_code=400, detail="feedback_type must be 'positive' or 'negative'")
    
    message.feedback_type = feedback_data.feedback_type
    message.feedback_comment = feedback_data.comment
    
    db.commit()
    logger.info(f"Feedback submitted for message {message_id}: {feedback_data.feedback_type}")
    
    return {
        "message": "Feedback submitted successfully",
        "message_id": str(message_id),
        "feedback_type": feedback_data.feedback_type
    }

