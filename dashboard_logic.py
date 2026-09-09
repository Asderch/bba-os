"""
V3/V4: Merkezi Dashboard hesaplamaları.

Performans notu: Bu modül önceden her gün için ayrı ayrı veritabanı sorgusu
atıyordu (90 günlük içgörü penceresi için ~1000 sorguya kadar çıkabiliyordu,
bu da ana sayfayı 3+ saniyeye kadar yavaşlatıyordu). Şimdi tüm hesaplamalar
tek bir DashboardContext üzerinden yapılıyor: ihtiyaç duyulan en geniş
pencere (90 gün) için gerekli veri BİR KEZ toplu çekiliyor, tüm alt
hesaplamalar bellek içi sözlüklerden okuyor.
"""
import calendar
from datetime import timedelta

from extensions import db
from models import (
    DailyTask, DailyTaskCompletion, DeadlineTask,
    Habit, HabitCompletion, OvertimeEntry, LeaveEntry, Transaction, MonthlyGoal, Subscription,
)

XP_PER_LEVEL = 1000
IYI_GUN_ESIGI = 50  # blended günlük performans bu yüzdenin üzerindeyse "iyi gün" sayılır
CONTEXT_LOOKBACK_DAYS = 90  # tüm alt hesaplamaların ihtiyaç duyduğu en geniş pencere


class DashboardContext:
    """
    Tek bir istek için gereken tüm günlük performans verisini önceden,
    toplu sorgularla çeker. Bu nesne oluşturulduğunda toplam 2-3 sorgu atılır,
    sonrasında daily_is_pct/daily_aliskanlik_pct/daily_blended_pct çağrıları
    hiç veritabanına gitmez.
    """

    def __init__(self, today, lookback_days=CONTEXT_LOOKBACK_DAYS):
        self.today = today
        self.window_start = today - timedelta(days=lookback_days - 1)

        # Uygulamanın fiilen kullanılmaya başlandığı ilk gün. Bundan ÖNCEKİ
        # günler için günlük performans "%0" değil None döner — yoksa 10 gün
        # önce başlayan biri için İstikrar/Momentum/içgörüler, geçmişi zorla
        # sıfırla doldurup yanıltıcı (ve cesaret kırıcı) çıkıyordu.
        self.activity_start = self._compute_activity_start(today)

        self.total_daily_tasks = DailyTask.query.count()

        self.habits = Habit.query.filter_by(active=True).all()
        self.max_puan = sum(h.impact for h in self.habits)
        habit_ids = {h.id for h in self.habits}

        daily_completions = DailyTaskCompletion.query.filter(
            DailyTaskCompletion.completion_date >= self.window_start,
            DailyTaskCompletion.completion_date <= today,
        ).all()
        self.daily_done_by_date = {}
        for c in daily_completions:
            self.daily_done_by_date.setdefault(c.completion_date, set()).add(c.daily_task_id)

        habit_completions = HabitCompletion.query.filter(
            HabitCompletion.completion_date >= self.window_start,
            HabitCompletion.completion_date <= today,
        ).all()
        self.habit_done_by_date = {}
        for c in habit_completions:
            if c.habit_id in habit_ids:  # arşivlenmiş alışkanlıklar günlük performansa katılmasın
                self.habit_done_by_date.setdefault(c.completion_date, set()).add(c.habit_id)

        # Bu ayın bütçe hedefi + net durumu + mesai saati — BİR KEZ çekilir,
        # compute_life_score / life_score_breakdown / monthly_balance hepsi
        # buradan okur (eskiden compute_life_score her çağrıda ayrı sorgu
        # atıyordu, life_score_history bunu 14 kez çağırıyordu → 28+ sorgu).
        month_start = today.replace(day=1)
        month_end = today.replace(day=calendar.monthrange(today.year, today.month)[1])
        self.month_start = month_start
        goal = MonthlyGoal.query.filter_by(year=today.year, month=today.month).first()
        self.month_goal_amount = goal.target_amount if (goal and goal.target_amount > 0) else None
        month_txs = Transaction.query.filter(
            Transaction.entry_date >= month_start, Transaction.entry_date <= month_end
        ).all()
        self.month_income = sum(t.amount for t in month_txs if t.kind == "gelir")
        self.month_expense = sum(t.amount for t in month_txs if t.kind == "gider")
        self.month_net = self.month_income - self.month_expense
        self.month_overtime_hours = (
            db.session.query(db.func.sum(OvertimeEntry.hours)).filter(
                OvertimeEntry.entry_date >= month_start, OvertimeEntry.entry_date <= today
            ).scalar() or 0
        )

    @staticmethod
    def _compute_activity_start(today):
        candidates = [
            db.session.query(db.func.min(DailyTaskCompletion.completion_date)).scalar(),
            db.session.query(db.func.min(HabitCompletion.completion_date)).scalar(),
            db.session.query(db.func.min(OvertimeEntry.entry_date)).scalar(),
        ]
        for created in (
            db.session.query(db.func.min(DailyTask.created_at)).scalar(),
            db.session.query(db.func.min(Habit.created_at)).scalar(),
        ):
            if created is not None:
                candidates.append(created.date() if hasattr(created, "date") else created)
        dates = [d for d in candidates if d is not None]
        return min(dates) if dates else today

    def daily_is_pct(self, day):
        if day < self.activity_start or self.total_daily_tasks == 0:
            return None
        done = len(self.daily_done_by_date.get(day, set()))
        return done / self.total_daily_tasks * 100

    def daily_aliskanlik_pct(self, day):
        if day < self.activity_start or self.max_puan == 0:
            return None
        done_ids = self.habit_done_by_date.get(day, set())
        gunun_puani = sum(h.impact for h in self.habits if h.id in done_ids)
        return gunun_puani / self.max_puan * 100

    def daily_blended_pct(self, day):
        parts = [p for p in (self.daily_is_pct(day), self.daily_aliskanlik_pct(day)) if p is not None]
        if not parts:
            return None
        return sum(parts) / len(parts)


