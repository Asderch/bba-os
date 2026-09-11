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
        home = dash.build_home_context(dash.DashboardContext(today), now_tr(), False)
        for key in ("life_score", "breakdown", "priorities", "insights",
                    "upcoming", "trend_points_str", "greeting"):
            assert key in home


def test_build_home_context_requires_gelir_gizli(flask_app, seeded):
    """3. parametre zorunlu (varsayılan yok) — unutulursa TypeError almalıyız,
    sessizce gelir görünür moduna düşmemeliyiz."""
    import app as appmod
    import dashboard_logic as dash
    from common import now_tr

    today, _ = seeded
    with appmod.app.app_context():
        with pytest.raises(TypeError):
            dash.build_home_context(dash.DashboardContext(today), now_tr())


# ----------------------------------------------------------------------
# GÖREV 1 — gelir gizliyken Life Score'un Finans bileşeni hiç eklenmemeli.
@pytest.fixture()
def seeded_with_finans(flask_app):
    """Aktif kullanım + bu ayın ortasında bir bütçe hedefi ve net gelir olan kullanıcı."""
    import app as appmod
    from extensions import db
    from models import DailyTask, DailyTaskCompletion, Habit, HabitCompletion, MonthlyGoal, Transaction

    with appmod.app.app_context():
        today = _today()
        # Ayın FINANS_GUVENILMEZ_GUN'dan sonrasında olduğundan emin olalım —
        # sabit bir tarih yerine bugünün ayının 20'sini simüle etmek yerine,
        # aktivite başlangıcını yeterince geriye çekip finans bileşeninin
        # devreye girebileceği bir gün varsayıyoruz (test ayın günü ne olursa
        # olsun day.day > FINANS_GUVENILMEZ_GUN olan GEÇMİŞ bir günü kullanır).
        start = today - timedelta(days=20)
        created = datetime.combine(start, datetime.min.time())

        task = DailyTask(title="T", sort_order=1, created_at=created)
        habit = Habit(name="H", impact=5, frequency_type="gunluk", active=True, created_at=created)
        db.session.add_all([task, habit])
        db.session.commit()
        for i in range(21):
            d = start + timedelta(days=i)
            db.session.add(DailyTaskCompletion(daily_task_id=task.id, completion_date=d))
            db.session.add(HabitCompletion(habit_id=habit.id, completion_date=d))

        # Hedefi kasıtlı büyük tutuyoruz ki finans tempo yüzdesi 100'e
        # doymasın — is/al zaten %100 olduğundan, finans dahilken/hariçken
        # skorun GERÇEKTEN farklı çıktığını doğrulayabilelim.
        db.session.add(MonthlyGoal(year=today.year, month=today.month, target_amount=100000))
        db.session.add(Transaction(entry_date=today, kind="gelir", category="Maaş", amount=1000))
        db.session.commit()
        yield today, start


def test_gelir_gizli_excludes_finans_from_life_score(flask_app, seeded_with_finans):
    import app as appmod
    import dashboard_logic as dash

    today, _ = seeded_with_finans
    with appmod.app.app_context():
        ctx = dash.DashboardContext(today)
        # Finansı görünürken hesaplanan skor, gizliyken hesaplanan skordan
        # farklı olmalı (aksi halde finans zaten etkisiz demektir, test anlamsız).
        score_visible = dash.compute_life_score(ctx, gelir_gizli=False)
        score_hidden = dash.compute_life_score(ctx, gelir_gizli=True)
        assert score_visible is not None and score_hidden is not None
        # Gizliyken skor SADECE is/al ortalaması olmalı (is=100, al=100 → 100).
        assert score_hidden == 100
        # Görünür moddaysa finans tempo yüzdesi düşük kalacak şekilde
        # kurulduğundan (hedef >> net), skor GERÇEKTEN düşmeli — yoksa finans
        # hâlâ etkisiz kalıyor olabilir ve test yanlışlıkla geçer.
        assert score_visible < score_hidden


def test_gelir_gizli_breakdown_hides_finans_and_weakest(flask_app, seeded_with_finans):
    import dashboard_logic as dash
    import app as appmod

    today, _ = seeded_with_finans
    with appmod.app.app_context():
        ctx = dash.DashboardContext(today)
        bd_visible = dash.life_score_breakdown(ctx, gelir_gizli=False)
        bd_hidden = dash.life_score_breakdown(ctx, gelir_gizli=True)
        assert bd_hidden["finans"] is None
        assert bd_hidden["weakest"] != "finans"
        # görünür moddaki finans None olmamalı (test kurulumu anlamlı olsun diye)
        if today.day > dash.FINANS_GUVENILMEZ_GUN:
            assert bd_visible["finans"] is not None


