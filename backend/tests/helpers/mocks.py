"""
Mock helpers for STT backend testing.

This module provides configurable mock classes for external services
and APIs, making it easy to test different scenarios without real dependencies.
"""

from typing import Dict, Any, List, Optional, Callable, Union
from unittest.mock import Mock, AsyncMock, MagicMock
from datetime import datetime
from uuid import uuid4
import json


# =============================================================================
# Evolution API Mock
# =============================================================================

class MockEvolutionAPI:
    """
    Mock for Evolution Cloud.ru API (transcription service).

    Provides configurable mock responses for transcription operations.
    Can be set to return success, failure, or raise exceptions.

    Example:
        >>> mock = MockEvolutionAPI()
        >>> mock.set_transcription_result("Success transcription", status="completed")
        >>> result = mock.transcribe("audio.mp3")
        >>> result["text"]
        'Success transcription'

        >>> # Simulate failure
        >>> mock.set_error("API error")
        >>> mock.transcribe("audio.mp3")  # Raises exception
    """

    def __init__(self):
        """Initialize the mock with default success behavior."""
        self._transcription_result = {
            "text": "This is a mock transcription result.",
            "verbose_json": {
                "language": "english",
                "duration": 120.0,
                "words": [
                    {"word": "This", "start": 0.0, "end": 0.3},
                    {"word": "is", "start": 0.3, "end": 0.5},
                    {"word": "a", "start": 0.5, "end": 0.6},
                    {"word": "test", "start": 0.6, "end": 0.9}
                ]
            },
            "srt": "1\\n00:00:00,000 --> 00:00:00,900\\nThis is a test"
        }
        self._status = "completed"
        self._error = None
        self._call_count = 0
        self._last_request = None

        # Create mock methods
        self.transcribe = Mock(side_effect=self._transcribe)
        self.get_status = Mock(side_effect=self._get_status)
        self.get_transcript = Mock(side_effect=self._get_transcript)

    def set_transcription_result(
        self,
        text: str,
        status: str = "completed",
        duration: Optional[float] = None,
        language: str = "english"
    ) -> None:
        """
        Set the mock transcription result.

        Args:
            text: Transcription text
            status: Transcription status
            duration: Audio duration in seconds
            language: Language code
        """
        words = []
        for i, word in enumerate(text.split()):
            words.append({
                "word": word,
                "start": i * 0.5,
                "end": (i + 1) * 0.5,
                "confidence": 0.95
            })

        self._transcription_result = {
            "text": text,
            "verbose_json": {
                "language": language,
                "duration": duration or len(text.split()) * 0.5,
                "words": words
            },
            "srt": self._generate_srt(words)
        }
        self._status = status
        self._error = None

    def set_error(self, error_message: str, error_code: int = 500) -> None:
        """
        Set the mock to return an error.

        Args:
            error_message: Error message to return/raise
            error_code: HTTP error code
        """
        self._error = {
            "error": error_message,
            "code": error_code
        }

    def set_delay(self, delay_ms: int) -> None:
        """
        Add a delay to simulate slow API responses.

        Args:
            delay_ms: Delay in milliseconds
        """
        import time
        original_transcribe = self.transcribe.side_effect

        def slow_transcribe(*args, **kwargs):
            time.sleep(delay_ms / 1000)
            return original_transcribe(*args, **kwargs)

        self.transcribe.side_effect = slow_transcribe

    def get_call_count(self) -> int:
        """Get the number of times the mock was called."""
        return self._call_count

    def get_last_request(self) -> Optional[Dict[str, Any]]:
        """Get the last request data sent to the mock."""
        return self._last_request

    def reset(self) -> None:
        """Reset the mock to initial state."""
        self._call_count = 0
        self._last_request = None
        self._error = None

    def _transcribe(self, audio_file: str, **kwargs) -> Dict[str, Any]:
        """Internal transcribe method."""
        self._call_count += 1
        self._last_request = {"audio_file": audio_file, **kwargs}

        if self._error:
            raise Exception(self._error["error"])

        return self._transcription_result

    def _get_status(self, job_id: str) -> Dict[str, Any]:
        """Internal status check method."""
        if self._error:
            return {
                "status": "failed",
                "error": self._error["error"]
            }

        return {
            "status": self._status,
            "progress": 1.0 if self._status == "completed" else 0.5
        }

    def _get_transcript(self, transcript_id: str) -> Dict[str, Any]:
        """Internal get transcript method."""
        if self._error:
            raise Exception(self._error["error"])

        return {
            "id": transcript_id,
            **self._transcription_result
        }

    @staticmethod
    def _generate_srt(words: List[Dict[str, Any]]) -> str:
        """Generate SRT format from word timestamps."""
        return "\\n".join([
            f"{i+1}\\n00:00:{w['start']:06.3f} --> 00:00:{w['end']:06.3f}\\n{w['word']}"
            for i, w in enumerate(words)
        ])


