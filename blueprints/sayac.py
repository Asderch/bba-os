from datetime import timedelta

from flask import Blueprint, render_template, request, redirect, url_for, flash

from extensions import db
from common import today_tr, TR_WEEKDAYS_SHORT, week_bounds, safe_positive_float
from models import Counter, CounterLog, WEEKDAYS

bp = Blueprint("sayac", __name__, url_prefix="/sayac")


@bp.context_processor
def inject_module_info():
    return {
        "module_theme": "sayac",
        "module_index_endpoint": "sayac.index",
        "module_brand_name": "Sayaçlar",
    }


def _format_amount(value, unit):
    value = value or 0
    text = f"{int(value):,}".replace(",", ".")
    return f"{text} {unit}" if unit else text


# ----------------------------------------------------------------------
@bp.route("/")
def index():
    today = today_tr()
    week_start, week_end = week_bounds(today)

    counters = Counter.query.filter_by(active=True).order_by(Counter.sort_order).all()

    today_totals = {}
    for log in CounterLog.query.filter_by(log_date=today).all():
        today_totals[log.counter_id] = today_totals.get(log.counter_id, 0) + log.amount

    week_totals = {}
    for log in CounterLog.query.filter(
        CounterLog.log_date >= week_start, CounterLog.log_date <= week_end,
    ).all():
        week_totals[log.counter_id] = week_totals.get(log.counter_id, 0) + log.amount

    rows = []
    for c in counters:
        today_total = today_totals.get(c.id, 0)
        rows.append({
            "counter": c,
            "today_total": today_total,
            "today_display": _format_amount(today_total, c.unit),
            "week_total_display": _format_amount(week_totals.get(c.id, 0), c.unit),
        })

    return render_template(
        "sayac/index.html", rows=rows, today=today, weekday_name=WEEKDAYS[today.weekday()],
    )


@bp.route("/<int:counter_id>/ekle-giris", methods=["POST"])
def log_amount(counter_id):
    """Sayaca bugün için bir miktar ekler (her zaman birikimli — sayaçların
    tek amacı toplamı görmek, bir hedefe ulaşma/tamamlanma kavramı yok)."""
    counter = Counter.query.get_or_404(counter_id)
    today = today_tr()
    amount = safe_positive_float(request.form.get("amount"))

    if amount is None:
        flash("Geçerli bir miktar gir.")
        return redirect(url_for("sayac.index"))

    db.session.add(CounterLog(counter_id=counter.id, log_date=today, amount=amount))
    db.session.commit()
    return redirect(url_for("sayac.index"))


@bp.route("/<int:counter_id>/geri-al", methods=["POST"])
def undo_last_log(counter_id):
    """Bugün için en son eklenen girişi siler (yanlışlıkla tıklanan bir
    '+1 dal' gibi hataları düzeltmek için)."""
    counter = Counter.query.get_or_404(counter_id)
    today = today_tr()
    last_log = (
        CounterLog.query.filter_by(counter_id=counter.id, log_date=today)
        .order_by(CounterLog.id.desc()).first()
    )
    if last_log:
        db.session.delete(last_log)
        db.session.commit()
    return redirect(url_for("sayac.index"))


# ----------------------------------------------------------------------
@bp.route("/yonet")
def manage_counters():
    counters = Counter.query.filter_by(active=True).order_by(Counter.sort_order).all()
    archived = Counter.query.filter_by(active=False).order_by(Counter.name).all()
    return render_template("sayac/yonet.html", counters=counters, archived=archived)


@bp.route("/ekle", methods=["POST"])
def add_counter():
    name = request.form.get("name", "").strip()
    unit = request.form.get("unit", "").strip()
    why = request.form.get("why", "").strip()

    if not name:
        flash("Sayaç adı zorunlu.")
        return redirect(url_for("sayac.manage_counters"))
    if Counter.query.filter_by(name=name).first():
        flash("Bu isimde bir sayaç zaten var.")
        return redirect(url_for("sayac.manage_counters"))

    max_order = db.session.query(db.func.max(Counter.sort_order)).scalar() or 0
    db.session.add(Counter(name=name, unit=unit or None, why=why or None, sort_order=max_order + 1, active=True))
    db.session.commit()
    return redirect(url_for("sayac.manage_counters"))


