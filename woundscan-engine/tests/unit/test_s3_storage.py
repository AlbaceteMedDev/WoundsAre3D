"""Tests for S3Storage: hash-on-write, verification, presigned URLs.

Uses moto to mock S3 in-process so the hash chain, metadata round-trip,
and object-lock retention paths are all exercised without touching AWS.
"""

from __future__ import annotations

import hashlib

import boto3
import pytest
from moto import mock_aws

from woundscan.storage.s3 import S3Settings, S3Storage


@pytest.fixture
def settings_no_lock() -> S3Settings:
    return S3Settings(
        region="us-east-1",
        bucket="ws-test-bucket",
        access_key_id="test",
        secret_access_key="test",
        enable_object_lock=False,
    )


@pytest.fixture
def settings_with_lock() -> S3Settings:
    return S3Settings(
        region="us-east-1",
        bucket="ws-test-lock-bucket",
        access_key_id="test",
        secret_access_key="test",
        enable_object_lock=True,
        retention_days=30,
    )


@pytest.fixture
def mocked_s3():
    with mock_aws():
        yield


def _make_bucket(name: str, *, object_lock: bool = False) -> None:
    client = boto3.client("s3", region_name="us-east-1")
    kwargs: dict = {"Bucket": name}
    if object_lock:
        kwargs["ObjectLockEnabledForBucket"] = True
    client.create_bucket(**kwargs)


class TestPutObject:
    def test_returns_sha256_of_body(self, mocked_s3, settings_no_lock):
        _make_bucket(settings_no_lock.bucket)
        storage = S3Storage(settings=settings_no_lock)
        data = b"hello wound"
        sha = storage.put_object("m/1/depth.bin", data)
        assert sha == hashlib.sha256(data).hexdigest()

    def test_stores_sha256_in_metadata(self, mocked_s3, settings_no_lock):
        _make_bucket(settings_no_lock.bucket)
        storage = S3Storage(settings=settings_no_lock)
        data = b"metadata roundtrip"
        sha = storage.put_object("m/1/cloud.bin", data)
        client = boto3.client("s3", region_name="us-east-1")
        head = client.head_object(Bucket=settings_no_lock.bucket, Key="m/1/cloud.bin")
        assert head["Metadata"]["sha256"] == sha

    def test_sets_content_type(self, mocked_s3, settings_no_lock):
        _make_bucket(settings_no_lock.bucket)
        storage = S3Storage(settings=settings_no_lock)
        storage.put_object("m/1/report.pdf", b"%PDF-1.4", content_type="application/pdf")
        client = boto3.client("s3", region_name="us-east-1")
        head = client.head_object(Bucket=settings_no_lock.bucket, Key="m/1/report.pdf")
        assert head["ContentType"] == "application/pdf"

    def test_object_lock_path_writes_retention(self, mocked_s3, settings_with_lock):
        _make_bucket(settings_with_lock.bucket, object_lock=True)
        storage = S3Storage(settings=settings_with_lock)
        storage.put_object("m/lock/depth.bin", b"locked-bytes")
        client = boto3.client("s3", region_name="us-east-1")
        head = client.head_object(
            Bucket=settings_with_lock.bucket, Key="m/lock/depth.bin"
        )
        assert head["ObjectLockMode"] == "GOVERNANCE"
        assert "ObjectLockRetainUntilDate" in head


class TestGetObject:
    def test_roundtrip_returns_bytes_and_sha(self, mocked_s3, settings_no_lock):
        _make_bucket(settings_no_lock.bucket)
        storage = S3Storage(settings=settings_no_lock)
        data = b"\x00\x01\x02 wound scan"
        sha = storage.put_object("m/2/blob.bin", data)
        body, meta_sha = storage.get_object("m/2/blob.bin")
        assert body == data
        assert meta_sha == sha


class TestVerifyObject:
    def test_returns_true_for_untouched_object(self, mocked_s3, settings_no_lock):
        _make_bucket(settings_no_lock.bucket)
        storage = S3Storage(settings=settings_no_lock)
        storage.put_object("m/3/ok.bin", b"trustworthy bytes")
        assert storage.verify_object("m/3/ok.bin") is True

    def test_returns_false_when_metadata_sha_mismatches_body(
        self, mocked_s3, settings_no_lock
    ):
        _make_bucket(settings_no_lock.bucket)
        client = boto3.client("s3", region_name="us-east-1")
        client.put_object(
            Bucket=settings_no_lock.bucket,
            Key="m/3/tampered.bin",
            Body=b"actual bytes",
            Metadata={"sha256": hashlib.sha256(b"different bytes").hexdigest()},
        )
        storage = S3Storage(settings=settings_no_lock)
        assert storage.verify_object("m/3/tampered.bin") is False


class TestSignedDownloadUrl:
    def test_returns_presigned_url_for_key(self, mocked_s3, settings_no_lock):
        _make_bucket(settings_no_lock.bucket)
        storage = S3Storage(settings=settings_no_lock)
        storage.put_object("m/4/dl.bin", b"download me")
        url = storage.signed_download_url("m/4/dl.bin", expires_seconds=60)
        assert url.startswith("https://")
        assert settings_no_lock.bucket in url
        assert "m/4/dl.bin" in url
        # boto3 may emit SigV4 (X-Amz-Signature) or SigV2 (Signature=) depending
        # on the configured signing version — both are valid presigned URLs.
        assert "X-Amz-Signature" in url or "Signature=" in url
        assert "Expires" in url
