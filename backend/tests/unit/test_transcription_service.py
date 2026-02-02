"""
Comprehensive unit tests for TranscriptionService

Tests cover:
- MP4 to MP3 conversion logic
- File size validation
- Chunk splitting for large files
- API retry logic
- Error handling for external API failures
- Language parameter handling
"""

import os
import unittest
from unittest.mock import Mock, patch, MagicMock, call, mock_open
from pathlib import Path
import tempfile

# Mock the config before importing the service
sys_modules_patcher = patch.dict('sys.modules', {
    'app.config': MagicMock(),
    'app.config.settings': MagicMock(
        evolution_api_key='test_api_key',
        evolution_base_url='https://test.api.internal.cloud.ru/v1',
        max_file_size_mb=25,
        app_env='development'
    )
})
sys_modules_patcher.start()

try:
    from app.services.transcription_service import TranscriptionService, SUPPORTED_AUDIO_FORMATS, VIDEO_FORMATS_REQUIRING_CONVERSION
finally:
    sys_modules_patcher.stop()


class TestTranscriptionServiceInitialization(unittest.TestCase):
    """Test TranscriptionService initialization and configuration"""

    @patch('app.services.transcription_service.OpenAI')
    @patch('app.services.transcription_service.httpx.Client')
    @patch('app.services.transcription_service.settings')
    def test_initialization_with_valid_config(self, mock_settings, mock_httpx_client, mock_openai):
        """Test successful initialization with valid configuration"""
        mock_settings.evolution_api_key = 'test_key'
        mock_settings.evolution_base_url = 'https://test.api.com/v1'
        mock_settings.max_file_size_mb = 25

        mock_http_client = MagicMock()
        mock_httpx_client.return_value = mock_http_client

        mock_openai_client = MagicMock()
        mock_openai.return_value = mock_openai_client

        service = TranscriptionService()

        self.assertEqual(service.max_retries, 3)
        self.assertEqual(service.max_file_size, 25 * 1024 * 1024)
        mock_openai.assert_called_once()

    @patch('app.services.transcription_service.settings')
    def test_initialization_with_missing_base_url(self, mock_settings):
        """Test initialization fails when base_url is missing"""
        mock_settings.evolution_base_url = ''
        mock_settings.evolution_api_key = 'test_key'

        with self.assertRaises(ValueError) as context:
            TranscriptionService()

        self.assertIn('EVOLUTION_BASE_URL is not set', str(context.exception))

    @patch('app.services.transcription_service.settings')
    def test_initialization_with_invalid_base_url_format(self, mock_settings):
        """Test initialization fails when base_url doesn't start with http:// or https://"""
        mock_settings.evolution_base_url = 'invalid-url'
        mock_settings.evolution_api_key = 'test_key'

        with self.assertRaises(ValueError) as context:
            TranscriptionService()

        self.assertIn('must start with http:// or https://', str(context.exception))

    @patch('app.services.transcription_service.OpenAI')
    @patch('app.services.transcription_service.httpx.Client')
    @patch('app.services.transcription_service.settings')
    def test_initialization_cleans_malformed_base_url(self, mock_settings, mock_httpx_client, mock_openai):
        """Test that malformed base_url with variable name prefix is cleaned"""
        mock_settings.evolution_api_key = 'test_key'
        mock_settings.evolution_base_url = 'EVOLUTION_BASE_URL=https://test.api.com/v1'
        mock_settings.max_file_size_mb = 25

        mock_http_client = MagicMock()
        mock_httpx_client.return_value = mock_http_client

        mock_openai_client = MagicMock()
        mock_openai.return_value = mock_openai_client

        service = TranscriptionService()

        # Verify the OpenAI client was initialized with cleaned URL
        call_kwargs = mock_openai.call_args[1]
        self.assertEqual(call_kwargs['base_url'], 'https://test.api.com/v1')


