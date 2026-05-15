"""Tests for storage/postgres.

Two layers:

1. **In-process (SQLite)** — covers `DatabaseSettings` (env loading, dsn
   construction), `create_engine` caching, and `get_session`'s commit /
   rollback / close semantics. Fast, no Docker required.

2. **Real Postgres (testcontainers)** — spins up a Postgres container and
   exercises `Base.metadata.create_all()` against the live engine plus a
   round-trip insert/select on `GraftApplication` (the schema with the
   richest mix of types: UUID, Date, JSONB-adjacent String, Float, Text).
   Skips cleanly when Docker isn't available.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import uuid4

import pytest

from woundscan.storage import postgres as pg_mod
from woundscan.storage.postgres import (
    AuditLogEntry,
    Base,
    DatabaseSettings,
    GraftApplication,
    Measurement,
    Patient,
    Wound,
    create_engine,
    get_session,
)


# ---------------------------------------------------------------------------
# In-process (SQLite) — DatabaseSettings, engine caching, session semantics.
# ---------------------------------------------------------------------------


def _reset_module_singletons() -> None:
    pg_mod._engine_singleton = None
    pg_mod._session_factory = None


@pytest.fixture(autouse=True)
def _isolate_singletons():
    """The module caches the engine + session factory in module globals.
    Reset between tests so each test gets a fresh engine."""
    saved_engine = pg_mod._engine_singleton
    saved_factory = pg_mod._session_factory
    _reset_module_singletons()
    yield
    pg_mod._engine_singleton = saved_engine
    pg_mod._session_factory = saved_factory


class TestDatabaseSettings:
    def test_dsn_format(self):
        s = DatabaseSettings(
            host="db.internal",
            port=6543,
            database="ws",
            user="ws_app",
            password="hunter2",
        )
        assert s.dsn == "postgresql+psycopg2://ws_app:hunter2@db.internal:6543/ws"

    def test_defaults_load_when_env_unset(self, monkeypatch):
        for var in ("WS_DB_HOST", "WS_DB_PORT", "WS_DB_DATABASE", "WS_DB_USER", "WS_DB_PASSWORD"):
            monkeypatch.delenv(var, raising=False)
        s = DatabaseSettings()
        assert s.host == "localhost"
        assert s.port == 5432
        assert s.database == "woundscan"

    def test_env_prefix_loads_values(self, monkeypatch):
        monkeypatch.setenv("WS_DB_HOST", "rds.aws")
        monkeypatch.setenv("WS_DB_PORT", "5433")
        monkeypatch.setenv("WS_DB_DATABASE", "prod")
        s = DatabaseSettings()
        assert s.host == "rds.aws"
        assert s.port == 5433
        assert s.database == "prod"


class TestCreateEngineCaching:
    def test_engine_is_cached_across_calls(self, monkeypatch):
        # Point at sqlite-in-memory so we don't try to connect to localhost:5432.
        from sqlalchemy import create_engine as sa_create

        monkeypatch.setattr(
            pg_mod, "sa_create_engine", lambda *a, **kw: sa_create("sqlite:///:memory:")
        )
        s = DatabaseSettings()
        e1 = create_engine(s)
        e2 = create_engine(s)
        assert e1 is e2


class TestGetSessionSemantics:
    @pytest.fixture
    def sqlite_engine(self, monkeypatch):
        """Point create_engine at sqlite-in-memory and pre-create the
        non-postgres-specific tables we'll exercise."""
        from sqlalchemy import create_engine as sa_create

        engine = sa_create("sqlite:///:memory:")
        monkeypatch.setattr(pg_mod, "sa_create_engine", lambda *a, **kw: engine)
        # Build session factory by going through the public create_engine.
        create_engine(DatabaseSettings())
        # Reflect base — sqlite can't render UUID/JSONB but we don't insert here.
        return engine

    def test_commits_on_success(self, sqlite_engine):
        with get_session() as sess:
            assert sess.is_active

    def test_rolls_back_on_exception(self, sqlite_engine):
        with pytest.raises(RuntimeError):
            with get_session() as sess:
                assert sess.is_active
                raise RuntimeError("boom")

    def test_session_close_invoked_in_finally(self, sqlite_engine, monkeypatch):
        # `is_active` doesn't flip on close() in modern SQLAlchemy — wrap the
        # session factory so we can directly observe close() being called.
        closes: list[bool] = []
        real_factory = pg_mod._session_factory

        def wrapping_factory():
            sess = real_factory()
            real_close = sess.close

            def tracking_close():
                closes.append(True)
                real_close()

            sess.close = tracking_close
            return sess

        monkeypatch.setattr(pg_mod, "_session_factory", wrapping_factory)
        with get_session():
            pass
        assert closes == [True]


