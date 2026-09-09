import calendar
import math
from datetime import date, datetime

from flask import Blueprint, render_template, request, redirect, url_for, flash, session

from extensions import db
from common import (
    TR_MONTHS, TR_WEEKDAYS, today_tr,
    month_bounds as _month_bounds, prev_next_month as _prev_next_month, clamp_year_month,
)
from salary import hourly_overtime_rate
from models import (
    Transaction, EXPENSE_CATEGORIES, INCOME_CATEGORIES, CATEGORY_COLORS,
    Subscription, SubscriptionCategory, SUBSCRIPTION_CATEGORY_COLORS,
    MonthlyGoal, MonthlySalary,
)
from chart_utils import build_donut_segments

bp = Blueprint("butce", __name__, url_prefix="/butce")


@bp.context_processor
def inject_module_info():
    return {
        "module_theme": "butce",
        "module_index_endpoint": "butce.index",
        "module_brand_name": "Bütçe Takip",
    }


@bp.app_template_filter("gunadi")
def format_entry_date(d):
    return f"{d.strftime('%d.%m')} {TR_WEEKDAYS[d.weekday()]}"


def _parse_month_arg():
    return clamp_year_month(request.args.get("year", type=int), request.args.get("month", type=int))


def _safe_amount(raw):
    """'12,50' → 12.5; geçersiz / inf / nan / <= 0 ise None döner."""
    try:
        value = float(str(raw).strip().replace(",", "."))
    except (TypeError, ValueError):
        return None
    if not math.isfinite(value) or value <= 0:
        return None
    return value


def _valid_month_form():
    """POST formundaki year/month'u doğrular; geçersizse (None, None) döner."""
    year = request.form.get("year", type=int)
    month = request.form.get("month", type=int)
    if not year or not month or not (1 <= month <= 12) or not (2000 <= year <= 2100):
        return None, None
    return year, month


def _advance_date(d, cycle):
    if cycle == "yillik":
        try:
            return d.replace(year=d.year + 1)
        except ValueError:
            return d.replace(year=d.year + 1, day=28)
    month = d.month + 1
    year = d.year + (1 if month > 12 else 0)
    month = 1 if month > 12 else month
    last_day = calendar.monthrange(year, month)[1]
    day = min(d.day, last_day)
    return date(year, month, day)


def _sub_urgency(next_renewal, today, reminder_days):
    delta = (next_renewal - today).days
    if delta < 0:
        return "gecikmis"
    if delta <= reminder_days:
        return "yaklasan"
    return "normal"


# ----------------------------------------------------------------------
@bp.route("/")
def index():
    year, month = _parse_month_arg()
    first_day, last_day = _month_bounds(year, month)
    (prev_y, prev_m), (next_y, next_m) = _prev_next_month(year, month)

    transactions = (
        Transaction.query
        .filter(Transaction.entry_date >= first_day, Transaction.entry_date <= last_day)
        .order_by(Transaction.entry_date.desc(), Transaction.created_at.desc())
        .all()
    )

    total_income = sum(t.amount for t in transactions if t.kind == "gelir")
    total_expense = sum(t.amount for t in transactions if t.kind == "gider")
    net = total_income - total_expense

    expense_by_category = {}
    for t in transactions:
        if t.kind == "gider":
            expense_by_category[t.category] = expense_by_category.get(t.category, 0) + t.amount

    category_totals = [
        {"category": cat, "amount": amt, "color": CATEGORY_COLORS.get(cat, "#8a8f98")}
        for cat, amt in sorted(expense_by_category.items(), key=lambda x: -x[1])
    ]
    donut_segments = build_donut_segments(category_totals)

    # V2: Bütçe hedefi + gerekirse mesai saat hesaplayıcı
    goal_row = MonthlyGoal.query.filter_by(year=year, month=month).first()
    goal_amount = goal_row.target_amount if goal_row else None
    goal_shortfall = None
    goal_extra_hours = None
    goal_progress_pct = None
    if goal_amount is not None:
        goal_shortfall = goal_amount - net
        # Yüzde: mutlak gelir/net rakamını sızdırmaz, gizli modda da gösterilebilir.
        goal_progress_pct = round(min(100, max(0, net / goal_amount * 100))) if goal_amount > 0 else 0
        if goal_shortfall > 0:
            salary_row = MonthlySalary.query.filter_by(year=year, month=month).first()
            saatlik_ucret = hourly_overtime_rate(salary_row.net_salary) if salary_row else None
            if saatlik_ucret:
                goal_extra_hours = goal_shortfall / saatlik_ucret

    return render_template(
        "butce/index.html",
        transactions=transactions,
        expense_categories=EXPENSE_CATEGORIES, income_categories=INCOME_CATEGORIES,
        year=year, month=month, month_name=TR_MONTHS[month - 1],
        prev_year=prev_y, prev_month=prev_m, next_year=next_y, next_month=next_m,
        total_income=total_income, total_expense=total_expense, net=net,
        donut_segments=donut_segments, today=today_tr().isoformat(),
        goal_amount=goal_amount, goal_shortfall=goal_shortfall, goal_extra_hours=goal_extra_hours,
        goal_progress_pct=goal_progress_pct,
    )