# =============================================================================
# OpenAI/LLM Mock
# =============================================================================

class MockOpenAI:
    """
    Mock for OpenAI-compatible LLM APIs.

    Supports chat completions and embeddings. Can simulate various
    response scenarios including rate limiting, timeouts, and errors.

    Example:
        >>> mock = MockOpenAI()
        >>> mock.set_completion_response("This is a summary.")
        >>> response = mock.chat.completions.create(...)
        >>> response.choices[0].message.content
        'This is a summary.'
    """

    def __init__(self):
        """Initialize the mock with default responses."""
        self._completion_text = "This is a mock LLM response."
        self._embedding = [0.1] * 1536  # OpenAI embedding dimension
        self._usage_tokens = 100
        self._error = None
        self._rate_limit = False
        self._call_history = []

        # Create mock structure mimicking OpenAI client
        self.chat = Mock()
        self.chat.completions = Mock()
        self.chat.completions.create = Mock(side_effect=self._create_completion)

        self.embeddings = Mock()
        self.embeddings.create = Mock(side_effect=self._create_embedding)

    def set_completion_response(
        self,
        text: str,
        model: str = "gpt-3.5-turbo",
        tokens_used: int = 100
    ) -> None:
        """
        Set the mock completion response.

        Args:
            text: Response text
            model: Model name
            tokens_used: Number of tokens used
        """
        self._completion_text = text
        self._model = model
        self._usage_tokens = tokens_used
        self._error = None

    def set_embedding_response(
        self,
        embedding: Optional[List[float]] = None,
        dimension: int = 1536
    ) -> None:
        """
        Set the mock embedding response.

        Args:
            embedding: Embedding vector (auto-generated if None)
            dimension: Embedding dimension for auto-generation
        """
        self._embedding = embedding or [0.1] * dimension

    def set_rate_limit(self, enabled: bool = True) -> None:
        """
        Enable or disable rate limiting simulation.

        Args:
            enabled: Whether to simulate rate limits
        """
        self._rate_limit = enabled

    def set_error(self, error_type: str = "api_error") -> None:
        """
        Set the mock to return errors.

        Args:
            error_type: Type of error ('api_error', 'rate_limit', 'timeout')
        """
        self._error = error_type

    def get_call_history(self) -> List[Dict[str, Any]]:
        """Get history of all API calls made to the mock."""
        return self._call_history

    def reset(self) -> None:
        """Reset the mock to initial state."""
        self._call_history.clear()
        self._error = None
        self._rate_limit = False

    def _create_completion(self, **kwargs) -> Dict[str, Any]:
        """Internal completion creation method."""
        self._call_history.append({"type": "completion", **kwargs})

        if self._rate_limit:
            raise Exception("Rate limit exceeded")

        if self._error == "api_error":
            raise Exception("API error occurred")
        elif self._error == "timeout":
            raise TimeoutError("Request timed out")

        # Create response structure matching OpenAI API
        return {
            "id": f"chatcmpl-{uuid4()}",
            "object": "chat.completion",
            "created": int(datetime.now().timestamp()),
            "model": kwargs.get("model", self._model),
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": self._completion_text
                },
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": self._usage_tokens // 2,
                "completion_tokens": self._usage_tokens // 2,
                "total_tokens": self._usage_tokens
            }
        }

    def _create_embedding(self, **kwargs) -> Dict[str, Any]:
        """Internal embedding creation method."""
        self._call_history.append({"type": "embedding", **kwargs})

        if self._rate_limit:
            raise Exception("Rate limit exceeded")

        if self._error:
            raise Exception("API error")

        return {
            "object": "list",
            "data": [{
                "object": "embedding",
                "embedding": self._embedding,
                "index": 0
            }],
            "model": kwargs.get("model", "text-embedding-ada-002"),
            "usage": {
                "prompt_tokens": len(kwargs.get("input", [])),
                "total_tokens": len(kwargs.get("input", []))
            }
        }


