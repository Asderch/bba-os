from datetime import timedelta

from flask import Blueprint, render_template, request, redirect, url_for, flash

from extensions import db
from common import today_tr, TR_WEEKDAYS_SHORT
from models import Habit, HabitCompletion, HabitLog, WEEKDAYS, DEFAULT_HABITS

bp = Blueprint("aliskanlik", __name__, url_prefix="/aliskanlik")


@bp.context_processor
def inject_module_info():
    return {
        "module_theme": "aliskanlik",
        "module_index_endpoint": "aliskanlik.index",
        "module_brand_name": "Alışkanlık Takip",
    }


def _week_bounds(today):
    week_start = today - timedelta(days=today.weekday())
    return week_start, week_start + timedelta(days=6)


def _calculate_streak(habit_id):
    """Bugünden geriye, art arda tamamlanmış gün sayısı (current streak)."""
    today = today_tr()
    completions = {c.completion_date for c in HabitCompletion.query.filter_by(habit_id=habit_id).all()}
    streak = 0
    d = today
    if d in completions:
        streak += 1
        d -= timedelta(days=1)
    else:
        d -= timedelta(days=1)
    for _ in range(365):
        if d in completions:
            streak += 1
            d -= timedelta(days=1)
        else:
            break
    return streak


def _calculate_best_streak(habit_id):
    """Şimdiye kadarki en uzun art arda tamamlama serisi (best streak)."""
    completions = sorted({c.completion_date for c in HabitCompletion.query.filter_by(habit_id=habit_id).all()})
    if not completions:
        return 0
    best = 1
    current = 1
    for i in range(1, len(completions)):
        if (completions[i] - completions[i - 1]).days == 1:
            current += 1
            best = max(best, current)
        else:
            current = 1
    return best


def _calculate_consistency(habit):
    """
    Alışkanlığın oluşturulduğu tarihten bugüne (en fazla 30 gün), kişisel
    tutarlılık yüzdesi. Haftalık hedefli alışkanlıklar için beklenen sayı
    haftalık hedefe göre orantılanıyor (her gün %100 beklemek adil olmaz).
    """
    today = today_tr()
    created_date = habit.created_at.date() if habit.created_at else today
    days_tracked = min(30, (today - created_date).days + 1)
    days_tracked = max(days_tracked, 1)
    window_start = today - timedelta(days=days_tracked - 1)

    completions_count = HabitCompletion.query.filter(
        HabitCompletion.habit_id == habit.id,
        HabitCompletion.completion_date >= window_start,
        HabitCompletion.completion_date <= today,
    ).count()

    if habit.frequency_type == "haftalik" and habit.weekly_target:
        weeks_tracked = max(days_tracked / 7, 1)
        expected = weeks_tracked * habit.weekly_target
    else:
        expected = days_tracked

    if expected <= 0:
        return 0
    return round(min(100, completions_count / expected * 100))


def _last_30_days_grid(habit_id):
    """Son 30 günün her biri için tamamlanma durumu (contribution-graph tarzı görünüm için)."""
    today = today_tr()
    completions = {c.completion_date for c in HabitCompletion.query.filter_by(habit_id=habit_id).all()}
    days = []
    for i in range(29, -1, -1):
        d = today - timedelta(days=i)
        days.append({"date": d, "done": d in completions})
    return days


def _format_amount(value, unit):
    """"amount" tipi bir alışkanlığın miktarını okunur biçime çevirir.
    ml -> litreye çevrilip gösterilir (ör. 2500 -> "2.5 L"), diğerleri
    binlik ayraçlı tam sayı + birim olarak (ör. 7000 -> "7.000 adım")."""
    if value is None:
        return "-"
    if unit == "ml":
        return f"{value / 1000:.1f} L"
    return f"{int(value):,} {unit}".replace(",", ".")


