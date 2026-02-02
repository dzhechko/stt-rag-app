"""
Comprehensive unit tests for RAGService

Tests cover:
- Qdrant integration
- Vector embedding generation
- Similarity search (vector and hybrid)
- Context window management
- BM25 integration
- Local embeddings fallback
- Collection management
"""

import unittest
from unittest.mock import Mock, patch, MagicMock, call
import uuid

# Mock the config before importing the service
sys_modules_patcher = patch.dict('sys.modules', {
    'app.config': MagicMock(),
    'app.config.settings': MagicMock(
        evolution_api_key='test_api_key',
        evolution_base_url='https://test.api.internal.cloud.ru/v1',
        app_env='development'
    )
})
sys_modules_patcher.start()

try:
    from app.services.rag_service import RAGService
finally:
    sys_modules_patcher.stop()


class TestRAGServiceInitialization(unittest.TestCase):
    """Test RAGService initialization"""

    @patch('app.services.rag_service.QdrantClient')
    @patch('app.services.rag_service.OpenAI')
    @patch('app.services.rag_service.httpx.Client')
    @patch('app.services.rag_service.settings')
    @patch.dict('os.environ', {'QDRANT_HOST': 'localhost'})
    def test_initialization_with_qdrant_connection(self, mock_settings, mock_httpx_client, mock_openai, mock_qdrant):
        """Test successful initialization with Qdrant connection"""
        mock_settings.evolution_api_key = 'test_key'
        mock_settings.evolution_base_url = 'https://test.api.com/v1'
        mock_settings.app_env = 'development'

        # Mock Qdrant client
        mock_qdrant_client = MagicMock()
        mock_qdrant_client.get_collections.return_value = MagicMock(collections=[])
        mock_qdrant.return_value = mock_qdrant_client

        # Mock embeddings test
        mock_openai_client = MagicMock()
        mock_embed_response = MagicMock()
        mock_embed_response.data = [MagicMock(embedding=[0.1] * 1536)]
        mock_openai_client.embeddings.create.return_value = mock_embed_response
        mock_openai.return_value = mock_openai_client

        service = RAGService()

        self.assertEqual(service.collection_name, "transcript_chunks")
        self.assertEqual(service.embeddings_dimension, 1536)
        mock_qdrant.assert_called_once()

    @patch('app.services.rag_service.QdrantClient')
    @patch('app.services.rag_service.OpenAI')
    @patch('app.services.rag_service.httpx.Client')
    @patch('app.services.rag_service.settings')
    @patch.dict('os.environ', {'QDRANT_HOST': 'localhost'})
    def test_initialization_with_qdrant_failure(self, mock_settings, mock_httpx_client, mock_openai, mock_qdrant):
        """Test initialization when Qdrant connection fails"""
        mock_settings.evolution_api_key = 'test_key'
        mock_settings.evolution_base_url = 'https://test.api.com/v1'
        mock_settings.app_env = 'development'

        # Mock Qdrant connection failure
        mock_qdrant.side_effect = Exception("Qdrant connection failed")

        service = RAGService()

        self.assertIsNone(service.qdrant_client)

    @patch('app.services.rag_service.QdrantClient')
    @patch('app.services.rag_service.OpenAI')
    @patch('app.services.rag_service.httpx.Client')
    @patch('app.services.rag_service.settings')
    @patch.dict('os.environ', {'QDRANT_HOST': 'localhost'})
    def test_initialization_with_embeddings_404_fallback(self, mock_settings, mock_httpx_client, mock_openai, mock_qdrant):
        """Test initialization falls back to local embeddings when API returns 404"""
        mock_settings.evolution_api_key = 'test_key'
        mock_settings.evolution_base_url = 'https://test.api.com/v1'
        mock_settings.app_env = 'development'

        # Mock Qdrant
        mock_qdrant_client = MagicMock()
        mock_qdrant_client.get_collections.return_value = MagicMock(collections=[])
        mock_qdrant.return_value = mock_qdrant_client

        # Mock embeddings API 404 error
        mock_openai_client = MagicMock()
        mock_openai_client.embeddings.create.side_effect = Exception("404 NotFound")
        mock_openai.return_value = mock_openai_client

        with patch('app.services.rag_service.SENTENCE_TRANSFORMERS_AVAILABLE', False):
            service = RAGService()

        # Should have None for embeddings client and local model
        self.assertIsNone(service.embeddings_client)


