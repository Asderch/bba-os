"""Analizler — eskiden 'Analizler' sidebar linki yanlışlıkla İş Takip'in
kendi istatistik sayfasına (/is/istatistik) gidiyordu. Bu testler yeni,
bağımsız modülün (/analizler) doğru çalıştığını ve eski route'un artık
var olmadığını doğrular."""
from datetime import date

from common import today_tr as _today


def test_analizler_index_ok(client):
    resp = client.get("/analizler/")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "Analizler" in html
    # tüm modüllerin özeti sayfada bulunmalı
    assert "İŞ TAKİP" in html
    assert "ALIŞKANLIKLAR" in html
    assert "FİNANS" in html
    assert "MESAİ" in html


def test_old_is_takip_istatistik_route_removed(client):
    assert client.get("/is/istatistik").status_code == 404


def test_analizler_masks_income_when_hidden(client):
    import app as appmod
    from extensions import db
    from models import Transaction
    with appmod.app.app_context():
        db.session.add(Transaction(entry_date=_today(), kind="gelir", category="Maaş", amount=48765.43))
        db.session.commit()

    html = client.get("/analizler/").get_data(as_text=True)
    assert "48765" not in html
    assert "••••••" in html


def test_analizler_shows_is_takip_weekly_table(client):
    import app as appmod
    from extensions import db
    from models import DailyTask

    with appmod.app.app_context():
        db.session.add(DailyTask(title="Test görevi", sort_order=1, active=True))
        db.session.commit()

    html = client.get("/analizler/").get_data(as_text=True)
    assert "GÜNLÜK DÖKÜM" in html
    assert "0 / 1" in html
