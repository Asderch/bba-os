from extensions import db
from common import local_now as _local_now
from common import TR_WEEKDAYS as WEEKDAYS


# Etiket/kategori renk paleti — Tag ve SubscriptionCategory arasında paylaşılan
# TEK kaynak (Tailwind'in 500 tonları, karanlık zeminde badge metni olarak
# okunaklı olacak şekilde seçildi). Berkcan'ın isteğiyle 7'den ~19'a çıkarıldı.
PALETTE_COLORS = [
    "#ef4444", "#f97316", "#f59e0b", "#eab308", "#84cc16", "#22c55e", "#10b981",
    "#14b8a6", "#06b6d4", "#0ea5e9", "#3b82f6", "#6366f1", "#8b5cf6", "#a855f7",
    "#d946ef", "#ec4899", "#f43f5e", "#64748b", "#78716c",
]


# ============================================================
# İŞ TAKİP
# ============================================================
TAG_COLORS = PALETTE_COLORS


class Tag(db.Model):
    __tablename__ = "tags"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    color = db.Column(db.String(20), default="#a855f7")


class DailyTask(db.Model):
    """Her gün aynı şekilde gösterilen, sabit/tekrarlayan işler (bitiş tarihi yok)."""
    __tablename__ = "daily_tasks"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    note = db.Column(db.Text)
    sort_order = db.Column(db.Integer, default=0)
    tag_id = db.Column(db.Integer, db.ForeignKey("tags.id"))
    active = db.Column(db.Boolean, default=True)   # False = arşivlenmiş, geçmiş verisi korunur
    created_at = db.Column(db.DateTime, default=_local_now)

    completions = db.relationship("DailyTaskCompletion", backref="task", lazy=True, cascade="all, delete-orphan")
    tag = db.relationship("Tag")


class DailyTaskCompletion(db.Model):
    """Bir günlük işin belirli bir günde tamamlandığını kaydeder (her gün sıfırlanır)."""
    __tablename__ = "daily_task_completions"

    id = db.Column(db.Integer, primary_key=True)
    daily_task_id = db.Column(db.Integer, db.ForeignKey("daily_tasks.id"), nullable=False, index=True)
    completion_date = db.Column(db.Date, nullable=False, index=True)
    completed_at = db.Column(db.DateTime, default=_local_now)

    __table_args__ = (
        db.UniqueConstraint("daily_task_id", "completion_date", name="uq_task_date"),
    )


class NonWorkDay(db.Model):
    """'Bugün çalışmıyorum' olarak işaretlenmiş bir gün — Berkcan'ın hafta
    sonu çalışması düzensiz (bazı Cumartesi/Pazar çalışıyor, bazı çalışmıyor),
    ve "Günlük İşlerim" listesi tamamen işyerine özgü görevlerden oluşuyor.
    Bu günlerde günlük iş görevleri Life Score'un İş boyutundan TAMAMEN hariç
    tutulur (0/total olarak cezalandırılmaz — activity_start öncesi günlerle
    aynı "hiç veri yok" mantığı, bkz. dashboard_logic.DashboardContext).
    Geriye dönük değil, ileriye dönük de işaretlenebilir (ör. bu hafta sonu
    için önceden)."""
    __tablename__ = "non_work_days"

    id = db.Column(db.Integer, primary_key=True)
    work_date = db.Column(db.Date, nullable=False, unique=True, index=True)
    note = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=_local_now)


class DeadlineTask(db.Model):
    """Termin (bitiş) tarihi olan, tek seferlik işler."""
    __tablename__ = "deadline_tasks"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    due_date = db.Column(db.Date, nullable=False, index=True)
    note = db.Column(db.Text)
    tag_id = db.Column(db.Integer, db.ForeignKey("tags.id"))
    done = db.Column(db.Boolean, default=False, index=True)
    done_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=_local_now)

    tag = db.relationship("Tag")


class Note(db.Model):
    """Serbest, hızlı notlar."""
    __tablename__ = "notes"

    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=_local_now)


