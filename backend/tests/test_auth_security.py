"""Security rules of the authentication flow and of the API's error handling.

Self-contained: an in-memory SQLite database of its own, no OpenAI, no SMTP.
"""

import asyncio
import io

import pytest
from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel
from typer.testing import CliRunner

import app.cli as cli_module
from app.api.routes import auth as auth_routes
from app.api.uploads import read_upload
from app.core.config import settings
from app.core.database import get_db
from app.core.exceptions import NotFoundError
from app.core.login_throttle import LoginThrottle
from app.core.security import hash_token
from app.main import UnhandledErrorMiddleware, app, app_error_handler
from app.models.user import User, UserProfile, UserSession
from app.services.auth import create_user

PASSWORD = "Str0ngPassw0rd"


@pytest.fixture
def db_factory():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(bind=engine)
    factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    yield factory
    SQLModel.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture
def client(db_factory, monkeypatch):
    def override_get_db():
        db = db_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    # A fresh throttle per test, so failures never leak from one test to another.
    monkeypatch.setattr(auth_routes, "login_throttle", LoginThrottle(3, 900))
    # Not used as a context manager: that would run the app's lifespan, which
    # creates the tables on the application's own engine, not on this test's.
    test_client = TestClient(app)
    test_client.db_factory = db_factory  # for create_account
    yield test_client
    app.dependency_overrides.clear()


def create_account(client, email="ana@example.com", username="ana", role="analyst"):
    """An account, as an admin or the create-admin command would make it."""
    db = client.db_factory()
    try:
        return create_user(db, UserProfile(email=email, username=username), PASSWORD, role=role)
    finally:
        db.close()


def login(client, email="ana@example.com", password=PASSWORD):
    return client.post("/api/auth/login", data={"username": email, "password": password})


def make_admin(db_factory, email):
    db = db_factory()
    user = db.query(User).filter(User.email == email).one()
    user.role = "admin"
    db.commit()
    db.close()


def admin_headers(client):
    create_account(client, email="boss@example.com", username="boss", role="admin")
    token = login(client, email="boss@example.com").json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def create_via_api(client, headers, **body):
    account = {"email": "ana@example.com", "username": "ana", "password": PASSWORD, **body}
    return client.post("/api/admin/users", json=account, headers=headers)


# --- Account creation ---------------------------------------------------------


def test_there_is_no_self_registration(client):
    body = {"email": "ana@example.com", "username": "ana", "password": PASSWORD}
    assert client.post("/api/auth/register", json=body).status_code in (404, 405)


def test_only_an_admin_creates_accounts(client):
    assert create_via_api(client, {}).status_code == 401
    create_account(client, email="bob@example.com", username="bob")
    token = login(client, email="bob@example.com").json()["access_token"]
    analyst = {"Authorization": f"Bearer {token}"}
    assert create_via_api(client, analyst).status_code == 403


def test_an_admin_creates_an_account_with_a_provisional_password(client):
    headers = admin_headers(client)
    response = create_via_api(client, headers)
    assert response.status_code == 201
    assert response.json()["role"] == "analyst"  # the default
    assert login(client).status_code == 200

    other = create_via_api(client, headers, email="lead@example.com", username="lead", role="admin")
    assert other.json()["role"] == "admin"


def test_account_creation_refuses_unknown_fields(client):
    response = create_via_api(client, admin_headers(client), is_active=False)
    assert response.status_code == 422


def test_password_longer_than_bcrypt_reads_is_refused(client):
    response = create_via_api(client, admin_headers(client), password="Aa1" + "x" * 80)
    assert response.status_code == 422


def test_duplicate_email_is_refused(client):
    headers = admin_headers(client)
    create_via_api(client, headers)
    response = create_via_api(client, headers, username="other")
    assert response.status_code == 409
    assert response.json()["detail"] == "Email already registered"


# --- Login --------------------------------------------------------------------