class TestQdrantIntegration(unittest.TestCase):
    """Test Qdrant vector database integration"""

    def setUp(self):
        """Set up test fixtures"""
        self.patcher_settings = patch('app.services.rag_service.settings')
        self.mock_settings = self.patcher_settings.start()
        self.mock_settings.evolution_api_key = 'test_key'
        self.mock_settings.evolution_base_url = 'https://test.api.com/v1'
        self.mock_settings.app_env = 'development'

    def tearDown(self):
        """Clean up patches"""
        self.patcher_settings.stop()

    @patch('app.services.rag_service.QdrantClient')
    @patch('app.services.rag_service.OpenAI')
    @patch('app.services.rag_service.httpx.Client')
    @patch.dict('os.environ', {'QDRANT_HOST': 'localhost'})
    def test_ensure_collection_creates_new_collection(self, mock_httpx_client, mock_openai, mock_qdrant):
        """Test that _ensure_collection creates a new collection if it doesn't exist"""
        mock_settings = self.mock_settings

        # Mock Qdrant
        mock_qdrant_client = MagicMock()
        mock_qdrant_client.get_collections.return_value = MagicMock(collections=[])
        mock_qdrant.return_value = mock_qdrant_client

        # Mock embeddings
        mock_openai_client = MagicMock()
        mock_embed_response = MagicMock()
        mock_embed_response.data = [MagicMock(embedding=[0.1] * 1536)]
        mock_openai_client.embeddings.create.return_value = mock_embed_response
        mock_openai.return_value = mock_openai_client

        service = RAGService()

        # Verify collection was created
        mock_qdrant_client.create_collection.assert_called_once()

        call_kwargs = mock_qdrant_client.create_collection.call_args[1]
        self.assertEqual(call_kwargs['collection_name'], 'transcript_chunks')
        self.assertEqual(call_kwargs['vectors_config'].size, 1536)

    @patch('app.services.rag_service.QdrantClient')
    @patch('app.services.rag_service.OpenAI')
    @patch('app.services.rag_service.httpx.Client')
    @patch.dict('os.environ', {'QDRANT_HOST': 'localhost'})
    def test_ensure_collection_handles_existing_collection(self, mock_httpx_client, mock_openai, mock_qdrant):
        """Test that _ensure_collection handles existing collection correctly"""
        # Mock Qdrant with existing collection
        mock_qdrant_client = MagicMock()
        mock_collection = MagicMock()
        mock_collection.name = 'transcript_chunks'
        mock_qdrant_client.get_collections.return_value = MagicMock(collections=[mock_collection])

        # Mock collection info with matching dimension
        mock_collection_info = MagicMock()
        mock_collection_info.config.params.vectors.size = 1536
        mock_qdrant_client.get_collection.return_value = mock_collection_info

        mock_qdrant.return_value = mock_qdrant_client

        # Mock embeddings
        mock_openai_client = MagicMock()
        mock_embed_response = MagicMock()
        mock_embed_response.data = [MagicMock(embedding=[0.1] * 1536)]
        mock_openai_client.embeddings.create.return_value = mock_embed_response
        mock_openai.return_value = mock_openai_client

        service = RAGService()

        # Should not create collection if it exists with correct dimension
        mock_qdrant_client.create_collection.assert_not_called()

    @patch('app.services.rag_service.QdrantClient')
    @patch('app.services.rag_service.OpenAI')
    @patch('app.services.rag_service.httpx.Client')
    @patch.dict('os.environ', {'QDRANT_HOST': 'localhost'})
    def test_delete_transcript_index(self, mock_httpx_client, mock_openai, mock_qdrant):
        """Test deletion of transcript index from Qdrant"""
        # Mock Qdrant
        mock_qdrant_client = MagicMock()
        mock_qdrant_client.get_collections.return_value = MagicMock(collections=[])
        mock_qdrant.return_value = mock_qdrant_client

        # Mock embeddings
        mock_openai_client = MagicMock()
        mock_embed_response = MagicMock()
        mock_embed_response.data = [MagicMock(embedding=[0.1] * 1536)]
        mock_openai_client.embeddings.create.return_value = mock_embed_response
        mock_openai.return_value = mock_openai_client

        service = RAGService()

        # Test deletion
        transcript_id = str(uuid.uuid4())
        result = service.delete_transcript_index(transcript_id)

        self.assertTrue(result)
        mock_qdrant_client.delete.assert_called_once()

    @patch('app.services.rag_service.QdrantClient')
    @patch('app.services.rag_service.OpenAI')
    @patch('app.services.rag_service.httpx.Client')
    @patch.dict('os.environ', {'QDRANT_HOST': 'localhost'})
    def test_delete_transcript_index_with_no_client(self, mock_httpx_client, mock_openai, mock_qdrant):
        """Test deletion returns False when Qdrant client is not available"""
        # Mock Qdrant connection failure
        mock_qdrant.side_effect = Exception("Connection failed")

        service = RAGService()

        result = service.delete_transcript_index(str(uuid.uuid4()))

        self.assertFalse(result)


