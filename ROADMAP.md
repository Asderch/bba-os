# BBA OS — Vizyon ve Yol Haritası

**Slogan:** Balance · Build · Advance — Your Life. Your System.

Bu döküman, Berkcan'ın 4 ayrı takip uygulamasını (İş, Bütçe, Mesai,
Alışkanlık) tek bir "Kişisel İşletim Sistemi"ne dönüştürme vizyonunu
kayıt altına alıyor. Kaybolmasın diye buraya yazıldı — her oturumda
yeniden anlatmaya gerek kalmasın.

## Mimari (V1'de tamamlandı)

Artık 4 ayrı Flask uygulaması yok — **tek bir Flask uygulaması**, **tek
bir SQLite veritabanı** (`data/personal_os.db`), her modül kendi
Blueprint'i:

```
personal-os/
  app.py              # ana uygulama, blueprint kayıtları, /yedekle route'u
  extensions.py        # ortak db = SQLAlchemy()
  models.py             # TÜM modellerin tanımlandığı tek dosya
  chart_utils.py         # donut grafik hesaplama (Bütçe + gelecekte diğerleri)
  blueprints/
    is_takip.py          # /is
    butce.py              # /butce
    mesai.py               # /mesai
    aliskanlik.py            # /aliskanlik
  templates/
    base.html               # ortak taban (geçiş çubuğu + navbar iskeleti)
    is_takip/, butce/, mesai/, aliskanlik/   # her modülün kendi şablonları
  static/
    vendor/tabler/            # Tabler.io (self-hosted)
    css/custom.css              # tüm modül temaları tek dosyada (body.theme-X)
    fonts/, icons/, js/
```

Bu sayede artık:
- Modüller arası veri paylaşımı (Mesai→Bütçe gibi) **aynı veritabanı
  oturumu içinde** mümkün — ayrı dosyalar arasında imkansızdı
- Tek `requirements.txt`, tek WSGI ayarı — PythonAnywhere'deki
  `DispatcherMiddleware` karmaşası tamamen kalktı
