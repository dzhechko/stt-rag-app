import os
import shutil
import uuid
import logging
from pathlib import Path
from typing import Optional
from app.config import settings

logger = logging.getLogger(__name__)


class FileService:
    def __init__(self):
        self.upload_dir = Path(settings.upload_dir)
        self.transcripts_dir = Path(settings.transcripts_dir)
        self.keep_original = settings.keep_original_files
        
        # Create directories if they don't exist
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.transcripts_dir.mkdir(parents=True, exist_ok=True)
    
    def save_uploaded_file(self, file_content: bytes, original_filename: str) -> str:
        """
        Save uploaded file to storage
        
        Args:
            file_content: File content as bytes
            original_filename: Original filename
        
        Returns:
            Path to saved file
        """
        # Generate unique filename
        file_id = str(uuid.uuid4())
        file_extension = Path(original_filename).suffix
        saved_filename = f"{file_id}{file_extension}"
        file_path = self.upload_dir / saved_filename
        
        # Save file
        with open(file_path, "wb") as f:
            f.write(file_content)
        
        logger.info(f"Saved uploaded file: {file_path}")
        return str(file_path)
    
    def save_transcript(
        self,
        transcript_id: str,
        text: str,
        json_data: Optional[dict] = None,
        srt: Optional[str] = None
    ) -> dict:
        """
        Save transcript files in different formats
        
        Args:
            transcript_id: UUID of transcript
            text: Plain text transcription
            json_data: JSON transcription data
            srt: SRT subtitle content
        
        Returns:
            Dictionary with paths to saved files
        """
        transcript_dir = self.transcripts_dir / transcript_id
        transcript_dir.mkdir(parents=True, exist_ok=True)
        
        saved_files = {}
        
        # Save text file
        text_path = transcript_dir / "transcript.txt"
        with open(text_path, "w", encoding="utf-8") as f:
            f.write(text)
        saved_files["text"] = str(text_path)
        
        # Save JSON file if provided
        if json_data:
            import json
            json_path = transcript_dir / "transcript.json"
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(json_data, f, ensure_ascii=False, indent=2)
            saved_files["json"] = str(json_path)
        
        # Save SRT file if provided
        if srt:
            srt_path = transcript_dir / "transcript.srt"
            with open(srt_path, "w", encoding="utf-8") as f:
                f.write(srt)
            saved_files["srt"] = str(srt_path)
        
        logger.info(f"Saved transcript files for {transcript_id}")
        return saved_files
    
    def delete_file(self, file_path: str) -> bool:
        """Delete file from storage"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Deleted file: {file_path}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting file {file_path}: {str(e)}")
            return False
    
    def delete_transcript_files(self, transcript_id: str) -> bool:
        """Delete all files related to a transcript"""
        try:
            transcript_dir = self.transcripts_dir / transcript_id
            if transcript_dir.exists():
                shutil.rmtree(transcript_dir)
                logger.info(f"Deleted transcript directory: {transcript_dir}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting transcript files for {transcript_id}: {str(e)}")
            return False
    
    def cleanup_original_file(self, file_path: str) -> bool:
        """Delete original audio file if keep_original_files is False"""
        if not self.keep_original:
            return self.delete_file(file_path)
        return False