class TestVectorEmbeddingGeneration(unittest.TestCase):
    """Test vector embedding generation"""

    def setUp(self):
        """Set up test fixtures"""
        self.patcher_settings = patch('app.services.rag_service.settings')
        self.mock_settings = self.patcher_settings.start()
        self.mock_settings.evolution_api_key = 'test_key'
        self.mock_settings.evolution_base_url = 'https://test.api.com/v1'
        self.mock_settings.app_env = 'development'

    def tearDown(self):
        """Clean up patches"""
        self.patcher_settings.stop()

    @patch('app.services.rag_service.QdrantClient')
    @patch('app.services.rag_service.OpenAI')
    @patch('app.services.rag_service.httpx.Client')
    @patch.dict('os.environ', {'QDRANT_HOST': 'localhost'})
    def test_generate_embeddings_with_api(self, mock_httpx_client, mock_openai, mock_qdrant):
        """Test embedding generation using Evolution Cloud.ru API"""
        # Mock Qdrant
        mock_qdrant_client = MagicMock()
        mock_qdrant_client.get_collections.return_value = MagicMock(collections=[])
        mock_qdrant.return_value = mock_qdrant_client

        # Mock embeddings API
        mock_openai_client = MagicMock()
        mock_embed_response = MagicMock()
        mock_embed_response.data = [
            MagicMock(embedding=[0.1] * 1536),
            MagicMock(embedding=[0.2] * 1536)
        ]
        mock_openai_client.embeddings.create.return_value = mock_embed_response
        mock_openai.return_value = mock_openai_client

        service = RAGService()

        texts = ["First text", "Second text"]
        embeddings = service._generate_embeddings(texts)

        self.assertEqual(len(embeddings), 2)
        self.assertEqual(len(embeddings[0]), 1536)
        self.assertEqual(len(embeddings[1]), 1536)

        # Verify API was called
        mock_openai_client.embeddings.create.assert_called_once()
        call_kwargs = mock_openai_client.embeddings.create.call_args[1]
        self.assertEqual(call_kwargs['model'], 'text-embedding-ada-002')
        self.assertEqual(call_kwargs['input'], texts)

    @patch('app.services.rag_service.QdrantClient')
    @patch('app.services.rag_service.OpenAI')
    @patch('app.services.rag_service.httpx.Client')
    @patch.dict('os.environ', {'QDRANT_HOST': 'localhost'})
    def test_generate_embeddings_api_failure(self, mock_httpx_client, mock_openai, mock_qdrant):
        """Test embedding generation when API fails"""
        # Mock Qdrant
        mock_qdrant_client = MagicMock()
        mock_qdrant_client.get_collections.return_value = MagicMock(collections=[])
        mock_qdrant.return_value = mock_qdrant_client

        # Mock embeddings API failure (404)
        mock_openai_client = MagicMock()
        mock_openai_client.embeddings.create.side_effect = Exception("404 NotFound")
        mock_openai.return_value = mock_openai_client

        with patch('app.services.rag_service.SENTENCE_TRANSFORMERS_AVAILABLE', False):
            service = RAGService()

        # Should raise error when no embeddings available
        with self.assertRaises(ValueError) as context:
            service._generate_embeddings(["Test text"])

        self.assertIn('Embeddings not available', str(context.exception))

    @patch('app.services.rag_service.QdrantClient')
    @patch('app.services.rag_service.OpenAI')
    @patch('app.services.rag_service.httpx.Client')
    @patch.dict('os.environ', {'QDRANT_HOST': 'localhost'})
    def test_generate_embeddings_dimension_check(self, mock_httpx_client, mock_openai, mock_qdrant):
        """Test that embeddings have correct dimension"""
        # Mock Qdrant
        mock_qdrant_client = MagicMock()
        mock_qdrant_client.get_collections.return_value = MagicMock(collections=[])
        mock_qdrant.return_value = mock_qdrant_client

        # Mock embeddings API with different dimension
        mock_openai_client = MagicMock()
        mock_embed_response = MagicMock()
        test_embedding = [0.1] * 768  # Different dimension
        mock_embed_response.data = [MagicMock(embedding=test_embedding)]
        mock_openai_client.embeddings.create.return_value = mock_embed_response
        mock_openai.return_value = mock_openai_client

        service = RAGService()

        texts = ["Test text"]
        embeddings = service._generate_embeddings(texts)

        self.assertEqual(len(embeddings), 1)
        self.assertEqual(len(embeddings[0]), len(test_embedding))