@bp.route("/<int:counter_id>/duzenle", methods=["GET", "POST"])
def edit_counter(counter_id):
    counter = Counter.query.get_or_404(counter_id)

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        unit = request.form.get("unit", "").strip()
        why = request.form.get("why", "").strip()

        if not name:
            flash("Sayaç adı zorunlu.")
            return redirect(url_for("sayac.edit_counter", counter_id=counter_id))

        duplicate = Counter.query.filter(Counter.name == name, Counter.id != counter_id).first()
        if duplicate:
            flash("Bu isimde başka bir sayaç zaten var.")
            return redirect(url_for("sayac.edit_counter", counter_id=counter_id))

        counter.name = name
        counter.unit = unit or None
        counter.why = why or None
        db.session.commit()
        flash(f"'{counter.name}' güncellendi.")
        return redirect(url_for("sayac.manage_counters"))

    return render_template("sayac/edit.html", counter=counter)


@bp.route("/<int:counter_id>/arsivle", methods=["POST"])
def archive_counter(counter_id):
    counter = Counter.query.get_or_404(counter_id)
    counter.active = False
    db.session.commit()
    flash(f"'{counter.name}' arşivlendi — geçmiş verisi korunuyor, istediğinde geri aktifleştirebilirsin.")
    return redirect(url_for("sayac.manage_counters"))


@bp.route("/<int:counter_id>/aktifle", methods=["POST"])
def unarchive_counter(counter_id):
    counter = Counter.query.get_or_404(counter_id)
    counter.active = True
    db.session.commit()
    flash(f"'{counter.name}' tekrar aktif.")
    return redirect(url_for("sayac.manage_counters"))


@bp.route("/<int:counter_id>/sil", methods=["POST"])
def delete_counter(counter_id):
    """Kalıcı silme — sadece arşivlenmiş sayaçlar için (geçmişiyle birlikte gider)."""
    counter = Counter.query.get_or_404(counter_id)
    if counter.active:
        flash("Önce arşivlemeden kalıcı silinemez.")
        return redirect(url_for("sayac.manage_counters"))
    db.session.delete(counter)
    db.session.commit()
    return redirect(url_for("sayac.manage_counters"))


# ----------------------------------------------------------------------
@bp.route("/istatistik")
def stats():
    today = today_tr()
    week_start, week_end = week_bounds(today)
    week_days = [week_start + timedelta(days=i) for i in range(7)]

    counters = Counter.query.filter_by(active=True).order_by(Counter.sort_order).all()

    week_logs = CounterLog.query.filter(
        CounterLog.log_date >= week_start, CounterLog.log_date <= week_end,
    ).all()
    daily_totals = {}
    for log in week_logs:
        key = (log.counter_id, log.log_date)
        daily_totals[key] = daily_totals.get(key, 0) + log.amount

    month_start = today.replace(day=1)
    month_logs = CounterLog.query.filter(
        CounterLog.log_date >= month_start, CounterLog.log_date <= today,
    ).all()
    month_totals = {}
    for log in month_logs:
        month_totals[log.counter_id] = month_totals.get(log.counter_id, 0) + log.amount

    table = []
    for c in counters:
        cells = [daily_totals.get((c.id, d), 0) for d in week_days]
        table.append({
            "counter": c,
            "cells": [_format_amount(v, c.unit) if v else "—" for v in cells],
            "week_total_display": _format_amount(sum(cells), c.unit),
            "month_total_display": _format_amount(month_totals.get(c.id, 0), c.unit),
        })

    return render_template(
        "sayac/istatistik.html",
        table=table, week_days=week_days, weekdays_short=TR_WEEKDAYS_SHORT, today=today,
    )
