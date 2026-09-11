"""DailyTask arşivleme: Habit'teki 'active' deseninin aynısı.

Kapsam:
- Aktif bir görev kalıcı silinemiyor (arşivlenmeye yönlendiriliyor).
- Arşivlenmiş bir görev kalıcı silinebiliyor.
- Arşivlenen görevin geçmiş tamamlama kaydı korunuyor (cascade silinmiyor).
- daily_is_pct / ctx.total_daily_tasks paydası sadece aktif görevleri sayıyor.
- index()/manage_tasks() sadece aktif görevleri listeliyor, yönet sayfası
  arşivlenenleri ayrı gösteriyor.
"""
from datetime import timedelta
from common import today_tr as _today


def _add_task(title="Görev", active=True):
    from extensions import db
    from models import DailyTask
    t = DailyTask(title=title, sort_order=1, active=active)
    db.session.add(t)
    db.session.commit()
    return t


def test_active_task_cannot_be_permanently_deleted(client, flask_app):
    import app as appmod
    with appmod.app.app_context():
        task = _add_task()
        task_id = task.id

    resp = client.post(f"/is/daily/{task_id}/delete", follow_redirects=True)
    assert resp.status_code == 200

    with appmod.app.app_context():
        from extensions import db
        from models import DailyTask
        assert db.session.get(DailyTask, task_id) is not None  # hâlâ var, silinmedi


def test_archived_task_can_be_permanently_deleted(client, flask_app):
    import app as appmod
    with appmod.app.app_context():
        task = _add_task()
        task_id = task.id

    client.post(f"/is/daily/{task_id}/archive")
    with appmod.app.app_context():
        from extensions import db
        from models import DailyTask
        assert db.session.get(DailyTask, task_id).active is False

    client.post(f"/is/daily/{task_id}/delete")
    with appmod.app.app_context():
        from extensions import db
        from models import DailyTask
        assert db.session.get(DailyTask, task_id) is None  # gerçekten silindi


def test_unarchive_reactivates_task(client, flask_app):
    import app as appmod
    with appmod.app.app_context():
        task = _add_task()
        task_id = task.id

    client.post(f"/is/daily/{task_id}/archive")
    client.post(f"/is/daily/{task_id}/unarchive")
    with appmod.app.app_context():
        from extensions import db
        from models import DailyTask
        assert db.session.get(DailyTask, task_id).active is True


def test_archiving_preserves_past_completions(client, flask_app):
    """Arşivleme, geçmiş DailyTaskCompletion kayıtlarını SİLMEMELİ (cascade yok)."""
    import app as appmod
    from extensions import db
    from models import DailyTaskCompletion

    today = _today()
    with appmod.app.app_context():
        task = _add_task()
        task_id = task.id
        db.session.add(DailyTaskCompletion(daily_task_id=task_id, completion_date=today))
        db.session.add(DailyTaskCompletion(daily_task_id=task_id, completion_date=today - timedelta(days=1)))
        db.session.commit()

    client.post(f"/is/daily/{task_id}/archive")

    with appmod.app.app_context():
        remaining = DailyTaskCompletion.query.filter_by(daily_task_id=task_id).count()
        assert remaining == 2  # arşivleme geçmişi silmedi


def test_daily_is_pct_denominator_excludes_archived_tasks(flask_app):
    """ctx.total_daily_tasks ve daily_is_pct payda'sı sadece active=True görevleri saymalı."""
    import app as appmod
    import dashboard_logic as dash

    today = _today()
    with appmod.app.app_context():
        active_task = _add_task("Aktif", active=True)
        _add_task("Arşivli", active=False)

        from extensions import db
        from models import DailyTaskCompletion
        db.session.add(DailyTaskCompletion(daily_task_id=active_task.id, completion_date=today))
        db.session.commit()

        ctx = dash.DashboardContext(today)
        assert ctx.total_daily_tasks == 1  # sadece aktif görev sayılıyor
        assert ctx.daily_is_pct(today) == 100.0  # 1/1, arşivli görev paydaya girmedi