class TestSimilaritySearch(unittest.TestCase):
    """Test similarity search functionality"""

    def setUp(self):
        """Set up test fixtures"""
        self.patcher_settings = patch('app.services.rag_service.settings')
        self.mock_settings = self.patcher_settings.start()
        self.mock_settings.evolution_api_key = 'test_key'
        self.mock_settings.evolution_base_url = 'https://test.api.com/v1'
        self.mock_settings.app_env = 'development'

    def tearDown(self):
        """Clean up patches"""
        self.patcher_settings.stop()

    @patch('app.services.rag_service.QdrantClient')
    @patch('app.services.rag_service.OpenAI')
    @patch('app.services.rag_service.httpx.Client')
    @patch.dict('os.environ', {'QDRANT_HOST': 'localhost'})
    def test_vector_search_only(self, mock_httpx_client, mock_openai, mock_qdrant):
        """Test vector search without hybrid mode"""
        # Mock Qdrant
        mock_qdrant_client = MagicMock()
        mock_qdrant_client.get_collections.return_value = MagicMock(collections=[])

        # Mock search results
        mock_search_result = MagicMock()
        mock_search_result.payload = {
            'chunk_text': 'Sample chunk text',
            'transcript_id': 'test-id',
            'chunk_index': 0,
            'metadata': {'key': 'value'}
        }
        mock_search_result.score = 0.95
        mock_qdrant_client.search.return_value = [mock_search_result]
        mock_qdrant.return_value = mock_qdrant_client

        # Mock embeddings
        mock_openai_client = MagicMock()
        mock_embed_response = MagicMock()
        mock_embed_response.data = [MagicMock(embedding=[0.1] * 1536)]
        mock_openai_client.embeddings.create.return_value = mock_embed_response
        mock_openai.return_value = mock_openai_client

        service = RAGService()

        results = service._vector_search_only("test query", top_k=5)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['chunk_text'], 'Sample chunk text')
        self.assertEqual(results[0]['transcript_id'], 'test-id')
        self.assertEqual(results[0]['score'], 0.95)

    @patch('app.services.rag_service.QdrantClient')
    @patch('app.services.rag_service.OpenAI')
    @patch('app.services.rag_service.httpx.Client')
    @patch.dict('os.environ', {'QDRANT_HOST': 'localhost'})
    def test_vector_search_with_transcript_filter(self, mock_httpx_client, mock_openai, mock_qdrant):
        """Test vector search with transcript ID filtering"""
        # Mock Qdrant
        mock_qdrant_client = MagicMock()
        mock_qdrant_client.get_collections.return_value = MagicMock(collections=[])
        mock_qdrant_client.search.return_value = []
        mock_qdrant.return_value = mock_qdrant_client

        # Mock embeddings
        mock_openai_client = MagicMock()
        mock_embed_response = MagicMock()
        mock_embed_response.data = [MagicMock(embedding=[0.1] * 1536)]
        mock_openai_client.embeddings.create.return_value = mock_embed_response
        mock_openai.return_value = mock_openai_client

        service = RAGService()

        transcript_ids = ['transcript-1', 'transcript-2']
        results = service._vector_search_only("test query", transcript_ids=transcript_ids, top_k=5)

        # Verify filter was applied
        mock_qdrant_client.search.assert_called_once()
        call_kwargs = mock_qdrant_client.search.call_args[1]
        self.assertIn('query_filter', call_kwargs)

    @patch('app.services.rag_service.QdrantClient')
    @patch('app.services.rag_service.OpenAI')
    @patch('app.services.rag_service.httpx.Client')
    @patch.dict('os.environ', {'QDRANT_HOST': 'localhost'})
    def test_vector_search_with_no_client(self, mock_httpx_client, mock_openai, mock_qdrant):
        """Test vector search returns empty when Qdrant is not available"""
        # Mock Qdrant connection failure
        mock_qdrant.side_effect = Exception("Connection failed")

        service = RAGService()

        results = service._vector_search_only("test query")

        self.assertEqual(results, [])

    @patch('app.services.rag_service.QdrantClient')
    @patch('app.services.rag_service.OpenAI')
    @patch('app.services.rag_service.httpx.Client')
    @patch.dict('os.environ', {'QDRANT_HOST': 'localhost'})
    def test_hybrid_search(self, mock_httpx_client, mock_openai, mock_qdrant):
        """Test hybrid search combining vector and BM25"""
        # Mock Qdrant
        mock_qdrant_client = MagicMock()
        mock_qdrant_client.get_collections.return_value = MagicMock(collections=[])
        mock_qdrant_client.scroll.return_value = ([], None)

        mock_vector_result = MagicMock()
        mock_vector_result.payload = {
            'chunk_text': 'Vector result',
            'transcript_id': 'test-id',
            'chunk_index': 0,
            'metadata': {}
        }
        mock_vector_result.score = 0.8
        mock_qdrant_client.search.return_value = [mock_vector_result]
        mock_qdrant.return_value = mock_qdrant_client

        # Mock embeddings
        mock_openai_client = MagicMock()
        mock_embed_response = MagicMock()
        mock_embed_response.data = [MagicMock(embedding=[0.1] * 1536)]
        mock_openai_client.embeddings.create.return_value = mock_embed_response
        mock_openai.return_value = mock_openai_client

        with patch('app.services.rag_service.BM25_AVAILABLE', True):
            service = RAGService()

        results = service.hybrid_search("test query", top_k=5)

        # Should return combined results
        self.assertIsInstance(results, list)

    @patch('app.services.rag_service.QdrantClient')
    @patch('app.services.rag_service.OpenAI')
    @patch('app.services.rag_service.httpx.Client')
    @patch.dict('os.environ', {'QDRANT_HOST': 'localhost'})
    def test_search_method(self, mock_httpx_client, mock_openai, mock_qdrant):
        """Test main search method"""
        # Mock Qdrant
        mock_qdrant_client = MagicMock()
        mock_qdrant_client.get_collections.return_value = MagicMock(collections=[])
        mock_qdrant_client.search.return_value = []
        mock_qdrant.return_value = mock_qdrant_client

        # Mock embeddings
        mock_openai_client = MagicMock()
        mock_embed_response = MagicMock()
        mock_embed_response.data = [MagicMock(embedding=[0.1] * 1536)]
        mock_openai_client.embeddings.create.return_value = mock_embed_response
        mock_openai.return_value = mock_openai_client

        service = RAGService()

        # Test vector search (use_hybrid=False)
        results = service.search("test query", use_hybrid=False)
        self.assertIsInstance(results, list)


