"""Otomatik kayıtların mükerrer koruması (Transaction.source)."""
from datetime import date


def test_subscription_double_renew_is_idempotent(client, flask_app):
    import app as appmod
    from extensions import db
    from models import Subscription, Transaction

    with appmod.app.app_context():
        db.session.add(Subscription(
            name="Netflix", amount=100, cycle="aylik", next_renewal=date(2026, 1, 1),
        ))
        db.session.commit()
        sub_id = Subscription.query.first().id

    client.post(f"/butce/subscription/{sub_id}/renew")
    client.post(f"/butce/subscription/{sub_id}/renew")  # çift tık

    with appmod.app.app_context():
        expenses = Transaction.query.filter_by(category="Abonelik").all()
        assert len(expenses) == 1  # ikinci tık yeni gider EKLEMEMELİ


def test_mesai_transfer_double_is_idempotent_and_correct_month(client, flask_app):
    import app as appmod
    from extensions import db
    from models import MonthlySalary, OvertimeEntry, Transaction

    with appmod.app.app_context():
        db.session.add(MonthlySalary(year=2026, month=3, net_salary=40000))
        db.session.add(OvertimeEntry(entry_date=date(2026, 3, 10), hours=12, category="hafta_ici"))
        db.session.commit()

    client.post("/mesai/transfer-to-butce", data={"year": 2026, "month": 3})
    client.post("/mesai/transfer-to-butce", data={"year": 2026, "month": 3})

    with appmod.app.app_context():
        rows = Transaction.query.filter_by(category="Mesai Geliri").all()
        assert len(rows) == 1
        assert rows[0].entry_date.month == 3  # Mart'a yazılmalı, bugüne değil
        assert rows[0].source == "mesai:2026-03"
