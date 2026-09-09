from datetime import timedelta

from flask import Blueprint, render_template, request, redirect, url_for, flash

from extensions import db
from common import today_tr
from models import Habit, HabitCompletion, WEEKDAYS, DEFAULT_HABITS

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


# ----------------------------------------------------------------------
@bp.route("/")
def index():
    today = today_tr()
    week_start, week_end = _week_bounds(today)

    habits = Habit.query.filter_by(active=True).order_by(Habit.sort_order).all()
    todays_completions = {c.habit_id for c in HabitCompletion.query.filter_by(completion_date=today).all()}

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
    for h in habits:
        done = h.id in todays_completions
        max_puan += h.impact
        if done:
            today_puan += h.impact
        rows.append({
            "habit": h,
            "done": done,
            "week_count": week_count_by_habit.get(h.id, 0),
            "week_target": h.weekly_target if h.frequency_type == "haftalik" else 7,
            "streak": _calculate_streak(h.id),
        })

    done_count = sum(1 for r in rows if r["done"])

    return render_template(
        "aliskanlik/index.html",
        rows=rows, done_count=done_count, today=today,
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

    return render_template(
        "aliskanlik/detail.html",
        habit=habit, streak=streak, best_streak=best_streak, consistency=consistency,
        grid=grid, this_month_count=this_month_count, days_this_month=days_this_month,
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
    impact = request.form.get("impact", type=int) or 3
    frequency_type = request.form.get("frequency_type", "gunluk").strip()
    weekly_target = request.form.get("weekly_target", type=int) if frequency_type == "haftalik" else None

    if not name:
        flash("Alışkanlık adı zorunlu.")
        return redirect(url_for("aliskanlik.manage_habits"))
    if Habit.query.filter_by(name=name).first():
        flash("Bu alışkanlık zaten var.")
        return redirect(url_for("aliskanlik.manage_habits"))
    if frequency_type == "haftalik":
        weekly_target = weekly_target if (weekly_target and weekly_target > 0) else 3
        weekly_target = min(7, weekly_target)

    max_order = db.session.query(db.func.max(Habit.sort_order)).scalar() or 0
    db.session.add(Habit(
        name=name, why=why or None, impact=max(1, min(5, impact)),
        frequency_type=frequency_type, weekly_target=weekly_target,
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
        impact = request.form.get("impact", type=int) or 3
        frequency_type = request.form.get("frequency_type", "gunluk").strip()
        weekly_target = request.form.get("weekly_target", type=int) if frequency_type == "haftalik" else None

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

        habit.name = name
        habit.why = why or None
        habit.impact = max(1, min(5, impact))
        habit.frequency_type = frequency_type
        habit.weekly_target = weekly_target
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
    for i, (name, why, impact, freq, target) in enumerate(DEFAULT_HABITS):
        if name in existing_names:
            continue
        db.session.add(Habit(
            name=name, why=why, impact=impact, frequency_type=freq,
            weekly_target=target, sort_order=max_order + i + 1, active=True,
        ))
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
        table=table, week_days=week_days, weekdays=WEEKDAYS, today=today,
        week_puan=week_puan, week_max_puan=week_max_puan,
    )