class TestContextWindowManagement(unittest.TestCase):
    """Test context window and text splitting management"""

    def setUp(self):
        """Set up test fixtures"""
        self.patcher_settings = patch('app.services.rag_service.settings')
        self.mock_settings = self.patcher_settings.start()
        self.mock_settings.evolution_api_key = 'test_key'
        self.mock_settings.evolution_base_url = 'https://test.api.com/v1'
        self.mock_settings.app_env = 'development'

    def tearDown(self):
        """Clean up patches"""
        self.patcher_settings.stop()

    @patch('app.services.rag_service.QdrantClient')
    @patch('app.services.rag_service.OpenAI')
    @patch('app.services.rag_service.httpx.Client')
    @patch.dict('os.environ', {'QDRANT_HOST': 'localhost'})
    def test_text_splitter_initialization(self, mock_httpx_client, mock_openai, mock_qdrant):
        """Test that text splitter is properly initialized"""
        # Mock Qdrant
        mock_qdrant_client = MagicMock()
        mock_qdrant_client.get_collections.return_value = MagicMock(collections=[])
        mock_qdrant.return_value = mock_qdrant_client

        # Mock embeddings
        mock_openai_client = MagicMock()
        mock_embed_response = MagicMock()
        mock_embed_response.data = [MagicMock(embedding=[0.1] * 1536)]
        mock_openai_client.embeddings.create.return_value = mock_embed_response
        mock_openai.return_value = mock_openai_client

        service = RAGService()

        # Verify text splitter is initialized
        self.assertIsNotNone(service.text_splitter)
        self.assertEqual(service.text_splitter._chunk_size, 1000)
        self.assertEqual(service.text_splitter._chunk_overlap, 200)

    @patch('app.services.rag_service.QdrantClient')
    @patch('app.services.rag_service.OpenAI')
    @patch('app.services.rag_service.httpx.Client')
    @patch.dict('os.environ', {'QDRANT_HOST': 'localhost'})
    def test_text_splitting_in_indexing(self, mock_httpx_client, mock_openai, mock_qdrant):
        """Test that text is split during indexing"""
        # Mock Qdrant
        mock_qdrant_client = MagicMock()
        mock_qdrant_client.get_collections.return_value = MagicMock(collections=[])
        mock_qdrant_client.upsert.return_value = None
        mock_qdrant.return_value = mock_qdrant_client

        # Mock embeddings
        mock_openai_client = MagicMock()
        mock_embed_response = MagicMock()
        # Mock multiple embeddings for chunks
        mock_embed_response.data = [
            MagicMock(embedding=[0.1] * 1536),
            MagicMock(embedding=[0.2] * 1536),
            MagicMock(embedding=[0.3] * 1536)
        ]
        mock_openai_client.embeddings.create.return_value = mock_embed_response
        mock_openai.return_value = mock_openai_client

        service = RAGService()

        # Text long enough to be split
        long_text = "This is a sentence. " * 200  # Long text

        chunks = service.text_splitter.split_text(long_text)
        self.assertGreater(len(chunks), 1, "Long text should be split into multiple chunks")


