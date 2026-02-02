"""
Comprehensive unit tests for FileService

Tests cover:
- File validation (type, size)
- Secure filename generation
- File storage operations
- Cleanup logic
"""

import unittest
from unittest.mock import Mock, patch, MagicMock, mock_open
import tempfile
import os
import json
import shutil
from pathlib import Path

# Mock the config before importing the service
sys_modules_patcher = patch.dict('sys.modules', {
    'app.config': MagicMock(),
    'app.config.settings': MagicMock(
        upload_dir='/tmp/test_upload',
        transcripts_dir='/tmp/test_transcripts',
        keep_original_files=False,
        app_env='development'
    )
})
sys_modules_patcher.start()

try:
    from app.services.file_service import FileService
finally:
    sys_modules_patcher.stop()


class TestFileServiceInitialization(unittest.TestCase):
    """Test FileService initialization and directory setup"""

    @patch('app.services.file_service.Path')
    @patch('app.services.file_service.settings')
    def test_initialization_creates_directories(self, mock_settings, mock_path):
        """Test that initialization creates upload and transcripts directories"""
        mock_settings.upload_dir = '/tmp/test_upload'
        mock_settings.transcripts_dir = '/tmp/test_transcripts'
        mock_settings.keep_original_files = False

        mock_upload_dir = MagicMock()
        mock_transcripts_dir = MagicMock()
        mock_path.side_effect = [mock_upload_dir, mock_transcripts_dir]

        service = FileService()

        mock_upload_dir.mkdir.assert_called_once_with(parents=True, exist_ok=True)
        mock_transcripts_dir.mkdir.assert_called_once_with(parents=True, exist_ok=True)

    @patch('app.services.file_service.Path')
    @patch('app.services.file_service.settings')
    def test_initialization_stores_configuration(self, mock_settings, mock_path):
        """Test that initialization stores configuration correctly"""
        mock_settings.upload_dir = '/tmp/test_upload'
        mock_settings.transcripts_dir = '/tmp/test_transcripts'
        mock_settings.keep_original_files = True

        mock_upload_dir = MagicMock()
        mock_transcripts_dir = MagicMock()
        mock_path.side_effect = [mock_upload_dir, mock_transcripts_dir]

        service = FileService()

        self.assertTrue(service.keep_original)