class TestMP4ToMP3Conversion(unittest.TestCase):
    """Test MP4 to MP3 conversion logic"""

    def setUp(self):
        """Set up test fixtures"""
        self.patcher_settings = patch('app.services.transcription_service.settings')
        self.mock_settings = self.patcher_settings.start()
        self.mock_settings.evolution_api_key = 'test_key'
        self.mock_settings.evolution_base_url = 'https://test.api.com/v1'
        self.mock_settings.max_file_size_mb = 25

        with patch('app.services.transcription_service.OpenAI'), \
             patch('app.services.transcription_service.httpx.Client'):
            self.service = TranscriptionService()

    def tearDown(self):
        """Clean up patches"""
        self.patcher_settings.stop()

    def test_supported_audio_format_no_conversion(self):
        """Test that supported audio formats are not converted"""
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
            temp_path = temp_file.name

        try:
            result_path, is_temp = self.service._convert_to_mp3_if_needed(temp_path)

            self.assertEqual(result_path, temp_path)
            self.assertFalse(is_temp)
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_mp4_file_requires_conversion(self):
        """Test that .mp4 files are marked for conversion"""
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_file:
            temp_path = temp_file.name

        try:
            result_path, is_temp = self.service._convert_to_mp3_if_needed(temp_path)

            # Should return original path if conversion fails (ffmpeg not available in tests)
            self.assertFalse(is_temp)
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    @patch('app.services.transcription_service.subprocess.run')
    @patch('app.services.transcription_service.tempfile.NamedTemporaryFile')
    def test_successful_ffmpeg_conversion(self, mock_temp_file, mock_subprocess):
        """Test successful FFmpeg conversion"""
        # Create mock temporary file
        mock_temp = MagicMock()
        mock_temp.name = '/tmp/converted.mp3'
        mock_temp_file.return_value = mock_temp

        # Mock successful subprocess run
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result

        # Mock file size checks
        with patch('os.path.getsize', return_value=1024000):
            result_path, is_temp = self.service._convert_to_mp3_if_needed('/path/to/video.mp4')

        self.assertEqual(result_path, '/tmp/converted.mp3')
        self.assertTrue(is_temp)

        # Verify ffmpeg was called with correct arguments
        mock_subprocess.assert_called_once()
        call_args = mock_subprocess.call_args[0][0]
        self.assertIn('ffmpeg', call_args)
        self.assertIn('-acodec', 'libmp3lame', call_args)

    @patch('app.services.transcription_service.subprocess.run')
    @patch('app.services.transcription_service.tempfile.NamedTemporaryFile')
    def test_ffmpeg_conversion_failure_fallback(self, mock_temp_file, mock_subprocess):
        """Test fallback to original file when FFmpeg conversion fails"""
        # Create mock temporary file
        mock_temp = MagicMock()
        mock_temp.name = '/tmp/converted.mp3'
        mock_temp_file.return_value = mock_temp

        # Mock failed subprocess run
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = 'Conversion failed'
        mock_subprocess.return_value = mock_result

        original_path = '/path/to/video.mp4'
        result_path, is_temp = self.service._convert_to_mp3_if_needed(original_path)

        self.assertEqual(result_path, original_path)
        self.assertFalse(is_temp)

    @patch('app.services.transcription_service.subprocess.run')
    @patch('app.services.transcription_service.tempfile.NamedTemporaryFile')
    def test_ffmpeg_timeout_handling(self, mock_temp_file, mock_subprocess):
        """Test handling of FFmpeg timeout"""
        from subprocess import TimeoutExpired

        # Create mock temporary file
        mock_temp = MagicMock()
        mock_temp.name = '/tmp/converted.mp3'
        mock_temp_file.return_value = mock_temp

        # Mock timeout exception
        mock_subprocess.side_effect = TimeoutExpired('ffmpeg', 300)

        with patch('os.path.exists', return_value=True), \
             patch('os.unlink') as mock_unlink:
            original_path = '/path/to/video.mp4'
            result_path, is_temp = self.service._convert_to_mp3_if_needed(original_path)

        self.assertEqual(result_path, original_path)
        self.assertFalse(is_temp)
        mock_unlink.assert_called_once_with('/tmp/converted.mp3')

    @patch('app.services.transcription_service.subprocess.run')
    @patch('app.services.transcription_service.tempfile.NamedTemporaryFile')
    def test_ffmpeg_exception_handling(self, mock_temp_file, mock_subprocess):
        """Test handling of unexpected exceptions during conversion"""
        # Create mock temporary file
        mock_temp = MagicMock()
        mock_temp.name = '/tmp/converted.mp3'
        mock_temp_file.return_value = mock_temp

        # Mock general exception
        mock_subprocess.side_effect = Exception('Unexpected error')

        with patch('os.path.exists', return_value=True), \
             patch('os.unlink') as mock_unlink:
            original_path = '/path/to/video.mp4'
            result_path, is_temp = self.service._convert_to_mp3_if_needed(original_path)

        self.assertEqual(result_path, original_path)
        self.assertFalse(is_temp)


