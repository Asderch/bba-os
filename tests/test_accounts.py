"""Hesaplar (banka hesabı / kredi kartı bakiye + basit faiz tahmini)."""
from datetime import date

from common import today_tr as _today
from accounts_logic import account_balance, estimated_interest


class _FakeAccount:
    """account_balance() sadece opening_balance + movements toplamına
    bakıyor — gerçek bir DB modeli kurmadan test etmek için basit bir stub."""
    def __init__(self, opening_balance, movement_amounts):
        self.opening_balance = opening_balance
        self.movements = [type("M", (), {"amount": a})() for a in movement_amounts]


def test_account_balance_is_opening_plus_movements():
    acc = _FakeAccount(opening_balance=-50000, movement_amounts=[1000, -250, 500])
    assert account_balance(acc) == -48750


def test_account_balance_no_movements_returns_opening():
    acc = _FakeAccount(opening_balance=1000, movement_amounts=[])
    assert account_balance(acc) == 1000


def test_estimated_interest_none_when_balance_positive():
    assert estimated_interest(1000, 4.25, date(2026, 9, 10)) is None


def test_estimated_interest_none_when_no_rate():
    assert estimated_interest(-1000, None, date(2026, 9, 10)) is None


def test_estimated_interest_basic_math():
    # -10.000 borç, %3 aylık faiz, ayın 10'u (30 günlük ay varsayımıyla).
    result = estimated_interest(-10000, 3.0, date(2026, 9, 10))
    daily_rate = 3.0 / 100 / 30
    assert result["bu_aya_kadar"] == 10000 * daily_rate * 10
    assert result["ay_sonuna_kadar"] == 10000 * daily_rate * 30  # Eylül 30 gün


# ----------------------------------------------------------------------
def test_hesaplar_index_ok(client):
    resp = client.get("/butce/hesaplar")
    assert resp.status_code == 200
    assert "Hesaplar" in resp.get_data(as_text=True)


def test_add_account_and_movement_updates_balance(client):
    client.post("/butce/hesaplar/ekle", data={
        "name": "Yapı Kredi", "account_type": "kredi_karti", "opening_balance": "-50000",
    })
    html = client.get("/butce/hesaplar").get_data(as_text=True)
    assert "Yapı Kredi" in html
    assert "-50000.00" in html or "-50000,00" in html

    import app as appmod
    from models import Account
    with appmod.app.app_context():
        acc_id = Account.query.filter_by(name="Yapı Kredi").first().id

    # "Azalt" (harcama) bakiyeyi daha da düşürmeli.
    client.post(f"/butce/hesaplar/{acc_id}/hareket/ekle", data={
        "movement_date": _today().isoformat(), "direction": "azalt", "amount": "500", "description": "Market",
    })
    html = client.get("/butce/hesaplar").get_data(as_text=True)
    assert "-50500.00" in html

    # "Artır" (ödeme) bakiyeyi yükseltmeli.
    client.post(f"/butce/hesaplar/{acc_id}/hareket/ekle", data={
        "movement_date": _today().isoformat(), "direction": "artir", "amount": "1000", "description": "Ödeme",
    })
    html = client.get("/butce/hesaplar").get_data(as_text=True)
    assert "-49500.00" in html


def test_duplicate_account_name_rejected(client):
    client.post("/butce/hesaplar/ekle", data={"name": "Akbank", "account_type": "banka", "opening_balance": "0"})
    resp = client.post(
        "/butce/hesaplar/ekle",
        data={"name": "Akbank", "account_type": "banka", "opening_balance": "100"},
        follow_redirects=True,
    )
    assert "zaten var" in resp.get_data(as_text=True)

    import app as appmod
    from models import Account
    with appmod.app.app_context():
        assert Account.query.filter_by(name="Akbank").count() == 1


def test_archive_account_hides_from_active_list(client):
    client.post("/butce/hesaplar/ekle", data={"name": "Garanti", "account_type": "banka", "opening_balance": "0"})
    import app as appmod
    from models import Account
    with appmod.app.app_context():
        acc_id = Account.query.filter_by(name="Garanti").first().id

    client.post(f"/butce/hesaplar/{acc_id}/arsivle")
    html = client.get("/butce/hesaplar").get_data(as_text=True)
    assert "Arşivlenen Hesaplar" in html

    with appmod.app.app_context():
        assert Account.query.get(acc_id).active is False


def test_interest_estimate_shown_only_for_debt_with_rate(client):
    client.post("/butce/hesaplar/ekle", data={
        "name": "Kredi Kartım", "account_type": "kredi_karti",
        "opening_balance": "-20000", "interest_rate_monthly": "3.5",
    })
    html = client.get("/butce/hesaplar").get_data(as_text=True)
    assert "Tahmini faiz" in html

    client.post("/butce/hesaplar/ekle", data={
        "name": "Pozitif Hesap", "account_type": "banka", "opening_balance": "5000",
    })
    html = client.get("/butce/hesaplar").get_data(as_text=True)
    # Pozitif bakiyeli hesap için faiz kutusu gösterilmemeli.
    assert html.count("Tahmini faiz") == 1