class TestIndexTranscript(unittest.TestCase):
    """Test transcript indexing functionality"""

    def setUp(self):
        """Set up test fixtures"""
        self.patcher_settings = patch('app.services.rag_service.settings')
        self.mock_settings = self.patcher_settings.start()
        self.mock_settings.evolution_api_key = 'test_key'
        self.mock_settings.evolution_base_url = 'https://test.api.com/v1'
        self.mock_settings.app_env = 'development'

    def tearDown(self):
        """Clean up patches"""
        self.patcher_settings.stop()

    @patch('app.services.rag_service.QdrantClient')
    @patch('app.services.rag_service.OpenAI')
    @patch('app.services.rag_service.httpx.Client')
    @patch.dict('os.environ', {'QDRANT_HOST': 'localhost'})
    def test_index_transcript_success(self, mock_httpx_client, mock_openai, mock_qdrant):
        """Test successful transcript indexing"""
        # Mock Qdrant
        mock_qdrant_client = MagicMock()
        mock_qdrant_client.get_collections.return_value = MagicMock(collections=[])
        mock_qdrant_client.upsert.return_value = None
        mock_qdrant.return_value = mock_qdrant_client

        # Mock embeddings
        mock_openai_client = MagicMock()
        mock_embed_response = MagicMock()
        mock_embed_response.data = [MagicMock(embedding=[0.1] * 1536)]
        mock_openai_client.embeddings.create.return_value = mock_embed_response
        mock_openai.return_value = mock_openai_client

        service = RAGService()

        transcript_id = str(uuid.uuid4())
        text = "This is a test transcript."

        num_indexed = service.index_transcript(transcript_id, text)

        self.assertGreater(num_indexed, 0)
        mock_qdrant_client.upsert.assert_called_once()

    @patch('app.services.rag_service.QdrantClient')
    @patch('app.services.rag_service.OpenAI')
    @patch('app.services.rag_service.httpx.Client')
    @patch.dict('os.environ', {'QDRANT_HOST': 'localhost'})
    def test_index_transcript_with_progress_callback(self, mock_httpx_client, mock_openai, mock_qdrant):
        """Test transcript indexing with progress callback"""
        # Mock Qdrant
        mock_qdrant_client = MagicMock()
        mock_qdrant_client.get_collections.return_value = MagicMock(collections=[])
        mock_qdrant_client.upsert.return_value = None
        mock_qdrant.return_value = mock_qdrant_client

        # Mock embeddings
        mock_openai_client = MagicMock()
        mock_embed_response = MagicMock()
        mock_embed_response.data = [MagicMock(embedding=[0.1] * 1536)]
        mock_openai_client.embeddings.create.return_value = mock_embed_response
        mock_openai.return_value = mock_openai_client

        service = RAGService()

        progress_values = []

        def progress_callback(progress):
            progress_values.append(progress)

        transcript_id = str(uuid.uuid4())
        text = "This is a test transcript."

        service.index_transcript(transcript_id, text, progress_callback=progress_callback)

        # Verify progress was updated
        self.assertGreater(len(progress_values), 0)
        # Check that progress reaches 1.0 (completed)
        self.assertIn(1.0, progress_values)

    @patch('app.services.rag_service.QdrantClient')
    @patch('app.services.rag_service.OpenAI')
    @patch('app.services.rag_service.httpx.Client')
    @patch.dict('os.environ', {'QDRANT_HOST': 'localhost'})
    def test_index_transcript_with_metadata(self, mock_httpx_client, mock_openai, mock_qdrant):
        """Test transcript indexing with metadata"""
        # Mock Qdrant
        mock_qdrant_client = MagicMock()
        mock_qdrant_client.get_collections.return_value = MagicMock(collections=[])
        mock_qdrant_client.upsert.return_value = None
        mock_qdrant.return_value = mock_qdrant_client

        # Mock embeddings
        mock_openai_client = MagicMock()
        mock_embed_response = MagicMock()
        mock_embed_response.data = [MagicMock(embedding=[0.1] * 1536)]
        mock_openai_client.embeddings.create.return_value = mock_embed_response
        mock_openai.return_value = mock_openai_client

        service = RAGService()

        transcript_id = str(uuid.uuid4())
        text = "Test transcript"
        metadata = {'title': 'Meeting', 'date': '2024-01-01'}

        service.index_transcript(transcript_id, text, metadata=metadata)

        # Verify metadata was included in payload
        call_args = mock_qdrant_client.upsert.call_args
        points = call_args[1]['points']
        self.assertIn('metadata', points[0].payload)
        self.assertEqual(points[0].payload['metadata'], metadata)

    @patch('app.services.rag_service.QdrantClient')
    @patch('app.services.rag_service.OpenAI')
    @patch('app.services.rag_service.httpx.Client')
    @patch.dict('os.environ', {'QDRANT_HOST': 'localhost'})
    def test_index_transcript_with_no_qdrant(self, mock_httpx_client, mock_openai, mock_qdrant):
        """Test transcript indexing when Qdrant is not available"""
        # Mock Qdrant connection failure
        mock_qdrant.side_effect = Exception("Connection failed")

        service = RAGService()

        transcript_id = str(uuid.uuid4())
        text = "Test transcript"

        num_indexed = service.index_transcript(transcript_id, text)

        self.assertEqual(num_indexed, 0)