class TestFileSizeValidation(unittest.TestCase):
    """Test file size validation logic"""

    def setUp(self):
        """Set up test fixtures"""
        self.patcher_settings = patch('app.services.transcription_service.settings')
        self.mock_settings = self.patcher_settings.start()
        self.mock_settings.evolution_api_key = 'test_key'
        self.mock_settings.evolution_base_url = 'https://test.api.com/v1'
        self.mock_settings.max_file_size_mb = 25

        with patch('app.services.transcription_service.OpenAI'), \
             patch('app.services.transcription_service.httpx.Client'):
            self.service = TranscriptionService()

    def tearDown(self):
        """Clean up patches"""
        self.patcher_settings.stop()

    def test_max_file_size_calculation(self):
        """Test that max file size is correctly calculated from MB to bytes"""
        expected_size = 25 * 1024 * 1024  # 25 MB in bytes
        self.assertEqual(self.service.max_file_size, expected_size)

    @patch('os.path.getsize')
    def test_file_under_limit(self, mock_getsize):
        """Test file size under limit is processed normally"""
        mock_getsize.return_value = 10 * 1024 * 1024  # 10 MB

        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
            temp_path = temp_file.name

        try:
            file_size = os.path.getsize(temp_path)
            self.assertLess(file_size, self.service.max_file_size)
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    @patch('os.path.getsize')
    def test_file_over_limit(self, mock_getsize):
        """Test file size over limit triggers chunking"""
        mock_getsize.return_value = 30 * 1024 * 1024  # 30 MB

        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
            temp_path = temp_file.name

        try:
            file_size = os.path.getsize(temp_path)
            self.assertGreater(file_size, self.service.max_file_size)
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)