# ----------------------------------------------------------------------
@bp.route("/")
def index():
    today = today_tr()
    week_start, week_end = _week_bounds(today)

    habits = Habit.query.filter_by(active=True).order_by(Habit.sort_order).all()
    todays_completions = {c.habit_id for c in HabitCompletion.query.filter_by(completion_date=today).all()}

    today_amount_by_habit = {}
    today_note_by_habit = {}
    for log in HabitLog.query.filter_by(log_date=today).all():
        if log.amount is not None:
            today_amount_by_habit[log.habit_id] = today_amount_by_habit.get(log.habit_id, 0) + log.amount
        if log.note is not None:
            today_note_by_habit[log.habit_id] = log.note

    week_completions = (
        HabitCompletion.query
        .filter(HabitCompletion.completion_date >= week_start, HabitCompletion.completion_date <= week_end)
        .all()
    )
    week_count_by_habit = {}
    for c in week_completions:
        week_count_by_habit[c.habit_id] = week_count_by_habit.get(c.habit_id, 0) + 1

    rows = []
    today_puan = 0
    max_puan = 0
    trackable_count = 0
    done_count = 0
    for h in habits:
        done = h.id in todays_completions
        # "counter" (ör. sigara) puana/tamamlanma sayısına hiç dahil değil —
        # azaltılması istenen bir şey, "yapıldı" kavramı burada anlamsız.
        if h.track_mode != "counter":
            trackable_count += 1
            max_puan += h.impact
            if done:
                today_puan += h.impact
                done_count += 1
        row = {
            "habit": h,
            "done": done,
            "week_count": week_count_by_habit.get(h.id, 0),
            "week_target": h.weekly_target if h.frequency_type == "haftalik" else 7,
            "streak": _calculate_streak(h.id),
        }
        if h.track_mode == "amount":
            total = today_amount_by_habit.get(h.id, 0)
            row["today_amount_raw"] = total
            row["today_amount_display"] = _format_amount(total, h.unit)
            row["target_amount_display"] = _format_amount(h.daily_target, h.unit)
            row["progress_pct"] = min(100, round(total / h.daily_target * 100)) if h.daily_target else 0
        elif h.track_mode == "note":
            row["today_note"] = today_note_by_habit.get(h.id)
        elif h.track_mode == "counter":
            row["today_amount_raw"] = today_amount_by_habit.get(h.id, 0)
            row["today_amount_display"] = _format_amount(row["today_amount_raw"], h.unit)
        rows.append(row)

    return render_template(
        "aliskanlik/index.html",
        rows=rows, done_count=done_count, trackable_count=trackable_count, today=today,
        weekday_name=WEEKDAYS[today.weekday()],
        today_puan=today_puan, max_puan=max_puan,
    )


@bp.route("/habit/<int:habit_id>/toggle", methods=["POST"])
def toggle_habit(habit_id):
    habit = Habit.query.get_or_404(habit_id)
    today = today_tr()

    existing = HabitCompletion.query.filter_by(habit_id=habit.id, completion_date=today).first()
    if existing:
        db.session.delete(existing)
    else:
        db.session.add(HabitCompletion(habit_id=habit.id, completion_date=today))
    db.session.commit()
    return redirect(url_for("aliskanlik.index"))


@bp.route("/habit/<int:habit_id>/log-amount", methods=["POST"])
def log_amount(habit_id):
    """'amount' tipi bir alışkanlığa bugün için bir miktar girer.

    amount_input_mode == "cumulative" (ör. su): her giriş günün toplamına
    EKLENİR, ayrı bir satır olarak.
    amount_input_mode == "latest" (ör. adım sayısı): girilen değer günün
    GÜNCEL toplam değeridir, önceki değerin üzerine yazılır — telefonun
    adım sayacı zaten kümülatif bir toplam gösterdiği için tekrar tekrar
    eklemek yanlış olurdu.
    """
    habit = Habit.query.get_or_404(habit_id)
    today = today_tr()
    amount = request.form.get("amount", type=float)

    if amount is None or amount < 0:
        flash("Geçerli bir miktar gir.")
        return redirect(url_for("aliskanlik.index"))

    if habit.track_mode == "counter":
        # "counter" (ör. sigara): sadece birikimli sayım, hiçbir hedef/
        # tamamlanma mantığı yok — azaltılması istenen bir şey ödüllendirilmez.
        if amount <= 0:
            flash("Geçerli bir miktar gir.")
            return redirect(url_for("aliskanlik.index"))
        db.session.add(HabitLog(habit_id=habit.id, log_date=today, amount=amount))
        db.session.commit()
        return redirect(url_for("aliskanlik.index"))

    if habit.amount_input_mode == "latest":
        existing_log = HabitLog.query.filter_by(habit_id=habit.id, log_date=today).first()
        if existing_log:
            existing_log.amount = amount
        else:
            db.session.add(HabitLog(habit_id=habit.id, log_date=today, amount=amount))
        db.session.commit()
    else:
        if amount <= 0:
            flash("Geçerli bir miktar gir.")
            return redirect(url_for("aliskanlik.index"))
        db.session.add(HabitLog(habit_id=habit.id, log_date=today, amount=amount))
        db.session.commit()

    total = db.session.query(db.func.sum(HabitLog.amount)).filter(
        HabitLog.habit_id == habit.id, HabitLog.log_date == today,
    ).scalar() or 0
    already_done = HabitCompletion.query.filter_by(habit_id=habit.id, completion_date=today).first()
    target_reached = bool(habit.daily_target) and total >= habit.daily_target
    if target_reached and not already_done:
        db.session.add(HabitCompletion(habit_id=habit.id, completion_date=today))
        db.session.commit()
    elif not target_reached and already_done and habit.amount_input_mode == "latest":
        # "latest" modunda değeri düzeltip hedefin altına çekmiş olabilir —
        # cumulative modda (su) kazanılan tamamlanma asla geri alınmaz.
        db.session.delete(already_done)
        db.session.commit()
    return redirect(url_for("aliskanlik.index"))


