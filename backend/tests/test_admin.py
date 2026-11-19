"""Account management by admins: search, role, activation, deletion."""

from app.models.company import Company
from app.models.user import User


def test_search_looks_at_every_account_not_just_the_page(client, admin, make_user, auth_headers):
    """The search used to filter only the page already fetched."""
    for _ in range(4):
        make_user()
    target = make_user(email="jane.target@example.com")

    body = client.get(
        "/api/admin/users?per_page=2&search=TARGET", headers=auth_headers(admin)
    ).json()
    assert [u["id"] for u in body["users"]] == [target.id]
    assert body["total"] == 1

    everyone = client.get("/api/admin/users?per_page=2", headers=auth_headers(admin)).json()
    assert (len(everyone["users"]), everyone["total"], everyone["total_pages"]) == (2, 6, 3)


def test_search_also_matches_the_company(client, db, admin, make_user, auth_headers):
    """The page offered it when it filtered in the browser."""
    make_user()
    target = make_user()
    target.company = "Example Partners"
    db.commit()

    body = client.get("/api/admin/users?search=partners", headers=auth_headers(admin)).json()
    assert [u["id"] for u in body["users"]] == [target.id]


def test_an_admin_cannot_demote_or_deactivate_themselves(client, admin, auth_headers):
    headers = auth_headers(admin)
    url = f"/api/admin/users/{admin.id}"
    assert client.put(f"{url}/role", json={"role": "analyst"}, headers=headers).status_code == 400
    assert (
        client.put(f"{url}/status", json={"is_active": False}, headers=headers).status_code == 400
    )
    assert client.delete(url, headers=headers).status_code == 400


def test_role_and_status_of_an_unknown_account(client, admin, auth_headers):
    headers = auth_headers(admin)
    assert (
        client.put("/api/admin/users/999/role", json={"role": "admin"}, headers=headers).status_code
        == 404
    )
    assert client.delete("/api/admin/users/999", headers=headers).status_code == 404


def test_an_account_that_owns_data_is_not_deleted(
    db, client, admin, make_user, make_company, auth_headers
):
    """Deleting it blanked the creator of its companies, which made them shared
    with every user."""
    owner = make_user()
    company = make_company(owner)
    response = client.delete(f"/api/admin/users/{owner.id}", headers=auth_headers(admin))
    assert response.status_code == 409
    db.expire_all()
    assert db.get(Company, company.id).created_by == owner.id


def test_an_account_without_data_is_deleted(db, client, admin, make_user, auth_headers):
    user = make_user()
    user_id = user.id
    response = client.delete(f"/api/admin/users/{user_id}", headers=auth_headers(admin))
    assert response.status_code == 200
    db.expire_all()
    assert db.get(User, user_id) is None


def test_an_admin_account_is_not_deleted(client, admin, make_user, auth_headers):
    other_admin = make_user("admin")
    response = client.delete(f"/api/admin/users/{other_admin.id}", headers=auth_headers(admin))
    assert response.status_code == 400
