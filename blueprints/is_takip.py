from datetime import datetime

from flask import Blueprint, render_template, request, redirect, url_for, flash

from extensions import db
from common import TR_MONTHS, TR_WEEKDAYS, today_tr, local_now, safe_redirect_target, valid_hex_color
from models import DailyTask, DailyTaskCompletion, DeadlineTask, NonWorkDay, Tag, TAG_COLORS

bp = Blueprint("is_takip", __name__, url_prefix="/is")

YAKLASAN_ESIK_GUN = 3


@bp.context_processor
def inject_module_info():
    return {
        "module_theme": "is-takip",
        "module_index_endpoint": "is_takip.index",
        "module_brand_name": "İş Takip",
    }


@bp.app_template_filter("tamtarih")
def format_full_date(d):
    return f"{TR_WEEKDAYS[d.weekday()]}, {d.day} {TR_MONTHS[d.month - 1]} {d.year}"


@bp.app_template_filter("kisatarih")
def format_short_date(d):
    return f"{d.day:02d}.{d.month:02d}.{d.year}"


def _urgency(due_date, today):
    delta = (due_date - today).days
    if delta < 0:
        return "gecikmis"
    if delta <= YAKLASAN_ESIK_GUN:
        return "yaklasan"
    return "normal"


def _get_tag_id():
    raw = request.form.get("tag_id", "").strip()
    try:
        return int(raw) if raw else None
    except ValueError:
        return None


# ----------------------------------------------------------------------
@bp.route("/")
def index():
    today = today_tr()
    is_non_work_today = NonWorkDay.query.filter_by(work_date=today).first() is not None

    daily_tasks = DailyTask.query.filter_by(active=True).order_by(DailyTask.sort_order).all()
    todays_completions = {
        c.daily_task_id
        for c in DailyTaskCompletion.query.filter_by(completion_date=today).all()
    }
    daily_rows = [{"task": t, "done": t.id in todays_completions} for t in daily_tasks]
    daily_done_count = sum(1 for r in daily_rows if r["done"])

    deadline_tasks = DeadlineTask.query.filter_by(done=False).order_by(DeadlineTask.due_date.asc()).all()
    deadline_rows = [
        {"task": t, "urgency": _urgency(t.due_date, today), "days_left": (t.due_date - today).days}
        for t in deadline_tasks
    ]

    return render_template(
        "is_takip/index.html",
        today=today, weekday_name=TR_WEEKDAYS[today.weekday()],
        daily_rows=daily_rows, daily_done_count=daily_done_count,
        deadline_rows=deadline_rows, is_non_work_today=is_non_work_today,
    )


@bp.route("/gun/bugun-calismiyorum", methods=["POST"])
def toggle_non_work_today():
    """'Bugün çalışmıyorum' — Günlük İşlerim tamamen işyerine özgü olduğu
    için, bu gün Life Score'un İş boyutundan tamamen hariç tutulur (bkz.
    dashboard_logic.DashboardContext.non_work_days)."""
    today = today_tr()
    existing = NonWorkDay.query.filter_by(work_date=today).first()
    if existing:
        db.session.delete(existing)
        flash("Bugün tekrar normal bir çalışma günü olarak işaretlendi.")
    else:
        db.session.add(NonWorkDay(work_date=today))
        flash("Bugün 'çalışmıyorum' olarak işaretlendi — günlük işler bugün için Life Score'u etkilemeyecek.")
    db.session.commit()
    return redirect(safe_redirect_target(request.referrer, request.host) or url_for("is_takip.index"))


@bp.route("/daily/<int:task_id>/toggle", methods=["POST"])
def toggle_daily_task(task_id):
    task = DailyTask.query.get_or_404(task_id)
    today = today_tr()
    existing = DailyTaskCompletion.query.filter_by(daily_task_id=task.id, completion_date=today).first()
    if existing:
        db.session.delete(existing)
    else:
        db.session.add(DailyTaskCompletion(daily_task_id=task.id, completion_date=today))
    db.session.commit()
    return redirect(safe_redirect_target(request.referrer, request.host) or url_for("is_takip.index"))