def test_archived_completion_not_double_counted_if_stale(flask_app):
    """Arşivlenmiş bir görevin tamamlama kaydı varsa (arşivlemeden önce
    işaretlenmiş), daily_done_by_date içine hiç girmemeli — habit_completions
    ile aynı 'if id in active_ids' deseni."""
    import app as appmod
    import dashboard_logic as dash
    from extensions import db
    from models import DailyTaskCompletion

    today = _today()
    with appmod.app.app_context():
        archived_task = _add_task("Arşivli", active=False)
        db.session.add(DailyTaskCompletion(daily_task_id=archived_task.id, completion_date=today))
        db.session.commit()

        ctx = dash.DashboardContext(today)
        assert ctx.total_daily_tasks == 0
        assert today not in ctx.daily_done_by_date or archived_task.id not in ctx.daily_done_by_date.get(today, set())


def test_manage_tasks_lists_active_and_archived_separately(client, flask_app):
    import app as appmod
    with appmod.app.app_context():
        _add_task("Aktif Görev", active=True)
        _add_task("Arşivli Görev", active=False)

    html = client.get("/is/yonet").get_data(as_text=True)
    assert "Aktif Görev" in html
    assert "Arşivli Görev" in html
    assert "Arşivlenen Günlük İşler" in html


def test_index_hides_archived_tasks(client, flask_app):
    import app as appmod
    with appmod.app.app_context():
        _add_task("Aktif Görev", active=True)
        _add_task("Arşivli Görev", active=False)

    html = client.get("/is/").get_data(as_text=True)
    assert "Aktif Görev" in html
    assert "Arşivli Görev" not in html


def test_stats_denominator_excludes_archived_tasks(client, flask_app):
    """blueprints/is_takip.py stats(): 'total'/'total_possible' payda'sı
    sadece active=True görevleri saymalı (aliskanlik.py stats() ile aynı desen).
    2 görev eklenip biri arşivlenirse, bugünün satırında total=1 görünmeli
    (2 değil) — daha önce DailyTask.query.all() kullanıldığı için 2 çıkıyordu."""
    import app as appmod
    with appmod.app.app_context():
        _add_task("Aktif", active=True)
        _add_task("Arşivli", active=False)

    resp = client.get("/is/istatistik")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    # Bugünün satırında "0 / 1" görünmeli (1 aktif görev, hiçbiri tamamlanmadı) —
    # arşivlenmiş görev payda'ya (1) dahil edilmemiş.
    assert "0 / 1" in html
    assert "0 / 2" not in html


def test_stats_keeps_archived_tasks_past_completions_in_weekly_done_count(client, flask_app):
    """Bir görev bugün tamamlanıp SONRA arşivlense bile, o günkü 'done' sayısına
    girmeye devam etmeli — geçmiş bütünlüğü korunur (completions_by_date görev
    aktifliğine göre filtrelenmiyor, sadece tarihe göre); sadece payda (aktif
    görev sayısı) arşivlenmiş görevi dışlar."""
    import app as appmod
    from extensions import db
    from models import DailyTaskCompletion

    today = _today()
    with appmod.app.app_context():
        task = _add_task("Sonra Arşivlenecek", active=True)
        task_id = task.id
        db.session.add(DailyTaskCompletion(daily_task_id=task_id, completion_date=today))
        db.session.commit()

    # Görevi arşivle — geçmiş tamamlama kaydı silinmiyor (cascade yok).
    client.post(f"/is/daily/{task_id}/archive")

    with appmod.app.app_context():
        from models import DailyTask, DailyTaskCompletion as DTC
        assert db.session.get(DailyTask, task_id).active is False
        # Tamamlama kaydı hâlâ duruyor.
        assert DTC.query.filter_by(daily_task_id=task_id, completion_date=today).count() == 1

    resp = client.get("/is/istatistik")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    # Payda artık 0 (aktif görev kalmadı) ama numaratör (total_done) hâlâ 1 —
    # arşivlenmiş görevin bugünkü tamamlaması istatistiklerden silinmedi.
    assert "1 / 0" in html