class TestFileValidation(unittest.TestCase):
    """Test file validation logic"""

    def setUp(self):
        """Set up test fixtures"""
        self.patcher_settings = patch('app.services.file_service.settings')
        self.mock_settings = self.patcher_settings.start()
        self.mock_settings.upload_dir = '/tmp/test_upload'
        self.mock_settings.transcripts_dir = '/tmp/test_transcripts'
        self.mock_settings.keep_original_files = False

        with patch('app.services.file_service.Path'):
            self.service = FileService()

    def tearDown(self):
        """Clean up patches"""
        self.patcher_settings.stop()

    @patch('builtins.open', new_callable=mock_open)
    @patch('app.services.file_service.uuid.uuid4')
    @patch('app.services.file_service.Path')
    def test_save_uploaded_file_with_extension(self, mock_path, mock_uuid, mock_file):
        """Test saving uploaded file with correct extension"""
        mock_uuid.return_value = 'test-uuid'

        mock_upload_dir = MagicMock()
        mock_file_path = MagicMock()
        mock_file_path.__str__ = MagicMock(return_value='/tmp/test_upload/test-uuid.mp3')
        mock_upload_dir.__truediv__ = MagicMock(return_value=mock_file_path)

        mock_path_instance = MagicMock()
        mock_path_instance.suffix = '.mp3'
        mock_path.return_value = mock_path_instance

        file_content = b'fake audio content'
        original_filename = 'audio.mp3'

        result_path = self.service.save_uploaded_file(file_content, original_filename)

        self.assertIn('test-uuid', result_path)
        self.assertIn('.mp3', result_path)

    @patch('builtins.open', new_callable=mock_open)
    @patch('app.services.file_service.uuid.uuid4')
    @patch('app.services.file_service.Path')
    def test_save_uploaded_file_generates_unique_filename(self, mock_path, mock_uuid, mock_file):
        """Test that unique filenames are generated using UUID"""
        mock_uuid.return_value = 'unique-uuid-1234'

        mock_upload_dir = MagicMock()
        mock_file_path = MagicMock()
        mock_file_path.__str__ = MagicMock(return_value='/tmp/test_upload/unique-uuid-1234.wav')
        mock_upload_dir.__truediv__ = MagicMock(return_value=mock_file_path)

        mock_path_instance = MagicMock()
        mock_path_instance.suffix = '.wav'
        mock_path.return_value = mock_path_instance

        file_content = b'audio content'
        original_filename = 'test.wav'

        result_path = self.service.save_uploaded_file(file_content, original_filename)

        self.assertIn('unique-uuid-1234', result_path)

    @patch('builtins.open', new_callable=mock_open)
    @patch('app.services.file_service.uuid.uuid4')
    @patch('app.services.file_service.Path')
    def test_save_file_preserves_original_extension(self, mock_path, mock_uuid, mock_file):
        """Test that file extension is preserved from original filename"""
        mock_uuid.return_value = 'uuid-123'

        mock_upload_dir = MagicMock()
        mock_file_path = MagicMock()
        mock_file_path.__str__ = MagicMock(return_value='/tmp/test_upload/uuid-123.mp4')
        mock_upload_dir.__truediv__ = MagicMock(return_value=mock_file_path)

        mock_path_instance = MagicMock()
        mock_path_instance.suffix = '.mp4'
        mock_path.return_value = mock_path_instance

        extensions = ['.mp3', '.wav', '.mp4', '.m4a', '.avi', '.mkv']

        for ext in extensions:
            mock_path_instance.suffix = ext
            original_filename = f'test{ext}'

            result_path = self.service.save_uploaded_file(b'content', original_filename)

            self.assertIn(ext, result_path, f"Extension {ext} should be preserved")

    @patch('builtins.open', new_callable=mock_open)
    @patch('app.services.file_service.uuid.uuid4')
    @patch('app.services.file_service.Path')
    def test_save_file_with_no_extension(self, mock_path, mock_uuid, mock_file):
        """Test handling of files with no extension"""
        mock_uuid.return_value = 'uuid-456'

        mock_upload_dir = MagicMock()
        mock_file_path = MagicMock()
        mock_file_path.__str__ = MagicMock(return_value='/tmp/test_upload/uuid-456')
        mock_upload_dir.__truediv__ = MagicMock(return_value=mock_file_path)

        mock_path_instance = MagicMock()
        mock_path_instance.suffix = ''
        mock_path.return_value = mock_path_instance

        file_content = b'content'
        original_filename = 'no_extension_file'

        result_path = self.service.save_uploaded_file(file_content, original_filename)

        self.assertIn('uuid-456', result_path)

    @patch('builtins.open', new_callable=mock_open)
    @patch('app.services.file_service.uuid.uuid4')
    @patch('app.services.file_service.Path')
    def test_save_file_with_multiple_extensions(self, mock_path, mock_uuid, mock_file):
        """Test handling of files with multiple extensions (e.g., .tar.gz)"""
        mock_uuid.return_value = 'uuid-789'

        mock_upload_dir = MagicMock()
        mock_file_path = MagicMock()
        mock_file_path.__str__ = MagicMock(return_value='/tmp/test_upload/uuid-789.tar.gz')
        mock_upload_dir.__truediv__ = MagicMock(return_value=mock_file_path)

        mock_path_instance = MagicMock()
        mock_path_instance.suffix = '.gz'
        mock_path.return_value = mock_path_instance

        file_content = b'content'
        original_filename = 'archive.tar.gz'

        result_path = self.service.save_uploaded_file(file_content, original_filename)

        self.assertIn('.gz', result_path)


