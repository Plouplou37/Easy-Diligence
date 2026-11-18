"""Per-user isolation (services/authz.py): admins see everything, other users
their own data plus what is shared."""

from types import SimpleNamespace

from app.services import authz

# --- The rules themselves ---------------------------------------------------------


def _user(user_id, role="analyst"):
    return SimpleNamespace(id=user_id, role=role)


def test_session_rules():
    session = SimpleNamespace(created_by=1, assigned_to=2)
    assert authz.user_can_access_session(session, _user(1))  # creator
    assert authz.user_can_access_session(session, _user(2))  # assignee
    assert not authz.user_can_access_session(session, _user(3))
    assert authz.user_can_access_session(session, _user(3, "admin"))


def test_dd_type_rules():
    own = SimpleNamespace(created_by=1, is_system=False)
    shared = SimpleNamespace(created_by=None, is_system=False)
    system = SimpleNamespace(created_by=2, is_system=True)
    other = SimpleNamespace(created_by=2, is_system=False)
    me = _user(1)
    assert authz.user_can_view_dd_type(own, me) and authz.user_can_modify_dd_type(own, me)
    assert authz.user_can_view_dd_type(shared, me) and not authz.user_can_modify_dd_type(shared, me)
    assert authz.user_can_view_dd_type(system, me) and not authz.user_can_modify_dd_type(system, me)
    assert not authz.user_can_view_dd_type(other, me)
    assert authz.user_can_modify_dd_type(other, _user(9, "admin"))


def test_company_rules():
    own, shared, other = (SimpleNamespace(created_by=c) for c in (1, None, 2))
    me = _user(1)
    assert authz.user_can_view_company(own, me) and authz.user_can_modify_company(own, me)
    assert authz.user_can_view_company(shared, me) and not authz.user_can_modify_company(shared, me)
    assert not authz.user_can_view_company(other, me)
    assert authz.user_can_modify_company(shared, _user(9, "admin"))


# --- Through the API ----------------------------------------------------------------


def test_session_list_shows_own_and_assigned_sessions(
    client, make_user, make_dd_session, auth_headers
):
    alice, bob = make_user(), make_user()
    own = make_dd_session(alice)
    assigned = make_dd_session(bob, assignee=alice)
    make_dd_session(bob)

    sessions = client.get("/api/session/", headers=auth_headers(alice)).json()["sessions"]
    assert {s["id"] for s in sessions} == {own.id, assigned.id}


def test_admin_lists_every_session(client, admin, make_user, make_dd_session, auth_headers):
    make_dd_session(make_user())
    make_dd_session(make_user())
    sessions = client.get("/api/session/", headers=auth_headers(admin)).json()["sessions"]
    assert len(sessions) == 2


def test_someone_elses_session_is_refused(client, make_user, make_dd_session, auth_headers):
    alice, bob = make_user(), make_user()
    session = make_dd_session(bob)
    headers = auth_headers(alice)
    assert client.get(f"/api/session/{session.id}", headers=headers).status_code == 403
    assert client.delete(f"/api/session/{session.id}", headers=headers).status_code == 403


def test_dd_type_list_shows_own_and_shared_types(client, make_user, make_dd_type, auth_headers):
    alice, bob = make_user(), make_user()
    own = make_dd_type(alice)
    shared = make_dd_type(None)
    make_dd_type(bob)

    codes = {t["code"] for t in client.get("/api/dd-types/", headers=auth_headers(alice)).json()}
    assert codes == {own.code, shared.code}


def test_private_dd_type_of_someone_else_is_hidden(client, make_user, make_dd_type, auth_headers):
    alice, bob = make_user(), make_user()
    private = make_dd_type(bob)
    response = client.get(f"/api/dd-types/{private.code}", headers=auth_headers(alice))
    assert response.status_code == 404
