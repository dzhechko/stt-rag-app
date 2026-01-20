import logging
import os
import uuid
import httpx
from typing import List, Dict, Any, Optional, Callable
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from langchain.text_splitter import RecursiveCharacterTextSplitter
from openai import OpenAI
from app.config import settings

logger = logging.getLogger(__name__)

# Try to import sentence-transformers for local embeddings fallback
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    logger.warning("sentence-transformers not available, local embeddings fallback disabled")

# Try to import rank-bm25 for hybrid search
try:
    from rank_bm25 import BM25Okapi
    BM25_AVAILABLE = True
except ImportError:
    BM25_AVAILABLE = False
    logger.warning("rank-bm25 not available, hybrid search will be disabled")


class RAGService:
    def __init__(self):
        # Initialize Qdrant client (will connect to Qdrant container)
        # In Docker Compose, use service name; locally use localhost
        qdrant_host = os.getenv("QDRANT_HOST", "qdrant")  # Default to service name in Docker Compose
        
        try:
            self.qdrant_client = QdrantClient(
                host=qdrant_host,
                port=6333,
                timeout=10  # Connection timeout
            )
            # Test connection
            self.qdrant_client.get_collections()
            logger.info(f"Successfully connected to Qdrant at {qdrant_host}:6333")
        except Exception as e:
            logger.warning(f"Qdrant connection failed ({qdrant_host}:6333): {str(e)}. RAG features will be limited.")
            # Create a dummy client that will fail gracefully
            self.qdrant_client = None
        self.collection_name = "transcript_chunks"
        
        # Initialize embeddings - try Evolution Cloud.ru API first, fallback to local embeddings
        self.embeddings_client = None
        self.local_embeddings_model = None
        self.embeddings_dimension = 1536  # Default OpenAI dimension
        self.use_local_embeddings = False
        
        # Try Evolution Cloud.ru embeddings API first
        embeddings_base_url = settings.evolution_base_url
        if not embeddings_base_url.endswith("/v1"):
            if embeddings_base_url.endswith("/v1/"):
                embeddings_base_url = embeddings_base_url[:-1]
            elif not embeddings_base_url.endswith("/v1"):
                embeddings_base_url = embeddings_base_url.rstrip("/") + "/v1"
        
        logger.info(f"Initializing embeddings with base_url: {embeddings_base_url}")
        try:
            http_client = httpx.Client(
                verify=False,
                timeout=httpx.Timeout(30.0, connect=10.0),
                limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
            )
            
            self.embeddings_client = OpenAI(
                api_key=settings.evolution_api_key,
                base_url=embeddings_base_url,
                http_client=http_client,
                max_retries=2
            )
            # Test if embeddings API is available
            try:
                test_response = self.embeddings_client.embeddings.create(
                    model="text-embedding-ada-002",
                    input=["test"]
                )
                logger.info("Evolution Cloud.ru embeddings API is available")
                self.embeddings_dimension = 1536
            except Exception as e:
                if "404" in str(e) or "NotFound" in str(type(e).__name__):
                    logger.warning("Evolution Cloud.ru embeddings API not available (404), using local embeddings fallback")
                    self.embeddings_client = None
                    self._init_local_embeddings()
                else:
                    raise
        except Exception as e:
            logger.warning(f"Failed to initialize Evolution Cloud.ru embeddings client: {str(e)}, using local embeddings fallback")
            self.embeddings_client = None
            self._init_local_embeddings()
        
        # Text splitter for chunking (always initialize, regardless of embeddings method)
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len
        )
        
        # BM25 index for hybrid search
        self.bm25_index = None
        self.bm25_chunks = []  # Store chunk texts for BM25
        self.bm25_chunk_map = {}  # Map BM25 index to (transcript_id, chunk_index)
        self._rebuild_bm25_index()  # Build initial index from existing chunks
        
        # Initialize collection if it doesn't exist (after embeddings dimension is determined)
        self._ensure_collection()
    
    def _init_local_embeddings(self):
        """Initialize local embeddings model as fallback"""
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            logger.error("sentence-transformers not available, cannot use local embeddings fallback")
            return
        
        # Try multiple models, starting with lighter ones
        models_to_try = [
            'all-MiniLM-L6-v2',  # Lightweight, English-focused but works for multilingual
            'paraphrase-multilingual-MiniLM-L12-v2',  # Multilingual but heavier
            'all-mpnet-base-v2'  # Alternative
        ]
        
        for model_name in models_to_try:
            try:
                logger.info(f"Attempting to initialize local embeddings model: {model_name}...")
                self.local_embeddings_model = SentenceTransformer(model_name)
                
                # Get model dimension
                test_embedding = self.local_embeddings_model.encode("test", convert_to_numpy=False)
                if hasattr(test_embedding, 'shape'):
                    self.embeddings_dimension = test_embedding.shape[0]
                elif isinstance(test_embedding, list):
                    self.embeddings_dimension = len(test_embedding)
                else:
                    # Default dimensions for common models
                    if 'L6' in model_name:
                        self.embeddings_dimension = 384
                    elif 'L12' in model_name:
                        self.embeddings_dimension = 384
                    elif 'mpnet' in model_name:
                        self.embeddings_dimension = 768
                    else:
                        self.embeddings_dimension = 384
                
                self.use_local_embeddings = True
                logger.info(f"Local embeddings model '{model_name}' initialized successfully (dimension: {self.embeddings_dimension})")
                return
            except Exception as e:
                logger.warning(f"Failed to initialize model '{model_name}': {str(e)}")
                if model_name == models_to_try[-1]:
                    logger.error("All local embeddings models failed to initialize")
                    self.local_embeddings_model = None
                continue
    
    def _generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a list of texts
        Uses Evolution Cloud.ru API if available, otherwise falls back to local embeddings
        
        Args:
            texts: List of texts to generate embeddings for
        
        Returns:
            List of embedding vectors
        """
        # Try Evolution Cloud.ru API first
        if self.embeddings_client is not None:
            try:
                response = self.embeddings_client.embeddings.create(
                    model="text-embedding-ada-002",
                    input=texts
                )
                embeddings = [item.embedding for item in response.data]
                logger.debug(f"Generated {len(embeddings)} embeddings via Evolution Cloud.ru API")
                return embeddings
            except Exception as e:
                error_msg = str(e)
                if "404" in error_msg or "NotFound" in str(type(e).__name__):
                    logger.warning(f"Evolution Cloud.ru embeddings API returned 404, falling back to local embeddings")
                    # Fall through to local embeddings
                else:
                    logger.warning(f"Error using Evolution Cloud.ru embeddings: {error_msg}, falling back to local embeddings")
                    # Fall through to local embeddings
        
        # Fallback to local embeddings
        if self.use_local_embeddings and self.local_embeddings_model is not None:
            try:
                logger.debug(f"Generating {len(texts)} embeddings using local model")
                embeddings = self.local_embeddings_model.encode(
                    texts,
                    convert_to_numpy=False,
                    show_progress_bar=False
                )
                # Convert to list of lists
                embeddings = [emb.tolist() if hasattr(emb, 'tolist') else list(emb) for emb in embeddings]
                logger.debug(f"Generated {len(embeddings)} embeddings via local model")
                return embeddings
            except Exception as e:
                logger.error(f"Error generating local embeddings: {str(e)}", exc_info=True)
                raise
        
        # No embeddings available
        logger.error("No embeddings method available (neither API nor local model)")
        raise ValueError("Embeddings not available - neither Evolution Cloud.ru API nor local model is working")
    
    def _ensure_collection(self):
        """Create Qdrant collection if it doesn't exist"""
        if self.qdrant_client is None:
            return
        try:
            collections = self.qdrant_client.get_collections().collections
            collection_names = [c.name for c in collections]
            
            if self.collection_name not in collection_names:
                # Create new collection with current embeddings dimension
                self.qdrant_client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.embeddings_dimension,
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"Created Qdrant collection: {self.collection_name} with dimension {self.embeddings_dimension}")
            else:
                # Check if collection dimension matches current embeddings dimension
                # Use a more robust method to get dimension
                try:
                    # Try to get collection info
                    collection_info = self.qdrant_client.get_collection(self.collection_name)
                    existing_dim = None
                    
                    # Try different ways to get dimension
                    try:
                        existing_dim = collection_info.config.params.vectors.size
                    except (AttributeError, KeyError):
                        try:
                            # Alternative: try to access via result
                            if hasattr(collection_info, 'result'):
                                existing_dim = collection_info.result.config.params.vectors.size
                        except (AttributeError, KeyError):
                            pass
                    
                    if existing_dim is not None and existing_dim != self.embeddings_dimension:
                        logger.warning(
                            f"Collection dimension mismatch: existing={existing_dim}, current={self.embeddings_dimension}. "
                            f"Recreating collection with correct dimension..."
                        )
                        # Delete old collection
                        self.qdrant_client.delete_collection(self.collection_name)
                        # Create new collection with correct dimension
                        self.qdrant_client.create_collection(
                            collection_name=self.collection_name,
                            vectors_config=VectorParams(
                                size=self.embeddings_dimension,
                                distance=Distance.COSINE
                            )
                        )
                        logger.info(f"Recreated Qdrant collection: {self.collection_name} with dimension {self.embeddings_dimension}")
                    elif existing_dim is not None:
                        logger.debug(f"Qdrant collection {self.collection_name} exists with correct dimension {self.embeddings_dimension}")
                    else:
                        # If we can't determine dimension, don't delete collection - it likely exists and works
                        # Just log a warning and continue (collection will be used as-is)
                        logger.warning(
                            f"Could not determine collection dimension for {self.collection_name}, "
                            f"but collection exists. Assuming it's correct and continuing. "
                            f"Expected dimension: {self.embeddings_dimension}"
                        )
                except Exception as e:
                    # If we can't check collection info, don't delete it - it likely exists and works
                    # Just log a warning and continue (collection will be used as-is)
                    logger.warning(
                        f"Could not check collection dimension for {self.collection_name}: {str(e)}. "
                        f"Collection exists, assuming it's correct and continuing. "
                        f"Expected dimension: {self.embeddings_dimension}"
                    )
        except Exception as e:
            logger.error(f"Error ensuring collection exists: {str(e)}")
            # In development, Qdrant might not be available
            if settings.app_env == "development":
                logger.warning("Qdrant not available, RAG features will be limited")
    
    def index_transcript(
        self,
        transcript_id: str,
        text: str,
        metadata: Optional[Dict[str, Any]] = None,
        progress_callback: Optional[Callable[[float], None]] = None
    ) -> int:
        """
        Index transcript text in Qdrant
        
        Args:
            transcript_id: UUID of transcript
            text: Transcript text
            metadata: Additional metadata
        
        Returns:
            Number of chunks indexed
        """
        if self.qdrant_client is None:
            logger.warning("Qdrant not available, skipping indexing")
            return 0
        
        # Check if any embeddings method is available
        if not self.use_local_embeddings and self.embeddings_client is None:
            logger.warning("No embeddings method available (neither API nor local), skipping indexing")
            return 0
        
        try:
            # Update progress: splitting started
            if progress_callback:
                progress_callback(0.05)
            
            # Split text into chunks
            chunks = self.text_splitter.split_text(text)
            logger.info(f"Splitting transcript {transcript_id} into {len(chunks)} chunks")
            
            if len(chunks) == 0:
                logger.warning(f"No chunks created for transcript {transcript_id}, text may be too short")
                if progress_callback:
                    progress_callback(1.0)
                return 0
            
            # Update progress: chunks split
            if progress_callback:
                progress_callback(0.15)
            
            # Generate embeddings for chunks
            chunk_embeddings = self._generate_embeddings(chunks)
            
            # Check if embeddings were generated
            if not chunk_embeddings or len(chunk_embeddings) == 0:
                logger.warning(f"No embeddings generated for transcript {transcript_id}")
                if progress_callback:
                    progress_callback(1.0)
                return 0
            
            if len(chunk_embeddings) != len(chunks):
                logger.warning(f"Embeddings count mismatch: {len(chunk_embeddings)} embeddings for {len(chunks)} chunks")
                if progress_callback:
                    progress_callback(1.0)
                return 0
            
            # Update progress: embeddings generated
            if progress_callback:
                progress_callback(0.4)
            
            # Delete existing points for this transcript_id before reindexing
            # This prevents duplicates when reindexing
            try:
                from qdrant_client.models import Filter, FieldCondition, MatchValue
                self.qdrant_client.delete(
                    collection_name=self.collection_name,
                    points_selector=Filter(
                        must=[
                            FieldCondition(
                                key="transcript_id",
                                match=MatchValue(value=transcript_id)
                            )
                        ]
                    )
                )
                logger.debug(f"Deleted existing chunks for transcript {transcript_id} before reindexing")
            except Exception as e:
                logger.warning(f"Could not delete existing chunks for transcript {transcript_id}: {str(e)}. Continuing with indexing...")
            
            # Update progress: old chunks deleted
            if progress_callback:
                progress_callback(0.5)
            
            # Prepare points for Qdrant
            points = []
            for i, (chunk_text, embedding) in enumerate(zip(chunks, chunk_embeddings)):
                point_id = str(uuid.uuid4())
                point = PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload={
                        "transcript_id": transcript_id,
                        "chunk_text": chunk_text,
                        "chunk_index": i,
                        "metadata": metadata or {}
                    }
                )
                points.append(point)
                
                # Update progress while preparing points (0.5 to 0.8)
                if progress_callback and (i + 1) % max(1, len(chunks) // 10) == 0:
                    progress = 0.5 + 0.3 * (i + 1) / len(chunks)
                    progress_callback(progress)
            
            # Update progress: points prepared
            if progress_callback:
                progress_callback(0.8)
            
            # Upsert points to Qdrant
            try:
                self.qdrant_client.upsert(
                    collection_name=self.collection_name,
                    points=points
                )
                logger.info(f"Indexed {len(points)} chunks for transcript {transcript_id}")
                
                # Update progress: points upserted
                if progress_callback:
                    progress_callback(0.9)
                
                # Update BM25 index with new chunks
                self._update_bm25_index(chunks, transcript_id)
                
                # Update progress: completed
                if progress_callback:
                    progress_callback(1.0)
                
                return len(points)
            except Exception as upsert_error:
                error_msg = str(upsert_error)
                # Check if it's a dimension mismatch error
                if "dimension" in error_msg.lower() or "expected dim" in error_msg.lower() or "got" in error_msg.lower():
                    logger.warning(
                        f"Dimension mismatch error when indexing transcript {transcript_id}: {error_msg}. "
                        f"Recreating collection with correct dimension {self.embeddings_dimension}..."
                    )
                    # Delete and recreate collection
                    try:
                        self.qdrant_client.delete_collection(self.collection_name)
                    except Exception as del_err:
                        logger.warning(f"Error deleting collection: {str(del_err)}")
                    self.qdrant_client.create_collection(
                        collection_name=self.collection_name,
                        vectors_config=VectorParams(
                            size=self.embeddings_dimension,
                            distance=Distance.COSINE
                        )
                    )
                    logger.info(f"Recreated collection with dimension {self.embeddings_dimension}, retrying index...")
                    # Retry upsert
                    self.qdrant_client.upsert(
                        collection_name=self.collection_name,
                        points=points
                    )
                    logger.info(f"Indexed {len(points)} chunks for transcript {transcript_id} after collection recreation")
                    
                    # Update BM25 index with new chunks
                    self._update_bm25_index(chunks, transcript_id)
                    
                    return len(points)
                else:
                    # Re-raise if it's not a dimension error
                    raise
        
        except Exception as e:
            logger.error(f"Error indexing transcript {transcript_id}: {str(e)}", exc_info=True)
            raise
    
    def _rebuild_bm25_index(self):
        """Rebuild BM25 index from all chunks in Qdrant"""
        if not BM25_AVAILABLE or self.qdrant_client is None:
            return
        
        try:
            # Get all points from collection
            all_points = []
            offset = None
            while True:
                result = self.qdrant_client.scroll(
                    collection_name=self.collection_name,
                    limit=100,
                    offset=offset,
                    with_payload=True,
                    with_vectors=False
                )
                points = result[0]
                if not points:
                    break
                all_points.extend(points)
                offset = result[1]
                if offset is None:
                    break
            
            # Build BM25 index
            self.bm25_chunks = []
            self.bm25_chunk_map = {}
            for i, point in enumerate(all_points):
                chunk_text = point.payload.get("chunk_text", "")
                if chunk_text:
                    # Tokenize for BM25 (simple whitespace split)
                    tokens = chunk_text.lower().split()
                    self.bm25_chunks.append(tokens)
                    self.bm25_chunk_map[i] = (
                        point.payload.get("transcript_id"),
                        point.payload.get("chunk_index", 0),
                        chunk_text
                    )
            
            if self.bm25_chunks:
                self.bm25_index = BM25Okapi(self.bm25_chunks)
                logger.info(f"Rebuilt BM25 index with {len(self.bm25_chunks)} chunks")
            else:
                self.bm25_index = None
                logger.info("BM25 index is empty")
        except Exception as e:
            logger.warning(f"Failed to rebuild BM25 index: {str(e)}")
            self.bm25_index = None
    
    def _update_bm25_index(self, chunks: List[str], transcript_id: str):
        """Update BM25 index with new chunks"""
        if not BM25_AVAILABLE:
            return
        
        try:
            # Add new chunks to BM25 index
            for i, chunk_text in enumerate(chunks):
                tokens = chunk_text.lower().split()
                if tokens:
                    idx = len(self.bm25_chunks)
                    self.bm25_chunks.append(tokens)
                    self.bm25_chunk_map[idx] = (transcript_id, i, chunk_text)
            
            # Rebuild BM25 index
            if self.bm25_chunks:
                self.bm25_index = BM25Okapi(self.bm25_chunks)
                logger.debug(f"Updated BM25 index, total chunks: {len(self.bm25_chunks)}")
        except Exception as e:
            logger.warning(f"Failed to update BM25 index: {str(e)}")
    
    def _bm25_search(
        self,
        query: str,
        transcript_ids: Optional[List[str]] = None,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """BM25 search for chunks"""
        if not BM25_AVAILABLE or self.bm25_index is None:
            return []
        
        try:
            query_tokens = query.lower().split()
            if not query_tokens:
                return []
            
            # Get BM25 scores
            scores = self.bm25_index.get_scores(query_tokens)
            
            # Get top-k results
            top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k * 2]  # Get more for filtering
            
            results = []
            for idx in top_indices:
                if scores[idx] <= 0:
                    continue
                
                transcript_id, chunk_index, chunk_text = self.bm25_chunk_map.get(idx, (None, 0, ""))
                
                # Filter by transcript_ids if provided
                if transcript_ids and transcript_id not in transcript_ids:
                    continue
                
                results.append({
                    "chunk_text": chunk_text,
                    "transcript_id": transcript_id,
                    "chunk_index": chunk_index,
                    "score": float(scores[idx]),
                    "metadata": {}
                })
                
                if len(results) >= top_k:
                    break
            
            return results
        except Exception as e:
            logger.error(f"Error in BM25 search: {str(e)}", exc_info=True)
            return []
    
    def _vector_search_only(
        self,
        query: str,
        transcript_ids: Optional[List[str]] = None,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """Vector search only (without hybrid)"""
        if self.qdrant_client is None:
            logger.warning("Qdrant not available, returning empty results")
            return []
        
        # Check if any embeddings method is available
        if not self.use_local_embeddings and self.embeddings_client is None:
            logger.warning("No embeddings method available (neither API nor local), returning empty results")
            return []
        try:
            # Generate query embedding using direct API
            query_embeddings = self._generate_embeddings([query])
            query_embedding = query_embeddings[0] if query_embeddings else None
            if not query_embedding:
                logger.warning("Failed to generate query embedding")
                return []
            
            # Build filter if transcript_ids provided
            query_filter = None
            if transcript_ids:
                from qdrant_client.models import Filter, FieldCondition, MatchValue
                query_filter = Filter(
                    must=[
                        FieldCondition(
                            key="transcript_id",
                            match=MatchValue(value=tid)
                        ) for tid in transcript_ids
                    ]
                )
            
            # Search in Qdrant
            search_results = self.qdrant_client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                query_filter=query_filter,
                limit=top_k
            )
            
            # Format results
            results = []
            for result in search_results:
                results.append({
                    "chunk_text": result.payload.get("chunk_text", ""),
                    "transcript_id": result.payload.get("transcript_id"),
                    "chunk_index": result.payload.get("chunk_index", 0),
                    "score": result.score,
                    "metadata": result.payload.get("metadata", {})
                })
            
            return results
        
        except Exception as e:
            logger.error(f"Error searching: {str(e)}", exc_info=True)
            return []
    
    def hybrid_search(
        self,
        query: str,
        transcript_ids: Optional[List[str]] = None,
        top_k: int = 5,
        vector_weight: float = 0.7,
        bm25_weight: float = 0.3
    ) -> List[Dict[str, Any]]:
        """Hybrid search combining vector and BM25"""
        # Get vector search results (direct call, no recursion)
        vector_results = self._vector_search_only(query, transcript_ids, top_k * 2)
        
        # Get BM25 results
        bm25_results = self._bm25_search(query, transcript_ids, top_k * 2)
        
        # Combine results
        combined = {}
        
        # Add vector results with weight
        for result in vector_results:
            key = (result["transcript_id"], result["chunk_index"])
            if key not in combined:
                combined[key] = result.copy()
                combined[key]["score"] = result["score"] * vector_weight
            else:
                combined[key]["score"] += result["score"] * vector_weight
        
        # Add BM25 results with weight
        for result in bm25_results:
            key = (result["transcript_id"], result["chunk_index"])
            if key not in combined:
                combined[key] = result.copy()
                combined[key]["score"] = result["score"] * bm25_weight
            else:
                combined[key]["score"] += result["score"] * bm25_weight
        
        # Sort by combined score and return top_k
        sorted_results = sorted(combined.values(), key=lambda x: x["score"], reverse=True)[:top_k]
        return sorted_results
    
    def search(
        self,
        query: str,
        transcript_ids: Optional[List[str]] = None,
        top_k: int = 5,
        use_hybrid: bool = False,
        vector_weight: float = 0.7,
        bm25_weight: float = 0.3
    ) -> List[Dict[str, Any]]:
        """
        Search for relevant chunks
        
        Args:
            query: Search query
            transcript_ids: Optional list of transcript IDs to search within
            top_k: Number of results to return
            use_hybrid: Use hybrid search (BM25 + Vector)
            vector_weight: Weight for vector search (default 0.7)
            bm25_weight: Weight for BM25 search (default 0.3)
        
        Returns:
            List of relevant chunks with metadata
        """
        try:
            if use_hybrid and BM25_AVAILABLE:
                return self.hybrid_search(query, transcript_ids, top_k, vector_weight, bm25_weight)
            
            # Use vector search only
            return self._vector_search_only(query, transcript_ids, top_k)
        except Exception as e:
            logger.error(f"Error searching: {str(e)}", exc_info=True)
            return []
    
    def delete_transcript_index(self, transcript_id: str) -> bool:
        """Delete all chunks for a transcript"""
        if self.qdrant_client is None:
            logger.warning("Qdrant not available, skipping deletion")
            return False
        try:
            from qdrant_client.models import Filter, FieldCondition, MatchValue
            
            # Delete points with matching transcript_id
            self.qdrant_client.delete(
                collection_name=self.collection_name,
                points_selector=Filter(
                    must=[
                        FieldCondition(
                            key="transcript_id",
                            match=MatchValue(value=transcript_id)
                        )
                    ]
                )
            )
            
            logger.info(f"Deleted index for transcript {transcript_id}")
            return True
        
        except Exception as e:
            logger.error(f"Error deleting index for transcript {transcript_id}: {str(e)}")
            return False