class TestBM25Integration(unittest.TestCase):
    """Test BM25 search integration"""

    def setUp(self):
        """Set up test fixtures"""
        self.patcher_settings = patch('app.services.rag_service.settings')
        self.mock_settings = self.patcher_settings.start()
        self.mock_settings.evolution_api_key = 'test_key'
        self.mock_settings.evolution_base_url = 'https://test.api.com/v1'
        self.mock_settings.app_env = 'development'

    def tearDown(self):
        """Clean up patches"""
        self.patcher_settings.stop()

    @patch('app.services.rag_service.QdrantClient')
    @patch('app.services.rag_service.OpenAI')
    @patch('app.services.rag_service.httpx.Client')
    @patch.dict('os.environ', {'QDRANT_HOST': 'localhost'})
    def test_bm25_search_with_results(self, mock_httpx_client, mock_openai, mock_qdrant):
        """Test BM25 search returns results"""
        # Mock Qdrant
        mock_qdrant_client = MagicMock()
        mock_qdrant_client.get_collections.return_value = MagicMock(collections=[])
        mock_qdrant_client.scroll.return_value = ([], None)
        mock_qdrant.return_value = mock_qdrant_client

        # Mock embeddings
        mock_openai_client = MagicMock()
        mock_embed_response = MagicMock()
        mock_embed_response.data = [MagicMock(embedding=[0.1] * 1536)]
        mock_openai_client.embeddings.create.return_value = mock_embed_response
        mock_openai.return_value = mock_openai_client

        with patch('app.services.rag_service.BM25_AVAILABLE', True):
            service = RAGService()

        # Add some BM25 data manually
        service.bm25_chunks = [['test', 'chunk', 'text'], ['another', 'chunk']]
        service.bm25_chunk_map = {
            0: ('transcript-1', 0, 'test chunk text'),
            1: ('transcript-2', 0, 'another chunk')
        }

        # Mock BM25 index
        mock_bm25 = MagicMock()
        mock_bm25.get_scores.return_value = [0.8, 0.3]
        service.bm25_index = mock_bm25

        results = service._bm25_search("test query")

        self.assertGreater(len(results), 0)

    @patch('app.services.rag_service.QdrantClient')
    @patch('app.services.rag_service.OpenAI')
    @patch('app.services.rag_service.httpx.Client')
    @patch.dict('os.environ', {'QDRANT_HOST': 'localhost'})
    def test_bm25_search_with_transcript_filter(self, mock_httpx_client, mock_openai, mock_qdrant):
        """Test BM25 search with transcript ID filtering"""
        # Mock Qdrant
        mock_qdrant_client = MagicMock()
        mock_qdrant_client.get_collections.return_value = MagicMock(collections=[])
        mock_qdrant_client.scroll.return_value = ([], None)
        mock_qdrant.return_value = mock_qdrant_client

        # Mock embeddings
        mock_openai_client = MagicMock()
        mock_embed_response = MagicMock()
        mock_embed_response.data = [MagicMock(embedding=[0.1] * 1536)]
        mock_openai_client.embeddings.create.return_value = mock_embed_response
        mock_openai.return_value = mock_openai_client

        with patch('app.services.rag_service.BM25_AVAILABLE', True):
            service = RAGService()

        # Add BM25 data with different transcript IDs
        service.bm25_chunks = [['test', 'text'], ['another', 'text']]
        service.bm25_chunk_map = {
            0: ('transcript-1', 0, 'test text'),
            1: ('transcript-2', 0, 'another text')
        }

        mock_bm25 = MagicMock()
        mock_bm25.get_scores.return_value = [0.8, 0.6]
        service.bm25_index = mock_bm25

        # Filter by transcript-1 only
        results = service._bm25_search("test query", transcript_ids=['transcript-1'])

        # Should only return results from transcript-1
        for result in results:
            self.assertEqual(result['transcript_id'], 'transcript-1')

    @patch('app.services.rag_service.QdrantClient')
    @patch('app.services.rag_service.OpenAI')
    @patch('app.services.rag_service.httpx.Client')
    @patch.dict('os.environ', {'QDRANT_HOST': 'localhost'})
    def test_bm25_search_unavailable(self, mock_httpx_client, mock_openai, mock_qdrant):
        """Test BM25 search when BM25 is not available"""
        # Mock Qdrant
        mock_qdrant_client = MagicMock()
        mock_qdrant_client.get_collections.return_value = MagicMock(collections=[])
        mock_qdrant.return_value = mock_qdrant_client

        # Mock embeddings
        mock_openai_client = MagicMock()
        mock_embed_response = MagicMock()
        mock_embed_response.data = [MagicMock(embedding=[0.1] * 1536)]
        mock_openai_client.embeddings.create.return_value = mock_embed_response
        mock_openai.return_value = mock_openai_client

        with patch('app.services.rag_service.BM25_AVAILABLE', False):
            service = RAGService()

        results = service._bm25_search("test query")

        self.assertEqual(results, [])