def test_gelir_gizli_history_and_delta_thread_through(flask_app, seeded_with_finans):
    import dashboard_logic as dash
    import app as appmod

    today, _ = seeded_with_finans
    with appmod.app.app_context():
        ctx = dash.DashboardContext(today)
        hist_hidden = dash.life_score_history(ctx, days=3, gelir_gizli=True)
        hist_visible = dash.life_score_history(ctx, days=3, gelir_gizli=False)
        assert len(hist_hidden) == len(hist_visible) == 3
        delta_hidden = dash.life_score_delta(ctx, gelir_gizli=True)
        delta_visible = dash.life_score_delta(ctx, gelir_gizli=False)
        # sadece imzanın çalıştığını doğruluyoruz — None ya da sayı olabilir
        assert delta_hidden is None or isinstance(delta_hidden, int)
        assert delta_visible is None or isinstance(delta_visible, int)


# ----------------------------------------------------------------------
# GÖREV 2 — finans ay-sınırı: geçmiş bir gün, KENDİ ayının verisini kullanmalı.
def test_finans_pace_pct_uses_for_days_own_month(flask_app):
    """Bu ayın hedefi/net'i, ÖNCEKİ ayın verisiyle karışmamalı."""
    import app as appmod
    from extensions import db
    from models import MonthlyGoal, Transaction
    import dashboard_logic as dash
    from common import prev_next_month

    today = _today()
    (prev_y, prev_m), _ = prev_next_month(today.year, today.month)
    with appmod.app.app_context():
        # Bu ay: hedef kasıtlı büyük (100000), net sadece 500 → tempo düşük
        # kalır, %100'e doymaz (aksi halde iki ayın da 100'e doyup testi
        # anlamsızlaştırma riski olurdu).
        db.session.add(MonthlyGoal(year=today.year, month=today.month, target_amount=100000))
        db.session.add(Transaction(entry_date=today, kind="gelir", category="Maaş", amount=500))
        # Önceki ay: hedef 2000, net TAM hedefe ulaşmış (2000) → tempo %100
        prev_last_day = dash.calendar.monthrange(prev_y, prev_m)[1]
        prev_day = today.replace(year=prev_y, month=prev_m, day=min(today.day, prev_last_day))
        db.session.add(MonthlyGoal(year=prev_y, month=prev_m, target_amount=2000))
        db.session.add(Transaction(entry_date=prev_day, kind="gelir", category="Maaş", amount=2000))
        db.session.commit()

        ctx = dash.DashboardContext(today)
        this_month_pct = dash._finans_pace_pct(ctx, today)
        prev_month_pct = dash._finans_pace_pct(ctx, prev_day)
        assert this_month_pct is not None and prev_month_pct is not None
        # Önceki ay tam hedefte olduğu için tempo yüzdesi bu aydan yüksek olmalı
        # (bu ayın net'i hedefin sadece yarısı kadar).
        assert prev_month_pct > this_month_pct
        assert prev_month_pct == pytest.approx(100.0, abs=0.01)


def test_finans_pace_pct_returns_none_without_goal_for_that_month(flask_app):
    """Bugünün ayında hedef olsa bile, hedefi olmayan bir ay için None dönmeli."""
    import app as appmod
    from extensions import db
    from models import MonthlyGoal
    import dashboard_logic as dash
    from common import prev_next_month

    today = _today()
    (prev_y, prev_m), _ = prev_next_month(today.year, today.month)
    with appmod.app.app_context():
        db.session.add(MonthlyGoal(year=today.year, month=today.month, target_amount=1000))
        db.session.commit()

        ctx = dash.DashboardContext(today)
        prev_last_day = dash.calendar.monthrange(prev_y, prev_m)[1]
        prev_day = today.replace(year=prev_y, month=prev_m, day=min(today.day, prev_last_day))
        assert dash._finans_pace_pct(ctx, prev_day) is None