# ----------------------------------------------------------------------
def compute_life_score(ctx, for_day=None):
    """
    0-100 arası Life Score. Sadece 'bugünü' değil, o günle birlikte önceki 7
    günün ortalamasını da harmanlıyor — tek bir iyi/kötü gün skoru gereğinden
    fazla oynatmasın diye. `for_day` verilmezse ctx.today kullanılır (geriye
    dönük tahmin için farklı bir gün de verilebilir - Bütçe hedef boyutu o
    durumda yine ctx.today'in ayına göre hesaplanır, basitleştirme).
    """
    day = for_day or ctx.today
    parts = []

    is_pct_today = ctx.daily_is_pct(day)
    al_pct_today = ctx.daily_aliskanlik_pct(day)

    week_days = [day - timedelta(days=i) for i in range(7)]
    is_week_vals = [v for v in (ctx.daily_is_pct(d) for d in week_days) if v is not None]
    al_week_vals = [v for v in (ctx.daily_aliskanlik_pct(d) for d in week_days) if v is not None]

    if is_pct_today is not None:
        is_week_avg = sum(is_week_vals) / len(is_week_vals) if is_week_vals else is_pct_today
        parts.append((is_pct_today + is_week_avg) / 2)

    if al_pct_today is not None:
        al_week_avg = sum(al_week_vals) / len(al_week_vals) if al_week_vals else al_pct_today
        parts.append((al_pct_today + al_week_avg) / 2)

    # Bütçe boyutu ctx'te önceden hesaplanan bu-ay verisinden (basitleştirme:
    # geçmiş günler için de bu ayın durumu kullanılır).
    if ctx.month_goal_amount:
        parts.append(min(100, max(0, ctx.month_net / ctx.month_goal_amount * 100)))

    if not parts:
        return None
    return round(sum(parts) / len(parts))


# Mesai alt-boyutu için "dolu" kabul edilen aylık fazla mesai saati (kaba
# referans; kesin bir hedef kavramı yok).
MESAI_AYLIK_REF_SAAT = 40
MIN_LIFESCORE_DAYS = 3  # bundan az günlük veriyle Life Score göstermek yerine "toplanıyor" denir


def _blend_today_week(today_val, week_vals):
    """compute_life_score ile aynı harman: (bugün + son 7 gün ort.) / 2."""
    if today_val is None:
        return None
    wk = sum(week_vals) / len(week_vals) if week_vals else today_val
    return (today_val + wk) / 2