# ============================================================
# BÜTÇE TAKİP
# ============================================================
EXPENSE_CATEGORIES = ["Sigara", "Yemek", "Market", "Alkol", "Fatura", "Eğlence", "Sağlık", "Giyim", "Abonelik", "Diğer Gider"]
INCOME_CATEGORIES = ["Maaş", "Mesai Geliri", "Kira Yardımı", "Ek gelir", "Diğer Gelir"]

CATEGORY_COLORS = {
    "Yemek": "#e0725e", "Sigara": "#be0303", "Market": "#e0a15e", "Alkol": "#e7da5f",
    "Fatura": "#8ec26a", "Eğlence": "#5eb9c2", "Sağlık": "#5e8ee0",
    "Giyim": "#8e5ee0", "Abonelik": "#06b6d4", "Diğer Gider": "#8a8f98",
}

SUBSCRIPTION_CATEGORY_COLORS = PALETTE_COLORS


class Transaction(db.Model):
    __tablename__ = "transactions"

    id = db.Column(db.Integer, primary_key=True)
    entry_date = db.Column(db.Date, nullable=False, index=True)
    kind = db.Column(db.String(10), nullable=False)  # "gelir" | "gider"
    category = db.Column(db.String(50), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    note = db.Column(db.String(255))
    # Otomatik oluşturulan kayıtların kaynağı (ör. "mesai:2026-09",
    # "abonelik:12:2026-09-01") — serbest-metin not eşleştirmesine güvenmeden
    # mükerrer aktarım/yenileme kontrolü için. Elle girilen kayıtlarda None.
    source = db.Column(db.String(64), index=True)
    created_at = db.Column(db.DateTime, default=_local_now)


class SubscriptionCategory(db.Model):
    __tablename__ = "subscription_categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    color = db.Column(db.String(20), default="#06b6d4")


class Subscription(db.Model):
    __tablename__ = "subscriptions"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    cycle = db.Column(db.String(10), nullable=False)  # "aylik" | "yillik"
    next_renewal = db.Column(db.Date, nullable=False, index=True)
    category_id = db.Column(db.Integer, db.ForeignKey("subscription_categories.id"))
    reminder_days = db.Column(db.Integer, default=3)
    note = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=_local_now)

    category = db.relationship("SubscriptionCategory")


class MonthlyGoal(db.Model):
    """Aylık birikim hedefi (V2: Mesai saat hesaplayıcıyla bağlantılı)."""
    __tablename__ = "monthly_goals"

    id = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.Integer, nullable=False)
    month = db.Column(db.Integer, nullable=False)
    target_amount = db.Column(db.Float, nullable=False)

    __table_args__ = (
        db.UniqueConstraint("year", "month", name="uq_goal_year_month"),
    )


# ============================================================
# MESAİ TAKİP
# ============================================================
OVERTIME_CATEGORIES = [
    ("hafta_ici", "Hafta İçi Mesaisi"),
    ("hafta_sonu", "Hafta Sonu Mesaisi"),
    ("resmi_tatil", "Resmi Tatil Mesaisi"),
]
OVERTIME_CATEGORY_LABELS = dict(OVERTIME_CATEGORIES)

LEAVE_TYPES = [
    ("ucretsiz", "Ücretsiz İzin"),
    ("raporlu", "Raporlu"),
    ("yillik_izin", "Yıllık İzin"),
]
LEAVE_TYPE_LABELS = dict(LEAVE_TYPES)


class OvertimeEntry(db.Model):
    __tablename__ = "overtime_entries"

    id = db.Column(db.Integer, primary_key=True)
    entry_date = db.Column(db.Date, nullable=False, index=True)
    hours = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(20), nullable=False)
    note = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=_local_now)


class LeaveEntry(db.Model):
    __tablename__ = "leave_entries"

    id = db.Column(db.Integer, primary_key=True)
    entry_date = db.Column(db.Date, nullable=False, index=True)
    days = db.Column(db.Float, nullable=False)
    leave_type = db.Column(db.String(20), nullable=False)
    note = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=_local_now)