@bp.route("/habit/<int:habit_id>/undo-last-log", methods=["POST"])
def undo_last_log(habit_id):
    """Bugün için en son eklenen birikimli girişi siler (yanlışlıkla
    tıklanan bir '+1 dal' ya da '+500 ml' gibi hataları düzeltmek için).
    'latest' modda anlamı yok — kullanıcı zaten değeri direkt düzeltiyor."""
    habit = Habit.query.get_or_404(habit_id)
    today = today_tr()
    last_log = (
        HabitLog.query.filter_by(habit_id=habit.id, log_date=today)
        .filter(HabitLog.amount.isnot(None))
        .order_by(HabitLog.id.desc())
        .first()
    )
    if last_log:
        db.session.delete(last_log)
        db.session.commit()

        total = db.session.query(db.func.sum(HabitLog.amount)).filter(
            HabitLog.habit_id == habit.id, HabitLog.log_date == today,
        ).scalar() or 0
        already_done = HabitCompletion.query.filter_by(habit_id=habit.id, completion_date=today).first()
        if habit.daily_target and total < habit.daily_target and already_done:
            db.session.delete(already_done)
            db.session.commit()
    return redirect(url_for("aliskanlik.index"))


@bp.route("/habit/<int:habit_id>/log-note", methods=["POST"])
def log_note(habit_id):
    """'note' tipi bir alışkanlığa bugün için serbest metin notu kaydeder
    (günde tek kayıt, üzerine yazılır) ve alışkanlığı 'yapıldı' işaretler."""
    habit = Habit.query.get_or_404(habit_id)
    today = today_tr()
    note = request.form.get("note", "").strip()

    if not note:
        flash("Not boş olamaz.")
        return redirect(url_for("aliskanlik.index"))

    existing_log = HabitLog.query.filter_by(habit_id=habit.id, log_date=today).first()
    if existing_log:
        existing_log.note = note
    else:
        db.session.add(HabitLog(habit_id=habit.id, log_date=today, note=note))
    if not HabitCompletion.query.filter_by(habit_id=habit.id, completion_date=today).first():
        db.session.add(HabitCompletion(habit_id=habit.id, completion_date=today))
    db.session.commit()
    return redirect(url_for("aliskanlik.index"))


# ----------------------------------------------------------------------
@bp.route("/habit/<int:habit_id>")
def habit_detail(habit_id):
    """Tek bir alışkanlığın detay sayfası: streak, en iyi streak, tutarlılık, 30 günlük görünüm."""
    habit = Habit.query.get_or_404(habit_id)
    today = today_tr()

    streak = _calculate_streak(habit.id)
    best_streak = _calculate_best_streak(habit.id)
    consistency = _calculate_consistency(habit)
    grid = _last_30_days_grid(habit.id)

    month_start = today.replace(day=1)
    this_month_count = HabitCompletion.query.filter(
        HabitCompletion.habit_id == habit.id,
        HabitCompletion.completion_date >= month_start,
        HabitCompletion.completion_date <= today,
    ).count()
    days_this_month = (today - month_start).days + 1

    recent_logs = []
    if habit.track_mode == "note":
        recent_logs = (
            HabitLog.query.filter_by(habit_id=habit.id)
            .filter(HabitLog.note.isnot(None))
            .order_by(HabitLog.log_date.desc())
            .limit(14).all()
        )
    elif habit.track_mode in ("amount", "counter"):
        daily_totals = {}
        logs = (
            HabitLog.query.filter_by(habit_id=habit.id)
            .filter(HabitLog.amount.isnot(None))
            .order_by(HabitLog.log_date.desc())
            .limit(200).all()
        )
        for log in logs:
            daily_totals[log.log_date] = daily_totals.get(log.log_date, 0) + log.amount
        recent_logs = [
            {"date": d, "amount_display": _format_amount(total, habit.unit)}
            for d, total in sorted(daily_totals.items(), reverse=True)[:14]
        ]

    return render_template(
        "aliskanlik/detail.html",
        habit=habit, streak=streak, best_streak=best_streak, consistency=consistency,
        grid=grid, this_month_count=this_month_count, days_this_month=days_this_month,
        recent_logs=recent_logs,
    )