@bp.route("/deadline/<int:task_id>/complete", methods=["POST"])
def complete_deadline_task(task_id):
    task = DeadlineTask.query.get_or_404(task_id)
    task.done = True
    task.done_at = local_now()
    db.session.commit()
    flash(f"'{task.title}' tamamlandı olarak işaretlendi.")
    return redirect(safe_redirect_target(request.referrer, request.host) or url_for("is_takip.index"))


@bp.route("/deadline/<int:task_id>/delete", methods=["POST"])
def delete_deadline_task(task_id):
    task = DeadlineTask.query.get_or_404(task_id)
    db.session.delete(task)
    db.session.commit()
    return redirect(safe_redirect_target(request.referrer, request.host) or url_for("is_takip.index"))


# ----------------------------------------------------------------------
@bp.route("/yonet")
def manage_tasks():
    daily_tasks = DailyTask.query.filter_by(active=True).order_by(DailyTask.sort_order).all()
    archived = DailyTask.query.filter_by(active=False).order_by(DailyTask.title).all()
    today = today_tr()
    deadline_tasks = DeadlineTask.query.filter_by(done=False).order_by(DeadlineTask.due_date.asc()).all()
    deadline_rows = [{"task": t, "urgency": _urgency(t.due_date, today)} for t in deadline_tasks]
    tags = Tag.query.order_by(Tag.name).all()
    # Geçmişi de göster (silinmiş bir gün kayıtta kalmaz) ama en yakın/gelecek
    # olanlar üstte olsun — planlama için asıl önemli olan bunlar.
    non_work_days = NonWorkDay.query.order_by(NonWorkDay.work_date.desc()).all()
    return render_template(
        "is_takip/yonet.html", daily_tasks=daily_tasks, archived=archived, deadline_rows=deadline_rows,
        today=today.isoformat(), tags=tags, tag_colors=TAG_COLORS, non_work_days=non_work_days,
    )


@bp.route("/gun/ekle", methods=["POST"])
def add_non_work_day():
    date_str = request.form.get("work_date", "").strip()
    note = request.form.get("note", "").strip()
    if not date_str:
        flash("Tarih zorunlu.")
        return redirect(url_for("is_takip.manage_tasks"))
    try:
        work_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        flash("Tarih formatı geçersiz.")
        return redirect(url_for("is_takip.manage_tasks"))

    if NonWorkDay.query.filter_by(work_date=work_date).first():
        flash(f"{work_date.strftime('%d.%m.%Y')} zaten çalışılmayan gün olarak işaretli.")
        return redirect(url_for("is_takip.manage_tasks"))

    db.session.add(NonWorkDay(work_date=work_date, note=note or None))
    db.session.commit()
    flash(f"{work_date.strftime('%d.%m.%Y')} çalışılmayan gün olarak işaretlendi.")
    return redirect(url_for("is_takip.manage_tasks"))


@bp.route("/gun/<int:non_work_day_id>/sil", methods=["POST"])
def delete_non_work_day(non_work_day_id):
    row = NonWorkDay.query.get_or_404(non_work_day_id)
    db.session.delete(row)
    db.session.commit()
    flash(f"{row.work_date.strftime('%d.%m.%Y')} tekrar normal bir çalışma günü.")
    return redirect(url_for("is_takip.manage_tasks"))


@bp.route("/tags/add", methods=["POST"])
def add_tag():
    name = request.form.get("name", "").strip()
    color = valid_hex_color(request.form.get("color"), TAG_COLORS[0])
    if not name:
        flash("Etiket adı zorunlu.")
        return redirect(url_for("is_takip.manage_tasks"))
    if Tag.query.filter_by(name=name).first():
        flash("Bu etiket zaten var.")
        return redirect(url_for("is_takip.manage_tasks"))
    db.session.add(Tag(name=name, color=color))
    db.session.commit()
    return redirect(url_for("is_takip.manage_tasks"))