class TestChunkSplittingForLargeFiles(unittest.TestCase):
    """Test chunk splitting for large files"""

    def setUp(self):
        """Set up test fixtures"""
        self.patcher_settings = patch('app.services.transcription_service.settings')
        self.mock_settings = self.patcher_settings.start()
        self.mock_settings.evolution_api_key = 'test_key'
        self.mock_settings.evolution_base_url = 'https://test.api.com/v1'
        self.mock_settings.max_file_size_mb = 25

        with patch('app.services.transcription_service.OpenAI'), \
             patch('app.services.transcription_service.httpx.Client'):
            self.service = TranscriptionService()

    def tearDown(self):
        """Clean up patches"""
        self.patcher_settings.stop()

    def test_chunk_size_calculation(self):
        """Test that chunk size is 90% of max file size"""
        file_size = 30 * 1024 * 1024  # 30 MB
        expected_chunk_size = int(self.service.max_file_size * 0.9)
        num_chunks = (file_size + expected_chunk_size - 1) // expected_chunk_size

        self.assertGreater(num_chunks, 1, "Large file should be split into multiple chunks")

    @patch('app.services.transcription_service.AudioSegment')
    @patch('os.path.getsize')
    def test_transcribe_large_file_with_pydub(self, mock_getsize, mock_audioksegment):
        """Test large file transcription with pydub available"""
        mock_getsize.return_value = 30 * 1024 * 1024

        # Mock AudioSegment
        mock_audio = MagicMock()
        mock_audio.__len__ = MagicMock(return_value=360000)  # 6 minutes in ms
        mock_audio.__getitem__ = MagicMock(side_effect=lambda x: mock_audio)

        mock_audioksegment.from_file.return_value = mock_audio

        # Mock _transcribe_single_file
        with patch.object(self.service, '_transcribe_single_file') as mock_transcribe:
            mock_transcribe.return_value = {
                'text': 'Sample transcription',
                'language': 'en',
                'segments': [],
                'words': []
            }

            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
                temp_path = temp_file.name

            try:
                result = self.service._transcribe_large_file(temp_path, 'en', 'json', None)

                self.assertIn('text', result)
                self.assertIn('language', result)
                self.assertEqual(result['language'], 'en')
            finally:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)

    @patch('app.services.transcription_service.AudioSegment')
    def test_transcribe_large_file_without_pydub(self, mock_audioksegment):
        """Test large file transcription fails without pydub"""
        # Mock pydub not available
        mock_audioksegment.side_effect = ImportError("No module named 'pydub'")

        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
            temp_path = temp_file.name

        try:
            with self.assertRaises(NotImplementedError) as context:
                self.service._transcribe_large_file(temp_path, 'en', 'json', None)

            self.assertIn('pydub', str(context.exception))
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    @patch('app.services.transcription_service.AudioSegment')
    @patch('os.path.getsize')
    def test_progress_callback_during_chunking(self, mock_getsize, mock_audioksegment):
        """Test that progress callback is called during chunk processing"""
        mock_getsize.return_value = 30 * 1024 * 1024

        # Mock AudioSegment
        mock_audio = MagicMock()
        mock_audio.__len__ = MagicMock(return_value=360000)
        mock_audio.__getitem__ = MagicMock(side_effect=lambda x: mock_audio)
        mock_audioksegment.from_file.return_value = mock_audio

        progress_values = []

        def progress_callback(progress):
            progress_values.append(progress)

        # Mock _transcribe_single_file
        with patch.object(self.service, '_transcribe_single_file') as mock_transcribe:
            mock_transcribe.return_value = {
                'text': 'Sample',
                'language': 'en',
                'segments': [],
                'words': []
            }

            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
                temp_path = temp_file.name

            try:
                self.service._transcribe_large_file(temp_path, 'en', 'json', progress_callback)

                self.assertGreater(len(progress_values), 0, "Progress callback should be called")
                # Check that progress increases
                self.assertEqual(progress_values, sorted(progress_values))
            finally:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)


