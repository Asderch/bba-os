"""Hesap/kredi kartı bakiye ve basit faiz tahmini hesaplamaları.

`salary.py`/`chart_utils.py` ile aynı desen: hesaplama mantığı blueprint'ten
ayrı, bağımsız test edilebilir bir modülde.
"""
import calendar


def account_balance(account):
    """Güncel bakiye: opening_balance + tüm hareketlerin toplamı."""
    return account.opening_balance + sum(m.amount for m in account.movements)


def estimated_interest(balance, interest_rate_monthly, today):
    """Borç (negatif bakiye) üzerinden KABA bir faiz tahmini.

    Aylık oranı 30 güne bölüp güne yayan basit bir orantı kullanır — hesap
    kesim tarihi, akdi/gecikme faizi ayrımı gibi gerçek banka/kredi kartı
    kurallarını MODELLEMEZ. Sadece "yaklaşık ne kadar faiz birikiyor"
    sorusuna kaba bir fikir vermek için; banka ekstresiyle birebir örtüşmez.

    Döner: {"bu_aya_kadar": ..., "ay_sonuna_kadar": ...} (₺) ya da borç/oran
    yoksa (bakiye pozitifse ya da faiz oranı girilmemişse) None.
    """
    if balance >= 0 or not interest_rate_monthly:
        return None
    days_in_month = calendar.monthrange(today.year, today.month)[1]
    daily_rate = interest_rate_monthly / 100 / 30
    debt = abs(balance)
    return {
        "bu_aya_kadar": debt * daily_rate * today.day,
        "ay_sonuna_kadar": debt * daily_rate * days_in_month,
    }
