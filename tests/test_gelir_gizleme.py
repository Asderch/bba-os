"""Gelir gizleme: gizli iken gerçek gelir değeri HTML'e HİÇ girmemeli."""
from datetime import date


def _seed_income(appmod):
    from extensions import db
    from models import Transaction
    with appmod.app.app_context():
        db.session.add(Transaction(
            entry_date=date.today(), kind="gelir", category="Maaş",
            amount=48765.43, note="test maaş",
        ))
        db.session.add(Transaction(
            entry_date=date.today(), kind="gider", category="Yemek", amount=120,
        ))
        db.session.commit()


def test_income_hidden_by_default(client, flask_app):
    import app as appmod
    _seed_income(appmod)
    html = client.get("/butce/").get_data(as_text=True)
    assert "48765" not in html and "48,765" not in html and "48.765" not in html
    assert "••••••" in html
    # gider görünür kalmalı
    assert "120" in html


def test_toggle_reveals_income(client, flask_app):
    import app as appmod
    _seed_income(appmod)
    client.post("/butce/gelir-gizle")           # göster
    html = client.get("/butce/").get_data(as_text=True)
    assert "48765.43" in html or "48765,43" in html
    client.post("/butce/gelir-gizle")           # tekrar gizle
    html2 = client.get("/butce/").get_data(as_text=True)
    assert "48765" not in html2


def test_dashboard_masks_mesai_amount_when_hidden(client, flask_app):
    import app as appmod
    from extensions import db
    from models import MonthlySalary, OvertimeEntry
    with appmod.app.app_context():
        db.session.add(MonthlySalary(year=date.today().year, month=date.today().month, net_salary=50000))
        db.session.add(OvertimeEntry(entry_date=date.today(), hours=10, category="hafta_ici"))
        db.session.commit()
    html = client.get("/").get_data(as_text=True)      # varsayılan: gizli
    assert "••••••" in html