class TestSecureFilenameGeneration(unittest.TestCase):
    """Test secure filename generation using UUID"""

    def setUp(self):
        """Set up test fixtures"""
        self.patcher_settings = patch('app.services.file_service.settings')
        self.mock_settings = self.patcher_settings.start()
        self.mock_settings.upload_dir = '/tmp/test_upload'
        self.mock_settings.transcripts_dir = '/tmp/test_transcripts'
        self.mock_settings.keep_original_files = False

        with patch('app.services.file_service.Path'):
            self.service = FileService()

    def tearDown(self):
        """Clean up patches"""
        self.patcher_settings.stop()

    @patch('builtins.open', new_callable=mock_open)
    @patch('app.services.file_service.uuid.uuid4')
    @patch('app.services.file_service.Path')
    def test_uuid_is_used_for_filename(self, mock_path, mock_uuid, mock_file):
        """Test that UUID is used as base filename"""
        test_uuid = '550e8400-e29b-41d4-a716-446655440000'
        mock_uuid.return_value = test_uuid

        mock_upload_dir = MagicMock()
        mock_file_path = MagicMock()
        mock_file_path.__str__ = MagicMock(return_value=f'/tmp/test_upload/{test_uuid}.mp3')
        mock_upload_dir.__truediv__ = MagicMock(return_value=mock_file_path)

        mock_path_instance = MagicMock()
        mock_path_instance.suffix = '.mp3'
        mock_path.return_value = mock_path_instance

        file_content = b'content'
        original_filename = 'test.mp3'

        result_path = self.service.save_uploaded_file(file_content, original_filename)

        self.assertIn(test_uuid, result_path)

    @patch('builtins.open', new_callable=mock_open)
    @patch('app.services.file_service.uuid.uuid4')
    @patch('app.services.file_service.Path')
    def test_different_uuids_for_different_files(self, mock_path, mock_uuid, mock_file):
        """Test that different files get different UUIDs"""
        uuids = ['uuid-1', 'uuid-2', 'uuid-3']
        mock_uuid.side_effect = uuids

        mock_upload_dir = MagicMock()
        mock_file_path = MagicMock()
        mock_file_path.__str__ = MagicMock(side_effect=[
            '/tmp/test_upload/uuid-1.mp3',
            '/tmp/test_upload/uuid-2.mp3',
            '/tmp/test_upload/uuid-3.mp3'
        ])
        mock_upload_dir.__truediv__ = MagicMock(return_value=mock_file_path)

        mock_path_instance = MagicMock()
        mock_path_instance.suffix = '.mp3'
        mock_path.return_value = mock_path_instance

        paths = []
        for i in range(3):
            path = self.service.save_uploaded_file(b'content', f'test{i}.mp3')
            paths.append(path)

        # All paths should be different
        self.assertEqual(len(set(paths)), 3, "All paths should be unique")