# ----------------------------------------------------------------------
@bp.route("/yonet")
def manage_habits():
    habits = Habit.query.filter_by(active=True).order_by(Habit.sort_order).all()
    archived = Habit.query.filter_by(active=False).order_by(Habit.name).all()
    return render_template("aliskanlik/yonet.html", habits=habits, archived=archived)


@bp.route("/habit/add", methods=["POST"])
def add_habit():
    name = request.form.get("name", "").strip()
    why = request.form.get("why", "").strip()
    target = request.form.get("target", "").strip()
    impact = request.form.get("impact", type=int) or 3
    frequency_type = request.form.get("frequency_type", "gunluk").strip()
    weekly_target = request.form.get("weekly_target", type=int) if frequency_type == "haftalik" else None
    track_mode = request.form.get("track_mode", "toggle").strip()
    unit = request.form.get("unit", "").strip()
    daily_target = request.form.get("daily_target", type=float) if track_mode == "amount" else None
    amount_input_mode = request.form.get("amount_input_mode", "cumulative").strip()

    if not name:
        flash("Alışkanlık adı zorunlu.")
        return redirect(url_for("aliskanlik.manage_habits"))
    if Habit.query.filter_by(name=name).first():
        flash("Bu alışkanlık zaten var.")
        return redirect(url_for("aliskanlik.manage_habits"))
    if frequency_type == "haftalik":
        weekly_target = weekly_target if (weekly_target and weekly_target > 0) else 3
        weekly_target = min(7, weekly_target)
    if track_mode not in ("amount", "counter"):
        unit = ""
        amount_input_mode = "cumulative"
    if track_mode == "counter":
        # "counter" puana/tamamlanmaya hiç dahil değil — etki puanı ve
        # haftalık hedef gibi alanların bir anlamı yok.
        frequency_type = "gunluk"
        weekly_target = None
        daily_target = None
        amount_input_mode = "cumulative"

    max_order = db.session.query(db.func.max(Habit.sort_order)).scalar() or 0
    db.session.add(Habit(
        name=name, why=why or None, target=target or None,
        impact=0 if track_mode == "counter" else max(1, min(5, impact)),
        frequency_type=frequency_type, weekly_target=weekly_target,
        track_mode=track_mode, unit=unit or None, daily_target=daily_target,
        amount_input_mode=amount_input_mode,
        sort_order=max_order + 1, active=True,
    ))
    db.session.commit()
    return redirect(url_for("aliskanlik.manage_habits"))