def life_score_breakdown(ctx):
    """
    Life Score'un 4 alt-boyutu (İş / Alışkanlık / Finans / Mesai) — her biri
    0-100 veya veri yoksa None. "78 — ama alışkanlıkta gelişim alanı var"
    tarzı bir okuma için: sayı bir not değil, nereye dokunacağını söyleyen harita.
    """
    day = ctx.today
    week = [day - timedelta(days=i) for i in range(7)]

    is_b = _blend_today_week(
        ctx.daily_is_pct(day),
        [v for v in (ctx.daily_is_pct(d) for d in week) if v is not None],
    )
    al_b = _blend_today_week(
        ctx.daily_aliskanlik_pct(day),
        [v for v in (ctx.daily_aliskanlik_pct(d) for d in week) if v is not None],
    )
    fin_b = None
    if ctx.month_goal_amount:
        fin_b = min(100, max(0, ctx.month_net / ctx.month_goal_amount * 100))
    mesai_b = None
    if ctx.month_overtime_hours:
        mesai_b = min(100, ctx.month_overtime_hours / MESAI_AYLIK_REF_SAAT * 100)

    def r(v):
        return round(v) if v is not None else None

    return {
        "is": r(is_b), "aliskanlik": r(al_b),
        "finans": r(fin_b), "mesai": r(mesai_b),
        # hangi boyut en düşük (odak önerisi için)
        "weakest": min(
            (("is", is_b), ("aliskanlik", al_b), ("finans", fin_b)),
            key=lambda kv: kv[1] if kv[1] is not None else 999,
        )[0] if any(v is not None for v in (is_b, al_b, fin_b)) else None,
    }


def life_score_days(ctx):
    """Son 14 günde 'veri var' sayısı — Life Score'a güven eşiği için."""
    return sum(
        1 for i in range(14)
        if ctx.daily_blended_pct(ctx.today - timedelta(days=i)) is not None
    )


def life_score_history(ctx, days=14):
    """Son N günün Life Score tahminini döner: [{'date': ..., 'score': ...}, ...] (eskiden yeniye)."""
    history = []
    for i in range(days - 1, -1, -1):
        d = ctx.today - timedelta(days=i)
        score = compute_life_score(ctx, for_day=d)
        history.append({"date": d, "score": score})
    return history


def life_score_delta(ctx):
    """Bugünün Life Score'u ile dünkü arasındaki fark (yüzde puan). Biri eksikse None."""
    today_score = compute_life_score(ctx, for_day=ctx.today)
    yesterday_score = compute_life_score(ctx, for_day=ctx.today - timedelta(days=1))
    if today_score is None or yesterday_score is None:
        return None
    return today_score - yesterday_score


# ----------------------------------------------------------------------
def compute_xp():
    """Mevcut tamamlama kayıtlarından toplam XP türetir (ayrı bir log tablosu yok)."""
    xp = 0
    xp += DailyTaskCompletion.query.count() * 10
    xp += DeadlineTask.query.filter_by(done=True).count() * 25
    xp += OvertimeEntry.query.count() * 10

    habit_completions = HabitCompletion.query.join(Habit).all()
    xp += sum(c.habit.impact * 5 for c in habit_completions)

    return xp


def level_info(xp):
    level = xp // XP_PER_LEVEL + 1
    progress_in_level = xp % XP_PER_LEVEL
    progress_pct = round(progress_in_level / XP_PER_LEVEL * 100)
    return {
        "level": level, "xp": xp,
        "progress_in_level": progress_in_level, "xp_per_level": XP_PER_LEVEL,
        "progress_pct": progress_pct,
    }


# ----------------------------------------------------------------------
def compute_momentum(ctx):
    """Son 14 gün ile önceki 14 günün ortalama performansı arasındaki fark (yüzde puan)."""
    today = ctx.today

    def avg_pct(days):
        vals = [v for v in (ctx.daily_blended_pct(d) for d in days) if v is not None]
        return sum(vals) / len(vals) if vals else None

    last_14 = [today - timedelta(days=i) for i in range(0, 14)]
    prev_14 = [today - timedelta(days=i) for i in range(14, 28)]

    avg_last = avg_pct(last_14)
    avg_prev = avg_pct(prev_14)

    if avg_last is None or avg_prev is None:
        return None
    return round(avg_last - avg_prev)


# ----------------------------------------------------------------------
MIN_ISTIKRAR_DAYS = 5  # bundan az günlük veriyle "İstikrar %" göstermek yanıltıcı/cesaret kırıcı olur


def compute_istikrar(ctx):
    """
    Son 30 günün kaçında 'iyi gün' geçirilmiş (blended performans >= eşik).
    Hem yüzde hem ham gün sayısını döner ("22/30 gün" gibi daha somut bir
    ifade kurabilmek için) — yeterli veri yoksa (en az MIN_ISTIKRAR_DAYS gün)
    None döner, düşük ve yanıltıcı bir erken yüzde göstermek yerine.
    """
    days = [ctx.today - timedelta(days=i) for i in range(30)]
    valid = [v for v in (ctx.daily_blended_pct(d) for d in days) if v is not None]
    if len(valid) < MIN_ISTIKRAR_DAYS:
        return None
    good_days = sum(1 for v in valid if v >= IYI_GUN_ESIGI)
    return {
        "pct": round(good_days / len(valid) * 100),
        "good_days": good_days,
        "total_days": len(valid),
    }


