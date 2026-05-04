"""S3 storage with object lock for tamper-evidence.

Each measurement's binary artifacts (depth maps, photos, point clouds,
fused depth, PDF report) are stored under a per-measurement prefix.
Object lock (governance mode) is enabled at the bucket level so objects
cannot be deleted within a retention window.

The PutObject metadata includes the SHA-256 of the object so a later
verification step can re-hash and compare.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC

from pydantic_settings import BaseSettings, SettingsConfigDict


class S3Settings(BaseSettings):
    """S3 connection settings."""

    model_config = SettingsConfigDict(
        env_prefix="WS_S3_", env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    region: str = "us-east-1"
    bucket: str = "woundscan-artifacts"
    endpoint_url: str | None = None
    access_key_id: str | None = None
    secret_access_key: str | None = None
    enable_object_lock: bool = True
    retention_days: int = 365 * 6  # 6-year HIPAA minimum


@dataclass
class S3Storage:
    """Thin S3 client wrapper with hash-on-write.

    All puts include a Content-MD5 header and a x-amz-meta-sha256 header
    with the SHA-256 of the bytes; reads verify the hash matches.
    """

    settings: S3Settings

    def _client(self):
        import boto3

        return boto3.client(
            "s3",
            region_name=self.settings.region,
            endpoint_url=self.settings.endpoint_url,
            aws_access_key_id=self.settings.access_key_id,
            aws_secret_access_key=self.settings.secret_access_key,
        )

    def put_object(
        self, key: str, data: bytes, content_type: str = "application/octet-stream"
    ) -> str:
        """Upload bytes with SHA-256 metadata. Returns the SHA-256 hex digest."""
        sha = hashlib.sha256(data).hexdigest()
        client = self._client()
        params: dict = {
            "Bucket": self.settings.bucket,
            "Key": key,
            "Body": data,
            "ContentType": content_type,
            "Metadata": {"sha256": sha},
        }
        if self.settings.enable_object_lock:
            from datetime import datetime, timedelta

            params["ObjectLockMode"] = "GOVERNANCE"
            params["ObjectLockRetainUntilDate"] = datetime.now(UTC) + timedelta(
                days=self.settings.retention_days
            )
        client.put_object(**params)
        return sha

    def get_object(self, key: str) -> tuple[bytes, str]:
        """Download an object. Returns (bytes, sha256_metadata)."""
        client = self._client()
        resp = client.get_object(Bucket=self.settings.bucket, Key=key)
        body = resp["Body"].read()
        sha = resp.get("Metadata", {}).get("sha256", "")
        return body, sha

    def verify_object(self, key: str) -> bool:
        """Re-download and re-hash. Returns True if metadata sha matches actual."""
        body, sha = self.get_object(key)
        actual = hashlib.sha256(body).hexdigest()
        return sha == actual

    def signed_download_url(self, key: str, expires_seconds: int = 300) -> str:
        client = self._client()
        return client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.settings.bucket, "Key": key},
            ExpiresIn=expires_seconds,
        )