def test_login_returns_both_tokens(client):
    create_account(client)
    body = login(client).json()
    assert body["token_type"] == "bearer"
    assert body["access_token"] and body["refresh_token"]


def test_login_with_a_wrong_password(client):
    create_account(client)
    response = login(client, password="Wrong-passw0rd")
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password"


def test_email_case_does_not_matter(client):
    # Stored lowercase: PostgreSQL would otherwise compare it case-sensitively.
    headers = admin_headers(client)
    create_via_api(client, headers, email="Mixed.Case@Example.com", username="mixed")
    assert login(client, email="MIXED.case@example.COM").status_code == 200
    again = create_via_api(client, headers, email="mixed.case@example.com", username="again")
    assert again.status_code == 409


def test_inactive_account_cannot_log_in(client, db_factory):
    create_account(client)
    db = db_factory()
    db.query(User).filter(User.email == "ana@example.com").one().is_active = False
    db.commit()
    db.close()
    assert login(client).status_code == 403


# --- Tokens -------------------------------------------------------------------


def test_tokens_are_stored_hashed(client, db_factory):
    create_account(client)
    tokens = login(client).json()

    db = db_factory()
    session = db.query(UserSession).one()
    db.close()
    assert session.refresh_token_hash == hash_token(tokens["refresh_token"])
    assert session.access_token_hash == hash_token(tokens["access_token"])
    assert tokens["refresh_token"] not in (session.refresh_token_hash, session.access_token_hash)


def test_refresh_takes_the_token_in_the_body_and_rotates_it(client):
    create_account(client)
    old = login(client).json()["refresh_token"]

    assert client.post(f"/api/auth/refresh?refresh_token={old}").status_code == 422

    response = client.post("/api/auth/refresh", json={"refresh_token": old})
    assert response.status_code == 200
    new = response.json()["refresh_token"]

    # The old refresh token no longer matches any session.
    assert client.post("/api/auth/refresh", json={"refresh_token": old}).status_code == 401
    assert client.post("/api/auth/refresh", json={"refresh_token": new}).status_code == 200


def test_me_uses_the_shared_dependency(client):
    create_account(client)
    token = login(client).json()["access_token"]
    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["email"] == "ana@example.com"


# --- Admin --------------------------------------------------------------------