# ----------------------------------------------------------------------
def monthly_balance(ctx):
    """
    4 modülün bu ay (ay başından bugüne) performans yüzdesi ('Bu Ay' widget'ı için).
    Not: Finans ve Mesai için sabit bir 'hedef' kavramı olmadığından basit
    referans değerler kullanılıyor (Finans: varsa aylık hedef yüzdesi,
    Mesai: ayda 40 saat = dolu kabul edilir) - kesin ölçüm değil, kabaca
    bir denge göstergesi.
    """
    month_start = ctx.today.replace(day=1)
    month_days = [month_start + timedelta(days=i) for i in range((ctx.today - month_start).days + 1)]

    is_vals = [v for v in (ctx.daily_is_pct(d) for d in month_days) if v is not None]
    is_pct = round(sum(is_vals) / len(is_vals)) if is_vals else None

    al_vals = [v for v in (ctx.daily_aliskanlik_pct(d) for d in month_days) if v is not None]
    al_pct = round(sum(al_vals) / len(al_vals)) if al_vals else None

    txs = Transaction.query.filter(
        Transaction.entry_date >= month_start, Transaction.entry_date <= ctx.today
    ).all()
    month_net = sum(t.amount for t in txs if t.kind == "gelir") - sum(t.amount for t in txs if t.kind == "gider")
    goal = MonthlyGoal.query.filter_by(year=ctx.today.year, month=ctx.today.month).first()
    if goal and goal.target_amount > 0:
        finans_pct = round(min(100, max(0, month_net / goal.target_amount * 100)))
    else:
        finans_pct = None

    month_hours = db.session.query(db.func.sum(OvertimeEntry.hours)).filter(
        OvertimeEntry.entry_date >= month_start, OvertimeEntry.entry_date <= ctx.today
    ).scalar() or 0
    mesai_pct = round(min(100, month_hours / 40 * 100)) if month_hours else 0

    return {
        "is_pct": is_pct, "aliskanlik_pct": al_pct,
        "finans_pct": finans_pct, "mesai_pct": mesai_pct,
    }


def upcoming_events(today, limit=5):
    """Terminli işler + abonelik yenilemelerini tek bir 'Yaklaşanlar' listesinde birleştirir.
    Geçmişte kalanlar buraya girmez — gecikmiş terminler öncelikler bölümünde gösteriliyor."""
    events = []

    deadlines = (
        DeadlineTask.query.filter(DeadlineTask.done == False, DeadlineTask.due_date >= today)  # noqa: E712
        .order_by(DeadlineTask.due_date.asc())
        .limit(limit * 2)
        .all()
    )
    for t in deadlines:
        events.append({"date": t.due_date, "title": t.title, "source": "İş"})

    subs = (
        Subscription.query.filter(Subscription.next_renewal >= today)
        .order_by(Subscription.next_renewal.asc())
        .limit(limit * 2)
        .all()
    )
    for s in subs:
        events.append({"date": s.next_renewal, "title": f"{s.name} yenileniyor", "source": "Finans"})

    events.sort(key=lambda e: e["date"])
    return events[:limit]


def upcoming_split(today, limit=4):
    """'Yaklaşanlar'ı iki ayrı sütun için böler: terminli işler ve abonelik
    yenilemeleri. Geçmişte kalanlar girmez."""
    deadlines = (
        DeadlineTask.query.filter(DeadlineTask.done == False, DeadlineTask.due_date >= today)  # noqa: E712
        .order_by(DeadlineTask.due_date.asc())
        .limit(limit)
        .all()
    )
    subs = (
        Subscription.query.filter(Subscription.next_renewal >= today)
        .order_by(Subscription.next_renewal.asc())
        .limit(limit)
        .all()
    )
    return {
        "isler": [
            {"date": t.due_date, "title": t.title, "days_left": (t.due_date - today).days}
            for t in deadlines
        ],
        "abonelik": [
            {"date": s.next_renewal, "title": s.name, "days_left": (s.next_renewal - today).days}
            for s in subs
        ],
    }


