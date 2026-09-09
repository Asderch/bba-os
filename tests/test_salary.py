"""Maaş / mesai hesabı — _calculate_salary."""
from datetime import date

import pytest


class _OT:
    def __init__(self, hours, category):
        self.hours = hours
        self.category = category


class _LV:
    def __init__(self, days, leave_type):
        self.days = days
        self.leave_type = leave_type


def test_no_salary_returns_none_fields(flask_app):
    import app as appmod
    from salary import calculate_salary

    with appmod.app.app_context():
        r = calculate_salary(2026, 1, [_OT(10, "hafta_ici")], [])
        assert r["net_salary"] is None
        assert r["mesai_tutari"] is None
        assert r["toplam_alinacak_ucret"] is None


def test_overtime_and_deduction_math(flask_app):
    import app as appmod
    from extensions import db
    from models import MonthlySalary
    import salary

    with appmod.app.app_context():
        db.session.add(MonthlySalary(year=2026, month=1, net_salary=45000))
        db.session.commit()

        ot = [_OT(10, "hafta_ici"), _OT(4, "hafta_sonu"), _OT(8, "resmi_tatil")]
        lv = [_LV(2, "ucretsiz")]
        r = salary.calculate_salary(2026, 1, ot, lv)

        hourly_15 = 45000 / salary.AY_ICI_BAZ_SAAT * salary.CARPAN_MESAI
        hourly_1 = 45000 / salary.AY_ICI_BAZ_SAAT * salary.CARPAN_RESMI_TATIL
        assert r["saat_1_5x"] == 14
        assert r["saat_1x"] == 8
        assert r["mesai_tutari"] == pytest.approx(hourly_15 * 14 + hourly_1 * 8)
        assert r["kesinti"] == pytest.approx(-2 * (45000 / salary.AY_ICI_BAZ_SAAT * salary.GUNLUK_KESINTI_SAAT))
        assert r["toplam_alinacak_ucret"] == pytest.approx(
            r["net_salary"] + r["mesai_tutari"] + r["kesinti"]
        )
        assert salary.hourly_overtime_rate(45000) == pytest.approx(hourly_15)
        assert salary.hourly_overtime_rate(None) is None
