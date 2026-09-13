"""Analizler — tüm modüllerin (İş/Alışkanlık/Finans/Mesai) tek bir sayfada
toplanan analiz/dashboard görünümü.

Önceden "Analizler" sidebar linki yanlışlıkla İş Takip modülünün kendi
istatistik sayfasına (`is_takip.stats`) gidiyordu — ayrı bir modül gibi
görünen bir sekme aslında başka bir modülün içine gömülüydü. Bu blueprint
o sayfayı buraya taşıyor (İş Takip haftalık tablosu) ve üstüne Life Score
(zaten İş+Alışkanlık+Finans'ı harmanlayan tek metrik), momentum, istikrar,
içgörüler ve her modülün kısa özetini ekleyerek gerçek bir "tüm bilgilerin
analizi" sayfası haline getiriyor.
"""
from datetime import timedelta

from flask import Blueprint, render_template

import dashboard_logic as dash
from common import TR_WEEKDAYS, today_tr
from salary import calculate_salary
from settings import get_gelir_gizli
from models import DailyTask, DailyTaskCompletion, Habit, HabitCompletion

bp = Blueprint("analizler", __name__, url_prefix="/analizler")


@bp.context_processor
def inject_module_info():
    return {
        "module_theme": "analizler",
        "module_index_endpoint": "analizler.index",
        "module_brand_name": "Analizler",
    }


def _week_bounds(today):
    week_start = today - timedelta(days=today.weekday())
    return week_start, week_start + timedelta(days=6)


def _is_takip_weekly(today, week_start, week_days):
    """`blueprints/is_takip.py`'nin eski `stats()` route'undan taşındı —
    aynı desen: payda sadece aktif görevleri sayar (arşivlenmiş görevler
    hariç), ama günlük tamamlama kayıtları tarihe göre filtrelenir, görev
    aktifliğine göre DEĞİL (geçmiş bütünlüğü korunur)."""
    daily_task_count = DailyTask.query.filter_by(active=True).count()
    completions = (
        DailyTaskCompletion.query
        .filter(DailyTaskCompletion.completion_date >= week_start, DailyTaskCompletion.completion_date <= today)
        .all()
    )
    completions_by_date = {}
    for c in completions:
        completions_by_date.setdefault(c.completion_date, set()).add(c.daily_task_id)

    week_table = []
    for d in week_days:
        done_count = len(completions_by_date.get(d, set()))
        week_table.append({
            "date": d, "weekday": TR_WEEKDAYS[d.weekday()],
            "done": done_count, "total": daily_task_count,
            "is_future": d > today,
        })

    total_possible = daily_task_count * sum(1 for d in week_days if d <= today)
    total_done = sum(len(v) for v in completions_by_date.values())
    completion_rate = round(total_done / total_possible * 100) if total_possible > 0 else 0
    return {
        "week_table": week_table, "completion_rate": completion_rate,
        "total_done": total_done, "total_possible": total_possible,
    }


def _aliskanlik_weekly(week_start, week_end):
    """Haftalık toplam puan özeti — `aliskanlik.stats()`'in kendi detaylı
    (alışkanlık bazlı) tablosunu tekrar üretmiyor, sadece toplamı verip
    detay için o sayfaya yönlendiriyor."""
    habits = Habit.query.filter_by(active=True).all()
    if not habits:
        return {"week_puan": 0, "week_max_puan": 0, "pct": None}
    completions = (
        HabitCompletion.query
        .filter(HabitCompletion.completion_date >= week_start, HabitCompletion.completion_date <= week_end)
        .all()
    )
    done_set = {(c.habit_id, c.completion_date) for c in completions}
    week_days = [week_start + timedelta(days=i) for i in range(7)]
    week_puan = sum(h.impact for h in habits for d in week_days if (h.id, d) in done_set)
    week_max_puan = sum(7 * h.impact for h in habits)
    pct = round(week_puan / week_max_puan * 100) if week_max_puan else None
    return {"week_puan": week_puan, "week_max_puan": week_max_puan, "pct": pct}


@bp.route("/")
def index():
    today = today_tr()
    week_start, week_end = _week_bounds(today)
    week_days = [week_start + timedelta(days=i) for i in range(7)]
    gelir_gizli = get_gelir_gizli()

    ctx = dash.DashboardContext(today)

    # --- Life Score + trend (tüm modülleri zaten harmanlayan tek metrik) ---
    life_score = dash.compute_life_score(ctx, gelir_gizli=gelir_gizli)
    ls_days = dash.life_score_days(ctx)
    breakdown = dash.life_score_breakdown(ctx, gelir_gizli=gelir_gizli)
    history = dash.life_score_history(ctx, days=14, gelir_gizli=gelir_gizli)
    trend_points_str, trend_last_point = dash.trend_svg_points(history)

    # --- Mesai (bu ay) — ctx'in önbelleğinden, ek sorgu yok ---
    mesai_calc = calculate_salary(today.year, today.month, ctx.month_overtime, ctx.month_leave)

    return render_template(
        "analizler/index.html",
        today=today,
        life_score=life_score, life_score_low=ls_days < dash.MIN_LIFESCORE_DAYS,
        life_score_days=ls_days, life_score_delta=dash.life_score_delta(ctx, gelir_gizli=gelir_gizli),
        breakdown=breakdown,
        momentum=dash.compute_momentum(ctx), istikrar=dash.compute_istikrar(ctx),
        insights=dash.get_insights(ctx),
        trend_points_str=trend_points_str, trend_last_point=trend_last_point,
        is_takip=_is_takip_weekly(today, week_start, week_days),
        aliskanlik=_aliskanlik_weekly(week_start, week_end),
        finans={"income": ctx.month_income, "expense": ctx.month_expense, "net": ctx.month_net},
        mesai={"hours": ctx.month_overtime_hours, "amount": mesai_calc.get("mesai_tutari")},
    )