def dashboard_priorities(ctx, limit=3):
    """
    Ana sayfadaki 'Günün Öncelikleri': en fazla `limit` madde. Önce gecikmiş/
    yaklaşan terminler, sonra bugün henüz tamamlanmamış günlük işler. ROADMAP
    ilkesi: "15 iş varsa hepsini değil, bugün en öncelikli 3'ünü öne çıkar."
    Tamamlanmış işlerle doldurma YOK — liste kısa ve eyleme dönük kalsın.
    Ayrıca bugünün ilerleme sayacı (done/total) döner.
    """
    priorities = []

    deadlines = DeadlineTask.query.filter_by(done=False).order_by(DeadlineTask.due_date.asc()).all()
    for t in deadlines:
        delta = (t.due_date - ctx.today).days
        if delta <= 3:
            priorities.append({
                "type": "deadline", "id": t.id, "title": t.title, "done": False,
                "urgency": "gecikmis" if delta < 0 else "yaklasan",
            })
        if len(priorities) >= limit:
            break

    todays_done_ids = ctx.daily_done_by_date.get(ctx.today, set())
    daily_tasks = DailyTask.query.order_by(DailyTask.sort_order).all()
    if len(priorities) < limit:
        undone = [t for t in daily_tasks if t.id not in todays_done_ids]
        for t in undone[: limit - len(priorities)]:
            priorities.append({
                "type": "daily", "id": t.id, "title": t.title,
                "done": False, "urgency": "normal",
            })

    done_count = sum(1 for t in daily_tasks if t.id in todays_done_ids)
    return {
        "rows": priorities[:limit],
        "done_today": done_count,
        "total_today": len(daily_tasks),
    }


# ----------------------------------------------------------------------
# V4: Kural tabanlı içgörüler - yeterli veri yoksa None döner, hiç gösterilmez
TR_WEEKDAY_NAMES = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
MIN_SAMPLES_PER_GROUP = 3


def insight_best_weekday(ctx):
    """Son 90 günde, ortalama performansı en yüksek haftanın günü (en az 2 örnekle)."""
    by_weekday = {}
    for i in range(CONTEXT_LOOKBACK_DAYS):
        d = ctx.today - timedelta(days=i)
        pct = ctx.daily_blended_pct(d)
        if pct is not None:
            by_weekday.setdefault(d.weekday(), []).append(pct)

    candidates = {wd: vals for wd, vals in by_weekday.items() if len(vals) >= 2}
    if not candidates:
        return None

    best_wd = max(candidates, key=lambda wd: sum(candidates[wd]) / len(candidates[wd]))
    avg = sum(candidates[best_wd]) / len(candidates[best_wd])
    return {"weekday": TR_WEEKDAY_NAMES[best_wd], "avg_pct": round(avg)}


def insight_is_full_days_habit_quality(ctx):
    """
    İş Takip'i tam tamamladığın günlerin kaçında Alışkanlık performansı da
    ortalamanın üzerindeydi. Önceki sürümden farkı: karşılaştırma için
    'tamamlamadığın günler' grubuna ihtiyaç duymuyor - bu yüzden başarı
    arttıkça (tamamlanmamış gün azaldıkça) bu içgörü kaybolmuyor.
    """
    full_days_al, all_al = [], []
    for i in range(CONTEXT_LOOKBACK_DAYS):
        d = ctx.today - timedelta(days=i)
        is_pct = ctx.daily_is_pct(d)
        al_pct = ctx.daily_aliskanlik_pct(d)
        if al_pct is None:
            continue
        all_al.append(al_pct)
        if is_pct is not None and is_pct >= 99.9:
            full_days_al.append(al_pct)

    if len(full_days_al) < 5:
        return None

    overall_avg = sum(all_al) / len(all_al)
    above_count = sum(1 for v in full_days_al if v >= overall_avg)
    if above_count / len(full_days_al) < 0.6:
        return None
    return {"above_count": above_count, "total": len(full_days_al)}


def _longest_streak_in_window(ctx):
    """ctx penceresi içinde (90 gün), şimdiye kadarki en uzun %100 günlük iş serisi."""
    best = current = 0
    for i in range(CONTEXT_LOOKBACK_DAYS - 1, -1, -1):
        d = ctx.today - timedelta(days=i)
        pct = ctx.daily_is_pct(d)
        if pct is not None and pct >= 99.9:
            current += 1
            best = max(best, current)
        else:
            current = 0
    return best


MIN_STREAK_FOR_CELEBRATION = 5