def test_admin_routes_refuse_an_analyst(client):
    create_account(client)
    token = login(client).json()["access_token"]
    response = client.get("/api/admin/users", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403


def test_admin_routes_refuse_an_inactive_admin(client, db_factory):
    create_account(client)
    make_admin(db_factory, "ana@example.com")
    token = login(client).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    assert client.get("/api/admin/users", headers=headers).status_code == 200

    db = db_factory()
    db.query(User).filter(User.email == "ana@example.com").one().is_active = False
    db.commit()
    db.close()
    assert client.get("/api/admin/users", headers=headers).status_code == 403


def test_role_update_accepts_only_known_roles(client, db_factory):
    create_account(client)
    create_account(client, email="bob@example.com", username="bob")
    make_admin(db_factory, "ana@example.com")
    headers = {"Authorization": f"Bearer {login(client).json()['access_token']}"}

    db = db_factory()
    bob_id = db.query(User).filter(User.email == "bob@example.com").one().id
    db.close()
    url = f"/api/admin/users/{bob_id}/role"
    assert client.put(url, json={"role": "viewer"}, headers=headers).status_code == 422
    assert client.put(url, json={"role": "admin"}, headers=headers).status_code == 200


# --- Login throttling ---------------------------------------------------------


def test_login_is_throttled_after_repeated_failures(client):
    create_account(client)
    for _ in range(3):
        assert login(client, password="Wrong-passw0rd").status_code == 401

    response = login(client)  # even the right password is refused for now
    assert response.status_code == 429
    assert int(response.headers["Retry-After"]) > 0


def test_throttle_window_expires():
    now = [0.0]
    throttle = LoginThrottle(2, 60, clock=lambda: now[0])
    throttle.record_failure("a@example.com", "10.1.1.1")
    throttle.record_failure("A@example.com ", "10.1.1.1")
    assert throttle.retry_after("a@example.com", None) > 0
    now[0] = 61
    assert throttle.retry_after("a@example.com", None) == 0


# --- Password reset -----------------------------------------------------------


def test_reset_token_works_only_once(client, monkeypatch):
    create_account(client)
    sent = {}

    async def fake_send(to_email, reset_token, user_name=""):
        sent["token"] = reset_token
        return True

    monkeypatch.setattr(auth_routes.email_service, "send_password_reset_email", fake_send)
    assert (
        client.post("/api/auth/reset-password", json={"email": "ana@example.com"}).status_code
        == 202
    )

    body = {"token": sent["token"], "new_password": "N3wPassword!"}
    assert client.post("/api/auth/reset-password-confirm", json=body).status_code == 200
    assert (
        client.post(
            "/api/auth/reset-password-confirm", json={**body, "new_password": "Th1rdPassword"}
        ).status_code
        == 400
    )
    assert login(client, password="N3wPassword!").status_code == 200


# --- Errors -------------------------------------------------------------------


def _error_app():
    error_app = FastAPI()
    error_app.add_middleware(UnhandledErrorMiddleware)
    error_app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://front.test"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    error_app.add_exception_handler(NotFoundError, app_error_handler)

    @error_app.get("/boom")
    def boom():
        raise RuntimeError("secret internal detail")

    @error_app.get("/missing")
    def missing():
        raise NotFoundError("Session not found")

    return error_app


def test_unexpected_error_is_generic_and_keeps_cors_headers():
    error_client = TestClient(_error_app(), raise_server_exceptions=False)
    response = error_client.get("/boom", headers={"Origin": "http://front.test"})
    assert response.status_code == 500
    assert response.json() == {"detail": "Internal server error"}
    assert "secret" not in response.text
    assert response.headers["access-control-allow-origin"] == "http://front.test"


def test_business_error_maps_to_its_status():
    response = TestClient(_error_app()).get("/missing")
    assert response.status_code == 404
    assert response.json() == {"detail": "Session not found"}


# --- Uploads ------------------------------------------------------------------


def _upload(name, content):
    return UploadFile(file=io.BytesIO(content), filename=name)


def test_upload_refuses_unknown_types():
    with pytest.raises(HTTPException) as exc:
        asyncio.run(read_upload(_upload("tool.exe", b"MZ")))
    assert exc.value.status_code == 400


def test_upload_refuses_files_over_the_limit(monkeypatch):
    monkeypatch.setattr(settings, "max_upload_size", 10)
    with pytest.raises(HTTPException) as exc:
        asyncio.run(read_upload(_upload("report.pdf", b"x" * 11)))
    assert exc.value.status_code == 413
    assert asyncio.run(read_upload(_upload("Report.PDF", b"x" * 10))) == b"x" * 10


# --- create-admin -------------------------------------------------------------


def test_create_admin_command(db_factory, monkeypatch):
    monkeypatch.setattr(cli_module, "SessionLocal", db_factory)
    runner = CliRunner()

    result = runner.invoke(
        cli_module.cli,
        ["create-admin", "boss@example.com", "Jane Boss"],
        input=f"{PASSWORD}\n{PASSWORD}\n",
    )
    assert result.exit_code == 0, result.output
    db = db_factory()
    user = db.query(User).filter(User.email == "boss@example.com").one()
    db.close()
    assert user.role == "admin"
    assert user.username == "boss"

    again = runner.invoke(
        cli_module.cli,
        ["create-admin", "boss@example.com", "Jane Boss"],
        input=f"{PASSWORD}\n{PASSWORD}\n",
    )
    assert again.exit_code == 1


@pytest.mark.parametrize("username", ["ab", "with space", "x" * 31])
def test_account_creation_checks_the_username(client, username):
    assert create_via_api(client, admin_headers(client), username=username).status_code == 422
