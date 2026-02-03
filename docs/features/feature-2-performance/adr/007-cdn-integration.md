# ADR-007: CDN Integration for Static Assets

**Status:** Accepted (Optional Enhancement)
**Date:** 2026-02-03
**Context:** Performance Optimization Feature

---

## Context

Audio files are served directly from the backend, causing:
1. Slow downloads for geographically distributed users
2. High bandwidth costs on origin server
3. No edge caching
4. Single point of failure

---

## Decision

Integrate CDN (Cloudflare R2 or similar) for serving audio files and static assets.

### Architecture

```
┌─────────────┐
│   User      │
└──────┬──────┘
       │
       ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  CDN Edge   │ ←→ │  CDN Edge   │ ←→ │  CDN Edge   │
│  (Frankfurt)│     │   (Tokyo)   │     │  (New York) │
└──────┬──────┘     └──────┬──────┘     └──────┬──────┘
       │                   │                   │
       └───────────────────┼───────────────────┘
                           │ Cache miss
                           ▼
                  ┌─────────────────┐
                  │  CDN Origin     │
                  │  (Cloudflare R2)│
                  └─────────────────┘
```

### Implementation

```python
# backend/app/services/cdn_service.py

import boto3
from botocore.exceptions import ClientError

class CDNService:
    """CDN integration using S3-compatible API (Cloudflare R2)"""

    def __init__(self):
        self.client = boto3.client(
            's3',
            endpoint_url=settings.cdn_endpoint_url,
            aws_access_key_id=settings.cdn_access_key,
            aws_secret_access_key=settings.cdn_secret_key
        )
        self.bucket_name = settings.cdn_bucket_name

    def upload_audio(self, file_path: str, transcript_id: str) -> str:
        """Upload audio file to CDN"""
        key = f"audio/{transcript_id}/{os.path.basename(file_path)}"

        try:
            self.client.upload_file(
                Filename=file_path,
                Bucket=self.bucket_name,
                Key=key,
                ExtraArgs={
                    'ContentType': 'audio/mpeg',
                    'CacheControl': 'public, max-age=31536000',  # 1 year
                }
            )

            return f"{settings.cdn_public_url}/{key}"

        except ClientError as e:
            logger.error(f"CDN upload failed: {e}")
            # Fallback to local hosting
            return f"/api/files/{transcript_id}/{os.path.basename(file_path)}"

    def delete_audio(self, transcript_id: str, filename: str) -> None:
        """Delete audio file from CDN"""
        key = f"audio/{transcript_id}/{filename}"

        try:
            self.client.delete_object(
                Bucket=self.bucket_name,
                Key=key
            )
        except ClientError as e:
            logger.error(f"CDN deletion failed: {e}")
```

### Cache Headers

```nginx
# nginx.conf for CDN assets
location /api/files/ {
    # Enable browser caching
    add_header Cache-Control "public, max-age=31536000, immutable";
    add_header X-Content-Type-Options "nosniff";

    # CORS for CDN
    add_header Access-Control-Allow-Origin "*";
}
```

---

## Consequences

**Positive:**
- Global edge delivery (<100ms)
- 90%+ cache hit rate
- Reduced origin bandwidth

**Negative:**
- Additional service complexity
- CDN costs (though R2 is cost-effective)
- Eventual consistency on updates

---

**Document Control**

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-03 | Performance Team | Initial ADR |
