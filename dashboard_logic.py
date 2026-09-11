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
from common import TR_MONTHS, TR_WEEKDAYS, month_bounds
from salary import calculate_salary
from models import (
    DailyTask, DailyTaskCompletion, DeadlineTask,
    Habit, HabitCompletion, OvertimeEntry, LeaveEntry, Transaction, MonthlyGoal, Subscription,
)

IYI_GUN_ESIGI = 50  # blended günlük performans bu yüzdenin üzerindeyse "iyi gün" sayılır
CONTEXT_LOOKBACK_DAYS = 90  # tüm alt hesaplamaların ihtiyaç duyduğu en geniş pencere


class DashboardContext:
    """
    Tek bir istek için gereken tüm günlük performans verisini önceden,
    toplu sorgularla çeker. Bu nesne oluşturulduğunda yaklaşık 10-20 sorgu
    atılır (activity_start hesaplaması, aktif görev/alışkanlık listeleri,
    tamamlama pencereleri ve ay-bazlı bütçe/mesai verisi dahil — tam sayı
    görev/alışkanlık sayısına ve ay geçişi olup olmamasına göre değişir),
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

        self.total_daily_tasks = DailyTask.query.filter_by(active=True).count()
        daily_task_ids = {t.id for t in DailyTask.query.filter_by(active=True).all()}

        self.habits = Habit.query.filter_by(active=True).all()
        self.max_puan = sum(h.impact for h in self.habits)
        habit_ids = {h.id for h in self.habits}

        daily_completions = DailyTaskCompletion.query.filter(
            DailyTaskCompletion.completion_date >= self.window_start,
            DailyTaskCompletion.completion_date <= today,
        ).all()
        self.daily_done_by_date = {}
        for c in daily_completions:
            if c.daily_task_id in daily_task_ids:  # arşivlenmiş görevler günlük performansa katılmasın
                self.daily_done_by_date.setdefault(c.completion_date, set()).add(c.daily_task_id)

        habit_completions = HabitCompletion.query.filter(
            HabitCompletion.completion_date >= self.window_start,
            HabitCompletion.completion_date <= today,
        ).all()
        self.habit_done_by_date = {}
        for c in habit_completions:
            if c.habit_id in habit_ids:  # arşivlenmiş alışkanlıklar günlük performansa katılmasın
                self.habit_done_by_date.setdefault(c.completion_date, set()).add(c.habit_id)

        # Bu ayın bütçe hedefi + net durumu + mesai kayıtları — BİR KEZ çekilir,
        # compute_life_score / life_score_breakdown / build_home_context hepsi
        # buradan okur (eskiden compute_life_score her çağrıda ayrı sorgu
        # atıyordu, life_score_history bunu 14 kez çağırıyordu → 28+ sorgu).
        # Pencere: tüm ay (month_start..month_end). Mesai/izin kayıtları
        # pratikte geçmişe yazıldığından "bugüne kadar" ile aynı sonucu verir
        # ama pencereyi her yerde eşit tutmak tutarlılık için önemli.
        month_start = today.replace(day=1)
        month_end = today.replace(day=calendar.monthrange(today.year, today.month)[1])
        self.month_start = month_start
        self.month_end = month_end
        self.month_days_total = calendar.monthrange(today.year, today.month)[1]
        goal = MonthlyGoal.query.filter_by(year=today.year, month=today.month).first()
        self.month_goal_amount = goal.target_amount if (goal and goal.target_amount > 0) else None
        month_txs = Transaction.query.filter(
            Transaction.entry_date >= month_start, Transaction.entry_date <= month_end
        ).all()
        self.month_income = sum(t.amount for t in month_txs if t.kind == "gelir")
        self.month_expense = sum(t.amount for t in month_txs if t.kind == "gider")
        self.month_net = self.month_income - self.month_expense
        self.month_overtime = OvertimeEntry.query.filter(
            OvertimeEntry.entry_date >= month_start, OvertimeEntry.entry_date <= month_end
        ).all()
        self.month_leave = LeaveEntry.query.filter(
            LeaveEntry.entry_date >= month_start, LeaveEntry.entry_date <= month_end
        ).all()
        self.month_overtime_hours = sum(e.hours for e in self.month_overtime)

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
def compute_life_score(ctx, for_day=None, gelir_gizli=False):
    """
    0-100 arası Life Score. Sadece 'bugünü' değil, o günle birlikte önceki 7
    günün ortalamasını da harmanlıyor — tek bir iyi/kötü gün skoru gereğinden
    fazla oynatmasın diye. `for_day` verilmezse ctx.today kullanılır (geriye
    dönük tahmin için farklı bir gün de verilebilir - Bütçe hedef boyutu o
    durumda `for_day`'in KENDİ ayına göre hesaplanır, bkz. `_finans_pace_pct`).

    `gelir_gizli=True` iken Finans boyutu HİÇ EKLENMEZ (0/None ile doldurmak
    değil, tamamen dışarıda bırakmak) — yoksa is%/al% zaten görünürken
    `finans = 3*life_score - is% - al%` ile gelir geri hesaplanabilir, gizleme
    sadece görsel/yüzeysel kalırdı.
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

    # Bütçe boyutu: `for_day`'in kendi ayına göre (bkz. _finans_pace_pct).
    # Uygulama kullanılmaya başlanmadan önceki günler için EKLENMEZ — yoksa
    # hedef tanımlıyken compute_life_score hiçbir gün None dönmez ve trend,
    # olmayan bir geçmiş için sahte "sadece-finans" puan üretir. Ayrıca ayın
    # ilk FINANS_GUVENILMEZ_GUN günü de eklenmez (maaş henüz girilmemiş
    # olabilir — life_score_breakdown'daki "en zayıf boyut" eşiğiyle tutarlı).
    if not gelir_gizli and day >= ctx.activity_start and day.day > FINANS_GUVENILMEZ_GUN:
        fin_pct = _finans_pace_pct(ctx, day)
        if fin_pct is not None:
            parts.append(fin_pct)

    if not parts:
        return None
    return round(sum(parts) / len(parts))


def _finans_pace_pct(ctx, for_day):
    """
    Bütçe boyutu: net birikimin, ayın geçen kısmına göre BEKLENEN tempoya
    oranı (0-100). Düz `net/hedef` değil — çünkü maaş ay ortasında girildiği
    için ayın ilk yarısı net hep negatif/sıfır çıkıyor ve "en büyük fırsat
    hep Finans" oluyordu.

    `for_day` ctx.today ile aynı ay ise ctx'in önbelleğe alınmış ay verisi
    kullanılır (ek sorgu yok). Farklı bir ay ise (life_score_history/delta ay
    geçişlerinde geçmiş bir güne bakabilir) o ayın MonthlyGoal/Transaction
    toplamlarını KENDİ sorgusuyla çeker — yoksa geçmiş bir güne yanlışlıkla
    ctx.today'in ayının verisi yapıştırılırdı. O ay için hedef tanımlı
    değilse None döner (çağıran hiç eklemez — düz 0 değil, çünkü 0 "kötü
    performans" anlamına gelirken None "bu boyut yok" anlamına gelir).
    """
    if for_day.year == ctx.today.year and for_day.month == ctx.today.month:
        goal_amount = ctx.month_goal_amount
        month_net = ctx.month_net
        month_days_total = ctx.month_days_total
    else:
        goal = MonthlyGoal.query.filter_by(year=for_day.year, month=for_day.month).first()
        goal_amount = goal.target_amount if (goal and goal.target_amount > 0) else None
        if not goal_amount:
            return None
        f_start, f_end = month_bounds(for_day.year, for_day.month)
        f_txs = Transaction.query.filter(
            Transaction.entry_date >= f_start, Transaction.entry_date <= f_end
        ).all()
        f_income = sum(t.amount for t in f_txs if t.kind == "gelir")
        f_expense = sum(t.amount for t in f_txs if t.kind == "gider")
        month_net = f_income - f_expense
        month_days_total = calendar.monthrange(for_day.year, for_day.month)[1]

    if not goal_amount:
        return None
    elapsed = max(1, for_day.day) / month_days_total
    pace_target = goal_amount * elapsed
    if pace_target <= 0:
        return 0
    return min(100, max(0, month_net / pace_target * 100))


MIN_LIFESCORE_DAYS = 3  # bundan az günlük veriyle Life Score göstermek yerine "toplanıyor" denir
FINANS_GUVENILMEZ_GUN = 10  # ayın ilk bu kadar günü Finans boyutu "en zayıf" seçilmez


def _blend_today_week(today_val, week_vals):
    """compute_life_score ile aynı harman: (bugün + son 7 gün ort.) / 2."""
    if today_val is None:
        return None
    wk = sum(week_vals) / len(week_vals) if week_vals else today_val
    return (today_val + wk) / 2


def life_score_breakdown(ctx, gelir_gizli=False):
    """
    Life Score'un 3 puanlı boyutu (İş / Alışkanlık / Finans) — her biri 0-100
    veya veri yoksa None. "78 — ama alışkanlıkta gelişim alanı var" tarzı bir
    okuma için: sayı bir not değil, nereye dokunacağını söyleyen harita.
    Mesai bir PUAN değil (azaltılabilir/opsiyonel bir emek); ayrı bir bilgi
    olarak `mesai_saat` döner, çubuk/skor yok.

    `gelir_gizli=True` iken `fin_b` None'a zorlanır — hem "en zayıf boyut"
    seçiminden otomatik dışlanır (aşağıdaki filtre zaten None'ları eler) hem
    de template'te `{{ v ~ '%' if v is not none else '—' }}` sayesinde "—"
    olarak görünür, gerçek finans verisi HTML'e hiç girmez.
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
    fin_b = _finans_pace_pct(ctx, day)
    if gelir_gizli:
        fin_b = None

    def r(v):
        return round(v) if v is not None else None

    # "En zayıf" seçimi: ayın ilk günlerinde Finans yapısal olarak güvenilmez
    # (maaş henüz girilmemiş) → o dönemde Finans'ı yarıştan çıkar.
    weak_candidates = [("is", is_b), ("aliskanlik", al_b)]
    if fin_b is not None and ctx.today.day > FINANS_GUVENILMEZ_GUN:
        weak_candidates.append(("finans", fin_b))
    scored = [(k, v) for k, v in weak_candidates if v is not None]
    weakest = min(scored, key=lambda kv: kv[1])[0] if scored else None

    h = ctx.month_overtime_hours
    return {
        "is": r(is_b), "aliskanlik": r(al_b), "finans": r(fin_b),
        "mesai_saat": (int(h) if h == int(h) else round(h, 1)) if h else 0,
        "weakest": weakest,
    }


def life_score_days(ctx):
    """Son 14 günde 'veri var' sayısı — Life Score'a güven eşiği için."""
    return sum(
        1 for i in range(14)
        if ctx.daily_blended_pct(ctx.today - timedelta(days=i)) is not None
    )


def life_score_history(ctx, days=14, gelir_gizli=False):
    """Son N günün Life Score tahminini döner: [{'date': ..., 'score': ...}, ...] (eskiden yeniye)."""
    history = []
    for i in range(days - 1, -1, -1):
        d = ctx.today - timedelta(days=i)
        score = compute_life_score(ctx, for_day=d, gelir_gizli=gelir_gizli)
        history.append({"date": d, "score": score})
    return history


def life_score_delta(ctx, gelir_gizli=False):
    """Bugünün Life Score'u ile dünkü arasındaki fark (yüzde puan). Biri eksikse None."""
    today_score = compute_life_score(ctx, for_day=ctx.today, gelir_gizli=gelir_gizli)
    yesterday_score = compute_life_score(ctx, for_day=ctx.today - timedelta(days=1), gelir_gizli=gelir_gizli)
    if today_score is None or yesterday_score is None:
        return None
    return today_score - yesterday_score


# ----------------------------------------------------------------------
MIN_MOMENTUM_DAYS = 5  # bundan az günlük veriyle 14 günlük pencere karşılaştırması yanıltıcı olur


def compute_momentum(ctx):
    """Son 14 gün ile önceki 14 günün ortalama performansı arasındaki fark (yüzde puan)."""
    today = ctx.today

    def avg_pct(days):
        vals = [v for v in (ctx.daily_blended_pct(d) for d in days) if v is not None]
        return (sum(vals) / len(vals), len(vals)) if vals else (None, 0)

    last_14 = [today - timedelta(days=i) for i in range(0, 14)]
    prev_14 = [today - timedelta(days=i) for i in range(14, 28)]

    avg_last, n_last = avg_pct(last_14)
    avg_prev, n_prev = avg_pct(prev_14)

    if avg_last is None or avg_prev is None:
        return None
    if n_last < MIN_MOMENTUM_DAYS or n_prev < MIN_MOMENTUM_DAYS:
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
    # active=True: arşivlenmiş görevler ne öncelik listesinde görünsün ne de
    # done_today/total_today sayaçlarına girsin (ctx.total_daily_tasks'la
    # tutarlı — ikisi de aynı "aktif görev" tanımını kullanmalı).
    daily_tasks = DailyTask.query.filter_by(active=True).order_by(DailyTask.sort_order).all()
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
from common import TR_WEEKDAYS as TR_WEEKDAY_NAMES
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

    # Not: Momentum ana ekranda "Son 14 Gün" grafiğinin rozetinde zaten
    # gösteriliyor — burada ayrıca bir içgörü kartına çevirmiyoruz.

    candidates.sort(key=lambda c: c[0])
    return [c[1] for c in candidates[:max_insights]]


# ======================================================================
# Ana ekran (home.html) için tek noktadan bağlam kurulumu.
# Eskiden bu ~120 satır app.py'nin root() view'ının içindeydi.
# ======================================================================
def build_home_context(ctx, now, gelir_gizli):
    """
    home.html'in ihtiyaç duyduğu HER ŞEYİ tek sözlükte döner. `ctx` önceden
    kurulmuş bir DashboardContext, `now` Türkiye saatiyle şu an (datetime).
    `gelir_gizli` ZORUNLU (varsayılan yok) — Life Score'un Finans bileşenini
    gerçekten kapatmak için compute_life_score/life_score_breakdown/
    life_score_history/life_score_delta'nın hepsine geçirilir; unutulursa
    (varsayılan verilseydi) gelir gizliyken bile finans verisi Life Score'a
    sızabilirdi.
    """
    today = ctx.today

    # --- Life Score + boyutlar ---
    life_score = compute_life_score(ctx, gelir_gizli=gelir_gizli)
    ls_days = life_score_days(ctx)
    breakdown = life_score_breakdown(ctx, gelir_gizli=gelir_gizli)

    # --- Bugün şeridi ---
    is_daily_count = ctx.total_daily_tasks
    is_daily_done_today = len(ctx.daily_done_by_date.get(today, set()))
    aliskanlik_total = len(ctx.habits)
    aliskanlik_done = len(ctx.habit_done_by_date.get(today, set()))

    open_deadlines = DeadlineTask.query.filter_by(done=False).all()
    # "acil" = gecikmiş VEYA 3 gün içinde (ikisi de eyleme çağırıyor)
    is_urgent_count = sum(1 for t in open_deadlines if (t.due_date - today).days <= 3)

    todays_expense = sum(
        t.amount for t in Transaction.query.filter_by(entry_date=today, kind="gider").all()
    )

    # Mesai — hepsi ctx'in ay-pencere önbelleğinden (yeniden sorgu yok, tutarlı pencere)
    mesai_today_hours = sum(e.hours for e in ctx.month_overtime if e.entry_date == today)
    mesai_calc = calculate_salary(today.year, today.month, ctx.month_overtime, ctx.month_leave)
    mesai_month_amount = mesai_calc.get("mesai_tutari")

    # --- Trend (SVG) ---
    history = life_score_history(ctx, days=14, gelir_gizli=gelir_gizli)
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
        "life_score_delta": life_score_delta(ctx, gelir_gizli=gelir_gizli),
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
