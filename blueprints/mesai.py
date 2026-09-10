from datetime import datetime

from flask import Blueprint, render_template, request, redirect, url_for, flash, session

from extensions import db
from common import (
    TR_MONTHS, today_tr,
    month_bounds as _month_bounds, prev_next_month as _prev_next_month,
    clamp_year_month, valid_year_month, safe_positive_float as _safe_positive_float,
)
from salary import calculate_salary
from models import (
    OvertimeEntry, LeaveEntry, MonthlySalary, Transaction,
    OVERTIME_CATEGORIES, OVERTIME_CATEGORY_LABELS, LEAVE_TYPES, LEAVE_TYPE_LABELS,
)

bp = Blueprint("mesai", __name__, url_prefix="/mesai")


@bp.context_processor
def inject_module_info():
    return {
        "module_theme": "mesai",
        "module_index_endpoint": "mesai.index",
        "module_brand_name": "Mesai Takip",
    }


# "gunadi" filtresi butce.py'de tanımlı (global scope, mesai şablonları da
# kullanabiliyor) — burada tekrar tanımlanmıyor.


def _get_entered_months():
    months = set()
    for row in db.session.query(MonthlySalary.year, MonthlySalary.month).all():
        months.add((row[0], row[1]))
    for row in db.session.query(
        db.extract("year", OvertimeEntry.entry_date), db.extract("month", OvertimeEntry.entry_date)
    ).distinct().all():
        months.add((int(row[0]), int(row[1])))
    for row in db.session.query(
        db.extract("year", LeaveEntry.entry_date), db.extract("month", LeaveEntry.entry_date)
    ).distinct().all():
        months.add((int(row[0]), int(row[1])))
    return sorted(months, key=lambda ym: (ym[0], ym[1]), reverse=True)


def _get_last_known_salary(before_year, before_month):
    row = (
        MonthlySalary.query
        .filter(
            db.or_(
                MonthlySalary.year < before_year,
                db.and_(MonthlySalary.year == before_year, MonthlySalary.month < before_month),
            )
        )
        .order_by(MonthlySalary.year.desc(), MonthlySalary.month.desc())
        .first()
    )
    return row.net_salary if row else None


def _parse_month_arg():
    return clamp_year_month(request.args.get("year", type=int), request.args.get("month", type=int))


def _valid_month_form():
    return valid_year_month(request.form.get("year", type=int), request.form.get("month", type=int))


# ----------------------------------------------------------------------
@bp.route("/")
def index():
    year, month = _parse_month_arg()
    first_day, last_day = _month_bounds(year, month)
    (prev_y, prev_m), (next_y, next_m) = _prev_next_month(year, month)

    overtime_entries = (
        OvertimeEntry.query
        .filter(OvertimeEntry.entry_date >= first_day, OvertimeEntry.entry_date <= last_day)
        .order_by(OvertimeEntry.entry_date.desc())
        .all()
    )

    saat_1_5x = sum(e.hours for e in overtime_entries if e.category in ("hafta_ici", "hafta_sonu"))
    saat_1x = sum(e.hours for e in overtime_entries if e.category == "resmi_tatil")
    entered_months = _get_entered_months()

    return render_template(
        "mesai/index.html",
        overtime_entries=overtime_entries,
        category_labels=OVERTIME_CATEGORY_LABELS, categories=OVERTIME_CATEGORIES,
        year=year, month=month, month_name=TR_MONTHS[month - 1],
        prev_year=prev_y, prev_month=prev_m, next_year=next_y, next_month=next_m,
        saat_1_5x=saat_1_5x, saat_1x=saat_1x, today=today_tr().isoformat(),
        entered_months=entered_months, tr_months=TR_MONTHS,
    )


@bp.route("/hesaplama")
def hesaplama():
    year, month = _parse_month_arg()
    first_day, last_day = _month_bounds(year, month)
    (prev_y, prev_m), (next_y, next_m) = _prev_next_month(year, month)

    overtime_entries = (
        OvertimeEntry.query
        .filter(OvertimeEntry.entry_date >= first_day, OvertimeEntry.entry_date <= last_day)
        .all()
    )
    leave_entries = (
        LeaveEntry.query
        .filter(LeaveEntry.entry_date >= first_day, LeaveEntry.entry_date <= last_day)
        .order_by(LeaveEntry.entry_date.desc())
        .all()
    )

    calc = calculate_salary(year, month, overtime_entries, leave_entries)
    entered_months = _get_entered_months()

    return render_template(
        "mesai/hesaplama.html",
        leave_entries=leave_entries,
        leave_type_labels=LEAVE_TYPE_LABELS, leave_types=LEAVE_TYPES,
        year=year, month=month, month_name=TR_MONTHS[month - 1],
        prev_year=prev_y, prev_month=prev_m, next_year=next_y, next_month=next_m,
        calc=calc, today=today_tr().isoformat(),
        entered_months=entered_months, tr_months=TR_MONTHS,
    )