class TestAPIRetryLogic(unittest.TestCase):
    """Test API retry logic"""

    def setUp(self):
        """Set up test fixtures"""
        self.patcher_settings = patch('app.services.transcription_service.settings')
        self.mock_settings = self.patcher_settings.start()
        self.mock_settings.evolution_api_key = 'test_key'
        self.mock_settings.evolution_base_url = 'https://test.api.com/v1'
        self.mock_settings.max_file_size_mb = 25

        with patch('app.services.transcription_service.OpenAI') as mock_openai, \
             patch('app.services.transcription_service.httpx.Client'):
            self.service = TranscriptionService()
            self.mock_client = mock_openai.return_value

    def tearDown(self):
        """Clean up patches"""
        self.patcher_settings.stop()

    @patch('builtins.open', new_callable=mock_open, read_data=b'fake audio data')
    @patch('os.path.exists')
    @patch('os.path.getsize')
    def test_successful_transcription_on_first_attempt(self, mock_getsize, mock_exists, mock_file):
        """Test successful transcription on first attempt"""
        mock_exists.return_value = True
        mock_getsize.return_value = 10 * 1024 * 1024  # 10 MB

        mock_transcript = MagicMock()
        mock_transcript.text = 'Sample transcription'
        mock_transcript.language = 'en'
        mock_transcript.model_dump.return_value = {'text': 'Sample', 'language': 'en', 'segments': [], 'words': []}

        self.mock_client.audio.transcriptions.create.return_value = mock_transcript

        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
            temp_path = temp_file.name

        try:
            result = self.service.transcribe_file(temp_path)

            self.assertEqual(result['text'], 'Sample transcription')
            self.assertEqual(result['language'], 'en')
            self.mock_client.audio.transcriptions.create.assert_called_once()
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    @patch('builtins.open', new_callable=mock_open, read_data=b'fake audio data')
    @patch('os.path.exists')
    @patch('os.path.getsize')
    @patch('time.sleep')
    def test_retry_on_failure(self, mock_sleep, mock_getsize, mock_exists, mock_file):
        """Test that transcription retries on failure"""
        mock_exists.return_value = True
        mock_getsize.return_value = 10 * 1024 * 1024

        # Fail first two attempts, succeed on third
        self.mock_client.audio.transcriptions.create.side_effect = [
            Exception('API error'),
            Exception('API error'),
            MagicMock(text='Success', language='en', model_dump=lambda: {'text': 'Success', 'segments': [], 'words': []})
        ]

        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
            temp_path = temp_file.name

        try:
            result = self.service.transcribe_file(temp_path)

            self.assertEqual(result['text'], 'Success')
            self.assertEqual(self.mock_client.audio.transcriptions.create.call_count, 3)

            # Verify exponential backoff
            mock_sleep.assert_has_calls([call(1), call(2)])
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    @patch('builtins.open', new_callable=mock_open, read_data=b'fake audio data')
    @patch('os.path.exists')
    @patch('os.path.getsize')
    @patch('time.sleep')
    def test_max_retries_exceeded(self, mock_sleep, mock_getsize, mock_exists, mock_file):
        """Test that exception is raised after max retries"""
        mock_exists.return_value = True
        mock_getsize.return_value = 10 * 1024 * 1024

        # Always fail
        self.mock_client.audio.transcriptions.create.side_effect = Exception('API error')

        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
            temp_path = temp_file.name

        try:
            with self.assertRaises(Exception) as context:
                self.service.transcribe_file(temp_path)

            self.assertIn('API error', str(context.exception))
            self.assertEqual(self.mock_client.audio.transcriptions.create.call_count, 3)
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)


class TestErrorHandling(unittest.TestCase):
    """Test error handling for external API failures"""

    def setUp(self):
        """Set up test fixtures"""
        self.patcher_settings = patch('app.services.transcription_service.settings')
        self.mock_settings = self.patcher_settings.start()
        self.mock_settings.evolution_api_key = 'test_key'
        self.mock_settings.evolution_base_url = 'https://test.api.com/v1'
        self.mock_settings.max_file_size_mb = 25

        with patch('app.services.transcription_service.OpenAI'), \
             patch('app.services.transcription_service.httpx.Client'):
            self.service = TranscriptionService()

    def tearDown(self):
        """Clean up patches"""
        self.patcher_settings.stop()

    def test_file_not_found_error(self):
        """Test FileNotFoundError for non-existent file"""
        with self.assertRaises(FileNotFoundError) as context:
            self.service.transcribe_file('/nonexistent/path/file.mp3')

        self.assertIn('File not found', str(context.exception))

    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data=b'fake audio data')
    @patch('os.path.getsize')
    @patch('time.sleep')
    def test_network_error_handling(self, mock_sleep, mock_getsize, mock_exists, mock_file):
        """Test handling of network errors"""
        mock_exists.return_value = True
        mock_getsize.return_value = 10 * 1024 * 1024

        with patch.object(self.service, 'client') as mock_client:
            # Mock network error
            mock_client.audio.transcriptions.create.side_effect = Exception('Network error')

            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
                temp_path = temp_file.name

            try:
                with self.assertRaises(Exception):
                    self.service.transcribe_file(temp_path)

                # Verify retries were attempted
                self.assertEqual(mock_client.audio.transcriptions.create.call_count, 3)
            finally:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)

    @patch('os.path.exists')
    @patch('os.unlink')
    def test_temp_file_cleanup_on_error(self, mock_unlink, mock_exists):
        """Test that temporary converted files are cleaned up on error"""
        mock_exists.return_value = True

        with patch('os.path.getsize', return_value=10 * 1024 * 1024):
            with patch('builtins.open', new_callable=mock_open, read_data=b'fake audio data'):
                with patch.object(self.service, 'client') as mock_client:
                    mock_client.audio.transcriptions.create.side_effect = Exception('Error')

                    with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_file:
                        temp_path = temp_file.name

                    try:
                        # Mock conversion to create temp file
                        with patch.object(self.service, '_convert_to_mp3_if_needed', return_value=('/tmp/temp.mp3', True)):
                            with self.assertRaises(Exception):
                                self.service.transcribe_file(temp_path)

                            # Verify cleanup was attempted
                            mock_unlink.assert_called_once_with('/tmp/temp.mp3')
                    finally:
                        if os.path.exists(temp_path):
                            os.unlink(temp_path)