@bp.route("/habit/<int:habit_id>/edit", methods=["GET", "POST"])
def edit_habit(habit_id):
    habit = Habit.query.get_or_404(habit_id)

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        why = request.form.get("why", "").strip()
        target = request.form.get("target", "").strip()
        impact = request.form.get("impact", type=int) or 3
        frequency_type = request.form.get("frequency_type", "gunluk").strip()
        weekly_target = request.form.get("weekly_target", type=int) if frequency_type == "haftalik" else None
        track_mode = request.form.get("track_mode", "toggle").strip()
        unit = request.form.get("unit", "").strip()
        daily_target = request.form.get("daily_target", type=float) if track_mode == "amount" else None
        amount_input_mode = request.form.get("amount_input_mode", "cumulative").strip()

        if not name:
            flash("Alışkanlık adı zorunlu.")
            return redirect(url_for("aliskanlik.edit_habit", habit_id=habit_id))

        duplicate = Habit.query.filter(Habit.name == name, Habit.id != habit_id).first()
        if duplicate:
            flash("Bu isimde başka bir alışkanlık zaten var.")
            return redirect(url_for("aliskanlik.edit_habit", habit_id=habit_id))

        if frequency_type == "haftalik":
            weekly_target = weekly_target if (weekly_target and weekly_target > 0) else 3
            weekly_target = min(7, weekly_target)
        if track_mode not in ("amount", "counter"):
            unit = ""
            amount_input_mode = "cumulative"
        if track_mode == "counter":
            frequency_type = "gunluk"
            weekly_target = None
            daily_target = None
            amount_input_mode = "cumulative"

        habit.name = name
        habit.why = why or None
        habit.target = target or None
        habit.impact = 0 if track_mode == "counter" else max(1, min(5, impact))
        habit.frequency_type = frequency_type
        habit.weekly_target = weekly_target
        habit.track_mode = track_mode
        habit.unit = unit or None
        habit.daily_target = daily_target
        habit.amount_input_mode = amount_input_mode
        db.session.commit()
        flash(f"'{habit.name}' güncellendi.")
        return redirect(url_for("aliskanlik.manage_habits"))

    return render_template("aliskanlik/edit.html", habit=habit)


@bp.route("/habit/<int:habit_id>/archive", methods=["POST"])
def archive_habit(habit_id):
    habit = Habit.query.get_or_404(habit_id)
    habit.active = False
    db.session.commit()
    flash(f"'{habit.name}' arşivlendi — geçmiş verisi korunuyor, istediğinde geri aktifleştirebilirsin.")
    return redirect(url_for("aliskanlik.manage_habits"))


@bp.route("/habit/<int:habit_id>/unarchive", methods=["POST"])
def unarchive_habit(habit_id):
    habit = Habit.query.get_or_404(habit_id)
    habit.active = True
    db.session.commit()
    flash(f"'{habit.name}' tekrar aktif.")
    return redirect(url_for("aliskanlik.manage_habits"))


@bp.route("/habit/<int:habit_id>/delete", methods=["POST"])
def delete_habit(habit_id):
    """Kalıcı silme — sadece arşivlenmiş alışkanlıklar için (geçmişiyle birlikte gider)."""
    habit = Habit.query.get_or_404(habit_id)
    db.session.delete(habit)
    db.session.commit()
    return redirect(url_for("aliskanlik.manage_habits"))


@bp.route("/habit/seed-defaults", methods=["POST"])
def seed_defaults():
    """Hazır 8 alışkanlık setini ekler, isim çakışanları atlar."""
    existing_names = {h.name for h in Habit.query.all()}
    max_order = db.session.query(db.func.max(Habit.sort_order)).scalar() or 0
    added = 0
    for i, defaults in enumerate(DEFAULT_HABITS):
        if defaults["name"] in existing_names:
            continue
        db.session.add(Habit(sort_order=max_order + i + 1, active=True, **defaults))
        added += 1
    db.session.commit()
    flash(f"{added} hazır alışkanlık eklendi." if added else "Hazır alışkanlıkların hepsi zaten listende.")
    return redirect(url_for("aliskanlik.manage_habits"))


# ----------------------------------------------------------------------
@bp.route("/istatistik")
def stats():
    today = today_tr()
    week_start, week_end = _week_bounds(today)
    week_days = [week_start + timedelta(days=i) for i in range(7)]

    habits = Habit.query.filter_by(active=True).order_by(Habit.sort_order).all()
    completions = (
        HabitCompletion.query
        .filter(HabitCompletion.completion_date >= week_start, HabitCompletion.completion_date <= week_end)
        .all()
    )
    done_set = {(c.habit_id, c.completion_date) for c in completions}

    table = []
    week_puan = 0
    week_max_puan = 0
    for h in habits:
        cells = [(h.id, d) in done_set for d in week_days]
        completed_days = sum(cells)
        week_puan += completed_days * h.impact
        week_max_puan += 7 * h.impact
        table.append({
            "habit": h, "cells": cells,
            "total": completed_days, "streak": _calculate_streak(h.id),
        })

    return render_template(
        "aliskanlik/istatistik.html",
        table=table, week_days=week_days, weekdays=WEEKDAYS, weekdays_short=TR_WEEKDAYS_SHORT, today=today,
        week_puan=week_puan, week_max_puan=week_max_puan,
    )
