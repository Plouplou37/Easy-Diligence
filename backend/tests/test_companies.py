"""Companies API: authentication, per-user isolation and audit fields."""

import pytest

COMPANY = {
    "name": "Example Asia Fund",
    "website_url": "https://fund.example.com",
    "description": "A test fund",
    "management_company_name": "Example Fund Management",
    "management_company_website": "https://manager.example.com",
}


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("post", "/api/company/"),
        ("get", "/api/company/"),
        ("get", "/api/company/1"),
        ("put", "/api/company/1"),
    ],
)
def test_every_company_endpoint_requires_a_user(client, method, path):
    response = client.request(method, path, json=COMPANY)
    assert response.status_code == 401


def test_create_sets_the_creator(client, db, analyst, auth_headers):
    response = client.post("/api/company/", json=COMPANY, headers=auth_headers(analyst))
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == COMPANY["name"]
    assert body["management_company_name"] == COMPANY["management_company_name"]

    from app.models.company import Company

    assert db.get(Company, body["id"]).created_by == analyst.id


def test_update_sets_the_editor(client, db, analyst, make_company, auth_headers):
    company = make_company(analyst)
    update = {**COMPANY, "name": "Renamed Fund"}
    response = client.put(f"/api/company/{company.id}", json=update, headers=auth_headers(analyst))
    assert response.status_code == 200
    assert response.json()["name"] == "Renamed Fund"
    db.refresh(company)
    assert company.updated_by == analyst.id


def test_analyst_sees_own_and_shared_companies(client, make_user, make_company, auth_headers):
    alice, bob = make_user(), make_user()
    own = make_company(alice, name="Alice Fund")
    shared = make_company(None, name="Shared Fund")
    make_company(bob, name="Bob Fund")

    names = {c["name"] for c in client.get("/api/company/", headers=auth_headers(alice)).json()}
    assert names == {own.name, shared.name}


def test_admin_sees_every_company(client, admin, make_user, make_company, auth_headers):
    make_company(make_user(), name="Alice Fund")
    make_company(make_user(), name="Bob Fund")
    names = {c["name"] for c in client.get("/api/company/", headers=auth_headers(admin)).json()}
    assert {"Alice Fund", "Bob Fund"} <= names


def test_other_users_company_is_hidden(client, make_user, make_company, auth_headers):
    alice, bob = make_user(), make_user()
    company = make_company(bob)
    response = client.get(f"/api/company/{company.id}", headers=auth_headers(alice))
    assert response.status_code == 404  # not 403: ids are not enumerable


def test_shared_company_is_visible_but_not_editable(client, analyst, make_company, auth_headers):
    shared = make_company(None)
    headers = auth_headers(analyst)
    assert client.get(f"/api/company/{shared.id}", headers=headers).status_code == 200
    assert client.put(f"/api/company/{shared.id}", json=COMPANY, headers=headers).status_code == 403


def test_unknown_company(client, analyst, auth_headers):
    response = client.get("/api/company/99999", headers=auth_headers(analyst))
    assert response.status_code == 404
    assert response.json()["detail"] == "Company not found"


def test_root_and_health(client):
    assert client.get("/health").json() == {"status": "healthy"}
    assert client.get("/").json()["message"].endswith("API")