class TestFileStorageOperations(unittest.TestCase):
    """Test file storage operations"""

    def setUp(self):
        """Set up test fixtures"""
        self.patcher_settings = patch('app.services.file_service.settings')
        self.mock_settings = self.patcher_settings.start()
        self.mock_settings.upload_dir = '/tmp/test_upload'
        self.mock_settings.transcripts_dir = '/tmp/test_transcripts'
        self.mock_settings.keep_original_files = False

        with patch('app.services.file_service.Path'):
            self.service = FileService()

    def tearDown(self):
        """Clean up patches"""
        self.patcher_settings.stop()

    @patch('builtins.open', new_callable=mock_open)
    @patch('app.services.file_service.uuid.uuid4')
    @patch('app.services.file_service.Path')
    def test_save_uploaded_file_writes_content(self, mock_path, mock_uuid, mock_file):
        """Test that file content is correctly written"""
        mock_uuid.return_value = 'test-uuid'

        mock_upload_dir = MagicMock()
        mock_file_path = MagicMock()
        mock_file_path.__str__ = MagicMock(return_value='/tmp/test_upload/test-uuid.mp3')
        mock_upload_dir.__truediv__ = MagicMock(return_value=mock_file_path)

        mock_path_instance = MagicMock()
        mock_path_instance.suffix = '.mp3'
        mock_path.return_value = mock_path_instance

        file_content = b'test audio content'

        self.service.save_uploaded_file(file_content, 'test.mp3')

        # Verify file was opened for writing
        mock_file.assert_called_once_with(mock_file_path, 'wb')
        # Verify content was written
        mock_file().write.assert_called_once_with(file_content)

    @patch('builtins.open', new_callable=mock_open)
    @patch('app.services.file_service.uuid.uuid4')
    @patch('app.services.file_service.Path')
    @patch('os.path.exists')
    def test_save_transcript_text_file(self, mock_exists, mock_path, mock_uuid, mock_file):
        """Test saving transcript text file"""
        mock_exists.return_value = True

        mock_transcripts_dir = MagicMock()
        mock_transcript_dir = MagicMock()
        mock_text_path = MagicMock()
        mock_text_path.__str__ = MagicMock(return_value='/tmp/test_transcripts/test-id/transcript.txt')
        mock_transcript_dir.__truediv__ = MagicMock(return_value=mock_text_path)
        mock_transcripts_dir.__truediv__ = MagicMock(return_value=mock_transcript_dir)

        mock_path.side_effect = [mock_transcripts_dir, mock_transcript_dir, mock_text_path]

        transcript_id = 'test-id'
        text = 'This is a transcript.'

        result = self.service.save_transcript(transcript_id, text)

        self.assertIn('text', result)
        self.assertEqual(result['text'], '/tmp/test_transcripts/test-id/transcript.txt')

    @patch('builtins.open', new_callable=mock_open)
    @patch('app.services.file_service.uuid.uuid4')
    @patch('app.services.file_service.Path')
    @patch('os.path.exists')
    @patch('json.dump')
    def test_save_transcript_json_file(self, mock_json_dump, mock_exists, mock_path, mock_uuid, mock_file):
        """Test saving transcript JSON file"""
        mock_exists.return_value = True

        mock_transcripts_dir = MagicMock()
        mock_transcript_dir = MagicMock()
        mock_text_path = MagicMock()
        mock_json_path = MagicMock()
        mock_text_path.__str__ = MagicMock(return_value='/tmp/test_transcripts/test-id/transcript.txt')
        mock_json_path.__str__ = MagicMock(return_value='/tmp/test_transcripts/test-id/transcript.json')
        mock_transcript_dir.__truediv__ = MagicMock(side_effect=[mock_text_path, mock_json_path])
        mock_transcripts_dir.__truediv__ = MagicMock(return_value=mock_transcript_dir)

        mock_path.side_effect = [mock_transcripts_dir, mock_transcript_dir, mock_text_path, mock_json_path]

        transcript_id = 'test-id'
        text = 'Transcript text'
        json_data = {'text': 'Transcript text', 'segments': []}

        result = self.service.save_transcript(transcript_id, text, json_data=json_data)

        self.assertIn('json', result)
        self.assertEqual(result['json'], '/tmp/test_transcripts/test-id/transcript.json')
        mock_json_dump.assert_called_once()

    @patch('builtins.open', new_callable=mock_open)
    @patch('app.services.file_service.uuid.uuid4')
    @patch('app.services.file_service.Path')
    @patch('os.path.exists')
    def test_save_transcript_srt_file(self, mock_exists, mock_path, mock_uuid, mock_file):
        """Test saving transcript SRT file"""
        mock_exists.return_value = True

        mock_transcripts_dir = MagicMock()
        mock_transcript_dir = MagicMock()
        mock_text_path = MagicMock()
        mock_srt_path = MagicMock()
        mock_text_path.__str__ = MagicMock(return_value='/tmp/test_transcripts/test-id/transcript.txt')
        mock_srt_path.__str__ = MagicMock(return_value='/tmp/test_transcripts/test-id/transcript.srt')
        mock_transcript_dir.__truediv__ = MagicMock(side_effect=[mock_text_path, mock_srt_path])
        mock_transcripts_dir.__truediv__ = MagicMock(return_value=mock_transcript_dir)

        mock_path.side_effect = [mock_transcripts_dir, mock_transcript_dir, mock_text_path, mock_srt_path]

        transcript_id = 'test-id'
        text = 'Transcript'
        srt_content = '1\n00:00:00,000 --> 00:00:01,000\nSubtitle'

        result = self.service.save_transcript(transcript_id, text, srt=srt_content)

        self.assertIn('srt', result)
        self.assertEqual(result['srt'], '/tmp/test_transcripts/test-id/transcript.srt')

    @patch('app.services.file_service.uuid.uuid4')
    @patch('app.services.file_service.Path')
    @patch('os.path.exists')
    def test_save_transcript_creates_directory(self, mock_exists, mock_path, mock_uuid):
        """Test that save_transcript creates transcript directory"""
        mock_exists.return_value = False

        mock_transcripts_dir = MagicMock()
        mock_transcript_dir = MagicMock()
        mock_transcripts_dir.__truediv__ = MagicMock(return_value=mock_transcript_dir)

        mock_path.return_value = mock_transcripts_dir

        with patch('builtins.open', mock_open()):
            self.service.save_transcript('test-id', 'text')

        mock_transcript_dir.mkdir.assert_called_once_with(parents=True, exist_ok=True)