@bp.route("/transfer-to-butce", methods=["POST"])
def transfer_to_butce():
    """V2: Bu ayın mesai tutarını Bütçe Takip'e gelir olarak aktarır."""
    year, month = _valid_month_form()
    if year is None:
        flash("Geçersiz ay/yıl.")
        return redirect(url_for("mesai.hesaplama"))
    first_day, last_day = _month_bounds(year, month)

    overtime_entries = OvertimeEntry.query.filter(
        OvertimeEntry.entry_date >= first_day, OvertimeEntry.entry_date <= last_day
    ).all()
    leave_entries = LeaveEntry.query.filter(
        LeaveEntry.entry_date >= first_day, LeaveEntry.entry_date <= last_day
    ).all()
    calc = calculate_salary(year, month, overtime_entries, leave_entries)

    if not calc["mesai_tutari"]:
        flash("Bu ay için net maaş girilmemiş ya da aktarılacak mesai tutarı yok.")
        return redirect(url_for("mesai.hesaplama", year=year, month=month))

    note = f"{TR_MONTHS[month - 1]} {year} mesai geliri"
    source = f"mesai:{year:04d}-{month:02d}"
    # Mükerrer koruması: kaynak etiketine bakıyoruz (kullanıcı Bütçe'de notu
    # ya da tarihi düzenlese bile guard tutar).
    if Transaction.query.filter_by(source=source).first():
        flash("Bu ayın mesai geliri zaten Bütçe Takip'e aktarılmış (tekrar aktarmak istersen önce Bütçe'den o kaydı sil).")
        return redirect(url_for("mesai.hesaplama", year=year, month=month))

    # Kayıt, gelirin ait olduğu AYA yazılmalı (bugünün tarihine değil) —
    # yoksa örn. Eylül'de Ağustos mesaisini aktarınca Eylül bütçesine düşerdi.
    db.session.add(Transaction(
        entry_date=last_day, kind="gelir", category="Mesai Geliri",
        amount=calc["mesai_tutari"], note=note, source=source,
    ))
    db.session.commit()
    if session.get("gelir_gizli", True):
        flash("Bu ayın mesai geliri Bütçe Takip'e aktarıldı.")
    else:
        flash(f"{calc['mesai_tutari']:.2f} ₺ Bütçe Takip'e gelir olarak aktarıldı.")
    return redirect(url_for("mesai.hesaplama", year=year, month=month))


@bp.route("/profil")
def profil():
    year, month = _parse_month_arg()
    entered_months = _get_entered_months()

    all_salaries = MonthlySalary.query.order_by(MonthlySalary.year.desc(), MonthlySalary.month.desc()).all()
    current_row = MonthlySalary.query.filter_by(year=year, month=month).first()
    current_salary = current_row.net_salary if current_row else _get_last_known_salary(year, month)

    return render_template(
        "mesai/profil.html",
        year=year, month=month, month_name=TR_MONTHS[month - 1],
        entered_months=entered_months, tr_months=TR_MONTHS,
        all_salaries=all_salaries, current_salary=current_salary,
        today=today_tr().isoformat(),
    )


@bp.route("/salary/set", methods=["POST"])
def set_salary():
    if session.get("gelir_gizli", True):
        flash("Maaş girmek/düzenlemek için önce gelirleri göster.")
        return redirect(url_for("mesai.profil"))

    year, month = _valid_month_form()
    if year is None:
        flash("Geçersiz ay/yıl.")
        return redirect(url_for("mesai.profil"))

    net_salary = _safe_positive_float(request.form.get("net_salary", ""))
    if net_salary is None:
        flash("Geçersiz maaş değeri (pozitif bir sayı girin).")
        return redirect(url_for("mesai.profil", year=year, month=month))

    row = MonthlySalary.query.filter_by(year=year, month=month).first()
    if row:
        row.net_salary = net_salary
    else:
        db.session.add(MonthlySalary(year=year, month=month, net_salary=net_salary))
    db.session.commit()
    flash("Net maaş kaydedildi.")
    return redirect(url_for("mesai.profil", year=year, month=month))


@bp.route("/overtime/add", methods=["POST"])
def add_overtime():
    entry_date_str = request.form.get("entry_date", "").strip()
    hours_str = request.form.get("hours", "").strip()
    category = request.form.get("category", "").strip()
    note = request.form.get("note", "").strip()

    if not entry_date_str or not hours_str or category not in OVERTIME_CATEGORY_LABELS:
        flash("Tarih, saat ve kategori zorunlu.")
        return redirect(url_for("mesai.index"))

    try:
        entry_date = datetime.strptime(entry_date_str, "%Y-%m-%d").date()
    except ValueError:
        flash("Tarih formatı geçersiz.")
        return redirect(url_for("mesai.index"))

    hours = _safe_positive_float(hours_str)
    if hours is None:
        flash("Saat geçerli ve 0'dan büyük olmalı.")
        return redirect(url_for("mesai.index"))

    db.session.add(OvertimeEntry(entry_date=entry_date, hours=hours, category=category, note=note or None))
    db.session.commit()
    flash("Mesai kaydı eklendi.")
    return redirect(url_for("mesai.index", year=entry_date.year, month=entry_date.month))


