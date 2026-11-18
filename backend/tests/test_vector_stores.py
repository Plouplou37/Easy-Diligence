"""Vector stores API on a real database, with OpenAI replaced by a fake
(conftest.FakeVectorStoreClient)."""

import pytest

from app.models.vector_store import SessionVectorStore, VectorStore


@pytest.fixture
def make_store(db):
    def _make(owner, store_id="vs_1", name="Fund documents"):
        store = VectorStore(id=store_id, name=name, created_by=owner.id)
        db.add(store)
        db.commit()
        db.refresh(store)
        return store

    return _make


def test_requires_a_user(client, fake_vector_stores):
    assert client.get("/api/vector-stores/").status_code == 401


def test_create(client, db, analyst, auth_headers, fake_vector_stores):
    response = client.post(
        "/api/vector-stores/",
        json={"name": "Fund documents", "description": "Prospectus and DDQ"},
        headers=auth_headers(analyst),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Fund documents"
    stored = db.get(VectorStore, body["id"])
    assert stored.created_by == analyst.id
    assert ("create_vector_store", "Fund documents") in fake_vector_stores.calls


def test_list_shows_own_stores_with_openai_details(
    client, make_user, make_store, auth_headers, fake_vector_stores
):
    alice, bob = make_user(), make_user()
    make_store(alice, "vs_alice")
    make_store(bob, "vs_bob")

    stores = client.get("/api/vector-stores/", headers=auth_headers(alice)).json()
    assert [s["id"] for s in stores] == ["vs_alice"]
    assert stores[0]["file_count"] == 2
    assert stores[0]["total_bytes"] == 2048
    assert stores[0]["status"] == "completed"


def test_admin_lists_every_store(
    client, admin, make_user, make_store, auth_headers, fake_vector_stores
):
    make_store(make_user(), "vs_alice")
    make_store(make_user(), "vs_bob")
    ids = {s["id"] for s in client.get("/api/vector-stores/", headers=auth_headers(admin)).json()}
    assert ids == {"vs_alice", "vs_bob"}


def test_get_own_store_and_hide_others(
    client, make_user, make_store, auth_headers, fake_vector_stores
):
    alice, bob = make_user(), make_user()
    make_store(alice, "vs_alice")
    assert client.get("/api/vector-stores/vs_alice", headers=auth_headers(alice)).status_code == 200
    assert client.get("/api/vector-stores/vs_alice", headers=auth_headers(bob)).status_code == 404


def test_rename(client, db, analyst, make_store, auth_headers, fake_vector_stores):
    """The update route called two methods the OpenAI client does not have:
    every update answered 500."""
    make_store(analyst, "vs_1", name="Old name")
    response = client.patch(
        "/api/vector-stores/vs_1",
        json={"name": "New name", "description": "Updated"},
        headers=auth_headers(analyst),
    )
    assert response.status_code == 200
    assert response.json()["name"] == "New name"
    assert ("update_vector_store_name", "vs_1", "New name") in fake_vector_stores.calls
    assert db.get(VectorStore, "vs_1").description == "Updated"


def test_the_list_shows_a_rename_at_once(
    client, analyst, make_store, auth_headers, fake_vector_stores
):
    """The list is cached for five minutes: a change must clear it."""
    make_store(analyst, "vs_1", name="Old name")
    headers = auth_headers(analyst)
    assert client.get("/api/vector-stores/", headers=headers).json()[0]["name"] == "Old name"

    client.patch("/api/vector-stores/vs_1", json={"name": "New name"}, headers=headers)
    assert client.get("/api/vector-stores/", headers=headers).json()[0]["name"] == "New name"


def test_delete_removes_the_store_and_its_assignments(
    client, db, analyst, make_store, make_dd_session, auth_headers, fake_vector_stores
):
    make_store(analyst, "vs_1")
    session = make_dd_session(analyst)
    db.add(
        SessionVectorStore(session_id=session.id, vector_store_id="vs_1", assigned_by=analyst.id)
    )
    db.commit()

    assert (
        client.delete("/api/vector-stores/vs_1", headers=auth_headers(analyst)).status_code == 200
    )
    db.expire_all()
    assert db.get(VectorStore, "vs_1") is None
    assert db.query(SessionVectorStore).count() == 0
    assert ("delete_vector_store", "vs_1") in fake_vector_stores.calls


def test_cannot_delete_someone_elses_store(
    client, make_user, make_store, auth_headers, fake_vector_stores
):
    make_store(make_user(), "vs_1")
    response = client.delete("/api/vector-stores/vs_1", headers=auth_headers(make_user()))
    assert response.status_code == 404


# --- Files ----------------------------------------------------------------------


def test_list_files(client, analyst, make_store, auth_headers, fake_vector_stores):
    make_store(analyst, "vs_1")
    response = client.get("/api/vector-stores/vs_1/files", headers=auth_headers(analyst))
    assert response.status_code == 200
    assert response.json()["files"][0]["filename"] == "prospectus.pdf"


def test_upload_file(client, analyst, make_store, auth_headers, fake_vector_stores):
    make_store(analyst, "vs_1")
    response = client.post(
        "/api/vector-stores/vs_1/files",
        files={"file": ("prospectus.pdf", b"%PDF-1.7 content", "application/pdf")},
        headers=auth_headers(analyst),
    )
    assert response.status_code == 200
    assert response.json()["filename"] == "prospectus.pdf"
    assert ("upload_file", "prospectus.pdf") in fake_vector_stores.calls


def test_upload_refuses_a_forbidden_type(
    client, analyst, make_store, auth_headers, fake_vector_stores
):
    make_store(analyst, "vs_1")
    response = client.post(
        "/api/vector-stores/vs_1/files",
        files={"file": ("tool.exe", b"MZ", "application/octet-stream")},
        headers=auth_headers(analyst),
    )
    assert response.status_code == 400
    assert not any(call[0] == "upload_file" for call in fake_vector_stores.calls)


def test_delete_file(client, analyst, make_store, auth_headers, fake_vector_stores):
    make_store(analyst, "vs_1")
    response = client.delete("/api/vector-stores/vs_1/files/file_9", headers=auth_headers(analyst))
    assert response.status_code == 200
    assert ("remove_file_from_vector_store", "vs_1", "file_9") in fake_vector_stores.calls
    assert ("delete_file", "file_9") in fake_vector_stores.calls


def test_file_details(client, analyst, make_store, auth_headers, fake_vector_stores):
    make_store(analyst, "vs_1")
    response = client.get(
        "/api/vector-stores/vs_1/files/file_9/content", headers=auth_headers(analyst)
    )
    assert response.status_code == 200
    assert response.json()["filename"] == "prospectus.pdf"


# --- Assignments to sessions ----------------------------------------------------


def test_assign_to_a_whole_session_then_unassign(
    client, analyst, make_store, make_dd_session, auth_headers, fake_vector_stores
):
    make_store(analyst, "vs_1")
    session = make_dd_session(analyst)
    headers = auth_headers(analyst)

    response = client.put(f"/api/vector-stores/vs_1/assign-session/{session.id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["assignment"]["dd_type_id"] is None

    listing = client.get(f"/api/vector-stores/session/{session.id}/assignments", headers=headers)
    assert [a["vector_store_id"] for a in listing.json()["assignments"]] == ["vs_1"]

    response = client.delete(
        f"/api/vector-stores/vs_1/assign-session/{session.id}", headers=headers
    )
    assert response.status_code == 200
    listing = client.get(f"/api/vector-stores/session/{session.id}/assignments", headers=headers)
    assert listing.json()["assignments"] == []


def test_assign_to_one_dd_type(
    client, analyst, make_store, make_dd_session, make_dd_type, auth_headers, fake_vector_stores
):
    make_store(analyst, "vs_1")
    session = make_dd_session(analyst)
    dd_type = make_dd_type()
    response = client.put(
        f"/api/vector-stores/vs_1/assign-session/{session.session_code}",
        json={"dd_type_id": dd_type.id},
        headers=auth_headers(analyst),
    )
    assert response.status_code == 200
    assert response.json()["assignment"]["dd_type_code"] == dd_type.code


def test_a_colleagues_store_can_serve_my_session(
    client, make_user, make_store, make_dd_session, auth_headers, fake_vector_stores
):
    """Assignments are shareable on purpose: any store can serve a session."""
    alice, bob = make_user(), make_user()
    make_store(bob, "vs_bob")
    session = make_dd_session(alice)
    response = client.put(
        f"/api/vector-stores/vs_bob/assign-session/{session.id}", headers=auth_headers(alice)
    )
    assert response.status_code == 200


def test_cannot_assign_to_someone_elses_session(
    client, make_user, make_store, make_dd_session, auth_headers, fake_vector_stores
):
    alice, bob = make_user(), make_user()
    make_store(alice, "vs_1")
    session = make_dd_session(bob)
    response = client.put(
        f"/api/vector-stores/vs_1/assign-session/{session.id}", headers=auth_headers(alice)
    )
    assert response.status_code == 404
