"""'Bugün çalışmıyorum' — Günlük İşlerim tamamen işyerine özgü olduğu için,
işaretlenen günlerde İş boyutu Life Score'dan tamamen hariç tutulmalı
(0/total olarak cezalandırılmamalı)."""
from datetime import date, timedelta

from common import today_tr as _today


def _seed_daily_task(active=True):
    from extensions import db
    from models import DailyTask
    task = DailyTask(title="Kodlar", sort_order=1, active=active)
    db.session.add(task)
    db.session.commit()
    return task


def test_toggle_non_work_today_route(client, flask_app):
    import app as appmod
    from models import NonWorkDay

    resp = client.get("/is/").get_data(as_text=True)
    assert "Bugün çalışmıyorum" in resp

    client.post("/is/gun/bugun-calismiyorum")
    with appmod.app.app_context():
        assert NonWorkDay.query.filter_by(work_date=_today()).count() == 1

    resp = client.get("/is/").get_data(as_text=True)
    assert "çalışmıyorum\" olarak işaretli" in resp
    assert "Bugün normal çalışma günü" in resp

    # tekrar tıklayınca geri alınmalı
    client.post("/is/gun/bugun-calismiyorum")
    with appmod.app.app_context():
        assert NonWorkDay.query.filter_by(work_date=_today()).count() == 0


def test_add_and_delete_non_work_day_via_manage_page(client, flask_app):
    import app as appmod
    from models import NonWorkDay

    future = (_today() + timedelta(days=3)).isoformat()
    client.post("/is/gun/ekle", data={"work_date": future, "note": "Hafta sonu izinli"})

    with appmod.app.app_context():
        row = NonWorkDay.query.filter_by(work_date=_today() + timedelta(days=3)).first()
        assert row is not None
        assert row.note == "Hafta sonu izinli"
        row_id = row.id

    html = client.get("/is/yonet").get_data(as_text=True)
    assert "Hafta sonu izinli" in html

    # mükerrer ekleme reddedilmeli
    client.post("/is/gun/ekle", data={"work_date": future, "note": "tekrar"})
    with appmod.app.app_context():
        assert NonWorkDay.query.filter_by(work_date=_today() + timedelta(days=3)).count() == 1

    client.post(f"/is/gun/{row_id}/sil")
    with appmod.app.app_context():
        assert NonWorkDay.query.get(row_id) is None


def test_non_work_day_excludes_is_dimension_from_life_score(client, flask_app):
    import app as appmod
    from extensions import db
    from models import DailyTaskCompletion, NonWorkDay
    import dashboard_logic as dash

    today = _today()
    with appmod.app.app_context():
        task = _seed_daily_task()
        task_id = task.id
        # Görev hiç tamamlanmadı (0/1) — normalde İş %0 çıkardı.

        ctx_before = dash.DashboardContext(today)
        is_pct_normal_day = ctx_before.daily_is_pct(today)
        assert is_pct_normal_day == 0.0  # normal günde 0/1 = %0, ceza var

        db.session.add(NonWorkDay(work_date=today))
        db.session.commit()

        ctx_after = dash.DashboardContext(today)
        is_pct_off_day = ctx_after.daily_is_pct(today)
        assert is_pct_off_day is None  # işaretli günde veri yokmuş gibi davranılır


def test_dashboard_priorities_excludes_daily_tasks_on_non_work_day(client, flask_app):
    import app as appmod
    from extensions import db
    from models import NonWorkDay
    import dashboard_logic as dash

    today = _today()
    with appmod.app.app_context():
        _seed_daily_task()
        db.session.add(NonWorkDay(work_date=today))
        db.session.commit()

        ctx = dash.DashboardContext(today)
        priorities = dash.dashboard_priorities(ctx)
        assert priorities["total_today"] == 0
        assert priorities["done_today"] == 0
        assert all(r["type"] != "daily" for r in priorities["rows"])


def test_analizler_weekly_table_shows_izin_for_non_work_day(client, flask_app):
    import app as appmod
    from extensions import db
    from models import NonWorkDay

    today = _today()
    with appmod.app.app_context():
        _seed_daily_task()
        db.session.add(NonWorkDay(work_date=today))
        db.session.commit()

    html = client.get("/analizler/").get_data(as_text=True)
    assert "izin günü" in html