@bp.route("/overtime/<int:entry_id>/edit", methods=["POST"])
def edit_overtime(entry_id):
    entry = OvertimeEntry.query.get_or_404(entry_id)
    old_year, old_month = entry.entry_date.year, entry.entry_date.month

    entry_date_str = request.form.get("entry_date", "").strip()
    hours_str = request.form.get("hours", "").strip()
    category = request.form.get("category", "").strip()
    note = request.form.get("note", "").strip()

    if not entry_date_str or not hours_str or category not in OVERTIME_CATEGORY_LABELS:
        flash("Tarih, saat ve kategori zorunlu.")
        return redirect(url_for("mesai.index", year=old_year, month=old_month))

    try:
        entry_date = datetime.strptime(entry_date_str, "%Y-%m-%d").date()
    except ValueError:
        flash("Tarih formatı geçersiz.")
        return redirect(url_for("mesai.index", year=old_year, month=old_month))

    hours = _safe_positive_float(hours_str)
    if hours is None:
        flash("Saat geçerli ve 0'dan büyük olmalı.")
        return redirect(url_for("mesai.index", year=old_year, month=old_month))

    entry.entry_date = entry_date
    entry.hours = hours
    entry.category = category
    entry.note = note or None
    db.session.commit()
    flash("Mesai kaydı güncellendi.")
    return redirect(url_for("mesai.index", year=entry_date.year, month=entry_date.month))


@bp.route("/overtime/<int:entry_id>/delete", methods=["POST"])
def delete_overtime(entry_id):
    entry = OvertimeEntry.query.get_or_404(entry_id)
    year, month = entry.entry_date.year, entry.entry_date.month
    db.session.delete(entry)
    db.session.commit()
    flash("Kayıt silindi.")
    return redirect(url_for("mesai.index", year=year, month=month))


@bp.route("/leave/add", methods=["POST"])
def add_leave():
    entry_date_str = request.form.get("entry_date", "").strip()
    days_str = request.form.get("days", "").strip()
    leave_type = request.form.get("leave_type", "").strip()
    note = request.form.get("note", "").strip()

    if not entry_date_str or not days_str or leave_type not in LEAVE_TYPE_LABELS:
        flash("Tarih, gün sayısı ve tür zorunlu.")
        return redirect(url_for("mesai.hesaplama"))

    try:
        entry_date = datetime.strptime(entry_date_str, "%Y-%m-%d").date()
    except ValueError:
        flash("Tarih formatı geçersiz.")
        return redirect(url_for("mesai.hesaplama"))

    days = _safe_positive_float(days_str)
    if days is None:
        flash("Gün sayısı geçerli ve 0'dan büyük olmalı.")
        return redirect(url_for("mesai.hesaplama"))

    db.session.add(LeaveEntry(entry_date=entry_date, days=days, leave_type=leave_type, note=note or None))
    db.session.commit()
    flash("İzin kaydı eklendi.")
    return redirect(url_for("mesai.hesaplama", year=entry_date.year, month=entry_date.month))


@bp.route("/leave/<int:entry_id>/edit", methods=["POST"])
def edit_leave(entry_id):
    entry = LeaveEntry.query.get_or_404(entry_id)
    old_year, old_month = entry.entry_date.year, entry.entry_date.month

    entry_date_str = request.form.get("entry_date", "").strip()
    days_str = request.form.get("days", "").strip()
    leave_type = request.form.get("leave_type", "").strip()
    note = request.form.get("note", "").strip()

    if not entry_date_str or not days_str or leave_type not in LEAVE_TYPE_LABELS:
        flash("Tarih, gün sayısı ve tür zorunlu.")
        return redirect(url_for("mesai.hesaplama", year=old_year, month=old_month))

    try:
        entry_date = datetime.strptime(entry_date_str, "%Y-%m-%d").date()
    except ValueError:
        flash("Tarih formatı geçersiz.")
        return redirect(url_for("mesai.hesaplama", year=old_year, month=old_month))

    days = _safe_positive_float(days_str)
    if days is None:
        flash("Gün sayısı geçerli ve 0'dan büyük olmalı.")
        return redirect(url_for("mesai.hesaplama", year=old_year, month=old_month))

    entry.entry_date = entry_date
    entry.days = days
    entry.leave_type = leave_type
    entry.note = note or None
    db.session.commit()
    flash("İzin kaydı güncellendi.")
    return redirect(url_for("mesai.hesaplama", year=entry_date.year, month=entry_date.month))


@bp.route("/leave/<int:entry_id>/delete", methods=["POST"])
def delete_leave(entry_id):
    entry = LeaveEntry.query.get_or_404(entry_id)
    year, month = entry.entry_date.year, entry.entry_date.month
    db.session.delete(entry)
    db.session.commit()
    flash("Kayıt silindi.")
    return redirect(url_for("mesai.hesaplama", year=year, month=month))
