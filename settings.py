"""Cihazdan bağımsız, kalıcı uygulama ayarları.

Flask `session` (çerez) tarayıcıya/cihaza özeldir — aynı kişi telefondan ve
bilgisayardan girdiğinde iki ayrı session görür. gelir_gizli gibi "tüm
cihazlarda tutarlı olması gereken" bir ayar session'da tutulursa, bir cihazda
gösterilip diğerinde gizli kalabilir; Life Score gibi bu ayara göre değişen
değerler de cihaza göre farklı çıkar (finans boyutu dahil/hariç). Bu modül
bu tür ayarları `AppSetting` tablosunda saklar, tüm cihazlarda aynı değeri
görsün diye.
"""
from extensions import db
from models import AppSetting

GELIR_GIZLI_KEY = "gelir_gizli"
GELIR_GIZLI_DEFAULT = True  # varsayılan: gizli (yeni kurulumda güvenli taraf)


def get_gelir_gizli():
    row = db.session.get(AppSetting, GELIR_GIZLI_KEY)
    if row is None:
        return GELIR_GIZLI_DEFAULT
    return row.value == "1"


def set_gelir_gizli(value):
    row = db.session.get(AppSetting, GELIR_GIZLI_KEY)
    if row is None:
        row = AppSetting(key=GELIR_GIZLI_KEY, value="1" if value else "0")
        db.session.add(row)
    else:
        row.value = "1" if value else "0"
    db.session.commit()
    return value