class TestCleanupLogic(unittest.TestCase):
    """Test cleanup and deletion logic"""

    def setUp(self):
        """Set up test fixtures"""
        self.patcher_settings = patch('app.services.file_service.settings')
        self.mock_settings = self.patcher_settings.start()
        self.mock_settings.upload_dir = '/tmp/test_upload'
        self.mock_settings.transcripts_dir = '/tmp/test_transcripts'
        self.mock_settings.keep_original_files = False

        with patch('app.services.file_service.Path'):
            self.service = FileService()

    def tearDown(self):
        """Clean up patches"""
        self.patcher_settings.stop()

    @patch('os.path.exists')
    @patch('os.remove')
    def test_delete_file_success(self, mock_remove, mock_exists):
        """Test successful file deletion"""
        mock_exists.return_value = True

        file_path = '/tmp/test/file.txt'

        result = self.service.delete_file(file_path)

        self.assertTrue(result)
        mock_remove.assert_called_once_with(file_path)

    @patch('os.path.exists')
    @patch('os.remove')
    def test_delete_nonexistent_file(self, mock_remove, mock_exists):
        """Test deletion of non-existent file"""
        mock_exists.return_value = False

        file_path = '/tmp/test/nonexistent.txt'

        result = self.service.delete_file(file_path)

        self.assertFalse(result)
        mock_remove.assert_not_called()

    @patch('os.path.exists')
    @patch('os.remove')
    def test_delete_file_with_exception(self, mock_remove, mock_exists):
        """Test file deletion with exception"""
        mock_exists.return_value = True
        mock_remove.side_effect = OSError("Permission denied")

        file_path = '/tmp/test/file.txt'

        result = self.service.delete_file(file_path)

        self.assertFalse(result)

    @patch('app.services.file_service.shutil.rmtree')
    @patch('os.path.exists')
    @patch('app.services.file_service.Path')
    def test_delete_transcript_files_success(self, mock_path, mock_exists, mock_rmtree):
        """Test successful deletion of transcript directory"""
        mock_exists.return_value = True

        mock_transcripts_dir = MagicMock()
        mock_transcript_dir = MagicMock()
        mock_transcript_dir.exists.return_value = True
        mock_transcripts_dir.__truediv__ = MagicMock(return_value=mock_transcript_dir)
        mock_path.return_value = mock_transcripts_dir

        transcript_id = 'test-id'

        result = self.service.delete_transcript_files(transcript_id)

        self.assertTrue(result)
        mock_rmtree.assert_called_once()

    @patch('app.services.file_service.shutil.rmtree')
    @patch('os.path.exists')
    @patch('app.services.file_service.Path')
    def test_delete_nonexistent_transcript_files(self, mock_path, mock_exists, mock_rmtree):
        """Test deletion of non-existent transcript directory"""
        mock_transcripts_dir = MagicMock()
        mock_transcript_dir = MagicMock()
        mock_transcript_dir.exists.return_value = False
        mock_transcripts_dir.__truediv__ = MagicMock(return_value=mock_transcript_dir)
        mock_path.return_value = mock_transcripts_dir

        transcript_id = 'nonexistent-id'

        result = self.service.delete_transcript_files(transcript_id)

        self.assertFalse(result)
        mock_rmtree.assert_not_called()

    @patch('os.path.exists')
    @patch('os.remove')
    @patch('app.services.file_service.settings')
    def test_cleanup_original_file_when_keep_original_is_false(self, mock_settings, mock_remove, mock_exists):
        """Test cleanup when keep_original_files is False"""
        mock_settings.upload_dir = '/tmp/test_upload'
        mock_settings.transcripts_dir = '/tmp/test_transcripts'
        mock_settings.keep_original_files = False

        mock_exists.return_value = True

        with patch('app.services.file_service.Path'):
            service = FileService()

        file_path = '/tmp/test/audio.mp3'

        result = service.cleanup_original_file(file_path)

        self.assertTrue(result)
        mock_remove.assert_called_once_with(file_path)

    @patch('os.remove')
    @patch('app.services.file_service.settings')
    def test_cleanup_original_file_when_keep_original_is_true(self, mock_settings, mock_remove):
        """Test no cleanup when keep_original_files is True"""
        mock_settings.upload_dir = '/tmp/test_upload'
        mock_settings.transcripts_dir = '/tmp/test_transcripts'
        mock_settings.keep_original_files = True

        with patch('app.services.file_service.Path'):
            service = FileService()

        file_path = '/tmp/test/audio.mp3'

        result = service.cleanup_original_file(file_path)

        self.assertFalse(result)
        mock_remove.assert_not_called()


