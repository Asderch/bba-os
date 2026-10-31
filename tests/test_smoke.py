"""Boş veritabanıyla her GET sayfası 500 vermemeli; birkaç bozuk POST da öyle."""
import pytest

GET_ROUTES = [
    "/mesai/", "/mesai/hesaplama", "/mesai/profil",
    "/yedekler", "/yedekle",
    # bozuk ay/yıl argümanları 500'e düşürmemeli
    "/mesai/?month=13", "/mesai/?month=-1", "/mesai/?year=abc",
]


@pytest.mark.parametrize("route", GET_ROUTES)
def test_get_route_no_server_error(client, route):
    assert client.get(route).status_code < 500


BAD_POSTS = [
    ("/mesai/salary/set", {"net_salary": "-100"}),
    ("/mesai/salary/set", {"net_salary": "nan"}),
    ("/mesai/overtime/add", {"entry_date": "2026-01-01", "hours": "nan", "category": "hafta_ici"}),
    ("/mesai/overtime/add", {"entry_date": "bozuk", "hours": "1", "category": "hafta_ici"}),
    ("/mesai/leave/add", {"entry_date": "2026-01-01", "days": "inf", "leave_type": "ucretsiz"}),
]


@pytest.mark.parametrize("path,data", BAD_POSTS)
def test_bad_post_no_server_error(client, path, data):
    assert client.post(path, data=data).status_code < 500


def test_root_redirects_to_mesai(client):
    resp = client.get("/")
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/mesai/")


@pytest.mark.parametrize("route", ["/is/", "/butce/", "/aliskanlik/", "/sayac/", "/analizler/", "/notlar/"])
def test_removed_modules_are_gone(client, route):
    assert client.get(route).status_code == 404


def test_auth_gate(monkeypatch, client):
    import app as appmod
    monkeypatch.setattr(appmod, "_AUTH_USER", "u")
    monkeypatch.setattr(appmod, "_AUTH_PASS", "p")
    assert client.get("/mesai/").status_code == 401
    assert client.get("/mesai/", headers={"Authorization": "Basic dTpw"}).status_code == 200