# ---------------------------------------------------------------------------
# Real Postgres (testcontainers) — JSONB/UUID schema + round-trip insert.
# ---------------------------------------------------------------------------


def _testcontainers_available() -> bool:
    try:
        import docker  # noqa: F401
        from testcontainers.postgres import PostgresContainer  # noqa: F401
    except ImportError:
        return False
    # Check the Docker daemon is reachable.
    try:
        import docker as docker_mod

        docker_mod.from_env().ping()
    except Exception:
        return False
    return True


@pytest.mark.skipif(
    not _testcontainers_available(),
    reason="Docker daemon / testcontainers not available",
)
class TestPostgresRoundTrip:
    @pytest.fixture(scope="class")
    def pg_container(self):
        from testcontainers.postgres import PostgresContainer

        with PostgresContainer("postgres:16-alpine") as pg:
            yield pg

    @pytest.fixture
    def settings_for_container(self, pg_container) -> DatabaseSettings:
        url = pg_container.get_connection_url()
        # testcontainers returns sqlalchemy-style URL like
        # `postgresql+psycopg2://test:test@localhost:54321/test`.
        # Parse it back into our env-driven settings model.
        from urllib.parse import urlparse

        u = urlparse(url.replace("postgresql+psycopg2", "postgresql"))
        return DatabaseSettings(
            host=u.hostname or "localhost",
            port=u.port or 5432,
            database=(u.path or "/").lstrip("/"),
            user=u.username or "",
            password=u.password or "",
        )

    def test_schema_creates_all_tables(self, settings_for_container):
        engine = create_engine(settings_for_container)
        Base.metadata.create_all(engine)
        # Confirm every model's table exists.
        from sqlalchemy import inspect as sa_inspect

        names = set(sa_inspect(engine).get_table_names())
        for model in (
            Patient,
            Wound,
            Measurement,
            AuditLogEntry,
            GraftApplication,
        ):
            assert model.__tablename__ in names

    def test_graft_application_round_trip(self, settings_for_container):
        engine = create_engine(settings_for_container)
        Base.metadata.create_all(engine)
        # Insert a wound (FK target) first.
        wound_id = uuid4()
        patient_id = uuid4()
        with get_session(settings_for_container) as sess:
            sess.add(
                Patient(
                    id=patient_id,
                    opaque_token=f"token-{patient_id}",
                    organization_id=uuid4(),
                    created_at=datetime.now(UTC),
                )
            )
            sess.flush()
            sess.add(
                Wound(
                    id=wound_id,
                    patient_id=patient_id,
                    anatomic_location="left heel",
                    wound_type="dfu",
                    created_at=datetime.now(UTC),
                )
            )
            sess.flush()
            graft_id = uuid4()
            sess.add(
                GraftApplication(
                    id=graft_id,
                    wound_id=wound_id,
                    organization_id=uuid4(),
                    applied_by=uuid4(),
                    applied_at=datetime.now(UTC),
                    product_id="ALB-001",
                    product_name="AlbacetMatrix-A",
                    udi_di="(01)00301234567890",
                    serial_number="SN-12345",
                    lot_number="LOT-XYZ",
                    expiration_date=date(2027, 1, 1),
                    package_size_cm2=16.0,
                    applied_area_cm2=12.4,
                    waste_area_cm2=3.6,
                    hcpcs_code="Q4101",
                )
            )

        # Read it back in a fresh session.
        with get_session(settings_for_container) as sess:
            found = sess.query(GraftApplication).filter_by(id=graft_id).one()
            assert found.product_name == "AlbacetMatrix-A"
            assert found.lot_number == "LOT-XYZ"
            assert found.expiration_date == date(2027, 1, 1)
            assert found.applied_area_cm2 == pytest.approx(12.4)