- **Veri Yedekleme** (V1'in en acil maddesi): her sayfanın sağ üstünde
  "💾 Yedekle" linki, tek tıkla `personal_os.db` dosyasını indiriyor

## Alışkanlık modülü — bu turda eklenen zenginleştirme

- Her alışkanlığın bir **"Neden?"** açıklaması var
- **Etki puanı** (1-5, 🔥 ile gösteriliyor) — ana sayfa artık
  "7/10 tamamlandı" yerine **"bugün X/Y puan topladın"** diyor
- **Sıklık tipi**: "Her gün" ya da "Haftada N kez" (esnek hedef,
  belirli günlere bağlı değil)
- **Hazır 8'li başlangıç seti** (Yönet sayfasında "🚀 Hazır 8
  Alışkanlığı Ekle" butonu): uyku düzeni, su, 7000 adım, sabah
  telefonsuz, 20dk öğrenme, ortam toparlama, gün değerlendirmesi,
  haftada 3x egzersiz

## Sıradaki aşamalar (henüz yapılmadı — sırasıyla)

### V1 — Sağlamlaştırma (tamamlandı)
- [x] Mimari birleştirme (tek app, tek db)
- [x] Veri yedekleme (indirme linki)
- [x] Otomatik/periyodik yedekleme (her gün ilk ziyarette otomatik snapshot,
      son 14 gün tutuluyor, "Yedek Geçmişi" sayfasından indirilebiliyor)

### V2 — Modülleri birbirine bağlama (tamamlandı)
- [x] Mesai → Bütçe otomatik gelir aktarımı (Hesaplama sayfasında "Bütçe'ye
      Aktar" butonu, mükerrer aktarımı engelliyor)
- [x] İş Takip tamamlama oranı → "Bugünkü Performans" göstergesi
- [x] Alışkanlık etki puanı → aynı performans göstergesine katkı
- [x] Bütçe hedefleri ("bu ay X TL biriktirmek istiyorum" + mesai saatiyle
      "kaç saat daha mesai gerekir" hesaplaması, gelir gizleme kuralına uyumlu)

### V3 — Merkezi Dashboard (tamamlandı)
- [x] Life Score (0-100, İş + Alışkanlık + Bütçe hedef durumunun ortalaması)
- [x] XP / Level sistemi (mevcut tamamlama kayıtlarından anlık türetiliyor)
- [x] Momentum (son 14 günün önceki 14 güne göre trend farkı, yüzde puan)
- [x] Streak Sağlığı (%) — son 30 günün "iyi gün" oranı, tek gün kaçırmak sıfırlamıyor
- [x] "Günün 3 önceliği" — acil terminler + tamamlanmamış günlük işler

### V4 — Akıllı analiz (başladı, devam ediyor)
- [x] İlk 2 içgörü kartı (kural tabanlı, yeterli veri yoksa hiç gösterilmiyor):
      "en üretken gün" ve "İş Takip tamamlama ↔ Alışkanlık performansı bağlantısı"
- [x] Her içgörüye somut bir "🎯 Öneri" eklendi (Veri → İçgörü → Eylem zinciri)
- [x] **Kritik düzeltme:** Life Score artık sadece "bugünü" değil, bugün + son 7
      günün ortalamasını harmanlıyor — tek bir iyi gün skoru 100'e fırlatıp
      İstikrar göstergesiyle çelişmiyor
- [x] "Streak Sağlığı" → "İstikrar" olarak yeniden adlandırıldı, daha
      somut bir ifadeyle ("son 30 günün 22'sinde..." gibi)
- [x] Ana sayfadaki 4 modül kartı istatistik göstermek yerine eylem odaklı
      hale getirildi (İş: X/Y tamamlandı + bekleyen iş uyarısı, Bütçe:
      bugünkü harcama, Mesai: bu ayki tahmini mesai geliri, Alışkanlık:
      kaç tanesi kaldı)
- [x] Bütçe + alışkanlık korelasyonu ("harcaman yüksek/düşük günlerde alışkanlık
      performansı nasıl değişiyor") — `insight_finans_aliskanlik_link`
- [ ] "Kötü gidişat" uyarısı + toparlanma önerisi
- [x] Life Score alt-boyutlara ayrıldı (İş/Alışkanlık/Finans/Mesai barları +
      "en büyük fırsat" ipucu) — `life_score_breakdown`, ana ekran hero kartı
- [ ] Haftalık özet raporu (haftanın skoru, momentum, en iyi/gelişecek alan,
      haftanın içgörüsü, gelecek hafta önerisi)

### V3.5 — Sağlamlaştırma turu (5 ajanlı analiz sonrası, 2026-09)
- [x] Güvenlik: HTTP Basic Auth (`BBA_USER`/`BBA_PASS`), secret key + debug env'de,
      `.gitignore` yedekleri kapsıyor
- [x] Doğruluk: "veri yok günü = None" (İstikrar/Momentum/içgörüler erken kullanımda
      artık yanılmıyor); abonelik + Mesai→Bütçe mükerrer koruması (`Transaction.source`);
      Mesai transferi doğru aya yazılıyor
- [x] Bütün form girişleri guard'landı (500 → flash); `@errorhandler(404/500)`
- [x] Türkiye saati tek noktadan (`common.now_tr/today_tr`) — "bugün" artık UTC'de kaymıyor
- [x] Ana ekran yeniden tasarlandı: XP/Level ve "BU AY" kaldırıldı, Life Score hero,
      "günün 3 önceliği" (tamamlanmış dolgu yok), içgörüler öne alındı
- [x] Tek stylesheet konsepti + odak halkaları + 44px dokunma hedefleri +
      emoji nav → Tabler SVG ikon + tek sayı fontu (mono) + harici font kaldırıldı
- [x] `common.py` / `salary.py` / `schema_upgrade.py` — kopya kod ve blueprint↔blueprint
      import'ları temizlendi; DB index'leri; `tests/` (pytest)
- [x] Mesai günlük kesinti formülü doğrulandı (Excel): `net/225*8` bilinçli —
      `salary.py` başında yazılı.
- [x] Gelir gizleme artık **sunucu tarafında**: `session["gelir_gizli"]` bayrağı,
      gizli iken gelir/net/maaş rakamları HTML'e hiç girmiyor (`••••••`), hedef
      ilerlemesi yüzde olarak gösteriliyor. Gelir kayıtları gizli modda
      düzenlenemez (silinebilir). `_inject_privacy` context processor.
- [ ] Para alanları `Float` → `Numeric(10,2)` (ertelendi — tüm para aritmetiğinin
      Decimal/float karışımı için gözden geçirilmesi gerek)
- [ ] Alembic/Flask-Migrate (şimdilik hafif `schema_upgrade.py` yetiyor)

### V4.5 — Kişisel Analiz (planlandı, henüz başlanmadı)
Berkcan'ın detaylı vizyonundan (bkz. konuşma geçmişi):
- [ ] Modüller arası gerçek korelasyon keşfi (örn. "mesai yaptığın haftalarda
      gelirin artıyor ama dışarıda yemek harcaman da artıyor")
- [ ] Kişisel öneri motoru — bazen "ekle" değil "azalt" önermeli
      (örn. alışkanlık tamamlama düşüyorsa yeni alışkanlık eklemek yerine
      mevcutlara odaklanmayı önersin)
- [ ] Haftalık rapor ekranı (bkz. yukarıdaki V4 son maddesi)

### V5 — Gerçek "BBA OS" hissi (planlandı, henüz başlanmadı)
Berkcan'ın "Life Engine" vizyonu:
- [ ] 🔮 Tahmin sistemi: mevcut harcama/birikim hızına göre ay sonu projeksiyonu
      ("bu hızla devam edersen bütçeni 2.300₺ aşabilirsin" gibi)
- [ ] 🔮 Hedef tahmini: "bu birikim hızıyla hedefe Kasım'da ulaşırsın, harcamaları
      %10 azaltırsan Ekim'de"
- [ ] 🧠 "What if?" simülatörü: "10 saat daha mesai yaparsam ne olur?" gibi
      sorulara anlık hesaplanan senaryo cevabı
- [ ] 🏆 Hedef parçalama: bir birikim hedefini alt-stratejilere bölme
      (aylık +X₺, harcama -Y₺, +Z saat mesai gibi)
- [ ] Achievement/rozet sistemi
- [ ] 🤖 Doğal dil katmanı (AI): "Bu ay neden daha kötüyüm?" gibi serbest
      sorulara veriye dayalı açıklama üretebilme — **Berkcan'ın kendi notu:**
      "Önce sistem kendi matematiğini ve veri modelini oturtsun", yani bu en son

## Önemli tasarım ilkeleri (unutulmasın)

- **XP ≠ Yaşam Skoru.** XP ilerlemeyi, Skor şu anki durumu gösterir.
- **Skor = bugün neredesin, Momentum = hangi yöne gidiyorsun.** İkisi
  birlikte çok daha anlamlı.
- **Streak cezalandırıcı olmamalı.** Bir gün kaçırmak tüm geçmişi
  silmemeli, "sağlık yüzdesi" mantığı kullanılmalı.
- **Düşük skor "başarısızsın" demek değil**, "en büyük fırsat burada"
  demeli.
- **Uygulama veri toplamamalı, karar vermeni kolaylaştırmalı.** 15
  yapılacak iş varsa, hepsini göstermek yerine sadece bugün en
  öncelikli 3 tanesini öne çıkarmalı.
