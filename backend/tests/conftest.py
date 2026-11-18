"""Shared fixtures.

Every test gets its own in-memory SQLite database. The API client, the engine
and the background tasks all run on it, and OpenAI is replaced by fakes. The
settings come from pyproject.toml (pytest-env): no test can reach a real
database or a real OpenAI key.
"""

import itertools

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel

import app.core.database as database
import app.models  # noqa: F401  (every table in SQLModel.metadata)
from app.core.cache import cache_service
from app.core.database import get_db
from app.core.security import create_access_token, get_password_hash
from app.main import app
from app.models.company import Company
from app.models.dd_types import DDType
from app.models.questions import DDQuestion, DDSection
from app.models.session import DDSession
from app.models.user import User

PASSWORD = "Str0ngPassw0rd"
# bcrypt is slow on purpose: hash the shared test password once.
PASSWORD_HASH = get_password_hash(PASSWORD)

_sequence = itertools.count(1)


# --- Database ---------------------------------------------------------------


@pytest.fixture
def engine():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )

    @event.listens_for(engine, "connect")
    def _foreign_keys(dbapi_connection, _record):
        # SQLite only enforces foreign keys (and ON DELETE) when asked to, like
        # PostgreSQL always does.
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    SQLModel.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def session_factory(engine, monkeypatch):
    """Sessions on the test database, also for code that opens its own
    (the engine and the background tasks go through database.SessionLocal)."""
    factory = sessionmaker(bind=engine, autoflush=False)
    monkeypatch.setattr(database, "SessionLocal", factory)
    return factory


@pytest.fixture
def db(session_factory) -> Session:
    session = session_factory()
    yield session
    session.close()


@pytest.fixture
def client(session_factory):
    def override_get_db():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def _empty_cache():
    """The response cache is process-wide: never let one test see another's."""
    cache_service.flush_all()
    yield
    cache_service.flush_all()


# --- Users ------------------------------------------------------------------


@pytest.fixture
def make_user(db):
    def _make(role: str = "analyst", *, email: str | None = None, is_active: bool = True) -> User:
        n = next(_sequence)
        user = User(
            email=(email or f"user{n}@example.com").lower(),
            username=f"user{n}",
            password_hash=PASSWORD_HASH,
            full_name=f"User {n}",
            role=role,
            is_active=is_active,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    return _make


@pytest.fixture
def auth_headers():
    """Authorization headers for a user, without going through /login."""

    def _headers(user: User) -> dict[str, str]:
        token = create_access_token({"sub": str(user.id), "email": user.email, "role": user.role})
        return {"Authorization": f"Bearer {token}"}

    return _headers


@pytest.fixture
def analyst(make_user):
    return make_user("analyst")


@pytest.fixture
def admin(make_user):
    return make_user("admin")


# --- Business objects ---------------------------------------------------------


@pytest.fixture
def make_company(db):
    def _make(owner: User | None = None, name: str = "Example Asia Fund") -> Company:
        company = Company(
            name=name,
            management_company_name="Example Fund Management",
            created_by=owner.id if owner else None,
        )
        db.add(company)
        db.commit()
        db.refresh(company)
        return company

    return _make


@pytest.fixture
def make_dd_type(db):
    """A questionnaire: sections x questions, shared unless an owner is given."""

    def _make(
        owner: User | None = None, *, sections: int = 1, questions: int = 2, code: str | None = None
    ) -> DDType:
        n = next(_sequence)
        dd_type = DDType(
            code=code or f"DD{n}", name=f"Questionnaire {n}", created_by=owner.id if owner else None
        )
        db.add(dd_type)
        db.flush()
        for s in range(sections):
            section = DDSection(
                dd_type_id=dd_type.id,
                section_code=f"S{s + 1}",
                title=f"Section {s + 1}",
                order_index=s,
            )
            db.add(section)
            db.flush()
            for q in range(questions):
                db.add(
                    DDQuestion(
                        section_id=section.id,
                        question_code=f"A.{s + 1}{q + 1:02d}",
                        question_text=f"Question {s + 1}.{q + 1}?",
                        order_index=q,
                    )
                )
        db.commit()
        db.refresh(dd_type)
        return dd_type

    return _make


@pytest.fixture
def make_dd_session(db, make_company):
    def _make(
        owner: User, *, company: Company | None = None, assignee: User | None = None
    ) -> DDSession:
        n = next(_sequence)
        session = DDSession(
            session_code=f"SES-{n}",
            company_id=(company or make_company(owner)).id,
            name=f"Session {n}",
            created_by=owner.id,
            assigned_to=assignee.id if assignee else None,
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        return session

    return _make


# --- OpenAI -------------------------------------------------------------------


class FakeVectorStoreClient:
    """Stands in for OpenAIProcessor on the vector store routes. Every store
    exists and reports two files; the calls are recorded."""

    calls: list[tuple] = []

    def __init__(self, *args, **kwargs):
        pass

    def _record(self, name, *args):
        FakeVectorStoreClient.calls.append((name, *args))

    async def create_vector_store(self, name, expires_after_days=None):
        self._record("create_vector_store", name)
        return f"vs_{next(_sequence)}"

    async def get_vector_store_info(self, vector_store_id):
        self._record("get_vector_store_info", vector_store_id)
        return {
            "id": vector_store_id,
            "status": "completed",
            "file_counts": {"total": 2},
            "usage_bytes": 2048,
        }

    async def update_vector_store_name(self, vector_store_id, name):
        self._record("update_vector_store_name", vector_store_id, name)
        return True

    async def delete_vector_store(self, vector_store_id):
        self._record("delete_vector_store", vector_store_id)
        return True

    async def list_vector_store_files(self, vector_store_id):
        self._record("list_vector_store_files", vector_store_id)
        return [{"id": "file_1", "filename": "prospectus.pdf", "status": "completed"}]

    async def upload_file(self, content, filename):
        self._record("upload_file", filename)
        return f"file_{next(_sequence)}"

    async def add_file_to_vector_store(self, vector_store_id, file_id, *args, **kwargs):
        self._record("add_file_to_vector_store", vector_store_id, file_id)
        return {"id": file_id, "status": "in_progress"}

    async def remove_file_from_vector_store(self, vector_store_id, file_id):
        self._record("remove_file_from_vector_store", vector_store_id, file_id)
        return True

    async def delete_file(self, file_id):
        self._record("delete_file", file_id)
        return True

    async def get_file(self, file_id):
        self._record("get_file", file_id)
        return {
            "filename": "prospectus.pdf",
            "bytes": 1024,
            "status": "processed",
            "purpose": "assistants",
        }

    async def wait_for_file_indexed(self, *args, **kwargs):
        return True


@pytest.fixture
def fake_vector_stores(monkeypatch):
    """Replace OpenAIProcessor wherever the vector store routes look it up."""
    from app.api.routes.vector_stores import core, files, search

    FakeVectorStoreClient.calls = []
    for module in (core, files, search):
        monkeypatch.setattr(module, "OpenAIProcessor", FakeVectorStoreClient)
    return FakeVectorStoreClient