@bp.route("/gelir-gizle", methods=["POST"])
def toggle_gelir_gizli():
    """Gelir gizleme bayrağını çevirir (session'da tutulur, cihaz başına)."""
    session["gelir_gizli"] = not session.get("gelir_gizli", True)
    return redirect(request.referrer or url_for("butce.index"))


@bp.route("/goal/set", methods=["POST"])
def set_goal():
    year, month = _valid_month_form()
    if year is None:
        flash("Geçersiz ay/yıl.")
        return redirect(url_for("butce.index"))

    amount = _safe_amount(request.form.get("target_amount", ""))
    if amount is None:
        flash("Geçersiz hedef tutarı.")
        return redirect(url_for("butce.index", year=year, month=month))

    row = MonthlyGoal.query.filter_by(year=year, month=month).first()
    if row:
        row.target_amount = amount
    else:
        db.session.add(MonthlyGoal(year=year, month=month, target_amount=amount))
    db.session.commit()
    flash("Bu ayın birikim hedefi kaydedildi.")
    return redirect(url_for("butce.index", year=year, month=month))


@bp.route("/add", methods=["POST"])
def add_transaction():
    entry_date_str = request.form.get("entry_date", "").strip()
    kind = request.form.get("kind", "").strip()
    category = request.form.get("category", "").strip()
    note = request.form.get("note", "").strip()

    if kind not in ("gelir", "gider") or not entry_date_str or not category:
        flash("Tarih, tür ve kategori zorunlu.")
        return redirect(url_for("butce.index"))

    try:
        entry_date = datetime.strptime(entry_date_str, "%Y-%m-%d").date()
    except ValueError:
        flash("Tarih formatı geçersiz.")
        return redirect(url_for("butce.index"))

    amount = _safe_amount(request.form.get("amount", ""))
    if amount is None:
        flash("Tutar geçerli ve 0'dan büyük olmalı.")
        return redirect(url_for("butce.index"))

    db.session.add(Transaction(entry_date=entry_date, kind=kind, category=category, amount=amount, note=note or None))
    db.session.commit()
    flash("Kayıt eklendi.")
    return redirect(url_for("butce.index", year=entry_date.year, month=entry_date.month))


@bp.route("/transaction/<int:t_id>/edit", methods=["POST"])
def edit_transaction(t_id):
    t = Transaction.query.get_or_404(t_id)
    old_year, old_month = t.entry_date.year, t.entry_date.month

    entry_date_str = request.form.get("entry_date", "").strip()
    kind = request.form.get("kind", "").strip()
    category = request.form.get("category", "").strip()
    note = request.form.get("note", "").strip()

    if kind not in ("gelir", "gider") or not entry_date_str or not category:
        flash("Tarih, tür ve kategori zorunlu.")
        return redirect(url_for("butce.index", year=old_year, month=old_month))

    try:
        entry_date = datetime.strptime(entry_date_str, "%Y-%m-%d").date()
    except ValueError:
        flash("Tarih formatı geçersiz.")
        return redirect(url_for("butce.index", year=old_year, month=old_month))

    amount = _safe_amount(request.form.get("amount", ""))
    if amount is None:
        flash("Tutar geçerli ve 0'dan büyük olmalı.")
        return redirect(url_for("butce.index", year=old_year, month=old_month))

    t.entry_date = entry_date
    t.kind = kind
    t.category = category
    t.amount = amount
    t.note = note or None
    db.session.commit()
    flash("Kayıt güncellendi.")
    return redirect(url_for("butce.index", year=entry_date.year, month=entry_date.month))


@bp.route("/transaction/<int:t_id>/delete", methods=["POST"])
def delete_transaction(t_id):
    t = Transaction.query.get_or_404(t_id)
    year, month = t.entry_date.year, t.entry_date.month
    db.session.delete(t)
    db.session.commit()
    flash("Kayıt silindi.")
    return redirect(url_for("butce.index", year=year, month=month))


# ----------------------------------------------------------------------
@bp.route("/abonelikler")
def subscriptions_list():
    today = today_tr()
    subs = Subscription.query.order_by(Subscription.next_renewal.asc()).all()
    rows = [
        {"sub": s, "urgency": _sub_urgency(s.next_renewal, today, s.reminder_days), "days_left": (s.next_renewal - today).days}
        for s in subs
    ]

    total_monthly = sum(s.amount if s.cycle == "aylik" else s.amount / 12 for s in subs)
    total_yearly = total_monthly * 12

    categories = SubscriptionCategory.query.order_by(SubscriptionCategory.name).all()

    return render_template(
        "butce/abonelikler.html",
        rows=rows, total_monthly=total_monthly, total_yearly=total_yearly,
        sub_count=len(subs), categories=categories, sub_colors=SUBSCRIPTION_CATEGORY_COLORS,
        today=today.isoformat(),
    )


