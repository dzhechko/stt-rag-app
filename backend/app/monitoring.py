from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Response
import time

# Metrics
transcription_requests = Counter(
    'stt_transcription_requests_total',
    'Total number of transcription requests',
    ['status']
)

transcription_duration = Histogram(
    'stt_transcription_duration_seconds',
    'Time spent processing transcriptions',
    buckets=[1, 5, 10, 30, 60, 120, 300]
)

summarization_requests = Counter(
    'stt_summarization_requests_total',
    'Total number of summarization requests',
    ['status']
)

rag_queries = Counter(
    'stt_rag_queries_total',
    'Total number of RAG queries',
    ['status']
)

rag_query_duration = Histogram(
    'stt_rag_query_duration_seconds',
    'Time spent processing RAG queries',
    buckets=[0.5, 1, 2, 5, 10, 30]
)

active_transcriptions = Gauge(
    'stt_active_transcriptions',
    'Number of active transcriptions'
)

active_summarizations = Gauge(
    'stt_active_summarizations',
    'Number of active summarizations'
)


def setup_monitoring(app):
    """Setup Prometheus metrics endpoint"""
    
    @app.get("/metrics")
    async def metrics():
        return Response(
            content=generate_latest(),
            media_type=CONTENT_TYPE_LATEST
        )