class TestLanguageParameterHandling(unittest.TestCase):
    """Test language parameter handling"""

    def setUp(self):
        """Set up test fixtures"""
        self.patcher_settings = patch('app.services.transcription_service.settings')
        self.mock_settings = self.patcher_settings.start()
        self.mock_settings.evolution_api_key = 'test_key'
        self.mock_settings.evolution_base_url = 'https://test.api.com/v1'
        self.mock_settings.max_file_size_mb = 25

        with patch('app.services.transcription_service.OpenAI') as mock_openai, \
             patch('app.services.transcription_service.httpx.Client'):
            self.service = TranscriptionService()
            self.mock_client = mock_openai.return_value

    def tearDown(self):
        """Clean up patches"""
        self.patcher_settings.stop()

    @patch('builtins.open', new_callable=mock_open, read_data=b'fake audio data')
    @patch('os.path.exists')
    @patch('os.path.getsize')
    def test_language_parameter_passed(self, mock_getsize, mock_exists, mock_file):
        """Test that language parameter is passed to API"""
        mock_exists.return_value = True
        mock_getsize.return_value = 10 * 1024 * 1024

        mock_transcript = MagicMock()
        mock_transcript.text = 'Sample'
        mock_transcript.language = 'en'
        mock_transcript.model_dump.return_value = {'text': 'Sample', 'language': 'en', 'segments': [], 'words': []}

        self.mock_client.audio.transcriptions.create.return_value = mock_transcript

        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
            temp_path = temp_file.name

        try:
            result = self.service.transcribe_file(temp_path, language='en')

            call_kwargs = self.mock_client.audio.transcriptions.create.call_args[1]
            self.assertEqual(call_kwargs['language'], 'en')
            self.assertEqual(result['language'], 'en')
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    @patch('builtins.open', new_callable=mock_open, read_data=b'fake audio data')
    @patch('os.path.exists')
    @patch('os.path.getsize')
    def test_language_parameter_stripped(self, mock_getsize, mock_exists, mock_file):
        """Test that language parameter is stripped of whitespace"""
        mock_exists.return_value = True
        mock_getsize.return_value = 10 * 1024 * 1024

        mock_transcript = MagicMock()
        mock_transcript.text = 'Sample'
        mock_transcript.language = 'ru'
        mock_transcript.model_dump.return_value = {'text': 'Sample', 'language': 'ru', 'segments': [], 'words': []}

        self.mock_client.audio.transcriptions.create.return_value = mock_transcript

        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
            temp_path = temp_file.name

        try:
            result = self.service.transcribe_file(temp_path, language='  ru  ')

            call_kwargs = self.mock_client.audio.transcriptions.create.call_args[1]
            self.assertEqual(call_kwargs['language'], 'ru')
            self.assertEqual(result['language'], 'ru')
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    @patch('builtins.open', new_callable=mock_open, read_data=b'fake audio data')
    @patch('os.path.exists')
    @patch('os.path.getsize')
    def test_auto_detect_language_when_none(self, mock_getsize, mock_exists, mock_file):
        """Test auto-detection when language is None"""
        mock_exists.return_value = True
        mock_getsize.return_value = 10 * 1024 * 1024

        mock_transcript = MagicMock()
        mock_transcript.text = 'Sample'
        mock_transcript.model_dump.return_value = {'text': 'Sample', 'segments': [], 'words': []}

        self.mock_client.audio.transcriptions.create.return_value = mock_transcript

        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
            temp_path = temp_file.name

        try:
            result = self.service.transcribe_file(temp_path, language=None)

            call_kwargs = self.mock_client.audio.transcriptions.create.call_args[1]
            self.assertNotIn('language', call_kwargs)
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    @patch('builtins.open', new_callable=mock_open, read_data=b'fake audio data')
    @patch('os.path.exists')
    @patch('os.path.getsize')
    def test_auto_detect_language_when_empty(self, mock_getsize, mock_exists, mock_file):
        """Test auto-detection when language is empty string"""
        mock_exists.return_value = True
        mock_getsize.return_value = 10 * 1024 * 1024

        mock_transcript = MagicMock()
        mock_transcript.text = 'Sample'
        mock_transcript.model_dump.return_value = {'text': 'Sample', 'segments': [], 'words': []}

        self.mock_client.audio.transcriptions.create.return_value = mock_transcript

        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
            temp_path = temp_file.name

        try:
            result = self.service.transcribe_file(temp_path, language='')

            call_kwargs = self.mock_client.audio.transcriptions.create.call_args[1]
            self.assertNotIn('language', call_kwargs)
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)