def insight_consistency_streak(ctx):
    """
    Günlük işleri art arda kaç gündür %100 tamamlıyor. Eğer bu, görebildiğimiz
    pencere içinde (90 gün) şimdiye kadarki en uzun seriyse 'is_record' True olur
    (rekor/milestone önceliği için).
    """
    streak = 0
    d = ctx.today
    for _ in range(CONTEXT_LOOKBACK_DAYS):
        pct = ctx.daily_is_pct(d)
        if pct is not None and pct >= 99.9:
            streak += 1
            d -= timedelta(days=1)
        else:
            break
    if streak < MIN_STREAK_FOR_CELEBRATION:
        return None
    best_ever = _longest_streak_in_window(ctx)
    return {"streak": streak, "is_record": streak >= best_ever}


def insight_week_over_week(ctx):
    """Bu haftanın (son 7 gün) ortalama performansı, önceki haftaya göre anlamlı ölçüde iyileştiyse gösterilir."""
    this_week = [ctx.today - timedelta(days=i) for i in range(7)]
    last_week = [ctx.today - timedelta(days=i) for i in range(7, 14)]

    this_vals = [v for v in (ctx.daily_blended_pct(d) for d in this_week) if v is not None]
    last_vals = [v for v in (ctx.daily_blended_pct(d) for d in last_week) if v is not None]
    if len(this_vals) < 4 or len(last_vals) < 4:
        return None

    diff = round(sum(this_vals) / len(this_vals) - sum(last_vals) / len(last_vals))
    if diff <= 5:
        return None
    return {"diff": diff}


def insight_momentum_summary(ctx):
    """Momentum'u okunabilir bir içgörü cümlesine çevirir - anlamlı bir değişim yoksa gösterilmez."""
    m = compute_momentum(ctx)
    if m is None or abs(m) < 5:
        return None
    return {"momentum": m}


def insight_finans_aliskanlik_link(ctx):
    """Harcamanın yüksek/düşük olduğu günlerde Alışkanlık performansı nasıl farklılaşıyor."""
    txs = Transaction.query.filter(
        Transaction.entry_date >= ctx.window_start, Transaction.entry_date <= ctx.today,
        Transaction.kind == "gider",
    ).all()
    if not txs:
        return None

    daily_expense = {}
    for t in txs:
        daily_expense[t.entry_date] = daily_expense.get(t.entry_date, 0) + t.amount
    avg_expense = sum(daily_expense.values()) / len(daily_expense)

    high_days_al, low_days_al = [], []
    for i in range(CONTEXT_LOOKBACK_DAYS):
        d = ctx.today - timedelta(days=i)
        al_pct = ctx.daily_aliskanlik_pct(d)
        if al_pct is None:
            continue
        (high_days_al if daily_expense.get(d, 0) > avg_expense else low_days_al).append(al_pct)

    if len(high_days_al) < MIN_SAMPLES_PER_GROUP or len(low_days_al) < MIN_SAMPLES_PER_GROUP:
        return None

    diff = round(sum(low_days_al) / len(low_days_al) - sum(high_days_al) / len(high_days_al))
    if abs(diff) < 3:
        return None
    return {"diff": diff, "higher_when_low_expense": diff > 0}


def insight_mesai_link(ctx):
    """Mesai yaptığın günlerde iş+alışkanlık performansı nasıl farklılaşıyor."""
    overtime_days = {
        o.entry_date for o in OvertimeEntry.query.filter(
            OvertimeEntry.entry_date >= ctx.window_start, OvertimeEntry.entry_date <= ctx.today,
        ).all()
    }
    if not overtime_days:
        return None

    mesai_perf, non_mesai_perf = [], []
    for i in range(CONTEXT_LOOKBACK_DAYS):
        d = ctx.today - timedelta(days=i)
        pct = ctx.daily_blended_pct(d)
        if pct is None:
            continue
        (mesai_perf if d in overtime_days else non_mesai_perf).append(pct)

    if len(mesai_perf) < MIN_SAMPLES_PER_GROUP or len(non_mesai_perf) < MIN_SAMPLES_PER_GROUP:
        return None

    diff = round(sum(mesai_perf) / len(mesai_perf) - sum(non_mesai_perf) / len(non_mesai_perf))
    if abs(diff) < 3:
        return None
    return {"diff": diff, "higher_when_mesai": diff > 0}


