from extensions import db
from common import local_now as _local_now

# Uygulama sadece Mesai Takip'e indirildi (2026-10-31). Diğer modüller
# (İş, Bütçe, Alışkanlık, Sayaçlar, Analizler, Notlar) kaldırıldı — git
# geçmişinde duruyor.

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