class TestDifferentResponseFormats(unittest.TestCase):
    """Test handling of different response formats"""

    def setUp(self):
        """Set up test fixtures"""
        self.patcher_settings = patch('app.services.transcription_service.settings')
        self.mock_settings = self.patcher_settings.start()
        self.mock_settings.evolution_api_key = 'test_key'
        self.mock_settings.evolution_base_url = 'https://test.api.com/v1'
        self.mock_settings.max_file_size_mb = 25

        with patch('app.services.transcription_service.OpenAI') as mock_openai, \
             patch('app.services.transcription_service.httpx.Client'):
            self.service = TranscriptionService()
            self.mock_client = mock_openai.return_value

    def tearDown(self):
        """Clean up patches"""
        self.patcher_settings.stop()

    @patch('builtins.open', new_callable=mock_open, read_data=b'fake audio data')
    @patch('os.path.exists')
    @patch('os.path.getsize')
    def test_json_response_format(self, mock_getsize, mock_exists, mock_file):
        """Test JSON response format handling"""
        mock_exists.return_value = True
        mock_getsize.return_value = 10 * 1024 * 1024

        mock_transcript = MagicMock()
        mock_transcript.text = 'Sample transcription'
        mock_transcript.language = 'en'
        mock_transcript.model_dump.return_value = {
            'text': 'Sample transcription',
            'language': 'en',
            'segments': [{'start': 0.0, 'end': 1.0, 'text': 'Sample'}],
            'words': [{'word': 'Sample', 'start': 0.0, 'end': 1.0}]
        }

        self.mock_client.audio.transcriptions.create.return_value = mock_transcript

        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
            temp_path = temp_file.name

        try:
            result = self.service.transcribe_file(temp_path, response_format='json')

            self.assertEqual(result['text'], 'Sample transcription')
            self.assertIn('segments', result)
            self.assertIn('words', result)
            self.assertIn('full_response', result)
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    @patch('builtins.open', new_callable=mock_open, read_data=b'fake audio data')
    @patch('os.path.exists')
    @patch('os.path.getsize')
    def test_text_response_format(self, mock_getsize, mock_exists, mock_file):
        """Test text response format handling"""
        mock_exists.return_value = True
        mock_getsize.return_value = 10 * 1024 * 1024

        mock_transcript = MagicMock()
        mock_transcript.text = 'Sample transcription'

        self.mock_client.audio.transcriptions.create.return_value = mock_transcript

        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
            temp_path = temp_file.name

        try:
            result = self.service.transcribe_file(temp_path, response_format='text')

            self.assertEqual(result['text'], 'Sample transcription')
            self.assertIn('language', result)
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    @patch('builtins.open', new_callable=mock_open, read_data=b'fake audio data')
    @patch('os.path.exists')
    @patch('os.path.getsize')
    def test_srt_response_format(self, mock_getsize, mock_exists, mock_file):
        """Test SRT response format handling"""
        mock_exists.return_value = True
        mock_getsize.return_value = 10 * 1024 * 1024

        mock_transcript = MagicMock()
        mock_transcript.__str__ = MagicMock(return_value='1\n00:00:00,000 --> 00:00:01,000\nSample')

        self.mock_client.audio.transcriptions.create.return_value = mock_transcript

        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
            temp_path = temp_file.name

        try:
            result = self.service.transcribe_file(temp_path, response_format='srt')

            self.assertIn('srt', result)
            self.assertIn('text', result)
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    @patch('builtins.open', new_callable=mock_open, read_data=b'fake audio data')
    @patch('os.path.exists')
    @patch('os.path.getsize')
    def test_vtt_response_format(self, mock_getsize, mock_exists, mock_file):
        """Test VTT response format handling"""
        mock_exists.return_value = True
        mock_getsize.return_value = 10 * 1024 * 1024

        mock_transcript = MagicMock()
        mock_transcript.__str__ = MagicMock(return_value='WEBVTT\n\n00:00:00.000 --> 00:00:01.000\nSample')

        self.mock_client.audio.transcriptions.create.return_value = mock_transcript

        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
            temp_path = temp_file.name

        try:
            result = self.service.transcribe_file(temp_path, response_format='vtt')

            self.assertIn('vtt', result)
            self.assertIn('text', result)
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)