def get_insights(ctx, max_insights=3):
    """
    Tüm hesaplanabilir içgörü adaylarını toplar, her birine bir öncelik puanı
    verir (1 = en değerli), sıralar ve en fazla `max_insights` tanesini döner.
    Öncelik sırası (değerden aza): 1) Yeni keşif (çapraz modül korelasyonu),
    2) Güçlü davranış ilişkisi, 3) Rekor/milestone, 4) Tutarlılık,
    5) Performans paterni. Anlamlı hiçbir şey yoksa boş liste döner - "her
    zaman bir şey söyle" kuralı yok, sahte/zorlama içgörü üretilmiyor.
    """
    candidates = []  # her biri: (öncelik, dict)

    # 3. Rekor/milestone VEYA 4. Tutarlılık (streak'in kendisine göre değişir)
    streak = insight_consistency_streak(ctx)
    if streak:
        if streak["is_record"]:
            candidates.append((3, {
                "icon": "trophy",
                "text": f"İlk kez {streak['streak']} günlük kesintisiz bir tamamlama serisi oluşturdun.",
                "suggestion": "Bu bir rekor — bugün bunu bozmamaya odaklan.",
            }))
        else:
            candidates.append((4, {
                "icon": "flame",
                "text": f"{streak['streak']} gündür günlük işlerini kesintisiz %100 tamamlıyorsun.",
                "suggestion": "Bu tempoyu bozmadan devam et — istikrar, tek bir mükemmel günden daha değerli.",
            }))

    # 4. Tutarlılık - hafta karşılaştırması
    wow = insight_week_over_week(ctx)
    if wow:
        candidates.append((4, {
            "icon": "chart-line",
            "text": f"Bu hafta, önceki haftaya göre ortalama {wow['diff']} puan daha istikrarlı ilerliyorsun.",
            "suggestion": "Bu haftaki neyin farklı olduğunu fark et, tekrar edilebilir hale getir.",
        }))

    # 2. Güçlü davranış ilişkisi (tek-grup, negatif karşılaştırma gerektirmiyor)
    full_quality = insight_is_full_days_habit_quality(ctx)
    if full_quality:
        candidates.append((2, {
            "icon": "link",
            "text": f"İşlerini tamamen tamamladığın {full_quality['total']} günün {full_quality['above_count']}'inde, Alışkanlık skorun da ortalamanın üzerindeydi.",
            "suggestion": "Günlük işlerini bitirmek, alışkanlıklarına da güç veriyor gibi görünüyor — bu düzeni koru.",
        }))

    # 1. Yeni keşif - çapraz modül korelasyonları
    finans_link = insight_finans_aliskanlik_link(ctx)
    if finans_link:
        if finans_link["higher_when_low_expense"]:
            candidates.append((1, {
                "icon": "coin",
                "text": f"Harcamanın düşük olduğu günlerde, Alışkanlık performansın ortalama {finans_link['diff']} puan daha yüksek.",
                "suggestion": "Büyük harcama yaptığın günlerde alışkanlıklarına da zaman ayırmayı unutma.",
            }))
        else:
            candidates.append((1, {
                "icon": "coin",
                "text": f"Harcamanın yüksek olduğu günlerde, Alışkanlık performansın ortalama {-finans_link['diff']} puan daha yüksek.",
                "suggestion": "Harcama ve alışkanlık arasında ilginç bir ilişki var — hangi günler olduğuna bir bak.",
            }))

    mesai_link = insight_mesai_link(ctx)
    if mesai_link:
        if mesai_link["higher_when_mesai"]:
            candidates.append((1, {
                "icon": "clock",
                "text": f"Mesai yaptığın günlerde, iş+alışkanlık performansın ortalama {mesai_link['diff']} puan daha yüksek.",
                "suggestion": "Mesai günlerinde disiplinin gerçekten güçlü görünüyor.",
            }))
        else:
            candidates.append((1, {
                "icon": "clock",
                "text": f"Mesai yaptığın günlerde, iş+alışkanlık performansın ortalama {-mesai_link['diff']} puan daha düşük.",
                "suggestion": "Mesai sonrası kendine biraz tolerans tanı, ertesi güne yıkma.",
            }))

    # 5. Performans paterni
    wd = insight_best_weekday(ctx)
    if wd:
        candidates.append((5, {
            "icon": "calendar",
            "text": f"{wd['weekday']} günleri ortalama performansın (%{wd['avg_pct']}) diğer günlerden daha yüksek.",
            "suggestion": f"Önemli işlerini mümkün olduğunca {wd['weekday']} gününe planla.",
        }))

    # Not: Momentum'un kendisi ana ekranda "Son 14 Gün" grafiğinin rozetinde
    # zaten gösteriliyor — burada ayrıca bir içgörü kartına çevirmiyoruz
    # (aynı bilgiyi iki kez söylememek için). insight_momentum_summary hâlâ
    # başka yerlerde kullanılabilir diye duruyor.

    candidates.sort(key=lambda c: c[0])
    return [c[1] for c in candidates[:max_insights]]


