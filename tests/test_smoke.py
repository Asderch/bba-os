"""Boş veritabanıyla her GET sayfası 500 vermemeli; birkaç bozuk POST da öyle."""
import pytest

GET_ROUTES = [
    "/", "/is/", "/is/yonet", "/is/gecmis",
    "/butce/", "/butce/abonelikler", "/butce/hesaplar", "/mesai/", "/mesai/hesaplama", "/mesai/profil",
    "/aliskanlik/", "/aliskanlik/yonet", "/aliskanlik/istatistik",
    "/analizler/", "/notlar/",
    "/yedekler", "/yedekle",
    # bozuk ay/yıl argümanları 500'e düşürmemeli
    "/butce/?month=99", "/butce/?month=0", "/butce/?year=abc",
    "/mesai/?month=13", "/mesai/?month=-1",
]


@pytest.mark.parametrize("route", GET_ROUTES)
def test_get_route_no_server_error(client, route):
    assert client.get(route).status_code < 500


BAD_POSTS = [
    ("/is/deadline/add", {"title": "x", "due_date": "bozuk"}),
    ("/is/daily/add", {"title": "x", "tag_id": "abc"}),
    ("/butce/add", {"entry_date": "2026-01-01", "kind": "gider", "category": "Yemek", "amount": "1e999"}),
    ("/butce/add", {"entry_date": "2026-01-01", "kind": "gider", "category": "Yemek", "amount": "-5"}),
    ("/butce/goal/set", {"target_amount": "100"}),
    ("/mesai/salary/set", {"net_salary": "-100"}),
    ("/mesai/transfer-to-butce", {}),
    ("/mesai/overtime/add", {"entry_date": "2026-01-01", "hours": "nan", "category": "hafta_ici"}),
]


@pytest.mark.parametrize("path,data", BAD_POSTS)
def test_bad_post_no_server_error(client, path, data):
    assert client.post(path, data=data).status_code < 500


def test_auth_gate(monkeypatch, client):
    import app as appmod
    monkeypatch.setattr(appmod, "_AUTH_USER", "u")
    monkeypatch.setattr(appmod, "_AUTH_PASS", "p")
    assert client.get("/").status_code == 401
    assert client.get("/", headers={"Authorization": "Basic dTpw"}).status_code == 200
