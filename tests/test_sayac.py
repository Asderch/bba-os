"""Sayaçlar modülü: Alışkanlık'tan bilinçli olarak ayrı — sadece azaltılmak
istenen bir şeyin (ör. sigara) sade, birikimli günlük sayımı. Hiçbir hedef,
'yapıldı' ya da puan mantığı yok."""
from common import today_tr as _today


def _seed_counter(unit="dal"):
    from extensions import db
    from models import Counter
    counter = Counter(name="Sigara", unit=unit)
    db.session.add(counter)
    db.session.commit()
    return counter


def test_index_shows_empty_state_then_counter_row(client, flask_app):
    html = client.get("/sayac/").get_data(as_text=True)
    assert "Henüz bir sayaç eklemedin" in html

    client.post("/sayac/ekle", data={"name": "Sigara", "unit": "dal"})
    html = client.get("/sayac/").get_data(as_text=True)
    assert "Sigara" in html
    assert "+1 dal" in html
    assert "Paket bitti (+20)" in html


def test_log_amount_accumulates(client, flask_app):
    import app as appmod
    from models import CounterLog

    with appmod.app.app_context():
        counter = _seed_counter()
        counter_id = counter.id

    client.post(f"/sayac/{counter_id}/ekle-giris", data={"amount": "1"})
    client.post(f"/sayac/{counter_id}/ekle-giris", data={"amount": "20"})
    with appmod.app.app_context():
        logs = CounterLog.query.filter_by(counter_id=counter_id).all()
        assert sum(l.amount for l in logs) == 21

    html = client.get("/sayac/").get_data(as_text=True)
    assert "21 dal" in html


def test_log_amount_rejects_invalid(client, flask_app):
    import app as appmod
    from models import CounterLog

    with appmod.app.app_context():
        counter = _seed_counter()
        counter_id = counter.id

    client.post(f"/sayac/{counter_id}/ekle-giris", data={"amount": "0"})
    client.post(f"/sayac/{counter_id}/ekle-giris", data={})
    with appmod.app.app_context():
        assert CounterLog.query.filter_by(counter_id=counter_id).count() == 0


def test_undo_last_log(client, flask_app):
    import app as appmod
    from models import CounterLog

    with appmod.app.app_context():
        counter = _seed_counter()
        counter_id = counter.id

    client.post(f"/sayac/{counter_id}/ekle-giris", data={"amount": "1"})
    client.post(f"/sayac/{counter_id}/ekle-giris", data={"amount": "20"})
    client.post(f"/sayac/{counter_id}/geri-al")
    with appmod.app.app_context():
        logs = CounterLog.query.filter_by(counter_id=counter_id).all()
        assert len(logs) == 1
        assert logs[0].amount == 1


def test_add_edit_archive_delete_counter(client, flask_app):
    import app as appmod
    from models import Counter

    client.post("/sayac/ekle", data={"name": "Sigara", "unit": "dal", "why": "Azaltmaya çalışıyorum"})
    with appmod.app.app_context():
        counter = Counter.query.filter_by(name="Sigara").first()
        counter_id = counter.id

    # aynı isimle ikinci ekleme reddedilmeli
    client.post("/sayac/ekle", data={"name": "Sigara"})
    with appmod.app.app_context():
        assert Counter.query.filter_by(name="Sigara").count() == 1

    client.post(f"/sayac/{counter_id}/duzenle", data={"name": "Sigara (dal)", "unit": "adet"})
    with appmod.app.app_context():
        counter = Counter.query.get(counter_id)
        assert counter.name == "Sigara (dal)"
        assert counter.unit == "adet"

    client.post(f"/sayac/{counter_id}/arsivle")
    with appmod.app.app_context():
        assert Counter.query.get(counter_id).active is False
    html = client.get("/sayac/").get_data(as_text=True)
    assert "Henüz bir sayaç eklemedin" in html

    client.post(f"/sayac/{counter_id}/aktifle")
    with appmod.app.app_context():
        assert Counter.query.get(counter_id).active is True

    client.post(f"/sayac/{counter_id}/arsivle")
    client.post(f"/sayac/{counter_id}/sil")
    with appmod.app.app_context():
        assert Counter.query.get(counter_id) is None


def test_stats_page_shows_weekly_and_monthly_totals(client, flask_app):
    import app as appmod

    with appmod.app.app_context():
        counter = _seed_counter()
        counter_id = counter.id

    client.post(f"/sayac/{counter_id}/ekle-giris", data={"amount": "5"})
    html = client.get("/sayac/istatistik").get_data(as_text=True)
    assert "Sigara" in html
    assert "5 dal" in html


def test_deleting_counter_cascades_logs(client, flask_app):
    import app as appmod
    from extensions import db
    from models import Counter, CounterLog

    with appmod.app.app_context():
        counter = _seed_counter()
        counter_id = counter.id
        db.session.add(CounterLog(counter_id=counter_id, log_date=_today(), amount=3))
        db.session.commit()
        counter.active = False
        db.session.commit()

    client.post(f"/sayac/{counter_id}/sil")
    with appmod.app.app_context():
        assert Counter.query.get(counter_id) is None
        assert CounterLog.query.filter_by(counter_id=counter_id).count() == 0
