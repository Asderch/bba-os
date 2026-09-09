"""
Modüller arası paylaşılan sabitler ve tarih yardımcıları.

Önceden bu liste ve fonksiyonlar 4 blueprint + app.py + dashboard_logic
içinde ayrı ayrı kopyalanmıştı. Tek kaynak burası.

Bu modül SADECE standart kütüphaneye bağlıdır (models/extensions import
ETMEZ) — döngüsel import riski yok.
"""
from datetime import datetime, timezone, timedelta
import calendar

# Türkiye 2016'dan beri kalıcı olarak UTC+3 (yaz saati uygulaması yok), bu
# yüzden sabit ofset yeterli — zoneinfo/tzdata bağımlılığına gerek yok.
TR_TZ = timezone(timedelta(hours=3))

TR_MONTHS = [
    "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
    "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık",
]
TR_WEEKDAYS = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]


def now_tr():
    """Türkiye saatiyle şu an (timezone-aware)."""
    return datetime.now(TR_TZ)


def today_tr():
    """Türkiye saatiyle bugünün tarihi. Sunucu UTC olsa bile doğru 'bugün'."""
    return now_tr().date()


def local_now():
    """Türkiye saatiyle şu an, ama naive (DB'deki naive datetime'larla
    kıyaslanabilsin diye)."""
    return now_tr().replace(tzinfo=None)


def month_bounds(year, month):
    """(ayın ilk günü, ayın son günü) — ikisi de date."""
    first_day = datetime(year, month, 1).date()
    last_day_num = calendar.monthrange(year, month)[1]
    return first_day, datetime(year, month, last_day_num).date()


def prev_next_month(year, month):
    """((önceki_yıl, önceki_ay), (sonraki_yıl, sonraki_ay))."""
    if month == 1:
        prev_y, prev_m = year - 1, 12
    else:
        prev_y, prev_m = year, month - 1
    if month == 12:
        next_y, next_m = year + 1, 1
    else:
        next_y, next_m = year, month + 1
    return (prev_y, prev_m), (next_y, next_m)


def clamp_year_month(year, month, fallback=None):
    """
    Kullanıcıdan gelen year/month'u güvenli aralığa çeker. `year`/`month`
    None ise fallback (verilmezse bugün) kullanılır. Her zaman geçerli bir
    (year, month) çifti döner — date()/TR_MONTHS[...] üzerinde asla patlamaz.
    """
    ref = fallback or today_tr()
    year = year or ref.year
    month = month or ref.month
    month = min(12, max(1, month))
    year = min(2100, max(2000, year))
    return year, month