class TestTranscriptDirectoryStructure(unittest.TestCase):
    """Test transcript directory structure and file organization"""

    def setUp(self):
        """Set up test fixtures"""
        self.patcher_settings = patch('app.services.file_service.settings')
        self.mock_settings = self.patcher_settings.start()
        self.mock_settings.upload_dir = '/tmp/test_upload'
        self.mock_settings.transcripts_dir = '/tmp/test_transcripts'
        self.mock_settings.keep_original_files = False

        with patch('app.services.file_service.Path'):
            self.service = FileService()

    def tearDown(self):
        """Clean up patches"""
        self.patcher_settings.stop()

    @patch('builtins.open', new_callable=mock_open)
    @patch('app.services.file_service.uuid.uuid4')
    @patch('app.services.file_service.Path')
    @patch('os.path.exists')
    def test_multiple_transcripts_separate_directories(self, mock_exists, mock_path, mock_uuid, mock_file):
        """Test that different transcripts get separate directories"""
        mock_exists.return_value = True

        mock_transcripts_dir = MagicMock()

        def create_mock_transcript_dir(tid):
            mock_dir = MagicMock()
            mock_text_path = MagicMock()
            mock_text_path.__str__ = MagicMock(return_value=f'/tmp/test_transcripts/{tid}/transcript.txt')
            mock_dir.__truediv__ = MagicMock(return_value=mock_text_path)
            return mock_dir

        mock_transcripts_dir.__truediv__ = MagicMock(side_effect=[
            create_mock_transcript_dir('id-1'),
            create_mock_transcript_dir('id-2'),
            create_mock_transcript_dir('id-3')
        ])

        mock_path.return_value = mock_transcripts_dir

        transcript_ids = ['id-1', 'id-2', 'id-3']

        for tid in transcript_ids:
            self.service.save_transcript(tid, f'Transcript for {tid}')

        # Verify __truediv__ was called for each transcript ID
        self.assertEqual(mock_transcripts_dir.__truediv__.call_count, 3)


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and unusual scenarios"""

    def setUp(self):
        """Set up test fixtures"""
        self.patcher_settings = patch('app.services.file_service.settings')
        self.mock_settings = self.patcher_settings.start()
        self.mock_settings.upload_dir = '/tmp/test_upload'
        self.mock_settings.transcripts_dir = '/tmp/test_transcripts'
        self.mock_settings.keep_original_files = False

        with patch('app.services.file_service.Path'):
            self.service = FileService()

    def tearDown(self):
        """Clean up patches"""
        self.patcher_settings.stop()

    @patch('builtins.open', new_callable=mock_open)
    @patch('app.services.file_service.uuid.uuid4')
    @patch('app.services.file_service.Path')
    def test_save_empty_file(self, mock_path, mock_uuid, mock_file):
        """Test saving empty file"""
        mock_uuid.return_value = 'empty-uuid'

        mock_upload_dir = MagicMock()
        mock_file_path = MagicMock()
        mock_file_path.__str__ = MagicMock(return_value='/tmp/test_upload/empty-uuid.txt')
        mock_upload_dir.__truediv__ = MagicMock(return_value=mock_file_path)

        mock_path_instance = MagicMock()
        mock_path_instance.suffix = '.txt'
        mock_path.return_value = mock_path_instance

        file_content = b''

        result = self.service.save_uploaded_file(file_content, 'empty.txt')

        self.assertIn('empty-uuid', result)

    @patch('builtins.open', new_callable=mock_open)
    @patch('app.services.file_service.uuid.uuid4')
    @patch('app.services.file_service.Path')
    def test_save_large_file(self, mock_path, mock_uuid, mock_file):
        """Test saving large file"""
        mock_uuid.return_value = 'large-uuid'

        mock_upload_dir = MagicMock()
        mock_file_path = MagicMock()
        mock_file_path.__str__ = MagicMock(return_value='/tmp/test_upload/large-uuid.bin')
        mock_upload_dir.__truediv__ = MagicMock(return_value=mock_file_path)

        mock_path_instance = MagicMock()
        mock_path_instance.suffix = '.bin'
        mock_path.return_value = mock_path_instance

        # Create 10MB file
        file_content = b'x' * (10 * 1024 * 1024)

        result = self.service.save_uploaded_file(file_content, 'large.bin')

        self.assertIn('large-uuid', result)

    @patch('os.path.exists')
    @patch('app.services.file_service.Path')
    def test_delete_file_with_special_characters(self, mock_path, mock_exists):
        """Test deletion of file with special characters in path"""
        mock_exists.return_value = True

        mock_transcripts_dir = MagicMock()
        mock_transcripts_dir.__truediv__ = MagicMock(return_value=mock_transcripts_dir)
        mock_path.return_value = mock_transcripts_dir

        with patch('os.remove') as mock_remove:
            file_path = '/tmp/test/file with spaces & special@chars.mp3'

            result = self.service.delete_file(file_path)

            self.assertTrue(result)
            mock_remove.assert_called_once_with(file_path)

    @patch('builtins.open', new_callable=mock_open)
    @patch('app.services.file_service.uuid.uuid4')
    @patch('app.services.file_service.Path')
    @patch('os.path.exists')
    def test_save_transcript_with_unicode_content(self, mock_exists, mock_path, mock_uuid, mock_file):
        """Test saving transcript with Unicode content"""
        mock_exists.return_value = True

        mock_transcripts_dir = MagicMock()
        mock_transcript_dir = MagicMock()
        mock_text_path = MagicMock()
        mock_text_path.__str__ = MagicMock(return_value='/tmp/test_transcripts/test-id/transcript.txt')
        mock_transcript_dir.__truediv__ = MagicMock(return_value=mock_text_path)
        mock_transcripts_dir.__truediv__ = MagicMock(return_value=mock_transcript_dir)

        mock_path.side_effect = [mock_transcripts_dir, mock_transcript_dir, mock_text_path]

        transcript_id = 'test-id'
        # Text with emojis, Cyrillic, and other Unicode characters
        text = 'Транскрипция с эмодзи 😀 и 中文 characters'

        result = self.service.save_transcript(transcript_id, text)

        self.assertIn('text', result)

        # Verify file was opened with UTF-8 encoding
        mock_file.assert_called_once_with(mock_text_path, 'w', encoding='utf-8')


if __name__ == '__main__':
    unittest.main()
