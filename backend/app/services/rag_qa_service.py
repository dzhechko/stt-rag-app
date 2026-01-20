import logging
import httpx
import re
from typing import List, Dict, Any, Optional
from openai import OpenAI
from app.config import settings
from app.services.rag_service import RAGService

logger = logging.getLogger(__name__)

# Try to import DSPy for multi-hop reasoning
try:
    import dspy
    DSPY_AVAILABLE = True
except ImportError:
    DSPY_AVAILABLE = False
    logger.warning("dspy-ai not available, multi-hop reasoning will be disabled")

# Try to import CrossEncoder for specialized reranking
try:
    from sentence_transformers import CrossEncoder
    CROSS_ENCODER_AVAILABLE = True
except ImportError:
    CROSS_ENCODER_AVAILABLE = False
    logger.warning("sentence-transformers CrossEncoder not available, specialized reranking will use LLM fallback")


class RAGQAService:
    def __init__(self):
        self.rag_service = RAGService()
        
        # Validate and clean base_url (same as other services)
        base_url = settings.evolution_base_url
        if not base_url:
            raise ValueError("EVOLUTION_BASE_URL is not set in environment variables")
        
        # Clean up base_url if it contains the variable name prefix
        original_url = base_url
        if "EVOLUTION_BASE_URL=" in base_url:
            last_eq_index = base_url.rfind("=")
            if last_eq_index >= 0:
                base_url = base_url[last_eq_index + 1:].strip()
                logger.warning(f"Cleaned malformed base_url: '{original_url}' -> '{base_url}'")
        
        if not base_url.startswith(('http://', 'https://')):
            raise ValueError(f"EVOLUTION_BASE_URL must start with http:// or https://, got: {base_url}")
        
        logger.info(f"Initializing RAGQAService with base_url: {base_url}")
        
        # Create custom HTTP client with SSL verification disabled
        http_client = httpx.Client(
            verify=False,  # Disable SSL verification for internal Cloud.ru endpoints
            timeout=httpx.Timeout(120.0, connect=30.0),
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
        )
        
        self.client = OpenAI(
            api_key=settings.evolution_api_key,
            base_url=base_url,
            http_client=http_client,
            max_retries=2
        )
        self.default_model = "GigaChat/GigaChat-2-Max"
        
        # Initialize reranker model
        self.reranker_model = None
        self.reranker_model_name = None
        self._init_reranker("ms-marco-MiniLM-L-6-v2")  # Default model
    
    def answer_question(
        self,
        question: str,
        transcript_ids: Optional[List[str]] = None,
        model: Optional[str] = None,
        top_k: int = 5,
        temperature: float = 0.3,
        use_reranking: bool = True,
        use_query_expansion: bool = True,
        use_multi_hop: bool = False,
        use_hybrid_search: bool = False,
        use_advanced_grading: bool = False,
        reranker_model: str = "ms-marco-MiniLM-L-6-v2"
    ) -> Dict[str, Any]:
        """
        Answer question using RAG
        
        Args:
            question: User question
            transcript_ids: Optional list of transcript IDs to search (can be UUID strings or UUID objects)
            model: Model to use for generation
        
        Returns:
            Dictionary with answer, sources, and quality score
        """
        model = model or self.default_model
        
        # Normalize transcript_ids to strings
        if transcript_ids:
            transcript_ids = [str(tid) for tid in transcript_ids]
        
        # Multi-hop reasoning: break complex questions into sub-queries
        search_queries = [question]
        if use_multi_hop:
            sub_queries = self._multi_hop_reasoning(question, model)
            if sub_queries:
                search_queries = sub_queries
                logger.info(f"Multi-hop reasoning: generated {len(sub_queries)} sub-queries")
        
        # Query expansion: reformulate question and generate hypothetical answer
        if use_query_expansion and not use_multi_hop:
            expanded_queries = self._expand_query(question, model)
            search_queries.extend(expanded_queries)
            logger.info(f"Query expansion: {len(expanded_queries)} additional queries generated")
        
        # Retrieve relevant chunks using all queries
        logger.info(f"Searching for answer to question: {question[:100]}...")
        logger.info(f"Transcript IDs filter: {transcript_ids}")
        
        # Search with multiple queries and combine results
        all_chunks = []
        for query in search_queries:
            chunks = self.rag_service.search(
                query=query,
                transcript_ids=transcript_ids,
                top_k=top_k * 2,  # Get more chunks for reranking
                use_hybrid=use_hybrid_search
            )
            all_chunks.extend(chunks)
        
        # Deduplicate chunks by transcript_id and chunk_index
        seen = set()
        unique_chunks = []
        for chunk in all_chunks:
            key = (chunk.get("transcript_id"), chunk.get("chunk_index"))
            if key not in seen:
                seen.add(key)
                unique_chunks.append(chunk)
        
        logger.info(f"Retrieved {len(unique_chunks)} unique chunks from {len(search_queries)} queries")
        
        # Reranking: reorder chunks by relevance
        if use_reranking and len(unique_chunks) > top_k:
            logger.info(f"Reranking {len(unique_chunks)} chunks to top {top_k}...")
            # Update reranker model if changed
            if reranker_model != self.reranker_model_name and reranker_model != "llm":
                self._init_reranker(reranker_model)
            # Use specialized reranker if available, otherwise use LLM
            if reranker_model != "llm" and self.reranker_model is not None:
                logger.info(f"Using specialized reranker model: {self.reranker_model_name}")
                retrieved_chunks = self._rerank_chunks_specialized(question, unique_chunks, top_k)
            else:
                logger.info("Using LLM-based reranking (specialized model not available)")
                retrieved_chunks = self._rerank_chunks(question, unique_chunks, top_k, model)
        else:
            # Take top_k by score
            if not use_reranking:
                logger.info(f"Reranking skipped: use_reranking=False")
            elif len(unique_chunks) <= top_k:
                logger.info(f"Reranking skipped: only {len(unique_chunks)} chunks available (need > {top_k})")
            retrieved_chunks = sorted(unique_chunks, key=lambda x: x.get("score", 0), reverse=True)[:top_k]
        
        logger.info(f"Final {len(retrieved_chunks)} chunks after reranking")
        
        if not retrieved_chunks:
            # Check if transcripts are indexed
            if transcript_ids:
                logger.warning(
                    f"No chunks found for transcript_ids: {transcript_ids}. "
                    f"Transcripts may not be indexed yet. Try reindexing the transcripts."
                )
                return {
                    "answer": "Не удалось найти релевантную информацию для ответа на ваш вопрос. Возможно, транскрипты еще не проиндексированы. Попробуйте переиндексировать транскрипты или проверьте, что они завершены.",
                    "sources": [],
                    "quality_score": 0.0,
                    "retrieved_chunks": []
                }
            else:
                logger.warning("No chunks found and no transcript_ids specified")
                return {
                    "answer": "Не удалось найти релевантную информацию. Убедитесь, что вы выбрали транскрипты для поиска и что они проиндексированы.",
                    "sources": [],
                    "quality_score": 0.0,
                    "retrieved_chunks": []
                }
        
        # Build context from retrieved chunks with numbered citations
        context = "\n\n".join([
            f"[{i+1}] {chunk['chunk_text']}"
            for i, chunk in enumerate(retrieved_chunks)
        ])
        
        # Generate answer with citation instructions
        prompt = f"""Используй следующую информацию из транскриптов, чтобы ответить на вопрос.
Если информация не содержит ответа, скажи об этом честно.

ВАЖНО: В ответе обязательно добавляй ссылки на источники в квадратных скобках [1], [2], [3] и т.д. 
Каждая ссылка должна соответствовать номеру источника из контекста.
Например: "Согласно информации [1], Distributed Train - это платформа [2] для управления GPU контейнерами."

Контекст:
{context}

Вопрос: {question}

Ответ (обязательно со ссылками на источники в формате [1], [2], [3]...):"""
        
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": "Ты помощник, который отвечает на вопросы на основе предоставленного контекста из транскриптов. ВАЖНО: Всегда добавляй ссылки на источники в квадратных скобках [1], [2], [3] и т.д. в тексте ответа, когда используешь информацию из контекста. Каждая ссылка должна соответствовать номеру источника из контекста."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=temperature,
                max_tokens=1000
            )
            
            answer = response.choices[0].message.content
            
            # Evaluate answer quality
            if use_advanced_grading:
                quality_metrics = self._evaluate_answer_quality_advanced(
                    question, 
                    answer, 
                    retrieved_chunks, 
                    model,
                    use_reranking=use_reranking,
                    use_hybrid_search=use_hybrid_search,
                    top_k=top_k
                )
                quality_score = quality_metrics["overall_score"]
                logger.info(f"Advanced quality grading: groundedness={quality_metrics['groundedness']:.2f}, completeness={quality_metrics['completeness']:.2f}, relevance={quality_metrics['relevance']:.2f}, overall={quality_score:.2f}")
            else:
                quality_score = self._evaluate_answer_quality(
                    question, 
                    answer, 
                    retrieved_chunks,
                    top_k=top_k,
                    use_reranking=use_reranking,
                    use_hybrid_search=use_hybrid_search
                )
                quality_metrics = None
                logger.info(f"Simple quality score: {quality_score:.2f} (top_k={top_k}, reranking={use_reranking}, hybrid={use_hybrid_search})")
            
            result = {
                "answer": answer,
                "sources": [
                    {
                        "transcript_id": chunk["transcript_id"],
                        "chunk_index": chunk["chunk_index"],
                        "score": chunk["score"]
                    }
                    for chunk in retrieved_chunks
                ],
                "quality_score": quality_score,
                "retrieved_chunks": retrieved_chunks
            }
            
            if quality_metrics:
                result["quality_metrics"] = quality_metrics
            
            return result
        
        except httpx.ConnectError as e:
            error_msg = f"Connection error: Unable to connect to Evolution API at {self.client.base_url}. Please check your network connection and API endpoint."
            logger.error(error_msg, exc_info=True)
            raise ConnectionError(error_msg) from e
        except httpx.TimeoutException as e:
            error_msg = f"Timeout error: Request to Evolution API timed out. The API may be overloaded or unreachable."
            logger.error(error_msg, exc_info=True)
            raise ConnectionError(error_msg) from e
        except Exception as e:
            error_msg = f"Error generating answer: {str(e)}"
            logger.error(error_msg, exc_info=True)
            # Check if it's a connection-related error
            if "connection" in str(e).lower() or "timeout" in str(e).lower() or "refused" in str(e).lower():
                raise ConnectionError(f"Connection error: {str(e)}") from e
            raise
    
    def _evaluate_answer_quality(
        self,
        question: str,
        answer: str,
        retrieved_chunks: List[Dict[str, Any]],
        top_k: int = 5,
        use_reranking: bool = True,
        use_hybrid_search: bool = False
    ) -> float:
        """
        Evaluate answer quality (simplified version)
        Returns score from 0.0 to 5.0
        
        Args:
            question: User question
            answer: Generated answer
            retrieved_chunks: List of retrieved chunks
            top_k: Number of chunks requested
            use_reranking: Whether reranking was used
            use_hybrid_search: Whether hybrid search was used
        """
        # Simple heuristic: check if answer is not empty and has reasonable length
        if not answer or len(answer) < 10:
            logger.info("Quality evaluation: answer too short or empty, returning score 1.0")
            return 1.0
        
        base_score = 2.0
        answer_len = len(answer)
        chunks_used = len(retrieved_chunks)
        logger.info(f"Quality evaluation started: answer_len={answer_len}, chunks_used={chunks_used}/{top_k}, use_reranking={use_reranking}, use_hybrid_search={use_hybrid_search}, base_score={base_score:.2f}")
        
        # Check if answer references the context (more sophisticated check)
        chunk_texts = " ".join([chunk.get("chunk_text", "") for chunk in retrieved_chunks])
        context_words = set(chunk_texts.lower().split()[:20]) if chunk_texts else set()
        answer_words = set(answer.lower().split())
        common_words = context_words.intersection(answer_words)
        context_overlap = len(common_words) / max(len(context_words), 1)
        
        if context_overlap > 0.1:  # At least 10% word overlap
            overlap_boost = 0.8 + min(0.4, context_overlap * 2)  # 0.8 to 1.2 based on overlap
            base_score += overlap_boost
            logger.info(f"Quality evaluation: context_overlap={context_overlap:.2f}, added overlap_boost={overlap_boost:.2f}, base_score={base_score:.2f}")
        
        # More gradient length scoring (optimal range depends on reranking, hybrid search, and chunk usage)
        # With reranking, optimal range is wider because reranking finds more focused, relevant chunks
        # With hybrid search, answers can be more comprehensive
        optimal_min = 100 if use_reranking else 200
        
        # Base optimal_max increases with advanced settings
        if use_reranking and use_hybrid_search:
            # Both advanced settings: allow for very detailed, comprehensive answers
            base_optimal_max = 1800
        elif use_reranking:
            # Reranking only: allow for detailed answers
            base_optimal_max = 1400
        elif use_hybrid_search:
            # Hybrid search only: allow for comprehensive answers
            base_optimal_max = 1200
        else:
            # No advanced settings: standard range
            base_optimal_max = 800
        
        # Adjust optimal_max based on number of chunks used (more chunks = longer answer is acceptable)
        # If using more chunks than top_k, the answer can be longer while still being relevant
        if chunks_used > top_k:
            chunk_ratio = chunks_used / top_k
            # Increase optimal_max by up to 50% if using significantly more chunks
            optimal_max_adjustment = min(0.5, (chunk_ratio - 1) * 0.3)
            optimal_max = base_optimal_max * (1 + optimal_max_adjustment)
        else:
            optimal_max = base_optimal_max
        
        # Calculate average chunk score for relevance-based adjustments
        avg_chunk_score = 0.0
        if retrieved_chunks:
            scores = [chunk.get("score", 0.0) for chunk in retrieved_chunks]
            avg_chunk_score = sum(scores) / len(scores) if scores else 0.0
        
        # Reduce length penalty if using many relevant chunks or advanced settings with high quality chunks
        length_penalty_reduction = 0.0
        # Case 1: More chunks than requested (original logic)
        if chunks_used > top_k and avg_chunk_score > 0.4:
            # High relevance + more chunks = longer answer is justified
            relevance_factor = min(1.0, (avg_chunk_score - 0.4) / 0.3)  # 0.4-0.7 maps to 0-1
            chunk_factor = min(1.0, (chunks_used / top_k - 1) / 1.0)  # 1x-2x chunks maps to 0-1
            length_penalty_reduction = min(0.3, relevance_factor * chunk_factor * 0.3)
        # Case 2: Reranking with high quality chunks (even if chunks_used == top_k)
        elif use_reranking and avg_chunk_score > 0.4:
            # Reranking selects best chunks, so high avg_chunk_score justifies longer answer
            relevance_factor = min(1.0, (avg_chunk_score - 0.4) / 0.3)  # 0.4-0.7 maps to 0-1
            # Use chunk usage ratio, but don't require chunks_used > top_k
            chunk_factor = min(1.0, chunks_used / max(top_k, 1))  # 0.5-1.0 maps to 0-1
            length_penalty_reduction = min(0.3, relevance_factor * chunk_factor * 0.3)
        # Case 3: Hybrid search with high quality chunks
        elif use_hybrid_search and avg_chunk_score > 0.4:
            # Hybrid search provides better coverage, high avg_chunk_score justifies longer answer
            relevance_factor = min(1.0, (avg_chunk_score - 0.4) / 0.3)  # 0.4-0.7 maps to 0-1
            chunk_factor = min(1.0, chunks_used / max(top_k, 1))  # 0.5-1.0 maps to 0-1
            length_penalty_reduction = min(0.25, relevance_factor * chunk_factor * 0.25)
        
        if length_penalty_reduction > 0:
            logger.info(f"Quality evaluation: length_penalty_reduction={length_penalty_reduction:.2f} (chunks_used={chunks_used}, top_k={top_k}, avg_chunk_score={avg_chunk_score:.3f}, reranking={use_reranking}, hybrid={use_hybrid_search})")
        
        length_score_adjustment = 0.0
        if answer_len < 50:
            length_score_adjustment = -0.5  # Too short
        elif 50 <= answer_len < optimal_min:
            length_score_adjustment = 0.3 + (answer_len - 50) / (optimal_min - 50) * 0.3  # 0.3 to 0.6
        elif optimal_min <= answer_len <= optimal_max:
            # Optimal range: higher score for this range
            range_size = optimal_max - optimal_min
            position = (answer_len - optimal_min) / range_size if range_size > 0 else 0.5
            length_score_adjustment = 0.9 - position * 0.2  # 0.9 to 0.7 (optimal range)
        elif optimal_max < answer_len <= optimal_max + 700:
            # Getting long, but apply penalty reduction if using many relevant chunks or advanced settings
            # Base value increases with advanced settings (detailed answers are expected)
            if use_reranking and use_hybrid_search:
                base_long_value = 0.8  # Both settings: very detailed answers are good
            elif use_reranking or use_hybrid_search:
                base_long_value = 0.7  # One setting: detailed answers are good
            else:
                base_long_value = 0.5  # No advanced settings: standard penalty
            
            # Adjust base value based on chunk quality
            if avg_chunk_score > 0.6:
                base_long_value += 0.1  # High quality chunks justify longer answer
            elif avg_chunk_score > 0.5:
                base_long_value += 0.05  # Good quality chunks
            
            length_penalty = (answer_len - optimal_max) / 700 * 0.2
            adjusted_penalty = max(0.0, length_penalty - length_penalty_reduction)
            length_score_adjustment = base_long_value - adjusted_penalty  # Adjusted based on settings and quality
            logger.info(f"Quality evaluation: long answer (len={answer_len}, optimal_max={optimal_max}), base_long_value={base_long_value:.2f}, length_penalty={length_penalty:.2f}, adjusted_penalty={adjusted_penalty:.2f}, length_score_adjustment={length_score_adjustment:.2f}")
        else:
            # Very long, but still apply penalty reduction if highly relevant or using advanced settings
            # Base value increases with advanced settings
            if use_reranking and use_hybrid_search:
                base_very_long_value = 0.4  # Both settings: very long but detailed answers can be good
            elif use_reranking or use_hybrid_search:
                base_very_long_value = 0.3  # One setting: long detailed answers can be acceptable
            else:
                base_very_long_value = 0.2  # No advanced settings: standard penalty
            
            # Adjust base value based on chunk quality
            if avg_chunk_score > 0.6:
                base_very_long_value += 0.1  # High quality chunks justify very long answer
            elif avg_chunk_score > 0.5:
                base_very_long_value += 0.05  # Good quality chunks
            
            base_penalty = 0.2 + min(0.2, (answer_len - (optimal_max + 700)) / 2000)
            adjusted_penalty = max(0.0, base_penalty - length_penalty_reduction)
            length_score_adjustment = base_very_long_value - adjusted_penalty  # Adjusted based on settings and quality
            logger.info(f"Quality evaluation: very long answer (len={answer_len}, optimal_max={optimal_max}), base_very_long_value={base_very_long_value:.2f}, base_penalty={base_penalty:.2f}, adjusted_penalty={adjusted_penalty:.2f}, length_score_adjustment={length_score_adjustment:.2f}")
        base_score += length_score_adjustment
        logger.info(f"Quality evaluation: length_score_adjustment={length_score_adjustment:.2f} (optimal_range={optimal_min}-{optimal_max}), base_score={base_score:.2f}")
        
        # Boost if multiple chunks were used (more context)
        chunk_usage_boost = 0.0
        if chunks_used > 1:
            chunk_usage_boost = 0.2 + min(0.2, (chunks_used - 1) / top_k * 0.2)  # 0.2 to 0.4 based on chunk usage
            base_score += chunk_usage_boost
        
        # Don't penalize for fewer chunks if reranking is used (reranking selects best chunks)
        chunk_penalty = 0.0
        if chunks_used >= top_k * 0.8:  # Used most of requested chunks
            chunk_penalty = 0.15
            base_score += chunk_penalty
        elif chunks_used < top_k * 0.5 and not use_reranking:  # Only penalize if reranking is NOT used
            chunk_penalty = -0.2
            base_score += chunk_penalty
        
        if chunk_usage_boost > 0 or chunk_penalty != 0:
            logger.info(f"Quality evaluation: chunk_usage_boost={chunk_usage_boost:.2f}, chunk_penalty={chunk_penalty:.2f}, base_score={base_score:.2f}")
        
        # Increased boost for reranking (better relevance through specialized reranking)
        reranking_boost = 0.0
        if use_reranking:
            if chunks_used > 1:
                reranking_boost = 0.5  # Increased from 0.25 to 0.5
            else:
                reranking_boost = 0.3  # Even with 1 chunk, reranking improves quality
            base_score += reranking_boost
        
        # Increased boost for hybrid search (better coverage through BM25 + Vector)
        hybrid_boost = 0.0
        if use_hybrid_search:
            hybrid_boost = 0.35  # Increased from 0.15 to 0.35
            base_score += hybrid_boost
        
        if reranking_boost > 0 or hybrid_boost > 0:
            logger.info(f"Quality evaluation: reranking_boost={reranking_boost:.2f}, hybrid_boost={hybrid_boost:.2f}, base_score={base_score:.2f}")
        
        # More sophisticated relevance score evaluation
        if retrieved_chunks:
            scores = [chunk.get("score", 0.0) for chunk in retrieved_chunks]
            avg_score = sum(scores) / len(scores)
            max_score = max(scores)
            min_score = min(scores)
            score_variance = max_score - min_score
            
            # Adjust score thresholds for hybrid search (combined scores may be lower)
            # Hybrid search combines vector (0-1) and BM25 (0-∞) scores, so combined scores can be different
            high_threshold = 0.6 if use_hybrid_search else 0.75
            medium_threshold = 0.4 if use_hybrid_search else 0.6
            low_threshold = 0.15 if use_hybrid_search else 0.2
            
            # High average relevance
            relevance_boost = 0.0
            if avg_score > high_threshold:
                relevance_boost = 0.4  # Very high relevance
            elif avg_score > medium_threshold:
                relevance_boost = 0.25  # High relevance
            elif avg_score > 0.3:
                relevance_boost = 0.1  # Medium relevance
            elif avg_score < low_threshold:
                relevance_boost = -0.2  # Low relevance
            base_score += relevance_boost
            logger.info(f"Quality evaluation: avg_chunk_score={avg_score:.3f} (thresholds: high={high_threshold}, medium={medium_threshold}, low={low_threshold}), relevance_boost={relevance_boost:.2f}, base_score={base_score:.2f}")
            
            # Consistent high scores (low variance) is better
            consistency_boost = 0.0
            if score_variance < 0.1 and avg_score > medium_threshold:
                consistency_boost = 0.1  # Consistent high quality chunks
                base_score += consistency_boost
                logger.info(f"Quality evaluation: consistency_boost={consistency_boost:.2f} (variance={score_variance:.3f}), base_score={base_score:.2f}")
        
        # Log base_score BEFORE normalization to see real differences
        logger.info(f"Quality evaluation: base_score before normalization={base_score:.2f}")
        
        # Normalize to 0-5 range
        final_score = min(5.0, max(0.0, base_score))
        
        # Log if score was clipped
        if base_score > 5.0:
            logger.warning(f"Quality evaluation: base_score ({base_score:.2f}) exceeded maximum (5.0), clipped to {final_score:.2f}")
        
        logger.info(
            f"Quality evaluation completed: length={answer_len}, chunks={chunks_used}/{top_k}, "
            f"context_overlap={context_overlap:.2f}, reranking={use_reranking}, "
            f"hybrid={use_hybrid_search}, base_score={base_score:.2f}, final_score={final_score:.2f}"
        )
        return final_score
    
    def _init_reranker(self, model_name: str):
        """Initialize reranker model"""
        if not CROSS_ENCODER_AVAILABLE:
            logger.warning("CrossEncoder not available, reranking will use LLM fallback")
            return
        
        try:
            # Try to load the specified model
            models_to_try = []
            if model_name == "ms-marco-MiniLM-L-6-v2":
                models_to_try = [
                    "cross-encoder/ms-marco-MiniLM-L-6-v2",
                    "ms-marco-MiniLM-L-6-v2"
                ]
            elif model_name == "bge-reranker-v2-m3":
                models_to_try = [
                    "BAAI/bge-reranker-v2-m3",
                    "bge-reranker-v2-m3"
                ]
            else:
                models_to_try = [model_name]
            
            for model_path in models_to_try:
                try:
                    logger.info(f"Attempting to load reranker model: {model_path}...")
                    self.reranker_model = CrossEncoder(model_path, device='cpu')  # Use CPU for compatibility
                    self.reranker_model_name = model_path
                    logger.info(f"Successfully loaded reranker model: {model_path}")
                    return
                except Exception as e:
                    logger.warning(f"Failed to load reranker model {model_path}: {str(e)}")
                    continue
            
            logger.warning("All reranker models failed to load, will use LLM fallback")
            self.reranker_model = None
        except Exception as e:
            logger.error(f"Error initializing reranker: {str(e)}", exc_info=True)
            self.reranker_model = None
    
    def _rerank_chunks_specialized(
        self,
        question: str,
        chunks: List[Dict[str, Any]],
        top_k: int
    ) -> List[Dict[str, Any]]:
        """Rerank chunks using specialized cross-encoder model"""
        if self.reranker_model is None:
            logger.warning(f"Specialized reranker model not available, using original order")
            return sorted(chunks, key=lambda x: x.get("score", 0), reverse=True)[:top_k]
        if len(chunks) <= top_k:
            logger.info(f"Specialized reranking skipped: only {len(chunks)} chunks available (need > {top_k})")
            return sorted(chunks, key=lambda x: x.get("score", 0), reverse=True)[:top_k]
        
        try:
            # Prepare pairs for cross-encoder: (question, chunk_text)
            pairs = [(question, chunk.get("chunk_text", chunk.get("text", ""))) for chunk in chunks]
            
            # Get scores from cross-encoder
            scores = self.reranker_model.predict(pairs)
            
            # Combine scores with original scores (weighted average)
            for i, chunk in enumerate(chunks):
                rerank_score = float(scores[i])
                original_score = chunk.get("score", 0.0)
                # Weighted combination: 70% reranker, 30% original
                chunk["rerank_score"] = rerank_score
                chunk["combined_score"] = 0.7 * rerank_score + 0.3 * original_score
            
            # Sort by combined score
            reranked = sorted(chunks, key=lambda x: x.get("combined_score", x.get("rerank_score", 0)), reverse=True)
            
            # Log score examples for debugging
            if len(reranked) > 0:
                top_score = reranked[0].get("combined_score", reranked[0].get("rerank_score", 0))
                bottom_score = reranked[-1].get("combined_score", reranked[-1].get("rerank_score", 0)) if len(reranked) > 1 else top_score
                logger.info(f"Specialized reranking completed: {len(chunks)} chunks reranked, top score={top_score:.4f}, bottom score={bottom_score:.4f}, returning top {top_k}")
            else:
                logger.info(f"Specialized reranking completed: {len(chunks)} chunks reranked, returning top {top_k}")
            return reranked[:top_k]
        except Exception as e:
            logger.warning(f"Specialized reranking failed: {str(e)}, using original order")
            return sorted(chunks, key=lambda x: x.get("score", 0), reverse=True)[:top_k]
    
    def _multi_hop_reasoning(self, question: str, model: str) -> List[str]:
        """Break complex question into sub-queries using DSPy"""
        if not DSPY_AVAILABLE:
            logger.warning("DSPy not available, skipping multi-hop reasoning")
            return []
        
        try:
            # Use LLM to break down complex questions
            prompt = f"""Разбей следующий сложный вопрос на 2-4 более простых подвопроса, которые помогут найти ответ.
Если вопрос простой и не требует разбиения, верни только исходный вопрос.

Вопрос: {question}

Подвопросы (каждый с новой строки, без нумерации):"""
            
            response = self.client.chat.completions.create(
                model=model or self.default_model,
                messages=[
                    {"role": "system", "content": "Ты помощник, который разбивает сложные вопросы на подвопросы для более точного поиска информации."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=300
            )
            
            sub_queries = [line.strip() for line in response.choices[0].message.content.split('\n') if line.strip()]
            
            # If only one query or same as original, return original
            if len(sub_queries) <= 1 or (len(sub_queries) == 1 and sub_queries[0] == question):
                return [question]
            
            logger.info(f"Multi-hop reasoning generated {len(sub_queries)} sub-queries")
            return sub_queries[:4]  # Limit to 4 sub-queries
            
        except Exception as e:
            logger.warning(f"Multi-hop reasoning failed: {str(e)}, using original question")
            return [question]
    
    def _evaluate_answer_quality_advanced(
        self,
        question: str,
        answer: str,
        retrieved_chunks: List[Dict[str, Any]],
        model: str,
        use_reranking: bool = True,
        use_hybrid_search: bool = False,
        top_k: int = 5
    ) -> Dict[str, float]:
        """Advanced quality evaluation with groundedness, completeness, and relevance"""
        try:
            # Prepare context from chunks
            context = "\n\n".join([chunk.get("chunk_text", "") for chunk in retrieved_chunks])
            
            # Groundedness check: are facts in answer supported by context?
            groundedness_prompt = f"""Оцени, насколько факты в ответе подтверждаются предоставленным контекстом.
Верни число от 0.0 до 1.0, где 1.0 = все факты подтверждены, 0.0 = много неподтвержденных фактов.

Контекст:
{context[:2000]}

Ответ:
{answer}

Оценка groundedness (только число от 0.0 до 1.0):"""
            
            groundedness_response = self.client.chat.completions.create(
                model=model or self.default_model,
                messages=[
                    {"role": "system", "content": "Ты помощник, который оценивает, насколько ответ основан на фактах из контекста."},
                    {"role": "user", "content": groundedness_prompt}
                ],
                temperature=0.1,
                max_tokens=50
            )
            
            groundedness_text = groundedness_response.choices[0].message.content.strip()
            # Extract number from response (re already imported at top)
            groundedness_match = re.search(r'0?\.?\d+', groundedness_text)
            groundedness = float(groundedness_match.group()) if groundedness_match else 0.5
            groundedness = max(0.0, min(1.0, groundedness))
            
            # Completeness check: does answer cover all aspects of question?
            completeness_prompt = f"""Оцени, насколько полно ответ покрывает все аспекты вопроса.
Верни число от 0.0 до 1.0, где 1.0 = полный ответ, 0.0 = неполный ответ.

Вопрос: {question}

Ответ: {answer}

Оценка completeness (только число от 0.0 до 1.0):"""
            
            completeness_response = self.client.chat.completions.create(
                model=model or self.default_model,
                messages=[
                    {"role": "system", "content": "Ты помощник, который оценивает полноту ответа относительно вопроса."},
                    {"role": "user", "content": completeness_prompt}
                ],
                temperature=0.1,
                max_tokens=50
            )
            
            completeness_text = completeness_response.choices[0].message.content.strip()
            completeness_match = re.search(r'0?\.?\d+', completeness_text)
            completeness = float(completeness_match.group()) if completeness_match else 0.5
            completeness = max(0.0, min(1.0, completeness))
            
            # Relevance: existing simple check
            relevance = self._evaluate_answer_quality(
                question, 
                answer, 
                retrieved_chunks,
                top_k=top_k,
                use_reranking=use_reranking,
                use_hybrid_search=use_hybrid_search
            ) / 5.0  # Normalize to 0-1
            
            # Overall score: weighted average
            overall_score = (groundedness * 0.4 + completeness * 0.3 + relevance * 0.3) * 5.0  # Scale to 0-5
            
            return {
                "groundedness": groundedness,
                "completeness": completeness,
                "relevance": relevance,
                "overall_score": overall_score
            }
        except Exception as e:
            logger.warning(f"Advanced quality evaluation failed: {str(e)}, using simple evaluation")
            simple_score = self._evaluate_answer_quality(
                question, 
                answer, 
                retrieved_chunks,
                top_k=top_k,
                use_reranking=use_reranking,
                use_hybrid_search=use_hybrid_search
            )
            return {
                "groundedness": 0.5,
                "completeness": 0.5,
                "relevance": simple_score / 5.0,
                "overall_score": simple_score
            }
    
    def _expand_query(self, question: str, model: str) -> List[str]:
        """
        Expand query by generating alternative formulations and hypothetical answer
        Returns list of additional search queries
        """
        try:
            # Generate alternative question formulations
            reformulation_prompt = f"""Переформулируй следующий вопрос 2-3 разными способами, сохраняя смысл.
Вопрос: {question}

Переформулировки (каждую с новой строки, без нумерации):"""
            
            response = self.client.chat.completions.create(
                model=model or self.default_model,
                messages=[
                    {"role": "system", "content": "Ты помощник, который переформулирует вопросы, сохраняя их смысл."},
                    {"role": "user", "content": reformulation_prompt}
                ],
                temperature=0.5,
                max_tokens=200
            )
            
            reformulations = [line.strip() for line in response.choices[0].message.content.split('\n') if line.strip()]
            
            # Generate hypothetical answer to create better search query
            hypothetical_prompt = f"""На основе следующего вопроса, сформулируй краткий гипотетический ответ (1-2 предложения).
Этот ответ будет использован для поиска релевантной информации.

Вопрос: {question}

Гипотетический ответ:"""
            
            response2 = self.client.chat.completions.create(
                model=model or self.default_model,
                messages=[
                    {"role": "system", "content": "Ты помощник, который создает гипотетические ответы для улучшения поиска."},
                    {"role": "user", "content": hypothetical_prompt}
                ],
                temperature=0.3,
                max_tokens=150
            )
            
            hypothetical_answer = response2.choices[0].message.content.strip()
            
            # Combine reformulations and hypothetical answer
            expanded_queries = reformulations[:2]  # Take first 2 reformulations
            if hypothetical_answer:
                expanded_queries.append(hypothetical_answer)
            
            logger.info(f"Query expansion generated {len(expanded_queries)} additional queries")
            return expanded_queries
            
        except Exception as e:
            logger.warning(f"Query expansion failed: {str(e)}, using original question only")
            return []
    
    def _rerank_chunks(
        self,
        question: str,
        chunks: List[Dict[str, Any]],
        top_k: int,
        model: str
    ) -> List[Dict[str, Any]]:
        """
        Rerank chunks by relevance using LLM
        Returns top_k most relevant chunks
        """
        if len(chunks) <= top_k:
            logger.info(f"LLM reranking skipped: only {len(chunks)} chunks available (need > {top_k})")
            return chunks
        
        try:
            # Prepare chunks for reranking
            chunks_text = "\n\n".join([
                f"[Chunk {i+1}]: {chunk.get('chunk_text', chunk.get('text', ''))}"
                for i, chunk in enumerate(chunks)
            ])
            
            rerank_prompt = f"""Оцени релевантность следующих фрагментов текста для ответа на вопрос.
Верни номера топ-{top_k} наиболее релевантных фрагментов, разделенные запятыми (например: 1,3,5).

Вопрос: {question}

Фрагменты:
{chunks_text}

Топ-{top_k} наиболее релевантных фрагментов (номера через запятую):"""
            
            response = self.client.chat.completions.create(
                model=model or self.default_model,
                messages=[
                    {"role": "system", "content": "Ты помощник, который оценивает релевантность текстовых фрагментов для ответа на вопрос."},
                    {"role": "user", "content": rerank_prompt}
                ],
                temperature=0.1,
                max_tokens=100
            )
            
            # Parse response to get chunk indices
            result_text = response.choices[0].message.content.strip()
            try:
                # Extract numbers from response
                indices = [int(x.strip()) - 1 for x in re.findall(r'\d+', result_text)[:top_k]]
                indices = [i for i in indices if 0 <= i < len(chunks)]
                
                if len(indices) >= top_k:
                    reranked = [chunks[i] for i in indices[:top_k]]
                    logger.info(f"LLM reranking completed: selected {len(reranked)} chunks from {len(chunks)} (indices: {indices[:top_k]})")
                    return reranked
            except Exception as e:
                logger.warning(f"Failed to parse reranking response: {str(e)}")
            
            # Fallback: use original scoring
            return sorted(chunks, key=lambda x: x.get("score", 0), reverse=True)[:top_k]
            
        except Exception as e:
            logger.warning(f"Reranking failed: {str(e)}, using original order")
            return sorted(chunks, key=lambda x: x.get("score", 0), reverse=True)[:top_k]

