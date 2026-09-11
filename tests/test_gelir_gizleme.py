"""Gelir gizleme: gizli iken gerçek gelir değeri HTML'e HİÇ girmemeli."""
from datetime import date, timedelta
from common import today_tr as _today

import pytest


def _seed_income(appmod):
    from extensions import db
    from models import Transaction
    with appmod.app.app_context():
        db.session.add(Transaction(
            entry_date=_today(), kind="gelir", category="Maaş",
            amount=48765.43, note="test maaş",
        ))
        db.session.add(Transaction(
            entry_date=_today(), kind="gider", category="Yemek", amount=120,
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


def test_dashboard_hides_mesai_amount_when_hidden(client, flask_app):
    """Gizli modda mesai ₺ tahmini HTML'e girmemeli (saat bilgisi girebilir)."""
    import app as appmod
    from extensions import db
    from models import MonthlySalary, OvertimeEntry
    with appmod.app.app_context():
        db.session.add(MonthlySalary(year=_today().year, month=_today().month, net_salary=50000))
        db.session.add(OvertimeEntry(entry_date=_today(), hours=10, category="hafta_ici"))
        db.session.commit()
    # 50000/225*1.5*10 = 3333.33 → "3.333" (TR binlik ayraç). Gizli modda yok.
    hidden = client.get("/").get_data(as_text=True)
    assert "3.333" not in hidden
    assert "MESAİ (BU AY)" in hidden      # saat bilgisi (hassas değil) görünür

    client.post("/butce/gelir-gizle")    # göster
    shown = client.get("/").get_data(as_text=True)
    assert "3.333" in shown              # ₺ tahmini artık görünür


def test_home_life_score_excludes_finans_when_hidden(client, flask_app):
    """Life Score'un KENDİSİ bile finans verisini sızdırmamalı: is/al %100
    iken gizli modda skor tam olarak is/al ortalaması olmalı (finans dahil
    olsaydı düşerdi, çünkü hedefi kasıtlı büyük tuttuk) — yoksa is%/al% zaten
    görünürken `finans = 3*life_score - is% - al%` ile gelir geri hesaplanabilirdi."""
    import app as appmod
    from extensions import db
    from models import DailyTask, DailyTaskCompletion, Habit, HabitCompletion, MonthlyGoal, Transaction
    import dashboard_logic as dash

    today = _today()
    if today.day <= dash.FINANS_GUVENILMEZ_GUN:
        pytest.skip("ayın ilk günlerinde finans zaten hiç eklenmiyor, test bu tarihte ayırt edici değil")

    with appmod.app.app_context():
        start = today - timedelta(days=14)
        task = DailyTask(title="T", sort_order=1)
        habit = Habit(name="H", impact=5, frequency_type="gunluk", active=True)
        db.session.add_all([task, habit])
        db.session.commit()
        d = start
        while d <= today:
            db.session.add(DailyTaskCompletion(daily_task_id=task.id, completion_date=d))
            db.session.add(HabitCompletion(habit_id=habit.id, completion_date=d))
            d += timedelta(days=1)
        # Hedefi kasıtlı büyük tutuyoruz: dahil edilseydi tempo düşük kalır,
        # skor 100'ün belirgin şekilde altına düşerdi.
        db.session.add(MonthlyGoal(year=today.year, month=today.month, target_amount=100000))
        db.session.add(Transaction(entry_date=today, kind="gelir", category="Maaş", amount=100))
        db.session.commit()

        ctx = dash.DashboardContext(today)
        score_hidden = dash.compute_life_score(ctx, gelir_gizli=True)
        score_shown = dash.compute_life_score(ctx, gelir_gizli=False)
    assert score_hidden == 100
    assert score_shown < 100  # finans dahil olunca gerçekten düşüyor

    hidden_html = client.get("/").get_data(as_text=True)
    assert f">{score_hidden}<" in hidden_html or f"{score_hidden}<span" in hidden_html

    client.post("/butce/gelir-gizle")   # göster
    shown_html = client.get("/").get_data(as_text=True)
    assert f">{score_shown}<" in shown_html or f"{score_shown}<span" in shown_html


def test_mesai_pages_mask_salary_when_hidden(client, flask_app):
    import app as appmod
    from extensions import db
    from models import MonthlySalary
    y, m = _today().year, _today().month
    with appmod.app.app_context():
        db.session.add(MonthlySalary(year=y, month=m, net_salary=48765))
        db.session.commit()
    for path in (f"/mesai/hesaplama?year={y}&month={m}", "/mesai/profil"):
        html = client.get(path).get_data(as_text=True)
        assert "48765" not in html, path
        assert "••••••" in html, path