@bp.route("/tags/<int:tag_id>/delete", methods=["POST"])
def delete_tag(tag_id):
    tag = Tag.query.get_or_404(tag_id)
    db.session.delete(tag)
    db.session.commit()
    return redirect(url_for("is_takip.manage_tasks"))


@bp.route("/daily/add", methods=["POST"])
def add_daily_task():
    title = request.form.get("title", "").strip()
    note = request.form.get("note", "").strip()
    if not title:
        flash("Görev başlığı zorunlu.")
        return redirect(url_for("is_takip.manage_tasks"))

    max_order = db.session.query(db.func.max(DailyTask.sort_order)).scalar() or 0
    db.session.add(DailyTask(title=title, note=note or None, sort_order=max_order + 1, tag_id=_get_tag_id()))
    db.session.commit()
    return redirect(url_for("is_takip.manage_tasks"))


@bp.route("/daily/<int:task_id>/archive", methods=["POST"])
def archive_daily_task(task_id):
    task = DailyTask.query.get_or_404(task_id)
    task.active = False
    db.session.commit()
    flash(f"'{task.title}' arşivlendi — geçmiş kaydı korunuyor, istediğinde geri aktifleştirebilirsin.")
    return redirect(url_for("is_takip.manage_tasks"))


@bp.route("/daily/<int:task_id>/unarchive", methods=["POST"])
def unarchive_daily_task(task_id):
    task = DailyTask.query.get_or_404(task_id)
    task.active = True
    db.session.commit()
    flash(f"'{task.title}' tekrar aktif.")
    return redirect(url_for("is_takip.manage_tasks"))


@bp.route("/daily/<int:task_id>/delete", methods=["POST"])
def delete_daily_task(task_id):
    """Kalıcı silme — sadece arşivlenmiş görevler için (geçmişiyle birlikte gider).
    Aktif bir görev silinmek istenirse reddedilir, önce arşivlemesi istenir —
    yoksa cascade ile geçmiş tamamlama kayıtları gider ve geçmiş Life Score'lar
    geriye dönük değişir (payda güncel görev sayısına göre yeniden hesaplanır)."""
    task = DailyTask.query.get_or_404(task_id)
    if task.active:
        flash(f"'{task.title}' önce arşivlenmeli — aktif bir görev kalıcı silinemez.")
        return redirect(url_for("is_takip.manage_tasks"))
    db.session.delete(task)
    db.session.commit()
    return redirect(url_for("is_takip.manage_tasks"))


@bp.route("/deadline/add", methods=["POST"])
def add_deadline_task():
    title = request.form.get("title", "").strip()
    due_date_str = request.form.get("due_date", "").strip()
    note = request.form.get("note", "").strip()

    if not title or not due_date_str:
        flash("Görev başlığı ve termin tarihi zorunlu.")
        return redirect(url_for("is_takip.manage_tasks"))

    try:
        due_date = datetime.strptime(due_date_str, "%Y-%m-%d").date()
    except ValueError:
        flash("Geçersiz termin tarihi.")
        return redirect(url_for("is_takip.manage_tasks"))

    db.session.add(DeadlineTask(title=title, due_date=due_date, note=note or None, tag_id=_get_tag_id()))
    db.session.commit()
    return redirect(url_for("is_takip.manage_tasks"))


# ----------------------------------------------------------------------
@bp.route("/gecmis")
def history():
    completed_deadlines = DeadlineTask.query.filter_by(done=True).order_by(DeadlineTask.done_at.desc()).all()
    daily_history = (
        DailyTaskCompletion.query
        .join(DailyTask)
        .order_by(DailyTaskCompletion.completion_date.desc(), DailyTaskCompletion.completed_at.desc())
        .limit(200)
        .all()
    )
    return render_template("is_takip/gecmis.html", completed_deadlines=completed_deadlines, daily_history=daily_history)


