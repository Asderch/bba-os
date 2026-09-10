"""dashboard_logic'in çekirdek matematiği — özellikle K1 (eksik gün = None)."""
from datetime import datetime, timedelta
from common import today_tr as _today

import pytest


@pytest.fixture()
def seeded(flask_app):
    """8 gün önce başlamış, her günü tam tamamlamış bir kullanıcı."""
    import app as appmod
    from extensions import db
    from models import DailyTask, DailyTaskCompletion, Habit, HabitCompletion

    with appmod.app.app_context():
        today = _today()
        start = today - timedelta(days=7)
        created = datetime.combine(start, datetime.min.time())

        task = DailyTask(title="T", sort_order=1, created_at=created)
        habit = Habit(name="H", impact=5, frequency_type="gunluk", active=True, created_at=created)
        db.session.add_all([task, habit])
        db.session.commit()
        for i in range(8):
            d = start + timedelta(days=i)
            db.session.add(DailyTaskCompletion(daily_task_id=task.id, completion_date=d))
            db.session.add(HabitCompletion(habit_id=habit.id, completion_date=d))
        db.session.commit()
        yield today, start


def test_activity_start_bounds_history(flask_app, seeded):
    import app as appmod
    import dashboard_logic as dash

    today, start = seeded
    with appmod.app.app_context():
        ctx = dash.DashboardContext(today)
        assert ctx.activity_start == start
        assert ctx.daily_is_pct(start - timedelta(days=1)) is None
        assert ctx.daily_blended_pct(start - timedelta(days=3)) is None
        assert ctx.daily_is_pct(start) == 100.0


def test_istikrar_counts_only_real_days(flask_app, seeded):
    import app as appmod
    import dashboard_logic as dash

    today, _ = seeded
    with appmod.app.app_context():
        ist = dash.compute_istikrar(dash.DashboardContext(today))
        assert ist is not None
        assert ist["total_days"] == 8      # 30 değil
        assert ist["pct"] == 100


def test_momentum_none_without_prior_window(flask_app, seeded):
    import app as appmod
    import dashboard_logic as dash

    today, _ = seeded
    with appmod.app.app_context():
        assert dash.compute_momentum(dash.DashboardContext(today)) is None


def test_life_score_in_range_and_none_when_empty(flask_app):
    import app as appmod
    import dashboard_logic as dash

    with appmod.app.app_context():
        assert dash.compute_life_score(dash.DashboardContext(_today())) is None


def test_breakdown_and_priorities_shape(flask_app, seeded):
    import app as appmod
    import dashboard_logic as dash

    today, _ = seeded
    with appmod.app.app_context():
        ctx = dash.DashboardContext(today)
        bd = dash.life_score_breakdown(ctx)
        assert set(bd) == {"is", "aliskanlik", "finans", "mesai_saat", "weakest"}
        assert bd["is"] == 100 and bd["aliskanlik"] == 100

        pri = dash.dashboard_priorities(ctx)
        assert set(pri) == {"rows", "done_today", "total_today"}
        assert len(pri["rows"]) <= 3


def test_upcoming_split_excludes_past(flask_app):
    import app as appmod
    from extensions import db
    from models import DeadlineTask
    import dashboard_logic as dash

    today = _today()
    with appmod.app.app_context():
        db.session.add(DeadlineTask(title="Geçmiş", due_date=today - timedelta(days=3)))
        db.session.add(DeadlineTask(title="Gelecek", due_date=today + timedelta(days=3)))
        db.session.commit()
        titles = [e["title"] for e in dash.upcoming_split(today)["isler"]]
        assert "Gelecek" in titles and "Geçmiş" not in titles


def test_upcoming_split_separates_is_and_abonelik(flask_app):
    import app as appmod
    from extensions import db
    from models import DeadlineTask, Subscription
    import dashboard_logic as dash

    today = _today()
    with appmod.app.app_context():
        db.session.add(DeadlineTask(title="Rapor", due_date=today + timedelta(days=2)))
        db.session.add(DeadlineTask(title="Geçmiş iş", due_date=today - timedelta(days=1)))
        db.session.add(Subscription(name="Spotify", amount=60, cycle="aylik",
                                    next_renewal=today + timedelta(days=5)))
        db.session.commit()
        s = dash.upcoming_split(today)
        assert [e["title"] for e in s["isler"]] == ["Rapor"]
        assert [e["title"] for e in s["abonelik"]] == ["Spotify"]


def test_build_home_context_smoke(flask_app, seeded):
    import app as appmod
    import dashboard_logic as dash
    from common import now_tr

    today, _ = seeded
    with appmod.app.app_context():
        home = dash.build_home_context(dash.DashboardContext(today), now_tr())
        for key in ("life_score", "breakdown", "priorities", "insights",
                    "upcoming", "trend_points_str", "greeting"):
            assert key in home
