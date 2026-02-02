"""
Unit tests for FileService

Tests use actual temporary directories and real file operations
instead of complex mocking for more reliable testing.
"""

import unittest
import tempfile
import os
import shutil
import json
from pathlib import Path
from unittest.mock import patch

from app.services.file_service import FileService


class TestFileServiceInitialization(unittest.TestCase):
    """Test FileService initialization and directory setup"""

    def setUp(self):
        """Create temporary directories for testing"""
        self.test_dir = tempfile.mkdtemp()
        self.upload_dir = os.path.join(self.test_dir, 'upload')
        self.transcripts_dir = os.path.join(self.test_dir, 'transcripts')

    def tearDown(self):
        """Clean up temporary directory"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    @patch('app.services.file_service.settings')
    def test_initialization_creates_directories(self, mock_settings):
        """Test that initialization creates upload and transcripts directories"""
        mock_settings.upload_dir = self.upload_dir
        mock_settings.transcripts_dir = self.transcripts_dir
        mock_settings.keep_original_files = False

        service = FileService()

        self.assertTrue(os.path.exists(self.upload_dir))
        self.assertTrue(os.path.exists(self.transcripts_dir))

    @patch('app.services.file_service.settings')
    def test_initialization_stores_configuration(self, mock_settings):
        """Test that initialization stores configuration correctly"""
        mock_settings.upload_dir = self.upload_dir
        mock_settings.transcripts_dir = self.transcripts_dir
        mock_settings.keep_original_files = True

        service = FileService()

        self.assertTrue(service.keep_original)


class TestFileValidation(unittest.TestCase):
    """Test file validation logic"""

    def setUp(self):
        """Create temporary directories for testing"""
        self.test_dir = tempfile.mkdtemp()
        self.upload_dir = os.path.join(self.test_dir, 'upload')
        self.transcripts_dir = os.path.join(self.test_dir, 'transcripts')
        os.makedirs(self.upload_dir)
        os.makedirs(self.transcripts_dir)

    def tearDown(self):
        """Clean up temporary directory"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    @patch('app.services.file_service.settings')
    def test_save_file_preserves_original_extension(self, mock_settings):
        """Test that file extension is preserved from original filename"""
        mock_settings.upload_dir = self.upload_dir
        mock_settings.transcripts_dir = self.transcripts_dir
        mock_settings.keep_original_files = False

        service = FileService()

        extensions = ['.mp3', '.wav', '.mp4', '.m4a', '.avi', '.mkv']

        for ext in extensions:
            original_filename = f'test{ext}'
            file_content = b'test content'

            result_path = service.save_uploaded_file(file_content, original_filename)

            self.assertTrue(result_path.endswith(ext), f"Extension {ext} should be preserved")
            self.assertTrue(os.path.exists(result_path), f"File should exist at {result_path}")

    @patch('app.services.file_service.settings')
    def test_save_file_with_no_extension(self, mock_settings):
        """Test handling of files with no extension"""
        mock_settings.upload_dir = self.upload_dir
        mock_settings.transcripts_dir = self.transcripts_dir
        mock_settings.keep_original_files = False

        service = FileService()

        file_content = b'content'
        original_filename = 'no_extension_file'

        result_path = service.save_uploaded_file(file_content, original_filename)

        self.assertTrue(os.path.exists(result_path))
        # File should be saved with UUID only (no extension)
        # Check that there's no extension in the saved path
        filename = os.path.basename(result_path)
        # Filename should be a UUID with no dots (except UUID dashes)
        self.assertNotIn('.', filename)

    @patch('app.services.file_service.settings')
    def test_save_file_with_multiple_extensions(self, mock_settings):
        """Test handling of files with multiple extensions (e.g., .tar.gz)"""
        mock_settings.upload_dir = self.upload_dir
        mock_settings.transcripts_dir = self.transcripts_dir
        mock_settings.keep_original_files = False

        service = FileService()

        file_content = b'content'
        original_filename = 'archive.tar.gz'

        result_path = service.save_uploaded_file(file_content, original_filename)

        # Should preserve the last extension
        self.assertTrue(result_path.endswith('.gz'))
        self.assertTrue(os.path.exists(result_path))

    @patch('app.services.file_service.settings')
    def test_save_uploaded_file_generates_unique_filename(self, mock_settings):
        """Test that unique filenames are generated using UUID"""
        mock_settings.upload_dir = self.upload_dir
        mock_settings.transcripts_dir = self.transcripts_dir
        mock_settings.keep_original_files = False

        service = FileService()

        file_content = b'audio content'
        original_filename = 'test.wav'

        result_path = service.save_uploaded_file(file_content, original_filename)

        # Path should contain UUID (36 hex chars with dashes)
        filename = os.path.basename(result_path)
        uuid_part = filename.replace('.wav', '')
        self.assertEqual(len(uuid_part), 36)  # UUID length

    @patch('app.services.file_service.settings')
    def test_save_uploaded_file_with_extension(self, mock_settings):
        """Test saving uploaded file with correct extension"""
        mock_settings.upload_dir = self.upload_dir
        mock_settings.transcripts_dir = self.transcripts_dir
        mock_settings.keep_original_files = False

        service = FileService()

        file_content = b'fake audio content'
        original_filename = 'audio.mp3'

        result_path = service.save_uploaded_file(file_content, original_filename)

        self.assertTrue(result_path.endswith('.mp3'))
        self.assertTrue(os.path.exists(result_path))