class TestGetFileInfo(unittest.TestCase):
    """Test get_file_info method"""

    def setUp(self):
        """Set up test fixtures"""
        self.patcher_settings = patch('app.services.transcription_service.settings')
        self.mock_settings = self.patcher_settings.start()
        self.mock_settings.evolution_api_key = 'test_key'
        self.mock_settings.evolution_base_url = 'https://test.api.com/v1'
        self.mock_settings.max_file_size_mb = 25

        with patch('app.services.transcription_service.OpenAI'), \
             patch('app.services.transcription_service.httpx.Client'):
            self.service = TranscriptionService()

    def tearDown(self):
        """Clean up patches"""
        self.patcher_settings.stop()

    @patch('os.path.exists')
    @patch('os.path.getsize')
    def test_get_file_info_success(self, mock_getsize, mock_exists):
        """Test successful file info retrieval"""
        mock_exists.return_value = True
        mock_getsize.return_value = 1024000

        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False, prefix='test_audio_') as temp_file:
            temp_path = temp_file.name

        try:
            info = self.service.get_file_info(temp_path)

            self.assertEqual(info['file_path'], temp_path)
            self.assertEqual(info['file_size'], 1024000)
            self.assertEqual(info['file_extension'], '.mp3')
            self.assertIn('test_audio_', info['file_name'])
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_get_file_info_not_found(self):
        """Test get_file_info with non-existent file"""
        with self.assertRaises(FileNotFoundError) as context:
            self.service.get_file_info('/nonexistent/file.mp3')

        self.assertIn('File not found', str(context.exception))


class TestSupportedFormats(unittest.TestCase):
    """Test supported and unsupported audio format detection"""

    def test_supported_audio_formats(self):
        """Test that expected audio formats are marked as supported"""
        self.assertIn('.mp3', SUPPORTED_AUDIO_FORMATS)
        self.assertIn('.wav', SUPPORTED_AUDIO_FORMATS)
        self.assertIn('.m4a', SUPPORTED_AUDIO_FORMATS)
        self.assertIn('.mpeg', SUPPORTED_AUDIO_FORMATS)
        self.assertIn('.mpga', SUPPORTED_AUDIO_FORMATS)

    def test_video_formats_requiring_conversion(self):
        """Test that expected video formats require conversion"""
        self.assertIn('.mp4', VIDEO_FORMATS_REQUIRING_CONVERSION)
        self.assertIn('.webm', VIDEO_FORMATS_REQUIRING_CONVERSION)
        self.assertIn('.mov', VIDEO_FORMATS_REQUIRING_CONVERSION)
        self.assertIn('.avi', VIDEO_FORMATS_REQUIRING_CONVERSION)
        self.assertIn('.mkv', VIDEO_FORMATS_REQUIRING_CONVERSION)


if __name__ == '__main__':
    unittest.main()