# ======================================================================
# Ana ekran (home.html) için tek noktadan bağlam kurulumu.
# Eskiden bu ~120 satır app.py'nin root() view'ının içindeydi.
# ======================================================================
def build_home_context(ctx, now):
    """
    home.html'in ihtiyaç duyduğu HER ŞEYİ tek sözlükte döner. `ctx` önceden
    kurulmuş bir DashboardContext, `now` Türkiye saatiyle şu an (datetime).
    """
    from common import TR_MONTHS, TR_WEEKDAYS

    today = ctx.today

    # --- Life Score + boyutlar ---
    life_score = compute_life_score(ctx)
    ls_days = life_score_days(ctx)
    breakdown = life_score_breakdown(ctx)

    # --- Bugün şeridi ---
    is_daily_count = ctx.total_daily_tasks
    is_daily_done_today = len(ctx.daily_done_by_date.get(today, set()))
    aliskanlik_total = len(ctx.habits)
    aliskanlik_done = len(ctx.habit_done_by_date.get(today, set()))

    open_deadlines = DeadlineTask.query.filter_by(done=False).all()
    is_urgent_count = sum(1 for t in open_deadlines if (t.due_date - today).days <= 3)

    todays_expense = sum(
        t.amount for t in Transaction.query.filter_by(entry_date=today, kind="gider").all()
    )

    mesai_today_hours = (
        db.session.query(db.func.sum(OvertimeEntry.hours))
        .filter(OvertimeEntry.entry_date == today)
        .scalar() or 0
    )
    # Bu ayki tahmini mesai geliri (net maaş girilmişse)
    from salary import calculate_salary
    month_end = today.replace(day=calendar.monthrange(today.year, today.month)[1])
    month_ot = OvertimeEntry.query.filter(
        OvertimeEntry.entry_date >= ctx.month_start, OvertimeEntry.entry_date <= month_end
    ).all()
    month_lv = LeaveEntry.query.filter(
        LeaveEntry.entry_date >= ctx.month_start, LeaveEntry.entry_date <= month_end
    ).all()
    mesai_calc = calculate_salary(today.year, today.month, month_ot, month_lv)
    mesai_month_amount = mesai_calc.get("mesai_tutari")

    # --- Trend (SVG) ---
    history = life_score_history(ctx, days=14)
    chart_w, chart_h = 280, 70
    n = len(history)
    pts = []
    for i, h in enumerate(history):
        if h["score"] is None:
            continue
        x = (i / (n - 1) * chart_w) if n > 1 else 0
        y = chart_h - (h["score"] / 100 * chart_h)
        pts.append(f"{x:.1f},{y:.1f}")
    trend_points_str = " ".join(pts)
    trend_last_point = pts[-1] if pts else None

    hour = now.hour
    greeting = (
        "İyi geceler" if hour < 6 else
        "Günaydın" if hour < 12 else
        "İyi günler" if hour < 18 else
        "İyi akşamlar"
    )

    return {
        "greeting": greeting,
        "today": today,
        "today_str": f"{today.day} {TR_MONTHS[today.month - 1]} {today.year}",
        "weekday_str": TR_WEEKDAYS[today.weekday()],

        "life_score": life_score,
        "life_score_delta": life_score_delta(ctx),
        "life_score_low": ls_days < MIN_LIFESCORE_DAYS,
        "life_score_days": ls_days,
        "breakdown": breakdown,

        "momentum": compute_momentum(ctx),
        "istikrar": compute_istikrar(ctx),

        "priorities": dashboard_priorities(ctx),
        "insights": get_insights(ctx),
        "upcoming": upcoming_split(today),

        "is_daily_count": is_daily_count,
        "is_daily_done_today": is_daily_done_today,
        "is_urgent_count": is_urgent_count,
        "aliskanlik_total": aliskanlik_total,
        "aliskanlik_done": aliskanlik_done,
        "todays_expense": todays_expense,
        "mesai_today_hours": mesai_today_hours,
        "mesai_month_amount": mesai_month_amount,

        "trend_points_str": trend_points_str,
        "trend_last_point": trend_last_point,
    }