class TestSecureFilenameGeneration(unittest.TestCase):
    """Test secure filename generation using UUID"""

    def setUp(self):
        """Create temporary directories for testing"""
        self.test_dir = tempfile.mkdtemp()
        self.upload_dir = os.path.join(self.test_dir, 'upload')
        self.transcripts_dir = os.path.join(self.test_dir, 'transcripts')
        os.makedirs(self.upload_dir)
        os.makedirs(self.transcripts_dir)

    def tearDown(self):
        """Clean up temporary directory"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    @patch('app.services.file_service.settings')
    def test_uuid_is_used_for_filename(self, mock_settings):
        """Test that UUID is used as base filename"""
        mock_settings.upload_dir = self.upload_dir
        mock_settings.transcripts_dir = self.transcripts_dir
        mock_settings.keep_original_files = False

        service = FileService()

        file_content = b'content'
        original_filename = 'test.mp3'

        result_path = service.save_uploaded_file(file_content, original_filename)

        filename = os.path.basename(result_path)
        uuid_part = filename.replace('.mp3', '')
        # UUID should be 36 characters (format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx)
        self.assertEqual(len(uuid_part), 36)
        self.assertEqual(uuid_part.count('-'), 4)

    @patch('app.services.file_service.settings')
    def test_different_uuids_for_different_files(self, mock_settings):
        """Test that different files get different UUIDs"""
        mock_settings.upload_dir = self.upload_dir
        mock_settings.transcripts_dir = self.transcripts_dir
        mock_settings.keep_original_files = False

        service = FileService()

        paths = []
        for i in range(3):
            path = service.save_uploaded_file(b'content', f'test{i}.mp3')
            paths.append(path)

        # All paths should be different
        self.assertEqual(len(set(paths)), 3, "All paths should be unique")


class TestFileStorageOperations(unittest.TestCase):
    """Test file storage operations"""

    def setUp(self):
        """Create temporary directories for testing"""
        self.test_dir = tempfile.mkdtemp()
        self.upload_dir = os.path.join(self.test_dir, 'upload')
        self.transcripts_dir = os.path.join(self.test_dir, 'transcripts')
        os.makedirs(self.upload_dir)
        os.makedirs(self.transcripts_dir)

    def tearDown(self):
        """Clean up temporary directory"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    @patch('app.services.file_service.settings')
    def test_save_uploaded_file_writes_content(self, mock_settings):
        """Test that file content is correctly written"""
        mock_settings.upload_dir = self.upload_dir
        mock_settings.transcripts_dir = self.transcripts_dir
        mock_settings.keep_original_files = False

        service = FileService()

        file_content = b'test audio content'

        result_path = service.save_uploaded_file(file_content, 'test.mp3')

        # Verify file exists and has correct content
        self.assertTrue(os.path.exists(result_path))
        with open(result_path, 'rb') as f:
            saved_content = f.read()
        self.assertEqual(saved_content, file_content)

    @patch('app.services.file_service.settings')
    def test_save_transcript_text_file(self, mock_settings):
        """Test saving transcript text file"""
        mock_settings.upload_dir = self.upload_dir
        mock_settings.transcripts_dir = self.transcripts_dir
        mock_settings.keep_original_files = False

        service = FileService()

        transcript_id = 'test-id'
        text = 'This is a transcript.'

        result = service.save_transcript(transcript_id, text)

        self.assertIn('text', result)
        self.assertTrue(os.path.exists(result['text']))
        self.assertTrue(result['text'].endswith('transcript.txt'))

        with open(result['text'], 'r', encoding='utf-8') as f:
            saved_text = f.read()
        self.assertEqual(saved_text, text)

    @patch('app.services.file_service.settings')
    def test_save_transcript_json_file(self, mock_settings):
        """Test saving transcript JSON file"""
        mock_settings.upload_dir = self.upload_dir
        mock_settings.transcripts_dir = self.transcripts_dir
        mock_settings.keep_original_files = False

        service = FileService()

        transcript_id = 'test-id'
        text = 'Transcript text'
        json_data = {'text': 'Transcript text', 'segments': []}

        result = service.save_transcript(transcript_id, text, json_data=json_data)

        self.assertIn('json', result)
        self.assertTrue(os.path.exists(result['json']))

        with open(result['json'], 'r', encoding='utf-8') as f:
            saved_json = json.load(f)
        self.assertEqual(saved_json, json_data)

    @patch('app.services.file_service.settings')
    def test_save_transcript_srt_file(self, mock_settings):
        """Test saving transcript SRT file"""
        mock_settings.upload_dir = self.upload_dir
        mock_settings.transcripts_dir = self.transcripts_dir
        mock_settings.keep_original_files = False

        service = FileService()

        transcript_id = 'test-id'
        text = 'Transcript'
        srt_content = '1\n00:00:00,000 --> 00:00:01,000\nSubtitle'

        result = service.save_transcript(transcript_id, text, srt=srt_content)

        self.assertIn('srt', result)
        self.assertTrue(os.path.exists(result['srt']))

        with open(result['srt'], 'r', encoding='utf-8') as f:
            saved_srt = f.read()
        self.assertEqual(saved_srt, srt_content)

    @patch('app.services.file_service.settings')
    def test_save_transcript_creates_directory(self, mock_settings):
        """Test that save_transcript creates transcript directory"""
        mock_settings.upload_dir = self.upload_dir
        mock_settings.transcripts_dir = self.transcripts_dir
        mock_settings.keep_original_files = False

        service = FileService()

        transcript_id = 'test-id-new'
        text = 'text'

        result = service.save_transcript(transcript_id, text)

        # Directory should be created
        transcript_dir = os.path.join(self.transcripts_dir, transcript_id)
        self.assertTrue(os.path.exists(transcript_dir))


