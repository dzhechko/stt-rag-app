import os
import time
import logging
import tempfile
import shutil
import subprocess
import httpx
from typing import Optional, Dict, Any, List, Callable, Tuple
from openai import OpenAI
from app.config import settings

logger = logging.getLogger(__name__)


# Supported audio formats by SberCloud API (no conversion needed)
SUPPORTED_AUDIO_FORMATS = {'.mp3', '.wav', '.m4a', '.mpeg', '.mpga'}

# Video formats that require conversion to MP3
VIDEO_FORMATS_REQUIRING_CONVERSION = {'.mp4', '.webm', '.mov', '.avi', '.mkv'}


class TranscriptionService:
    def __init__(self):
        import httpx
        # Validate and clean base_url
        base_url = settings.evolution_base_url
        if not base_url:
            raise ValueError("EVOLUTION_BASE_URL is not set in environment variables")
        
        # Clean up base_url if it contains the variable name prefix (common .env mistake)
        # This happens when .env has: EVOLUTION_BASE_URL=EVOLUTION_BASE_URL=https://...
        original_url = base_url
        if "EVOLUTION_BASE_URL=" in base_url:
            # Find the last "=" and take everything after it
            last_eq_index = base_url.rfind("=")
            if last_eq_index >= 0:
                base_url = base_url[last_eq_index + 1:].strip()
                logger.warning(f"Cleaned malformed base_url: '{original_url}' -> '{base_url}'")
        
        if not base_url.startswith(('http://', 'https://')):
            raise ValueError(f"EVOLUTION_BASE_URL must start with http:// or https://, got: {base_url}")
        
        logger.info(f"Initializing TranscriptionService with base_url: {base_url}")
        
        # Create custom HTTP client with SSL verification disabled for internal Cloud.ru endpoints
        # and increased timeout for large files
        http_client = httpx.Client(
            verify=False,  # Disable SSL verification for internal Cloud.ru endpoints
            timeout=httpx.Timeout(120.0, connect=30.0),  # 120s total, 30s for connection
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
        )
        self.client = OpenAI(
            api_key=settings.evolution_api_key,
            base_url=base_url,
            http_client=http_client,
            max_retries=2  # Additional retries at client level
        )
        self.max_retries = 3
        self.max_file_size = settings.max_file_size_mb * 1024 * 1024  # Convert to bytes

    def _convert_to_mp3_if_needed(self, file_path: str) -> Tuple[str, bool]:
        """
        Convert video/audio files to MP3 format for SberCloud API compatibility.

        SberCloud API returns 503 for MP4 files - they must be converted to MP3 first.

        Args:
            file_path: Path to the input file

        Returns:
            Tuple of (file_path_to_use, is_temporary)
            - file_path_to_use: Either original path or converted MP3 path
            - is_temporary: True if converted file should be deleted after use
        """
        ext = os.path.splitext(file_path)[1].lower()

        # Check if conversion is needed
        if ext in SUPPORTED_AUDIO_FORMATS:
            logger.debug(f"File format {ext} is supported by SberCloud API, no conversion needed")
            return file_path, False

        if ext in VIDEO_FORMATS_REQUIRING_CONVERSION or ext not in SUPPORTED_AUDIO_FORMATS:
            logger.info(f"Converting {ext} file to MP3 for SberCloud API compatibility")

            # Create temporary MP3 file
            temp_mp3 = tempfile.NamedTemporaryFile(suffix='.mp3', delete=False)
            temp_mp3_path = temp_mp3.name
            temp_mp3.close()

            try:
                # Use ffmpeg to convert (extract audio as MP3)
                logger.info(f"Running ffmpeg conversion: {file_path} -> {temp_mp3_path}")
                result = subprocess.run(
                    ['ffmpeg', '-i', file_path,
                     '-vn',  # No video
                     '-acodec', 'libmp3lame',  # MP3 codec
                     '-q:a', '2',  # High quality (0-9, lower is better)
                     '-y',  # Overwrite output file
                     temp_mp3_path],
                    capture_output=True,
                    text=True,
                    timeout=300  # 5 minute timeout for conversion
                )

                if result.returncode != 0:
                    logger.error(f"FFmpeg conversion failed: {result.stderr}")
                    # Fall back to original file
                    return file_path, False

                # Get file sizes for logging
                original_size = os.path.getsize(file_path)
                converted_size = os.path.getsize(temp_mp3_path)
                logger.info(f"✅ Conversion successful: {original_size / 1024 / 1024:.2f} MB -> {converted_size / 1024 / 1024:.2f} MB")

                return temp_mp3_path, True

            except subprocess.TimeoutExpired:
                logger.error(f"FFmpeg conversion timed out after 5 minutes")
                if os.path.exists(temp_mp3_path):
                    os.unlink(temp_mp3_path)
                return file_path, False
            except Exception as e:
                logger.error(f"Error during conversion: {e}")
                if os.path.exists(temp_mp3_path):
                    os.unlink(temp_mp3_path)
                return file_path, False

        return file_path, False
    
    def transcribe_file(
        self,
        file_path: str,
        language: Optional[str] = None,
        response_format: str = "json",
        progress_callback: Optional[Callable[[float], None]] = None
    ) -> Dict[str, Any]:
        """
        Transcribe audio file using Whisper Large v3
        Automatically handles large files by splitting into chunks

        Args:
            file_path: Path to audio file
            language: ISO-639-1 language code (None for auto-detect)
            response_format: Format of response (text, json) - Evolution Cloud.ru supports only json and text

        Returns:
            Dictionary with transcription results
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        # Convert video/unsupported formats to MP3 for SberCloud API compatibility
        file_path, is_temp_file = self._convert_to_mp3_if_needed(file_path)

        try:
            file_size = os.path.getsize(file_path)

            # If file is too large, split and process in chunks
            if file_size > self.max_file_size:
                logger.info(f"File size ({file_size / 1024 / 1024:.2f} MB) exceeds limit, splitting into chunks")
                return self._transcribe_large_file(file_path, language, response_format, progress_callback)

            # Process normally for files under limit
            for attempt in range(self.max_retries):
                try:
                    logger.info(f"Transcription attempt {attempt + 1}/{self.max_retries} for {file_path}")

                    with open(file_path, "rb") as audio_file:
                        transcription_params = {
                            "model": "openai/whisper-large-v3",
                            "file": audio_file,
                            "response_format": response_format,
                            "temperature": 0.0
                        }
                        if language and language.strip():
                            # Force language parameter - Evolution Cloud.ru should respect it
                            transcription_params["language"] = language.strip()
                            logger.info(f"Transcribing with EXPLICIT language: {language.strip()} (will be forced)")
                        else:
                            logger.info("Transcribing with auto-detection (language not specified)")

                        transcript = self.client.audio.transcriptions.create(**transcription_params)

                    logger.info(f"Successfully transcribed {file_path}")

                    # Parse response based on format
                    # Evolution Cloud.ru returns json format (not verbose_json)
                    if response_format == "json":
                        # Try to get full response data
                        if hasattr(transcript, "model_dump"):
                            full_data = transcript.model_dump()
                        elif hasattr(transcript, "dict"):
                            full_data = transcript.dict()
                        else:
                            full_data = {"text": str(transcript)}

                        return {
                            "text": transcript.text if hasattr(transcript, "text") else str(transcript),
                            "language": getattr(transcript, "language", language),
                            "segments": full_data.get("segments", []),
                            "words": full_data.get("words", []),
                            "full_response": full_data
                        }
                    elif response_format == "srt":
                        return {
                            "text": str(transcript),
                            "srt": str(transcript),
                            "language": language
                        }
                    elif response_format == "vtt":
                        return {
                            "text": str(transcript),
                            "vtt": str(transcript),
                            "language": language
                        }
                    else:  # text
                        return {
                            "text": transcript.text if hasattr(transcript, "text") else str(transcript),
                            "language": language
                        }

                except Exception as e:
                    logger.error(f"Error in transcription attempt {attempt + 1}: {str(e)}")

                    if attempt < self.max_retries - 1:
                        wait_time = 2 ** attempt  # Exponential backoff
                        logger.info(f"Waiting {wait_time} seconds before retry...")
                        time.sleep(wait_time)
                    else:
                        logger.error(f"Failed to transcribe after {self.max_retries} attempts")
                        raise
        finally:
            # Clean up temporary converted file
            if is_temp_file and os.path.exists(file_path):
                logger.debug(f"Cleaning up temporary file: {file_path}")
                os.unlink(file_path)
    
    def _transcribe_large_file(
        self,
        file_path: str,
        language: Optional[str] = None,
        response_format: str = "json",
        progress_callback: Optional[Callable[[float], None]] = None
    ) -> Dict[str, Any]:
        """
        Transcribe large file by splitting into chunks and merging results
        
        Note: This is a simplified implementation. For production use,
        consider using pydub or ffmpeg for proper audio splitting.
        """
        try:
            # Try to use pydub if available
            from pydub import AudioSegment
            use_pydub = True
        except ImportError:
            logger.warning("pydub not available, using basic file splitting (may not work for all formats)")
            use_pydub = False
        
        file_size = os.path.getsize(file_path)
        chunk_size_bytes = int(self.max_file_size * 0.9)  # Use 90% of max to be safe
        num_chunks = (file_size + chunk_size_bytes - 1) // chunk_size_bytes
        
        logger.info(f"Splitting file into {num_chunks} chunks")
        
        all_texts = []
        all_segments = []
        all_words = []
        detected_language = language
        
        if use_pydub:
            # Use pydub for proper audio splitting
            audio = AudioSegment.from_file(file_path)
            duration_ms = len(audio)
            chunk_duration_ms = int((duration_ms / num_chunks))
            
            for i in range(num_chunks):
                logger.info(f"Processing chunk {i+1}/{num_chunks}")
                start_ms = i * chunk_duration_ms
                end_ms = min((i + 1) * chunk_duration_ms, duration_ms)
                
                chunk_audio = audio[start_ms:end_ms]
                
                # Save chunk to temporary file
                with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_file:
                    chunk_path = temp_file.name
                    chunk_audio.export(chunk_path, format="mp3")
                
                try:
                    # Transcribe chunk (language handling is done in _transcribe_single_file)
                    chunk_result = self._transcribe_single_file(
                        chunk_path, language, response_format
                    )
                    
                    all_texts.append(chunk_result["text"])
                    if "segments" in chunk_result:
                        # Adjust segment timestamps
                        for segment in chunk_result["segments"]:
                            segment["start"] = segment.get("start", 0) + (start_ms / 1000.0)
                            segment["end"] = segment.get("end", 0) + (start_ms / 1000.0)
                        all_segments.extend(chunk_result["segments"])
                    if "words" in chunk_result:
                        # Adjust word timestamps
                        for word in chunk_result["words"]:
                            word["start"] = word.get("start", 0) + (start_ms / 1000.0)
                            word["end"] = word.get("end", 0) + (start_ms / 1000.0)
                        all_words.extend(chunk_result["words"])
                    
                    if not detected_language and "language" in chunk_result:
                        detected_language = chunk_result["language"]
                    
                    # Update progress after each chunk
                    if progress_callback:
                        progress = 0.1 + 0.8 * (i + 1) / num_chunks
                        progress_callback(progress)
                        logger.info(f"Progress updated: {progress:.2%} after chunk {i+1}/{num_chunks}")
                
                finally:
                    # Cleanup temp file
                    if os.path.exists(chunk_path):
                        os.unlink(chunk_path)
        else:
            # Fallback: try to process file in binary chunks (may not work for all formats)
            logger.warning("Using basic binary splitting - may not work correctly for audio files")
            raise NotImplementedError(
                "Large file processing requires pydub. Install with: pip install pydub"
            )
        
        # Merge results
        merged_text = " ".join(all_texts)
        
        result = {
            "text": merged_text,
            "language": detected_language or language,
            "full_response": {
                "text": merged_text,
                "language": detected_language or language,
                "segments": all_segments,
                "words": all_words
            }
        }
        
        if response_format == "verbose_json":
            result["segments"] = all_segments
            result["words"] = all_words
        
        logger.info(f"Successfully transcribed large file with {num_chunks} chunks")
        return result
    
    def _transcribe_single_file(
        self,
        file_path: str,
        language: Optional[str] = None,
        response_format: str = "json"
    ) -> Dict[str, Any]:
        """Internal method to transcribe a single file (used by chunking)"""
        for attempt in range(self.max_retries):
            try:
                with open(file_path, "rb") as audio_file:
                    transcription_params = {
                        "model": "openai/whisper-large-v3",
                        "file": audio_file,
                        "response_format": response_format,
                        "temperature": 0.0
                    }
                    if language and language.strip():
                        # Force language parameter - Evolution Cloud.ru should respect it
                        transcription_params["language"] = language.strip()
                        logger.info(f"Transcribing chunk with EXPLICIT language: {language.strip()}")
                    else:
                        logger.info("Transcribing chunk with auto-detection (language not specified)")
                    
                    transcript = self.client.audio.transcriptions.create(**transcription_params)
                
                # Parse response - Evolution Cloud.ru returns json format
                if hasattr(transcript, "model_dump"):
                    full_data = transcript.model_dump()
                elif hasattr(transcript, "dict"):
                    full_data = transcript.dict()
                else:
                    full_data = {"text": str(transcript)}
                
                return {
                    "text": transcript.text if hasattr(transcript, "text") else str(transcript),
                    "language": getattr(transcript, "language", language),
                    "segments": full_data.get("segments", []),
                    "words": full_data.get("words", []),
                }
            
            except Exception as e:
                logger.error(f"Error in transcription attempt {attempt + 1}: {str(e)}")
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt
                    time.sleep(wait_time)
                else:
                    raise
    
    def get_file_info(self, file_path: str) -> Dict[str, Any]:
        """Get basic information about audio file"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        file_size = os.path.getsize(file_path)
        file_extension = os.path.splitext(file_path)[1].lower()
        
        return {
            "file_path": file_path,
            "file_size": file_size,
            "file_extension": file_extension,
            "file_name": os.path.basename(file_path)
        }

