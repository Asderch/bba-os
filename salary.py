"""
Maaş / fazla mesai hesabı — tek kaynak.

Önceden `_calculate_salary` mesai blueprint'inin içindeydi ve hem app.py
(private import), hem butce.py (saatlik ücret formülünü satır içinde
yeniden yazarak) ona bağımlıydı. Artık ikisi de buradan alıyor.

Formül (Berkcan'ın Excel'iyle doğrulandı — 2026-09):
  saatlik ücret        = net_maaş / 225 * çarpan       (225 = aylık baz saat)
  fazla mesai tutarı   = saat_1.5x * 1.5-ücret + saat_1x * 1.0-ücret
  günlük eksik-gün kesintisi = net_maaş / 225 * 8      (kesinti günlük 8 saat
                              üzerinden, 225 tabanıyla — bilinçli tercih)
"""
from models import MonthlySalary

AY_ICI_BAZ_SAAT = 225       # aylık baz çalışma saati (saatlik ücret paydası)
CARPAN_MESAI = 1.5          # hafta içi + hafta sonu fazla mesai çarpanı
CARPAN_RESMI_TATIL = 1.0    # resmi tatil mesaisi çarpanı
GUNLUK_KESINTI_SAAT = 8     # ücretsiz/raporlu her gün için kesilen saat (225 tabanıyla)


def hourly_overtime_rate(net_salary, multiplier=CARPAN_MESAI):
    """Net maaştan saatlik (fazla mesai) ücret. net_salary None ise None."""
    if not net_salary or net_salary <= 0:
        return None
    return net_salary / AY_ICI_BAZ_SAAT * multiplier


def calculate_salary(year, month, overtime_entries, leave_entries):
    salary_row = MonthlySalary.query.filter_by(year=year, month=month).first()
    net_salary = salary_row.net_salary if salary_row else None

    saat_1_5x = sum(e.hours for e in overtime_entries if e.category in ("hafta_ici", "hafta_sonu"))
    saat_1x = sum(e.hours for e in overtime_entries if e.category == "resmi_tatil")

    eksik_gun = sum(l.days for l in leave_entries if l.leave_type in ("ucretsiz", "raporlu"))
    yillik_izin_gun = sum(l.days for l in leave_entries if l.leave_type == "yillik_izin")

    result = {
        "net_salary": net_salary, "saat_1_5x": saat_1_5x, "saat_1x": saat_1x,
        "eksik_gun": eksik_gun, "yillik_izin_gun": yillik_izin_gun,
    }

    if net_salary is None:
        result.update({
            "saatlik_ucret_1_5": None, "saatlik_ucret_1": None,
            "mesai_tutari": None, "kesinti": None, "toplam_alinacak_ucret": None,
        })
        return result

    saatlik_ucret_1_5 = net_salary / AY_ICI_BAZ_SAAT * CARPAN_MESAI
    saatlik_ucret_1 = net_salary / AY_ICI_BAZ_SAAT * CARPAN_RESMI_TATIL
    mesai_tutari = saatlik_ucret_1_5 * saat_1_5x + saatlik_ucret_1 * saat_1x

    gunluk_kesinti_orani = net_salary / AY_ICI_BAZ_SAAT * GUNLUK_KESINTI_SAAT
    kesinti = -eksik_gun * gunluk_kesinti_orani

    toplam_alinacak_ucret = net_salary + mesai_tutari + kesinti

    result.update({
        "saatlik_ucret_1_5": saatlik_ucret_1_5, "saatlik_ucret_1": saatlik_ucret_1,
        "mesai_tutari": mesai_tutari, "kesinti": kesinti,
        "toplam_alinacak_ucret": toplam_alinacak_ucret,
    })
    return result