def test_finans_guvenilmez_gun_excluded_from_life_score(flask_app):
    """Ayın ilk FINANS_GUVENILMEZ_GUN günü, hedef tanımlı olsa bile finans
    Life Score'a eklenmemeli (compute_life_score seviyesinde, sadece
    breakdown'daki 'en zayıf' seçiminde değil)."""
    import app as appmod
    from extensions import db
    from models import DailyTask, DailyTaskCompletion, Habit, HabitCompletion, MonthlyGoal, Transaction
    import dashboard_logic as dash

    with appmod.app.app_context():
        today = _today()
        month_start = today.replace(day=1)
        early_day = month_start + timedelta(days=min(2, dash.FINANS_GUVENILMEZ_GUN - 1))
        if early_day > today:
            pytest.skip("ayın erken bir günü bugünden sonra kalıyor, test bu ay için uygulanamaz")

        # Aktiviteyi bolca geriye çekiyoruz ki early_day'in haftalık ortalaması
        # için baktığı ÖNCEKİ 7 gün de tamamen dolu olsun — yoksa hafta
        # ortalaması kendi başına skoru 100'den saptırır, testi anlamsızlaştırır.
        start = early_day - timedelta(days=14)
        created = datetime.combine(start, datetime.min.time())
        task = DailyTask(title="T", sort_order=1, created_at=created)
        habit = Habit(name="H", impact=5, frequency_type="gunluk", active=True, created_at=created)
        db.session.add_all([task, habit])
        db.session.commit()
        d = start
        while d <= today:
            db.session.add(DailyTaskCompletion(daily_task_id=task.id, completion_date=d))
            db.session.add(HabitCompletion(habit_id=habit.id, completion_date=d))
            d += timedelta(days=1)
        # Hedefi kasıtlı büyük tutuyoruz: dahil edilseydi tempo düşük (100'den
        # belirgin farklı) çıkar ve skor 100'ün altına düşerdi.
        db.session.add(MonthlyGoal(year=today.year, month=today.month, target_amount=100000))
        db.session.add(Transaction(entry_date=early_day, kind="gelir", category="Maaş", amount=100))
        db.session.commit()

        ctx = dash.DashboardContext(today)
        # is=100, al=100, finans devreye girseydi ortalamayı düşürürdü;
        # FINANS_GUVENILMEZ_GUN eşiği yüzünden devreye girmemeli → skor 100.
        score = dash.compute_life_score(ctx, for_day=early_day)
        assert score == 100

        # Sağlamlık kontrolü: finans GERÇEKTEN düşük bir tempo yüzdesine
        # hesaplanıyor (guard olmasaydı skor gözle görülür düşerdi) — yoksa
        # yukarıdaki assert yanlışlıkla (finans zaten 100 çıktığı için) geçebilirdi.
        fin_pct = dash._finans_pace_pct(ctx, early_day)
        assert fin_pct is not None and fin_pct < 50


# ----------------------------------------------------------------------
# GÖREV 3 — compute_momentum: her iki pencerede de en az MIN_MOMENTUM_DAYS
# geçerli gün olmalı, aksi halde None.
def test_momentum_none_when_window_has_too_few_valid_days(flask_app):
    import app as appmod
    from extensions import db
    from models import DailyTask, DailyTaskCompletion
    import dashboard_logic as dash

    with appmod.app.app_context():
        today = _today()
        # Aktivite başlangıcı 20 gün önce, ama sadece SON 3 günde tamamlama var
        # → last_14 penceresinde 3 geçerli gün (activity_start'tan sonrası
        # None değil ama done kaydı yok, yine de daily_is_pct 0 döner — o
        # yüzden "geçerli gün" sayısı activity_start'a göre belirleniyor).
        # Burada gerçek MIN_MOMENTUM_DAYS eşiğini test etmek için
        # activity_start'ı son 3 güne çekiyoruz (created_at ile).
        start = today - timedelta(days=2)
        created = datetime.combine(start, datetime.min.time())
        task = DailyTask(title="T", sort_order=1, created_at=created)
        db.session.add(task)
        db.session.commit()
        db.session.add(DailyTaskCompletion(daily_task_id=task.id, completion_date=today))
        db.session.commit()

        ctx = dash.DashboardContext(today)
        # last_14 penceresinde sadece 3 geçerli gün var (< MIN_MOMENTUM_DAYS=5)
        assert dash.compute_momentum(ctx) is None