class TestErrorHandling(unittest.TestCase):
    """Test error handling in RAG service"""

    def setUp(self):
        """Set up test fixtures"""
        self.patcher_settings = patch('app.services.rag_service.settings')
        self.mock_settings = self.patcher_settings.start()
        self.mock_settings.evolution_api_key = 'test_key'
        self.mock_settings.evolution_base_url = 'https://test.api.com/v1'
        self.mock_settings.app_env = 'development'

    def tearDown(self):
        """Clean up patches"""
        self.patcher_settings.stop()

    @patch('app.services.rag_service.QdrantClient')
    @patch('app.services.rag_service.OpenAI')
    @patch('app.services.rag_service.httpx.Client')
    @patch.dict('os.environ', {'QDRANT_HOST': 'localhost'})
    def test_search_exception_handling(self, mock_httpx_client, mock_openai, mock_qdrant):
        """Test that search exceptions are handled gracefully"""
        # Mock Qdrant
        mock_qdrant_client = MagicMock()
        mock_qdrant_client.get_collections.return_value = MagicMock(collections=[])
        mock_qdrant_client.search.side_effect = Exception("Search error")
        mock_qdrant.return_value = mock_qdrant_client

        # Mock embeddings
        mock_openai_client = MagicMock()
        mock_embed_response = MagicMock()
        mock_embed_response.data = [MagicMock(embedding=[0.1] * 1536)]
        mock_openai_client.embeddings.create.return_value = mock_embed_response
        mock_openai.return_value = mock_openai_client

        service = RAGService()

        results = service.search("test query")

        # Should return empty list on error
        self.assertEqual(results, [])

    @patch('app.services.rag_service.QdrantClient')
    @patch('app.services.rag_service.OpenAI')
    @patch('app.services.rag_service.httpx.Client')
    @patch.dict('os.environ', {'QDRANT_HOST': 'localhost'})
    def test_index_transcript_exception_handling(self, mock_httpx_client, mock_openai, mock_qdrant):
        """Test that indexing exceptions are handled"""
        # Mock Qdrant
        mock_qdrant_client = MagicMock()
        mock_qdrant_client.get_collections.return_value = MagicMock(collections=[])
        mock_qdrant_client.upsert.side_effect = Exception("Upsert error")
        mock_qdrant.return_value = mock_qdrant_client

        # Mock embeddings
        mock_openai_client = MagicMock()
        mock_embed_response = MagicMock()
        mock_embed_response.data = [MagicMock(embedding=[0.1] * 1536)]
        mock_openai_client.embeddings.create.return_value = mock_embed_response
        mock_openai.return_value = mock_openai_client

        service = RAGService()

        with self.assertRaises(Exception):
            service.index_transcript(str(uuid.uuid4()), "Test text")


if __name__ == '__main__':
    unittest.main()