class MonthlySalary(db.Model):
    __tablename__ = "monthly_salary"

    id = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.Integer, nullable=False)
    month = db.Column(db.Integer, nullable=False)
    net_salary = db.Column(db.Float, nullable=False)

    __table_args__ = (
        db.UniqueConstraint("year", "month", name="uq_year_month"),
    )


# ============================================================
# ALIŞKANLIK TAKİP
# ============================================================
# WEEKDAYS artık common.TR_WEEKDAYS'in re-export'u (dosya başındaki import
# bloğuna bakın) — aliskanlik.py hiç değişmeden aynı ismi kullanmaya devam eder.

# (isim, neden, etki[1-5], sıklık['gunluk'|'haftalik'], haftalık_hedef)
DEFAULT_HABITS = [
    ("Aynı saatte yat/kalk", "Düzenli uyku ritmi için.", 5, "gunluk", None),
    ("Yeterli su iç", "Enerjini ve odağını yüksek tutmak için.", 4, "gunluk", None),
    ("7.000+ adım", "Günlük hareketi garantiye almak için.", 4, "gunluk", None),
    ("İlk 30 dk telefonsuz", "Günün kontrolünü algoritmalara vermemek için.", 4, "gunluk", None),
    ("20 dk öğrenme", "Bir yılda 120+ saat kendine yatırım yapmak için.", 3, "gunluk", None),
    ("10 dk ortamı toparla", "Zihnini dağıtan görsel kaosu azaltmak için.", 2, "gunluk", None),
    ("5 dk gün değerlendirmesi", "Günden ders çıkarıp yarına daha hazır başlamak için.", 2, "gunluk", None),
    ("Egzersiz", "Daha güçlü ve fit bir vücut için.", 5, "haftalik", 3),
]


class Habit(db.Model):
    """Süre hedefi olmayan, işaretleme + etki puanıyla takip edilen alışkanlık."""
    __tablename__ = "habits"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, unique=True)
    why = db.Column(db.String(255))               # "Neden?" açıklaması
    impact = db.Column(db.Integer, default=3)      # 1-5 arası etki puanı
    frequency_type = db.Column(db.String(10), default="gunluk")  # "gunluk" | "haftalik"
    weekly_target = db.Column(db.Integer)          # sadece frequency_type == "haftalik" için
    active = db.Column(db.Boolean, default=True)   # False = arşivlenmiş, geçmiş verisi korunur
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=_local_now)

    completions = db.relationship("HabitCompletion", backref="habit", lazy=True, cascade="all, delete-orphan")


class HabitCompletion(db.Model):
    __tablename__ = "habit_completions"

    id = db.Column(db.Integer, primary_key=True)
    habit_id = db.Column(db.Integer, db.ForeignKey("habits.id"), nullable=False, index=True)
    completion_date = db.Column(db.Date, nullable=False, index=True)
    completed_at = db.Column(db.DateTime, default=_local_now)

    __table_args__ = (
        db.UniqueConstraint("habit_id", "completion_date", name="uq_habit_date"),
    )


class AppSetting(db.Model):
    """Cihazdan bağımsız, kalıcı tek-kullanıcı ayarları (anahtar/değer).

    Flask `session` tarayıcıya özel bir çerezde tutulur: aynı kullanıcı
    telefondan ve bilgisayardan girince iki ayrı session görür. gelir_gizli
    gibi "tüm cihazlarda aynı olması gereken" bir ayar session'da tutulursa,
    bir cihazda açıp diğerinde kapalı kalabilir — Life Score gibi bu ayara
    göre değişen değerler cihaza göre farklı görünür. Bu yüzden böyle
    ayarlar burada, veritabanında saklanır (bkz. settings.py)."""
    __tablename__ = "app_settings"

    key = db.Column(db.String(64), primary_key=True)
    value = db.Column(db.String(255))
