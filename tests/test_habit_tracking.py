"""Alışkanlıklarda 'amount' (miktar) ve 'note' (not) takip modları:
sadece tik yerine gerçek veri girilebilmeli, hedefe ulaşınca otomatik
'yapıldı' işaretlenmeli ve girilen veri (miktar/not) kalıcı olmalı
(gelecekte insight'larda kullanılabilmesi için)."""
from common import today_tr as _today


def _seed_amount_habit(unit="ml", daily_target=2500):
    from extensions import db
    from models import Habit
    habit = Habit(
        name="Su iç", impact=4, frequency_type="gunluk",
        track_mode="amount", unit=unit, daily_target=daily_target,
    )
    db.session.add(habit)
    db.session.commit()
    return habit


def _seed_note_habit():
    from extensions import db
    from models import Habit
    habit = Habit(name="Öğrenme", impact=3, frequency_type="gunluk", track_mode="note")
    db.session.add(habit)
    db.session.commit()
    return habit


def test_log_amount_accumulates_and_auto_completes_at_target(client, flask_app):
    import app as appmod
    from models import Habit, HabitCompletion, HabitLog

    with appmod.app.app_context():
        habit = _seed_amount_habit(daily_target=500)
        habit_id = habit.id

    client.post(f"/aliskanlik/habit/{habit_id}/log-amount", data={"amount": "200"})
    with appmod.app.app_context():
        assert HabitCompletion.query.filter_by(habit_id=habit_id, completion_date=_today()).first() is None
        assert HabitLog.query.filter_by(habit_id=habit_id).count() == 1

    # ikinci ekleme toplamı hedefe (500) ulaştırıyor -> otomatik "yapıldı"
    client.post(f"/aliskanlik/habit/{habit_id}/log-amount", data={"amount": "300"})
    with appmod.app.app_context():
        assert HabitCompletion.query.filter_by(habit_id=habit_id, completion_date=_today()).first() is not None
        logs = HabitLog.query.filter_by(habit_id=habit_id).all()
        assert sum(l.amount for l in logs) == 500


def test_log_amount_rejects_invalid_amount(client, flask_app):
    import app as appmod
    from models import HabitLog

    with appmod.app.app_context():
        habit = _seed_amount_habit()
        habit_id = habit.id

    client.post(f"/aliskanlik/habit/{habit_id}/log-amount", data={"amount": "0"})
    client.post(f"/aliskanlik/habit/{habit_id}/log-amount", data={})
    with appmod.app.app_context():
        assert HabitLog.query.filter_by(habit_id=habit_id).count() == 0


def test_index_shows_amount_progress(client, flask_app):
    import app as appmod

    with appmod.app.app_context():
        habit = _seed_amount_habit(daily_target=2500)
        habit_id = habit.id

    client.post(f"/aliskanlik/habit/{habit_id}/log-amount", data={"amount": "1250"})
    html = client.get("/aliskanlik/").get_data(as_text=True)
    assert "1.3 L / 2.5 L" in html or "1.2 L / 2.5 L" in html
    assert "%50" in html


def test_log_note_saves_and_marks_done(client, flask_app):
    import app as appmod
    from models import HabitCompletion, HabitLog

    with appmod.app.app_context():
        habit = _seed_note_habit()
        habit_id = habit.id

    client.post(f"/aliskanlik/habit/{habit_id}/log-note", data={"note": "Flask blueprint yapısını tekrar ettim."})
    with appmod.app.app_context():
        assert HabitCompletion.query.filter_by(habit_id=habit_id, completion_date=_today()).first() is not None
        log = HabitLog.query.filter_by(habit_id=habit_id, log_date=_today()).first()
        assert log.note == "Flask blueprint yapısını tekrar ettim."

    # aynı gün ikinci kayıt üzerine yazmalı, ikinci bir satır oluşturmamalı
    client.post(f"/aliskanlik/habit/{habit_id}/log-note", data={"note": "Ek olarak testleri de okudum."})
    with appmod.app.app_context():
        assert HabitLog.query.filter_by(habit_id=habit_id, log_date=_today()).count() == 1
        log = HabitLog.query.filter_by(habit_id=habit_id, log_date=_today()).first()
        assert log.note == "Ek olarak testleri de okudum."


def test_log_note_rejects_empty_note(client, flask_app):
    import app as appmod
    from models import HabitCompletion, HabitLog

    with appmod.app.app_context():
        habit = _seed_note_habit()
        habit_id = habit.id

    client.post(f"/aliskanlik/habit/{habit_id}/log-note", data={"note": "   "})
    with appmod.app.app_context():
        assert HabitLog.query.filter_by(habit_id=habit_id).count() == 0
        assert HabitCompletion.query.filter_by(habit_id=habit_id).count() == 0


def test_seed_defaults_assigns_track_modes(client, flask_app):
    import app as appmod
    from models import Habit

    client.post("/aliskanlik/habit/seed-defaults")
    with appmod.app.app_context():
        su = Habit.query.filter_by(name="Yeterli su iç").first()
        adim = Habit.query.filter_by(name="7.000+ adım").first()
        ogrenme = Habit.query.filter_by(name="20 dk öğrenme").first()
        toparla = Habit.query.filter_by(name="10 dk ortamı toparla").first()

        assert su.track_mode == "amount" and su.unit == "ml" and su.daily_target == 2500
        assert adim.track_mode == "amount" and adim.unit == "adım" and adim.daily_target == 7000
        assert ogrenme.track_mode == "note"
        assert toparla.track_mode == "toggle"