@bp.route("/subscription/add", methods=["POST"])
def add_subscription():
    name = request.form.get("name", "").strip()
    cycle = request.form.get("cycle", "").strip()
    next_renewal_str = request.form.get("next_renewal", "").strip()
    reminder_days = request.form.get("reminder_days", type=int)
    reminder_days = reminder_days if (reminder_days is not None and reminder_days >= 0) else 3
    note = request.form.get("note", "").strip()
    category_id_raw = request.form.get("category_id", "").strip()
    try:
        category_id = int(category_id_raw) if category_id_raw else None
    except ValueError:
        category_id = None

    if not name or cycle not in ("aylik", "yillik") or not next_renewal_str:
        flash("İsim, döngü ve yenilenme tarihi zorunlu.")
        return redirect(url_for("butce.subscriptions_list"))

    try:
        next_renewal = datetime.strptime(next_renewal_str, "%Y-%m-%d").date()
    except ValueError:
        flash("Tarih formatı geçersiz.")
        return redirect(url_for("butce.subscriptions_list"))

    amount = _safe_amount(request.form.get("amount", ""))
    if amount is None:
        flash("Tutar geçerli ve 0'dan büyük olmalı.")
        return redirect(url_for("butce.subscriptions_list"))

    db.session.add(Subscription(
        name=name, amount=amount, cycle=cycle, next_renewal=next_renewal,
        category_id=category_id, reminder_days=reminder_days, note=note or None,
    ))
    db.session.commit()
    flash(f"'{name}' aboneliği eklendi.")
    return redirect(url_for("butce.subscriptions_list"))


@bp.route("/subscription/<int:sub_id>/renew", methods=["POST"])
def renew_subscription(sub_id):
    sub = Subscription.query.get_or_404(sub_id)
    today = today_tr()
    renew_note = f"{sub.name} aboneliği yenilendi"
    source_prefix = f"abonelik:{sub.id}:"
    source = f"{source_prefix}{sub.next_renewal.isoformat()}"

    # Mükerrer koruması: bu abonelik bugün zaten yenilenmişse (çift tık / çift
    # submit — ilk tık next_renewal'ı ilerlettiği için source da değişiyor, o
    # yüzden id+bugün'e bakıyoruz) tekrar ekleme ve tarihi bir daha ilerletme.
    already = (
        Transaction.query
        .filter(Transaction.source.like(source_prefix + "%"), Transaction.entry_date == today)
        .first()
    )
    if already:
        flash(f"'{sub.name}' bugün zaten yenilenmiş.")
        return redirect(url_for("butce.subscriptions_list"))

    db.session.add(Transaction(
        entry_date=today, kind="gider", category="Abonelik", amount=sub.amount,
        note=renew_note, source=source,
    ))

    # Yenilenme tarihi geçmişte kaldıysa bugünün ilerisine taşınana kadar
    # ilerlet (tek tıkta yakalasın, geçmişte takılı kalmasın).
    next_renewal = _advance_date(sub.next_renewal, sub.cycle)
    guard = 0
    while next_renewal <= today and guard < 120:
        next_renewal = _advance_date(next_renewal, sub.cycle)
        guard += 1
    sub.next_renewal = next_renewal

    db.session.commit()
    flash(f"'{sub.name}' yenilendi, bir sonraki tarih {sub.next_renewal.strftime('%d.%m.%Y')} olarak güncellendi ve gider kaydına eklendi.")
    return redirect(url_for("butce.subscriptions_list"))


@bp.route("/subscription/<int:sub_id>/delete", methods=["POST"])
def delete_subscription(sub_id):
    sub = Subscription.query.get_or_404(sub_id)
    db.session.delete(sub)
    db.session.commit()
    flash(f"'{sub.name}' aboneliği kaldırıldı.")
    return redirect(url_for("butce.subscriptions_list"))


@bp.route("/subscription-category/add", methods=["POST"])
def add_subscription_category():
    name = request.form.get("name", "").strip()
    color = request.form.get("color", "").strip() or SUBSCRIPTION_CATEGORY_COLORS[0]
    if not name:
        flash("Kategori adı zorunlu.")
        return redirect(url_for("butce.subscriptions_list"))
    if SubscriptionCategory.query.filter_by(name=name).first():
        flash("Bu kategori zaten var.")
        return redirect(url_for("butce.subscriptions_list"))
    db.session.add(SubscriptionCategory(name=name, color=color))
    db.session.commit()
    return redirect(url_for("butce.subscriptions_list"))


@bp.route("/subscription-category/<int:cat_id>/delete", methods=["POST"])
def delete_subscription_category(cat_id):
    cat = SubscriptionCategory.query.get_or_404(cat_id)
    db.session.delete(cat)
    db.session.commit()
    return redirect(url_for("butce.subscriptions_list"))