class TestCleanupLogic(unittest.TestCase):
    """Test cleanup and deletion logic"""

    def setUp(self):
        """Create temporary directories for testing"""
        self.test_dir = tempfile.mkdtemp()
        self.upload_dir = os.path.join(self.test_dir, 'upload')
        self.transcripts_dir = os.path.join(self.test_dir, 'transcripts')
        os.makedirs(self.upload_dir)
        os.makedirs(self.transcripts_dir)

    def tearDown(self):
        """Clean up temporary directory"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    @patch('app.services.file_service.settings')
    def test_delete_file_success(self, mock_settings):
        """Test successful file deletion"""
        mock_settings.upload_dir = self.upload_dir
        mock_settings.transcripts_dir = self.transcripts_dir
        mock_settings.keep_original_files = False

        service = FileService()

        # Create a test file
        file_path = os.path.join(self.upload_dir, 'test_file.txt')
        with open(file_path, 'w') as f:
            f.write('test content')

        self.assertTrue(os.path.exists(file_path))

        result = service.delete_file(file_path)

        self.assertTrue(result)
        self.assertFalse(os.path.exists(file_path))

    @patch('app.services.file_service.settings')
    def test_delete_nonexistent_file(self, mock_settings):
        """Test deletion of non-existent file"""
        mock_settings.upload_dir = self.upload_dir
        mock_settings.transcripts_dir = self.transcripts_dir
        mock_settings.keep_original_files = False

        service = FileService()

        file_path = os.path.join(self.upload_dir, 'nonexistent.txt')

        result = service.delete_file(file_path)

        self.assertFalse(result)

    @patch('app.services.file_service.settings')
    def test_delete_file_with_exception(self, mock_settings):
        """Test file deletion with exception (directory instead of file)"""
        mock_settings.upload_dir = self.upload_dir
        mock_settings.transcripts_dir = self.transcripts_dir
        mock_settings.keep_original_files = False

        service = FileService()

        # Try to delete a directory (should fail gracefully)
        dir_path = os.path.join(self.upload_dir, 'test_dir')
        os.makedirs(dir_path)

        result = service.delete_file(dir_path)

        self.assertFalse(result)

    @patch('app.services.file_service.settings')
    def test_delete_transcript_files_success(self, mock_settings):
        """Test successful deletion of transcript directory"""
        mock_settings.upload_dir = self.upload_dir
        mock_settings.transcripts_dir = self.transcripts_dir
        mock_settings.keep_original_files = False

        service = FileService()

        transcript_id = 'test-id-delete'
        text = 'test transcript'

        # Create transcript files
        service.save_transcript(transcript_id, text)

        transcript_dir = os.path.join(self.transcripts_dir, transcript_id)
        self.assertTrue(os.path.exists(transcript_dir))

        result = service.delete_transcript_files(transcript_id)

        self.assertTrue(result)
        self.assertFalse(os.path.exists(transcript_dir))

    @patch('app.services.file_service.settings')
    def test_delete_nonexistent_transcript_files(self, mock_settings):
        """Test deletion of non-existent transcript directory"""
        mock_settings.upload_dir = self.upload_dir
        mock_settings.transcripts_dir = self.transcripts_dir
        mock_settings.keep_original_files = False

        service = FileService()

        transcript_id = 'nonexistent-id'

        result = service.delete_transcript_files(transcript_id)

        self.assertFalse(result)

    @patch('app.services.file_service.settings')
    def test_cleanup_original_file_when_keep_original_is_false(self, mock_settings):
        """Test cleanup when keep_original_files is False"""
        mock_settings.upload_dir = self.upload_dir
        mock_settings.transcripts_dir = self.transcripts_dir
        mock_settings.keep_original_files = False

        service = FileService()

        # Create test file
        file_path = os.path.join(self.upload_dir, 'audio.mp3')
        with open(file_path, 'wb') as f:
            f.write(b'audio content')

        result = service.cleanup_original_file(file_path)

        self.assertTrue(result)
        self.assertFalse(os.path.exists(file_path))

    @patch('app.services.file_service.settings')
    def test_cleanup_original_file_when_keep_original_is_true(self, mock_settings):
        """Test no cleanup when keep_original_files is True"""
        mock_settings.upload_dir = self.upload_dir
        mock_settings.transcripts_dir = self.transcripts_dir
        mock_settings.keep_original_files = True

        service = FileService()

        # Create test file
        file_path = os.path.join(self.upload_dir, 'audio.mp3')
        with open(file_path, 'wb') as f:
            f.write(b'audio content')

        result = service.cleanup_original_file(file_path)

        self.assertFalse(result)
        self.assertTrue(os.path.exists(file_path))


class TestTranscriptDirectoryStructure(unittest.TestCase):
    """Test transcript directory structure and file organization"""

    def setUp(self):
        """Create temporary directories for testing"""
        self.test_dir = tempfile.mkdtemp()
        self.upload_dir = os.path.join(self.test_dir, 'upload')
        self.transcripts_dir = os.path.join(self.test_dir, 'transcripts')
        os.makedirs(self.upload_dir)
        os.makedirs(self.transcripts_dir)

    def tearDown(self):
        """Clean up temporary directory"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    @patch('app.services.file_service.settings')
    def test_multiple_transcripts_separate_directories(self, mock_settings):
        """Test that different transcripts get separate directories"""
        mock_settings.upload_dir = self.upload_dir
        mock_settings.transcripts_dir = self.transcripts_dir
        mock_settings.keep_original_files = False

        service = FileService()

        transcript_ids = ['id-1', 'id-2', 'id-3']

        for tid in transcript_ids:
            service.save_transcript(tid, f'Transcript for {tid}')

        # Each transcript should have its own directory
        for tid in transcript_ids:
            transcript_dir = os.path.join(self.transcripts_dir, tid)
            self.assertTrue(os.path.exists(transcript_dir), f"Directory for {tid} should exist")


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and unusual scenarios"""

    def setUp(self):
        """Create temporary directories for testing"""
        self.test_dir = tempfile.mkdtemp()
        self.upload_dir = os.path.join(self.test_dir, 'upload')
        self.transcripts_dir = os.path.join(self.test_dir, 'transcripts')
        os.makedirs(self.upload_dir)
        os.makedirs(self.transcripts_dir)

    def tearDown(self):
        """Clean up temporary directory"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    @patch('app.services.file_service.settings')
    def test_save_empty_file(self, mock_settings):
        """Test saving empty file"""
        mock_settings.upload_dir = self.upload_dir
        mock_settings.transcripts_dir = self.transcripts_dir
        mock_settings.keep_original_files = False

        service = FileService()

        file_content = b''

        result = service.save_uploaded_file(file_content, 'empty.txt')

        self.assertTrue(os.path.exists(result))
        with open(result, 'rb') as f:
            saved_content = f.read()
        self.assertEqual(saved_content, b'')

    @patch('app.services.file_service.settings')
    def test_save_large_file(self, mock_settings):
        """Test saving large file"""
        mock_settings.upload_dir = self.upload_dir
        mock_settings.transcripts_dir = self.transcripts_dir
        mock_settings.keep_original_files = False

        service = FileService()

        # Create 1MB file (reduced from 10MB for faster tests)
        file_content = b'x' * (1 * 1024 * 1024)

        result = service.save_uploaded_file(file_content, 'large.bin')

        self.assertTrue(os.path.exists(result))

        # Verify file size
        self.assertEqual(os.path.getsize(result), len(file_content))

    @patch('app.services.file_service.settings')
    def test_delete_file_with_special_characters(self, mock_settings):
        """Test deletion of file with special characters in path"""
        mock_settings.upload_dir = self.upload_dir
        mock_settings.transcripts_dir = self.transcripts_dir
        mock_settings.keep_original_files = False

        service = FileService()

        # Create file with special characters
        file_path = os.path.join(self.upload_dir, 'file with spaces & special@chars.mp3')
        with open(file_path, 'wb') as f:
            f.write(b'audio content')

        result = service.delete_file(file_path)

        self.assertTrue(result)
        self.assertFalse(os.path.exists(file_path))

    @patch('app.services.file_service.settings')
    def test_save_transcript_with_unicode_content(self, mock_settings):
        """Test saving transcript with Unicode content"""
        mock_settings.upload_dir = self.upload_dir
        mock_settings.transcripts_dir = self.transcripts_dir
        mock_settings.keep_original_files = False

        service = FileService()

        transcript_id = 'test-id'
        # Text with emojis, Cyrillic, and other Unicode characters
        text = 'Транскрипция с эмодзи 😀 и 中文 characters'

        result = service.save_transcript(transcript_id, text)

        self.assertIn('text', result)
        self.assertTrue(os.path.exists(result['text']))

        with open(result['text'], 'r', encoding='utf-8') as f:
            saved_text = f.read()
        self.assertEqual(saved_text, text)


if __name__ == '__main__':
    unittest.main()