# =============================================================================
# Qdrant Client Mock
# =============================================================================

class MockQdrantClient:
    """
    Mock for Qdrant vector database client.

    Simulates vector operations like search, upsert, and collection management.
    Can be configured to return specific search results or simulate errors.

    Example:
        >>> mock = MockQdrantClient()
        >>> mock.add_documents([
        ...     {"id": "1", "vector": [0.1, 0.2], "payload": {"text": "doc1"}}
        ... ])
        >>> results = mock.search(collection="test", query_vector=[0.1, 0.2])
        >>> len(results)
        1
    """

    def __init__(self):
        """Initialize the mock with empty collections."""
        self._collections: Dict[str, List[Dict[str, Any]]] = {}
        self._search_results: List[Dict[str, Any]] = []
        self._error = None

        # Create mock methods
        self.search = Mock(side_effect=self._search)
        self.upsert = Mock(side_effect=self._upsert)
        self.create_collection = Mock(side_effect=self._create_collection)
        self.delete_collection = Mock(side_effect=self._delete_collection)
        self.collection_exists = Mock(side_effect=self._collection_exists)
        self.get_collection = Mock(side_effect=self._get_collection)
        self.count = Mock(side_effect=self._count)
        self.delete = Mock(side_effect=self._delete)
        self.scroll = Mock(side_effect=self._scroll)

    def add_collection(self, name: str) -> None:
        """
        Add a collection to the mock.

        Args:
            name: Collection name
        """
        if name not in self._collections:
            self._collections[name] = []

    def add_documents(
        self,
        documents: List[Dict[str, Any]],
        collection: str = "test"
    ) -> None:
        """
        Add documents to a collection.

        Args:
            documents: List of documents with 'id', 'vector', and 'payload'
            collection: Collection name
        """
        if collection not in self._collections:
            self._collections[collection] = []

        self._collections[collection].extend(documents)

    def set_search_results(
        self,
        results: List[Dict[str, Any]]
    ) -> None:
        """
        Set fixed search results.

        Args:
            results: List of search result dicts
        """
        self._search_results = results

    def set_error(self, error_message: str) -> None:
        """
        Set the mock to return errors.

        Args:
            error_message: Error message
        """
        self._error = error_message

    def get_collections(self) -> List[str]:
        """Get list of collection names."""
        return list(self._collections.keys())

    def get_document_count(self, collection: str) -> int:
        """Get number of documents in a collection."""
        return len(self._collections.get(collection, []))

    def reset(self) -> None:
        """Reset the mock to initial state."""
        self._collections.clear()
        self._search_results.clear()
        self._error = None

    def _search(
        self,
        collection_name: str,
        query_vector: List[float],
        limit: int = 10,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """Internal search method."""
        if self._error:
            raise Exception(self._error)

        # Return fixed results if set
        if self._search_results:
            return self._search_results[:limit]

        # Otherwise return documents from collection
        if collection_name not in self._collections:
            return []

        documents = self._collections[collection_name][:limit]
        return [
            {
                "id": doc["id"],
                "score": 0.9,  # Mock score
                "payload": doc.get("payload", {})
            }
            for doc in documents
        ]

    def _upsert(self, collection_name: str, points: List[Any], **kwargs) -> Dict[str, Any]:
        """Internal upsert method."""
        if self._error:
            raise Exception(self._error)

        if collection_name not in self._collections:
            self._collections[collection_name] = []

        # Convert points to documents (simplified)
        for point in points:
            doc = {
                "id": getattr(point, "id", str(uuid4())),
                "vector": getattr(point, "vector", []),
                "payload": getattr(point, "payload", {})
            }
            self._collections[collection_name].append(doc)

        return {"status": "completed"}

    def _create_collection(self, collection_name: str, **kwargs) -> bool:
        """Internal collection creation method."""
        if self._error:
            raise Exception(self._error)

        if collection_name not in self._collections:
            self._collections[collection_name] = []

        return True

    def _delete_collection(self, collection_name: str) -> bool:
        """Internal collection deletion method."""
        if collection_name in self._collections:
            del self._collections[collection_name]
        return True

    def _collection_exists(self, collection_name: str) -> bool:
        """Internal collection exists check method."""
        return collection_name in self._collections

    def _get_collection(self, collection_name: str) -> Dict[str, Any]:
        """Internal get collection method."""
        if collection_name not in self._collections:
            raise Exception(f"Collection {collection_name} not found")

        return {
            "name": collection_name,
            "points_count": len(self._collections[collection_name])
        }

    def _count(self, collection_name: str, **kwargs) -> Dict[str, Any]:
        """Internal count method."""
        return {
            "count": len(self._collections.get(collection_name, []))
        }

    def _delete(self, collection_name: str, points_selector: Any, **kwargs) -> Dict[str, Any]:
        """Internal delete method."""
        if collection_name in self._collections:
            self._collections[collection_name].clear()
        return {"status": "completed"}

    def _scroll(self, collection_name: str, **kwargs) -> List[Dict[str, Any]]:
        """Internal scroll method."""
        return self._collections.get(collection_name, [])


# =============================================================================
# File Storage Mock
# =============================================================================

class MockFileStorage:
    """
    Mock for file storage operations.

    Simulates file upload, download, deletion, and metadata retrieval.
    Useful for testing file handling without actual disk I/O.

    Example:
        >>> mock = MockFileStorage()
        >>> path = mock.save_file("test.mp3", b"audio data")
        >>> assert mock.file_exists(path)
        >>> mock.delete_file(path)
    """

    def __init__(self):
        """Initialize the mock with empty storage."""
        self._files: Dict[str, bytes] = {}
        self._metadata: Dict[str, Dict[str, Any]] = {}
        self._save_error = False
        self._delete_error = False

        # Create mock methods
        self.save_file = Mock(side_effect=self._save_file)
        self.delete_file = Mock(side_effect=self._delete_file)
        self.file_exists = Mock(side_effect=self._file_exists)
        self.get_file = Mock(side_effect=self._get_file)
        self.get_file_size = Mock(side_effect=self._get_file_size)
        self.get_file_metadata = Mock(side_effect=self._get_file_metadata)

    def add_file(
        self,
        path: str,
        content: bytes,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Add a file to the mock storage.

        Args:
            path: File path
            content: File content
            metadata: Optional metadata
        """
        self._files[path] = content
        self._metadata[path] = metadata or {
            "size": len(content),
            "created_at": datetime.now().isoformat()
        }

    def set_save_error(self, enabled: bool = True) -> None:
        """
        Enable or disable save errors.

        Args:
            enabled: Whether to simulate save errors
        """
        self._save_error = enabled

    def set_delete_error(self, enabled: bool = True) -> None:
        """
        Enable or disable delete errors.

        Args:
            enabled: Whether to simulate delete errors
        """
        self._delete_error = enabled

    def get_all_files(self) -> List[str]:
        """Get list of all stored file paths."""
        return list(self._files.keys())

    def reset(self) -> None:
        """Reset the mock to initial state."""
        self._files.clear()
        self._metadata.clear()

    def _save_file(
        self,
        filename: str,
        content: bytes,
        **kwargs
    ) -> str:
        """Internal save file method."""
        if self._save_error:
            raise IOError("Failed to save file")

        path = f"/uploads/{filename}"
        self._files[path] = content
        self._metadata[path] = {
            "size": len(content),
            "filename": filename,
            "created_at": datetime.now().isoformat(),
            **kwargs
        }

        return path

    def _delete_file(self, path: str) -> bool:
        """Internal delete file method."""
        if self._delete_error:
            raise IOError("Failed to delete file")

        if path in self._files:
            del self._files[path]
            del self._metadata[path]
            return True

        return False

    def _file_exists(self, path: str) -> bool:
        """Internal file exists check method."""
        return path in self._files

    def _get_file(self, path: str) -> bytes:
        """Internal get file method."""
        if path not in self._files:
            raise FileNotFoundError(f"File not found: {path}")

        return self._files[path]

    def _get_file_size(self, path: str) -> int:
        """Internal get file size method."""
        if path not in self._files:
            raise FileNotFoundError(f"File not found: {path}")

        return len(self._files[path])

    def _get_file_metadata(self, path: str) -> Dict[str, Any]:
        """Internal get file metadata method."""
        if path not in self._metadata:
            raise FileNotFoundError(f"File not found: {path}")

        return self._metadata[path]


# =============================================================================
# Database Session Mock
# =============================================================================

class MockDatabaseSession:
    """
    Mock for SQLAlchemy database sessions.

    Provides a simple in-memory database for testing without
    requiring actual database connections.

    Example:
        >>> mock = MockDatabaseSession()
        >>> mock.add({"id": 1, "name": "test"})
        >>> result = mock.query(id=1)
        >>> result["name"]
        'test'
    """

    def __init__(self):
        """Initialize the mock with empty data store."""
        self._data: Dict[str, List[Dict[str, Any]]] = {}
        self._commits = 0
        self._rollbacks = 0

        # Create mock methods
        self.add = Mock(side_effect=self._add)
        self.commit = Mock(side_effect=self._commit)
        self.rollback = Mock(side_effect=self._rollback)
        self.query = Mock(side_effect=self._query)
        self.delete = Mock(side_effect=self._delete)
        self.refresh = Mock(side_effect=self._refresh)

    def add_table(self, table_name: str) -> None:
        """
        Add a table to the mock database.

        Args:
            table_name: Name of the table
        """
        if table_name not in self._data:
            self._data[table_name] = []

    def add_data(self, table_name: str, data: Dict[str, Any]) -> None:
        """
        Add data to a table.

        Args:
            table_name: Name of the table
            data: Data to add
        """
        if table_name not in self._data:
            self._data[table_name] = []

        self._data[table_name].append(data)

    def get_commits(self) -> int:
        """Get number of commits made."""
        return self._commits

    def get_rollbacks(self) -> int:
        """Get number of rollbacks made."""
        return self._rollbacks

    def reset(self) -> None:
        """Reset the mock to initial state."""
        self._data.clear()
        self._commits = 0
        self._rollbacks = 0

    def _add(self, obj: Any) -> None:
        """Internal add method."""
        # Convert object to dict if it's a model
        if hasattr(obj, '__table__'):
            table_name = obj.__table__.name
            if table_name not in self._data:
                self._data[table_name] = []

            data = {key: getattr(obj, key) for key in obj.__dict__.keys() if not key.startswith('_')}
            self._data[table_name].append(data)

    def _commit(self) -> None:
        """Internal commit method."""
        self._commits += 1

    def _rollback(self) -> None:
        """Internal rollback method."""
        self._rollbacks += 1

    def _query(self, **filters) -> List[Dict[str, Any]]:
        """Internal query method."""
        # Search across all tables
        results = []
        for table_name, data in self._data.items():
            for item in data:
                match = True
                for key, value in filters.items():
                    if item.get(key) != value:
                        match = False
                        break
                if match:
                    results.append(item)

        return results

    def _delete(self, obj: Any) -> None:
        """Internal delete method."""
        if hasattr(obj, '__table__'):
            table_name = obj.__table__.name
            if table_name in self._data:
                # Find and remove the object
                obj_id = getattr(obj, 'id', None)
                if obj_id is not None:
                    self._data[table_name] = [
                        item for item in self._data[table_name]
                        if item.get('id') != obj_id
                    ]

    def _refresh(self, obj: Any) -> None:
        """Internal refresh method."""
        # In a real mock, this would refresh from the "database"
        pass


# =============================================================================
# Async Mock Helpers
# =============================================================================

def create_async_mock(
    return_value: Any = None,
    side_effect: Optional[Callable] = None
) -> AsyncMock:
    """
    Create an async mock function.

    Args:
        return_value: Value to return
        side_effect: Side effect function

    Returns:
        AsyncMock object

    Example:
        >>> mock_func = create_async_mock(return_value={"status": "ok"})
        >>> await mock_func()
        {'status': 'ok'}
    """
    mock = AsyncMock()
    if return_value is not None:
        mock.return_value = return_value
    if side_effect is not None:
        mock.side_effect = side_effect
    return mock


def create_mock_context_manager(
    enter_result: Any = None,
    exit_exception: Optional[Exception] = None
) -> Mock:
    """
    Create a mock context manager.

    Args:
        enter_result: Value to return from __enter__
        exit_exception: Exception to raise from __exit__

    Returns:
        Mock object with __enter__ and __exit__ methods

    Example:
        >>> mock_cm = create_mock_context_manager(enter_result={"data": "test"})
        >>> with mock_cm as result:
        ...     print(result)
        {'data': 'test'}
    """
    mock = Mock()
    mock.__enter__ = Mock(return_value=enter_result)
    mock.__exit__ = Mock(side_effect=lambda *args: exit_exception)
    return mock


# =============================================================================
# Mock Configuration Builders
# =============================================================================

def configure_transcription_success(mock_api: MockEvolutionAPI) -> None:
    """
    Configure a mock transcription API for success scenario.

    Args:
        mock_api: MockEvolutionAPI instance to configure
    """
    mock_api.set_transcription_result(
        text="This is a successful transcription of the audio file.",
        status="completed",
        duration=120.0,
        language="en"
    )


def configure_transcription_failure(mock_api: MockEvolutionAPI) -> None:
    """
    Configure a mock transcription API for failure scenario.

    Args:
        mock_api: MockEvolutionAPI instance to configure
    """
    mock_api.set_error("Transcription failed: audio format not supported")


def configure_llm_success(mock_llm: MockOpenAI, text: Optional[str] = None) -> None:
    """
    Configure a mock LLM for success scenario.

    Args:
        mock_llm: MockOpenAI instance to configure
        text: Response text (auto-generated if None)
    """
    if text is None:
        text = "This is a generated summary based on the transcript content."

    mock_llm.set_completion_response(text)


def configure_llm_rate_limit(mock_llm: MockOpenAI) -> None:
    """
    Configure a mock LLM to simulate rate limiting.

    Args:
        mock_llm: MockOpenAI instance to configure
    """
    mock_llm.set_rate_limit(enabled=True)


def configure_vector_search_success(
    mock_qdrant: MockQdrantClient,
    num_results: int = 5
) -> None:
    """
    Configure a mock Qdrant client for successful search.

    Args:
        mock_qdrant: MockQdrantClient instance to configure
        num_results: Number of results to return
    """
    results = []
    for i in range(num_results):
        results.append({
            "id": str(uuid4()),
            "score": 0.95 - (i * 0.05),
            "payload": {
                "text": f"Sample document content {i}",
                "transcript_id": str(uuid4()),
                "metadata": {"chunk_index": i}
            }
        })

    mock_qdrant.set_search_results(results)
