"""PostgreSQL storage with row-level security and column-level encryption.

The database stores:
- Patients (identifier, encrypted PII columns, opaque token for app use)
- Wounds (per-patient, with anatomic location)
- Measurements (the result of each scan + provenance)
- Audit log (every access)
- Phantom calibrations
- Saline cross-checks

Row-level security policies are enforced at the Postgres level so that
even direct DB access cannot bypass RBAC. Application code passes the
clinician's session as a Postgres session variable.

Migrations are managed by Alembic (see migrations/ directory).
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    String,
    Text,
)
from sqlalchemy import (
    create_engine as sa_create_engine,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class DatabaseSettings(BaseSettings):
    """Postgres connection settings, loaded from env."""

    model_config = SettingsConfigDict(
        env_prefix="WS_DB_", env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    host: str = "localhost"
    port: int = 5432
    database: str = "woundscan"
    user: str = "woundscan"
    password: str = "woundscan"  # MUST be overridden in production via env

    @property
    def dsn(self) -> str:
        return (
            f"postgresql+psycopg2://{self.user}:{self.password}@"
            f"{self.host}:{self.port}/{self.database}"
        )


class Base(DeclarativeBase):
    pass


class Patient(Base):
    __tablename__ = "patients"
    id = Column(UUID(as_uuid=True), primary_key=True)
    opaque_token = Column(String, unique=True, nullable=False, index=True)
    encrypted_mrn = Column(Text, nullable=True)
    encrypted_first_name = Column(Text, nullable=True)
    encrypted_last_name = Column(Text, nullable=True)
    encrypted_dob = Column(Text, nullable=True)
    organization_id = Column(UUID(as_uuid=True), nullable=False)
    created_at = Column(DateTime, nullable=False)
    deleted_at = Column(DateTime, nullable=True)


class Wound(Base):
    __tablename__ = "wounds"
    id = Column(UUID(as_uuid=True), primary_key=True)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False, index=True)
    anatomic_location = Column(String, nullable=False)
    wound_type = Column(String, nullable=False)
    onset_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False)
    notes = Column(Text, nullable=True)


class Measurement(Base):
    __tablename__ = "measurements"
    id = Column(UUID(as_uuid=True), primary_key=True)
    wound_id = Column(UUID(as_uuid=True), ForeignKey("wounds.id"), nullable=False, index=True)
    clinician_id = Column(UUID(as_uuid=True), nullable=False)
    captured_at = Column(DateTime, nullable=False)
    processed_at = Column(DateTime, nullable=False)
    volume_cm3 = Column(Float, nullable=False)
    volume_ci_low = Column(Float, nullable=False)
    volume_ci_high = Column(Float, nullable=False)
    surface_area_cm2 = Column(Float, nullable=False)
    surface_area_ci_low = Column(Float, nullable=False)
    surface_area_ci_high = Column(Float, nullable=False)
    max_depth_cm = Column(Float, nullable=False)
    mean_depth_cm = Column(Float, nullable=False)
    perimeter_cm = Column(Float, nullable=False)
    footprint_area_cm2 = Column(Float, nullable=False)
    quality_grade = Column(String(1), nullable=False)
    quality_score = Column(Float, nullable=False)
    provenance_json = Column(JSONB, nullable=False)
    s3_artifact_prefix = Column(String, nullable=False)
    signed_off_at = Column(DateTime, nullable=True)
    signed_off_by = Column(UUID(as_uuid=True), nullable=True)


class AuditLogEntry(Base):
    __tablename__ = "audit_log"
    id = Column(UUID(as_uuid=True), primary_key=True)
    occurred_at = Column(DateTime, nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), nullable=True)
    organization_id = Column(UUID(as_uuid=True), nullable=True)
    action = Column(String, nullable=False)
    resource_type = Column(String, nullable=False)
    resource_id = Column(String, nullable=False)
    metadata_json = Column(JSONB, nullable=False)


class PhantomScanRecord(Base):
    __tablename__ = "phantom_scans"
    id = Column(UUID(as_uuid=True), primary_key=True)
    clinician_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    phantom_catalog_id = Column(String, nullable=False)
    captured_at = Column(DateTime, nullable=False)
    measured_volume_cm3 = Column(Float, nullable=False)
    measured_surface_area_cm2 = Column(Float, nullable=False)
    true_volume_cm3 = Column(Float, nullable=False)
    true_surface_area_cm2 = Column(Float, nullable=False)


class SalineCrossCheck(Base):
    __tablename__ = "saline_cross_checks"
    id = Column(UUID(as_uuid=True), primary_key=True)
    measurement_id = Column(UUID(as_uuid=True), ForeignKey("measurements.id"), nullable=False)
    saline_volume_ml = Column(Float, nullable=False)
    captured_at = Column(DateTime, nullable=False)
    notes = Column(Text, nullable=True)


_engine_singleton = None
_session_factory = None


def create_engine(settings: DatabaseSettings | None = None):
    """Create or return cached SQLAlchemy engine."""
    global _engine_singleton, _session_factory
    if _engine_singleton is None:
        s = settings or DatabaseSettings()
        _engine_singleton = sa_create_engine(s.dsn, pool_pre_ping=True)
        _session_factory = sessionmaker(bind=_engine_singleton, expire_on_commit=False)
    return _engine_singleton


@contextmanager
def get_session(settings: DatabaseSettings | None = None) -> Iterator[Session]:
    """Yield a SQLAlchemy session; commits on success, rolls back on exception."""
    create_engine(settings)
    assert _session_factory is not None
    sess = _session_factory()
    try:
        yield sess
        sess.commit()
    except Exception:
        sess.rollback()
        raise
    finally:
        sess.close()
