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
  - *Değerlendirme (2026-09-11):* 1 Ekim'i beklemeden **şimdi** yapılabilir.
    Kod incelemesi: bu madde `compute_momentum(ctx)`'un zaten ürettiği değeri
    (son 14 gün — önceki 14 gün farkı, yüzde puan) okuyup belirli bir negatif
    eşiğin altına düştüğünde EKRANA yeni bir banner/kart ekliyor;
    `compute_momentum`, `compute_life_score`, `compute_istikrar`,
    `life_score_breakdown` gibi puanlama fonksiyonlarının hiçbirine
    dokunmuyor, `IYI_GUN_ESIGI`/`MIN_MOMENTUM_DAYS`/`FINANS_GUVENILMEZ_GUN`/
    `MIN_LIFESCORE_DAYS`/`MIN_ISTIKRAR_DAYS` eşiklerinden hiçbiri değişmiyor —
    yani VERİYİ değil sadece SUNUMU değiştiren yeni bir katman, "algoritma/
    eşik kırma" yasağı kapsamına girmiyor.
  - *Uygulama yaklaşımı:* `dashboard_logic.py`'ye saf bir `recovery_alert(ctx,
    breakdown)` fonksiyonu eklenir — `compute_momentum(ctx)` `None` değilse ve
    seçilecek bir negatif eşiğin altındaysa (örn. `-10`) tetiklenir
    (`compute_momentum` zaten `MIN_MOMENTUM_DAYS` kontrolünü kendi içinde
    yapıp yetersiz veri varken `None` döndürüyor, ek koruma gerekmiyor).
    Toparlanma önerisi için `life_score_breakdown(ctx)`'ün döndürdüğü
    `"weakest"` alanı kullanılır. `build_home_context()`'e yeni bir anahtar
    (`"recovery_alert"`) eklenir, `home.html`'e küçük bir banner eklenir —
    ama `get_insights()`'ın `max_insights=3` sınırının İÇİNDE bir aday olarak
    DEĞİL, ayrı/bağımsız bir slot olarak (yoksa mevcut 3 içgörüden birini
    dışarı iter). Boyut: küçük (~20-30 satır yeni fonksiyon + küçük bir
    template bloğu); veritabanı şeması/mevcut eşikler değişmiyor.
  - *Ton uyarısı (kritik):* "Kötü gidişat" sadece ROADMAP içi bir isim;
    KULLANICIYA gösterilecek metinde bu ifade ve "başarısız", "düşüş",
    "kötüye gidiyorsun" gibi suçlayıcı/alarmcı kelimeler KULLANILMAMALI —
    ROADMAP'in "düşük skor 'başarısızsın' demek değil, 'en büyük fırsat
    burada' demeli" ilkesiyle çelişmemeli. Arayüzdeki başlık örn.
    **"Toparlanma Fırsatı"** ya da **"Odak Noktası"** olmalı; örnek metin:
    *"Son 14 gün, önceki 14 güne göre {momentum} puan geride — bu bir
    başarısızlık değil, dikkatini nereye vereceğini gösteren bir sinyal. En
    büyük fırsat: {weakest_tr}. Bugün sadece orada küçük bir adım at."*
    Görsel dil de alarm kırmızısı/ünlem yerine diğer içgörü kartlarıyla
    tutarlı, "fırsat" hissi veren bir renk/ikon (🧭/🎯) kullanmalı.
- [x] Life Score alt-boyutlara ayrıldı (İş/Alışkanlık/Finans/Mesai barları +
      "en büyük fırsat" ipucu) — `life_score_breakdown`, ana ekran hero kartı
- [ ] Haftalık özet raporu (haftanın skoru, momentum, en iyi/gelişecek alan,
      haftanın içgörüsü, gelecek hafta önerisi)
  - *Değerlendirme (2026-09-11):* Kod olarak 1 Ekim'i beklemeden yazılmaya
    BAŞLANABİLİR — bu madde de puanlama fonksiyonlarını/eşiklerini
    DEĞİŞTİRMİYOR, sadece var olan `compute_life_score`,
    `life_score_breakdown`, `insight_week_over_week`, `get_insights`
    çıktılarını haftalık pencerede toplayıp sunuyor. Ama ilk maddeden daha
    büyük bir iş: yeni bir agregasyon fonksiyonu, muhtemelen yeni bir
    ekran/route ve yeni bir kural-tabanlı metin üretici gerektiriyor.
    Berkcan'ın elinde şu an (2026-09-11) ~11 günlük gerçek kullanım verisi
    var; "bu hafta vs geçen hafta" karşılaştırması her iki haftada da en az
    birkaç geçerli gün istiyor, bu yüzden rapor ancak ~2 haftalık veri
    birikince (Eylül sonuna doğru) anlamlı dolacak — ama "yeterli veri yoksa
    gösterme" mantığı zaten mevcut fonksiyonlarda var, yani erken/yanıltıcı
    gösterim riski yok, koda şimdiden başlanabilir.
  - *Uygulama yaklaşımı:* Yeni bir `weekly_summary(ctx, gelir_gizli=False)`
    fonksiyonu `dashboard_logic.py`'ye eklenir:
    - *Haftanın skoru:* Son 7 günün `compute_life_score(ctx, for_day=d)`
      değerlerinin ortalaması (None olanlar hariç) — `life_score_history(ctx,
      days=7)` bu değerleri zaten üretiyor.
    - *Momentum:* `insight_week_over_week(ctx)` zaten "bu hafta vs geçen
      hafta" farkını hesaplıyor, doğrudan yeniden kullanılabilir.
    - *En iyi/gelişecek alan:* `life_score_breakdown(ctx)` şu an sadece
      `"weakest"` döndürüyor; aynı `weak_candidates` listesinden `min`
      yerine `max` alınarak bir `"strongest"` alanı da eklenmeli — mevcut
      `"weakest"` mantığına (ayın ilk `FINANS_GUVENILMEZ_GUN` günü Finans'ı
      hariç tutma kuralı dahil) dokunmayan, katkısal (additive) bir ek.
    - *Haftanın içgörüsü:* `get_insights(ctx)` listesinin ilk (en öncelikli)
      öğesi yeniden kullanılabilir.
    - *Gelecek hafta önerisi:* Burası gerçekten yeni bir kural-tabanlı metin
      üretici gerektiriyor — `weakest` boyut + momentum yönüne göre şablon
      bir cümle (örn. "Bu hafta {weakest_tr} alanı geride kaldı, gelecek
      hafta sadece orada küçük bir hedef koy"). Yeni bir "skor"/"eşik"
      üretmiyor, var olan hesaplanmış verilerin üzerine bir dil katmanı.
    - *Sunum:* 5 madde ana sayfa kartına sığmayacak kadar zengin olduğundan
      muhtemelen ayrı bir sayfa/route (örn. `/haftalik-rapor` +
      `templates/haftalik_rapor.html`) gerekir; ana sayfaya küçük bir
      "Haftalık Özeti Gör" linki eklenebilir.
  - *Boyut:* Orta — yeni fonksiyon(lar) + `life_score_breakdown`'a
    `"strongest"` eklenmesi + muhtemelen yeni route/template. Veritabanı
    şeması ve mevcut algoritma değişmiyor. Kaba tahmin: yarım gün - 1 gün.
    (Bu iş kalemi V4.5'te de ayrı bir madde olarak tekrar ediyordu — tek
    bir yerde toplandı, takip noktası burası; bkz. V4.5 bölümü.)

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
- [x] Gelir gizleme artık **sunucu tarafında**: gizli iken gelir/net/maaş
      rakamları HTML'e hiç girmiyor (`••••••`), hedef ilerlemesi yüzde olarak
      gösteriliyor. Gelir kayıtları gizli modda düzenlenemez (silinebilir).
      `_inject_privacy` context processor. Bayrak `settings.py` üzerinden
      veritabanında (`AppSetting`) tutulur — eskiden `session["gelir_gizli"]`
      idi, yani cihaza özeldi; telefon ve bilgisayar farklı Life Score
      gösterebiliyordu (finans boyutu dahil/hariç). Artık tüm cihazlarda aynı.
- [ ] Para alanları `Float` → `Numeric(10,2)` (ertelendi — tüm para aritmetiğinin
      Decimal/float karışımı için gözden geçirilmesi gerek)
  - *Değerlendirme:* **1 Ekim'den sonra yapılmalı.** `models.py`'de gerçek para
    alanı olan 4 kolon `db.Column(db.Float)` ile tanımlı: `Transaction.amount`
    (models.py:97), `Subscription.amount` (models.py:119), `MonthlyGoal.target_amount`
    (models.py:137), `MonthlySalary.net_salary` (models.py:190). (Ayrıca
    `OvertimeEntry.hours` ve `LeaveEntry.days` da Float ama bunlar para değil,
    saat/gün miktarı — bu maddenin kapsamı dışında.) `Float` → `Numeric(10,2)`
    bir **kolon TİPİ değişikliği**; `schema_upgrade.py` bunu açıkça
    desteklemediğini kendi docstring'inde belirtiyor (satır 11-12: "Kolon
    TİPİ değiştiremez (Float -> Numeric gibi). Onun için Alembic gerekir.") ve
    `_ADDED_COLUMNS` listesi/`run()` fonksiyonu yalnızca `ALTER TABLE ... ADD
    COLUMN` ve eksik index `CREATE INDEX` çalıştırıyor — `ALTER COLUMN TYPE`
    yolu yok. Yani bu değişiklik gerçek bir migration aracı (Alembic) veya
    elle yazılmış `ALTER TABLE ... MODIFY/ALTER COLUMN` script'i gerektiriyor;
    canlıda (PythonAnywhere/MySQL) aktif veri birikirken bunu yapmak hem
    riskli (yanlış giden bir ALTER, tabloyu kilitleyebilir/veri kaybına yol
    açabilir) hem de gereksiz — Float→Decimal geçişi Life Score hesaplamasını
    bozmaz ama şema değişikliği + olası veri temizliği (mevcut float
    yuvarlama hatalarının düzeltilmesi) her ihtimalde "son bir tur" mantığına
    daha uygun. **Öneri:** 1 Ekim'de, önce Alembic kurulumu yapıldıktan sonra
    (bkz. alt madde), 4 kolon için `Numeric(10,2)` migration'ı yazılıp
    staging/yedek üzerinde test edilsin, sonra canlıya uygulansın. Bu arada
    şimdiden yapılabilecek risksiz bir hazırlık: tüm para hesaplamalarının
    (`salary.py`, bütçe/hedef hesaplayıcılar) round/format noktalarını not
    almak, ama kod/şema değişikliği yapmamak.

- [ ] Alembic/Flask-Migrate (şimdilik hafif `schema_upgrade.py` yetiyor)
  - *Değerlendirme:* **1 Ekim'den sonra yapılmalı.** `schema_upgrade.py`
    şu an kasıtlı olarak minimal: idempotent, her açılışta çalışan, sadece
    (a) `_ADDED_COLUMNS` listesindeki eksik kolonları `ALTER TABLE ADD COLUMN`
    ile ekleyen ve (b) modeldeki `index=True`/`Index(...)` tanımlarına göre
    eksik index'leri `CREATE INDEX` ile tamamlayan ~65 satırlık bir modül.
    Kolon tipi değişikliği, kolon/tablo silme, veri taşıma (data migration)
    gibi gerçek migration senaryolarını desteklemiyor — bunu dosyanın kendi
    docstring'i de teyit ediyor ("Şema büyümeye devam ederse Alembic/
    Flask-Migrate'e geçilmeli"). Bugün için bu yeterli çünkü V3.5'te sadece
    2 kolon eklendi (`transactions.source`, `daily_tasks.active`) ve bu model
    şemayı kırmadan çalışıyor. Alembic'e geçiş başlı başına bir altyapı
    değişikliği: `flask db init/migrate/upgrade` akışına geçmek, mevcut
    canlı MySQL şemasını "baseline" olarak Alembic'e tanıtmak (stamp),
    `schema_upgrade.py`'nin yerini alacak yeni bir deploy adımı kurmak
    gerekiyor — bunu 1 Ekim öncesi, aktif günlük kullanım + veri birikimi
    sürerken yapmak, olası bir hatalı migration'ın günlük kullanımı ve
    üzerinde çalışılan referans veri setini (Life Score kalibrasyonu için
    toplanan 1 aylık veri) riske atar. **Öneri:** 1 Ekim'de, çoklu-kullanıcı
    "app" lansmanına geçiş hazırlığının bir parçası olarak ele alınsın
    (bkz. V6 — Çok Kullanıcı Dönüşümü) — zaten o noktada çoklu kullanıcı
    şeması (users tablosu vb.) için de gerçek migration'lara ihtiyaç
    doğacak, dolayısıyla Alembic'e geçiş ile Float→Numeric migration'ı aynı
    turda, birlikte yapılabilir: önce `flask db init` + mevcut şemayı
    stamp'le, sonra Numeric migration'ını Alembic revizyonu olarak yaz,
    `schema_upgrade.py`'yi kademeli olarak emekliye ayır (ya da sadece
    gerçekten "ADD COLUMN" düzeyinde kalan hafif değişiklikler için tut).

**Not (1 Ekim 2026'ya kadar geçerli kısıtlama):** 1 Ekim 2026'ya kadar Life
Score algoritmasını/eşiklerini kıracak ya da geçmiş veriyle yeni veriyi
kıyaslanamaz hale getirecek değişiklik yapılmaz (bug fix/güvenlik düzeltmesi
istisna) — çünkü şu an ~11 günlük gerçek kullanım verisi birikiyor ve plan,
1 Ekim'de yaklaşık 1 aylık veriye bakılarak Life Score eşiklerinin
kalibre edilmesi; bu pencerede biriken verinin baştan sona aynı algoritma/
şema mantığıyla üretilmiş olması (karşılaştırılabilir kalması) gerekiyor.
Yukarıdaki iki madde (`Float`→`Numeric` ve Alembic) tam da bu nedenle
1 Ekim'den sonraya ertelendi: ikisi de şema/veri katmanında risk taşıyan,
Life Score'un ürettiği sayılarla doğrudan ilgisi olmasa da canlı veri
birikimini kesintiye uğratabilecek (hatalı migration, kilitlenme, veri
kaybı) değişiklikler.

### V4.5 — Kişisel Analiz (planlandı, henüz başlanmadı)
Berkcan'ın detaylı vizyonundan (bkz. konuşma geçmişi):

*Not (2026-09-11 değerlendirmesi):* Aşağıdaki maddeler, mevcut
`dashboard_logic.py` içindeki kural-tabanlı içgörü altyapısı (`get_insights`,
`insight_finans_aliskanlik_link`, `insight_mesai_link`,
`MIN_SAMPLES_PER_GROUP = 3`, `CONTEXT_LOOKBACK_DAYS = 90`) ışığında tek tek
değerlendirildi. "1 Ekim 2026'ya kadar Life Score algoritması/eşikleri
kırılmayacak" kısıtı göz önünde tutularak her maddeye bir uygulama
zamanlaması etiketi eklendi. Bu bölüm sadece değerlendirme notudur — henüz
kod değişikliği yapılmadı.

- [ ] **Modüller arası gerçek korelasyon keşfi** (örn. "mesai yaptığın
      haftalarda gelirin artıyor ama dışarıda yemek harcaman da artıyor")
  - *Değerlendirme:* Mevcut `insight_finans_aliskanlik_link` ve
    `insight_mesai_link` zaten çapraz-modül korelasyon yapıyor, ama
    **günlük** bazda ve tek çift (harcama↔alışkanlık, mesai-günü↔performans).
    Bu maddenin istediği "mesai haftası" örneği daha ileri bir adım: (a) önce
    bir "mesai haftası" tanımı gerekir (örn. o hafta içinde ≥1 mesai kaydı
    olan haftalar), (b) sonra o haftalık gruplar için gelir VE harcama
    kategorisi (örn. "dışarıda yemek") ayrı ayrı toplanıp iki grup (mesai
    haftası / mesai olmayan hafta) karşılaştırılmalı — mevcut fonksiyonların
    ikisi de bunu yapmıyor, yeni bir haftalık-agregasyon katmanı gerekiyor.
  - *İstatistiksel örneklem yeterliliği:* Mevcut `MIN_SAMPLES_PER_GROUP = 3`
    deseniyle tutarlı olmak için en az 3 "mesai haftası" + 3 "mesai olmayan
    hafta" = **6 farklı hafta** (yaklaşık 1.5 ay) gerekir; ideal olarak daha
    fazla, çünkü her haftanın ayrıca ilgili harcama kategorisi verisine de
    sahip olması lazım (bazı haftalarda o kategori hiç harcama olmayabilir,
    örneklem daha da daralır). `CONTEXT_LOOKBACK_DAYS = 90` günlük pencere
    (~12-13 hafta) mekanizma olarak yeterli, ama gerçek kullanım verisi 1
    Ekim'de sadece **~30 gün (~4-4.5 hafta)** olacak — bu, 6 haftalık
    minimum eşiğin bile altında. Yani 1 Ekim'de bu içgörü muhtemelen
    "yeterli veri yok, hiç gösterilmiyor" durumunda kalacak (mevcut
    `insight_*` fonksiyonlarının "veri yetersizse None dön" deseniyle
    tutarlı bir şekilde sessiz kalır, yanlış/zorlama bir korelasyon üretmez).
  - *Etiket:* İskelet şimdi kurulabilir, veri arttıkça kendiliğinden
    olgunlaşır — fonksiyon `MIN_SAMPLES_PER_GROUP` benzeri bir eşikle
    yazılıp `get_insights` candidate listesine eklenebilir; 1 Ekim'deki
    geliştirme turunda muhtemelen hâlâ "yeterli veri yok" gösterecek ama
    kod o zaman zaten hazır ve test edilmiş olur, sonraki haftalarda veri
    arttıkça otomatik olarak aktifleşir. Gerçek/anlamlı çıktı için
    muhtemelen Kasım-Aralık 2026 beklenmeli.

- [ ] **Kişisel öneri motoru** — bazen "ekle" değil "azalt" önermeli
      (örn. alışkanlık tamamlama düşüyorsa yeni alışkanlık eklemek yerine
      mevcutlara odaklanmayı önersin)
  - *Değerlendirme:* `get_insights`'ın öncelik-puanlı candidate-list deseni
    (`candidates.append((öncelik, {...}))`, `candidates.sort(...)`) yeni bir
    kural eklemek için zaten hazır bir iskelet — mekanik olarak **düşük
    efor**. Somut bir boşluk da var: `insight_week_over_week` şu an sadece
    `diff > 5` (iyileşme) durumunu raporluyor; `diff < -5` gibi bir gerileme
    hiç yakalanmıyor/gösterilmiyor. Yani "azalt" önerisi için ek veri
    kaynağına gerek yok — aynı `ctx.daily_blended_pct` / haftalık ortalama
    karşılaştırması ters yönde kullanılarak (ya da ayrı bir
    `insight_declining_trend` fonksiyonuyla) "performans düşüyor → yeni
    alışkanlık ekleme, mevcutlara odaklan" mesajı üretilebilir. Daha
    kişiselleştirilmiş bir "azalt" önerisi (örn. hangi spesifik alışkanlığın
    en çok gerilediğini bulmak) için `habit_done_by_date` üzerinden
    alışkanlık bazlı (agregat değil, tek tek) tamamlanma trendi
    hesaplanması gerekir — bu, mevcut agregat `daily_aliskanlik_pct`
    yaklaşımından biraz daha fazla iş ister ama yine de mevcut veri
    modeliyle (ek migration/yeni alan olmadan) yapılabilir.
  - *Etiket:* Teknik olarak kolay/yapılabilir, ama 1 Ekim sonrasına
    ertelenmeli — bu yeni bir içgörü kartı olduğu ve doğrudan Life Score
    hesaplamasına (`compute_life_score`/`life_score_breakdown`) dokunmadığı
    için katı anlamda "Life Score algoritmasını/eşiklerini kırma" yasağına
    girmeyebilir, ama gösterilen önerilerin kullanıcı davranışını
    (dolayısıyla dolaylı olarak toplanan veriyi) etkileme riski var; 1
    Ekim'deki tek geliştirme turunda ele alınması daha güvenli.

- [ ] **Haftalık rapor ekranı** — bkz. **V4 — "Haftalık özet raporu"**
      (bu iş kalemi eskiden burada da ayrı bir `[ ]` madde olarak
      duruyordu; iki fazda aynı işin ayrı takip edilmesi karışıklığa yol
      açacağından tekilleştirildi — tek takip noktası V4'ün sonundaki
      "Haftalık özet raporu" maddesi).

### V5 — Gerçek "BBA OS" hissi (planlandı, henüz başlanmadı)
Berkcan'ın "Life Engine" vizyonu:
- [ ] 🔮 Tahmin sistemi: mevcut harcama/birikim hızına göre ay sonu projeksiyonu
      ("bu hızla devam edersen bütçeni 2.300₺ aşabilirsin" gibi)
  - *Değerlendirme:* Teknik olarak kolay — `_finans_pace_pct` zaten "ayın
    geçen kısmına göre beklenen tempo" hesabını yapıyor, ay sonu projeksiyonu
    bunun `month_net / elapsed_gün * ay_toplam_gün` şeklinde basit bir
    ekstrapolasyonu. Asıl mesele veri: tek bir ayın içindeki günlük harcama
    eğrisi (maaş ay ortasında giriliyor, ilk yarı hep negatif/sıfır net
    çıkıyor — `_finans_pace_pct`'in kendi docstring'i bunu zaten anlatıyor)
    anlamlı bir "hız" çıkarmak için birkaç ay geriye bakmayı gerektirir.
    1 Ekim'de elde ~1 aylık veri var; bu, projeksiyonu göstermek için değil
    ama "düşük güven" etiketiyle bir ilk sürüm çıkarmak için yeterli olabilir.
    Kod tabanının zaten oturmuş deseniyle tutarlı olmalı: yetersiz örnek
    varsa (`MIN_LIFESCORE_DAYS`, `MIN_ISTIKRAR_DAYS`, `MIN_MOMENTUM_DAYS`
    gibi eşiklerde olduğu gibi) hiç gösterme, yanıltıcı bir sayı üretme.
  - *Ne zaman:* 1 Ekim sonrası başlanabilir, birkaç ay veri biriktikçe
    (Kasım/Aralık) projeksiyonun güvenilirliği asıl o zaman artar.
- [ ] 🔮 Hedef tahmini: "bu birikim hızıyla hedefe Kasım'da ulaşırsın, harcamaları
      %10 azaltırsan Ekim'de"
  - *Değerlendirme:* Madde 1 ile aynı temel altyapıyı (aylık net birikim
    hızı) kullanıyor, üzerine "hedefe kalan tutar / aylık hız = kaç ay"
    basit bölmesi ekleniyor — teknik karmaşıklık düşük. Aynı veri kısıtı
    geçerli: tek aylık veriyle "hız" tahmini gürültülü olur (maaş günü,
    tek seferlik büyük harcamalar hızı kolayca çarpıtır). 1 Ekim'de
    "başlangıç" versiyonu (düşük güven etiketiyle) yapılabilir, ama
    "yeterli veri yoksa hiç gösterme" ilkesine sadık kalınmalı — burada
    eşik muhtemelen en az 2-3 aylık `MonthlyGoal` geçmişi olmalı.
  - *Ne zaman:* 1 Ekim'den sonra, tercihen madde 1 ile birlikte; asıl
    olgunlaşması Kasım/Aralık'ta birden fazla ay verisi birikince.
- [ ] 🧠 "What if?" simülatörü: "10 saat daha mesai yaparsam ne olur?" gibi
      sorulara anlık hesaplanan senaryo cevabı
  - *Değerlendirme:* Kod tabanının mimarisine **kolay** ölçüde uygun.
    `calculate_salary(year, month, overtime_entries, leave_entries)`
    tamamen saf bir fonksiyon — DB'ye yazmıyor, sadece parametre olarak
    verilen liste üzerinden hesaplıyor (`salary.py:29`); "10 saat daha
    mesai" senaryosu için gerçek `ctx.month_overtime` listesinin bir
    kopyasına hipotetik bir `OvertimeEntry`-benzeri obje eklemek ve aynı
    fonksiyonu tekrar çağırmak yeterli. `compute_life_score` /
    `_finans_pace_pct` / `life_score_breakdown` de aynı şekilde saf:
    hepsi önceden kurulmuş `DashboardContext` (`ctx`) üzerinden okuma
    yapıyor, hiçbiri DB'ye yazmıyor. `ctx`'in kendisi `__init__`'te DB'den
    veri çekiyor ama bir kez kurulduktan sonra alt hesaplamalar bellek içi
    sözlüklerden (`daily_done_by_date`, `month_net`, `month_overtime_hours`
    vb.) okuyor — yani `ctx`'i klonlayıp birkaç alanını (ör. `month_net`,
    `month_overtime_hours`) hipotetik değerlerle değiştirip aynı
    `compute_life_score`/`_finans_pace_pct` fonksiyonlarını tekrar
    çağırmak, gerçek veriye hiç dokunmadan senaryo sonucu üretir.
    Önemli tespit: **bu özellik veri birikimine bağlı değil** — mevcut
    verinin ne kadar olduğundan bağımsız, tamamen mimari bir iş (mevcut
    veriyi DEĞİŞTİRMİYOR, sadece hipotetik/anlık hesap yapıyor). 1 Ekim'i
    beklemeden, istenildiği an ele alınabilir; Life Score algoritmasının
    kendisine dokunmuyor (salt okuma + parametre ile çağrı), bu yüzden
    "1 Ekim'e kadar algoritmayı kırma" kısıtıyla da çelişmiyor.
  - *Ne zaman:* İstenildiği zaman — hatta 1 Ekim öncesi bile yapılabilir.
- [ ] 🏆 Hedef parçalama: bir birikim hedefini alt-stratejilere bölme
      (aylık +X₺, harcama -Y₺, +Z saat mesai gibi)
  - *Değerlendirme:* Esasen basit bir UI + hesaplama işi — hedefe kalan
    tutarı birkaç sabit senaryoya (sadece mesai / sadece harcama kısma /
    karma) bölüştürüp göstermek. "What if?" simülatörü (madde 3) zaten
    kurulduysa bu, onun üzerine ince bir sunum katmanı olarak inşa
    edilebilir (aynı saf hesaplama fonksiyonlarını birkaç farklı
    parametre kombinasyonuyla çağırıp sonuçları yan yana listelemek).
    Veri birikimine bağımlı değil, Life Score algoritmasını değiştirmiyor.
  - *Ne zaman:* Madde 3'ten sonra (ona bağımlı/onun üzerine kurulu),
    istenildiği zaman — 1 Ekim'i beklemesi gerekmez.
- [ ] Achievement/rozet sistemi
  - *Değerlendirme:* ⚠️ Netleştirilmeli — mevcut tasarım ilkeleriyle
    çelişebilir. ROADMAP'in kendi "Önemli tasarım ilkeleri" bölümü
    "**XP ≠ Yaşam Skoru**" diyor ve proje geçmişinde (V3'te XP/Level
    sistemi eklenmiş, V3.5'te ise bilinçli olarak **kaldırılmış** —
    "Ana ekran yeniden tasarlandı: XP/Level ve 'BU AY' kaldırıldı, Life
    Score hero..." maddesine bakınız) gamification bilinçli olarak
    azaltılmış. Bunun gerekçesi muhtemelen "düşük skor başarısızsın
    demek değil" ve "streak cezalandırıcı olmamalı" ilkeleriyle bağlantılı:
    XP/Level/rozet gibi biriktirilen/kaybedilen mekanikler kolayca
    "skor düştü = ilerleme kaybettin" hissi yaratabilir. Rozet sistemi bu
    kaldırılmış mekaniğe **geri dönüş gibi duruyor**. Eklemeden önce
    Berkcan'ın gerçekten bunu isteyip istemediği, ve isteniyorsa "rozet"in
    XP/Level'dan farklı olarak nasıl tasarlanacağı (ör. kaybedilemeyen,
    sadece pozitif kilometre taşlarını işaretleyen bir liste mi, yoksa
    skor bazlı bir ilerleme sistemi mi) netleşmeli. Bu madde diğerleri
    gibi doğrudan uygulamaya alınmamalı; önce bir tasarım/onay konuşması
    gerekiyor.
  - *Ne zaman:* Belirsiz — önce Berkcan ile tasarım ilkesi netleşmeli;
    netleşse bile 1 Ekim öncesi Life Score/streak mantığına karışmaması
    için dikkatli izole edilmeli.
- [ ] 🤖 Doğal dil katmanı (AI): "Bu ay neden daha kötüyüm?" gibi serbest
      sorulara veriye dayalı açıklama üretebilme — **Berkcan'ın kendi notu:**
      "Önce sistem kendi matematiğini ve veri modelini oturtsun", yani bu en son
  - *Değerlendirme:* Dokümanın kendi notuna katılıyorum — bu gerçekten
    en son yapılması gereken madde. Ek olarak: bu bir **LLM API
    entegrasyonu** demek — maliyet (her soru bir API çağrısı), API key
    yönetimi/güvenliği, ve rate limiting gerektirir. Mevcut mimari
    **tek kullanıcılı** (Berkcan'ın kendi kullanımı, PythonAnywhere'de tek
    SQLite/MySQL, kimlik doğrulama HTTP Basic Auth ile tek kullanıcı
    varsayımıyla kurulu) — bu haliyle bir maliyet sorunu yaratmaz. Ancak
    plan çok-kullanıcılı bir "app"e dönüşmekse, kullanıcı başına API
    maliyeti kontrolü (kota, önbellekleme, model seçimi) olmadan bu
    özelliği açmak maliyeti öngörülemez hale getirir. Mevcut mimari buna
    hazır değil (bkz. V6 — Çok Kullanıcı Dönüşümü).
  - *Ne zaman:* 1 Ekim sonrası, hatta **çok-kullanıcı dönüşümünden de
    sonra** — maliyet kontrolü ve API key/rate-limit altyapısı olmadan
    açılmamalı.

### V6 — Çok Kullanıcı Dönüşümü (planlandı, 1 Ekim 2026'dan ÖNCE başlanmayacak)
Berkcan'ın nihai hedefi: BBA OS'i çok-kullanıcılı bir "app" olarak piyasaya
sürmek. Bugünkü kod (2026-09-11 itibarıyla) **uçtan uca tek-kullanıcılık**
varsayımıyla yazıldı — hiçbir modelde tenant/owner ayrımı yok, kimlik
doğrulama tek bir global kullanıcı/şifre çifti, dağıtım tek WSGI instance'ı +
tek veritabanı. Bu bölüm o boşluğu kapatıyor. Önce 1 Ekim 2026'da (yaklaşık
1 aylık gerçek kullanım verisi birikince) kendi kullanımına göre son bir
algoritma/kalite kalibrasyon turu tamamlanacak; çok-kullanıcı dönüşümüne
ANCAK ondan sonra başlanacak.

- [ ] **En kritik/riskli iş: her modele `user_id`, her sorguya filtre**
  - `models.py`'deki **15 model sınıfının hiçbirinde** `user_id` (veya
    başka bir tenant/owner alanı) yok: `Tag`, `DailyTask`,
    `DailyTaskCompletion`, `DeadlineTask`, `Note`, `Transaction`,
    `SubscriptionCategory`, `Subscription`, `MonthlyGoal`, `OvertimeEntry`,
    `LeaveEntry`, `MonthlySalary`, `Habit`, `HabitCompletion`, `AppSetting`.
    Bugün her sorgu **GLOBAL** — tüm kullanıcıların verisi aynı tablolarda
    karışık olacak şekilde tasarlanmış.
  - Etkilenen dosya sayısı kabaca: 6 blueprint dosyası
    (`blueprints/is_takip.py` ~227 satır/18 sorgu call-site'ı,
    `blueprints/aliskanlik.py` ~337 satır/22, `blueprints/butce.py` ~371
    satır/11, `blueprints/mesai.py` ~364 satır/13, `blueprints/analizler.py`
    ~124 satır/2, `blueprints/notlar.py` ~47 satır/2) + `app.py` +
    `models.py` + `settings.py` + `salary.py` (1 sorgu) — toplam **~9-10
    çekirdek Python dosyası**. (Analizler ve Notlar, İş Takip'in içinden
    ayrı modüllere taşındığı için bir kısım sorgu call-site'ı da onlara
    geçti — is_takip.py küçüldü, toplam sayı yaklaşık aynı kaldı.)
  - `.query.` / `db.session.query(` / `filter_by(` / `db.session.get(`
    kalıplarına göre grep'te blueprints genelinde **~68 sorgu call-site'ı**
    tespit edildi (+ `salary.py`'de 1 tane daha). Her biri tek tek
    `filter_by(user_id=...)` (ya da eşdeğeri) ile filtrelenmeli — bu satır
    satır kontrol gerektiren, hatası doğrudan **veri sızıntısına** (bir
    kullanıcının diğerinin bütçe/maaş/alışkanlık verisini görmesi) yol
    açabilecek büyük çaplı bir refactor olarak ele alınmalı. Tek seferde
    "hepsini değiştir" yerine modül modül (önce İş Takip, sonra Alışkanlık,
    Bütçe, Mesai) yapılıp her adımdan sonra manuel/otomatik test
    önerilir.
  - Unique constraint'lerin de gözden geçirilmesi gerekir: örn. `Tag.name`,
    `Habit.name`, `MonthlyGoal(year, month)`, `MonthlySalary(year, month)`
    şu an global-unique — çok-kullanıcıda bunlar `(user_id, name)` /
    `(user_id, year, month)` bileşik unique'e dönüşmeli, yoksa iki
    kullanıcı aynı alışkanlık adını veya aynı ay için maaş kaydı giremez.

- [ ] **Auth: gerçek kullanıcı hesapları**
  - Bugün `app.py` içindeki `_guard_request`/`_auth_ok`, `BBA_USER` ve
    `BBA_PASS` ortam değişkenlerinden okunan **TEK bir global kullanıcı adı/
    şifre** ile HTTP Basic Auth yapıyor — kayıt, login, şifre hash'leme,
    oturum (session) yönetimi gibi gerçek bir kullanıcı hesap sistemi
    yok. `BBA_USER`/`BBA_PASS`'tan biri eksikse auth tamamen kapanıyor
    (kasıtlı "tehlikeli" uyarı zaten kodda var).
  - Bunun yerini gerçek bir kullanıcı hesapları sisteminin alması gerekir:
    kayıt/login/logout akışı, şifrelerin hash'lenmesi (ör.
    `werkzeug.security.generate_password_hash`/`check_password_hash`),
    oturum yönetimi (ör. Flask-Login) ve her request'te "hangi kullanıcı"
    bilgisinin `g.user`/`current_user` olarak modele/sorgulara
    aktarılması. CSRF koruması (`_guard_request` içindeki Origin/Referer
    kontrolü) da yeni auth akışıyla uyumlu hale getirilmeli.

- [ ] **`AppSetting` per-user hale getirilmeli**
  - `models.py`'deki `AppSetting` docstring'i bunun bugün (2026-09-11)
    **bilinçli olarak** tek-satırlık, tüm cihazlar için ortak (session
    yerine DB'de) bir ayar olarak tasarlandığını açıkça belirtiyor —
    ama bu tasarım "tek kullanıcı" varsayımına dayanıyor.
    `settings.py`'deki `get_gelir_gizli`/`set_gelir_gizli`,
    `db.session.get(AppSetting, GELIR_GIZLI_KEY)` ile primary key'i
    doğrudan sabit string (`"gelir_gizli"`) olarak kullanıyor.
  - Çok-kullanıcıya geçerken `AppSetting`'in primary key'i
    `(user_id, key)` bileşik olmalı (ya da `user_id` sütunu eklenip
    `key` ile birlikte unique constraint kurulmalı) — yoksa bir
    kullanıcının "gelir gizle" tercihi tüm kullanıcıları etkiler (bir
    kullanıcı kapatırsa herkeste açılır gibi bir senaryo bile mümkün).

- [ ] **Migration stratejisi: Alembic'e geçiş**
  - `schema_upgrade.py` bilinçli olarak "hafif" tutulmuş: sadece eksik
    kolon (`ALTER TABLE ADD COLUMN`) ve eksik index (`CREATE INDEX`)
    ekleyebiliyor; kolon TİPİ değiştiremiyor, ve dosyanın kendi
    docstring'i zaten "şema büyümeye devam ederse Alembic/Flask-Migrate'e
    geçilmeli" diyor (V3.5'te de aynı not roadmap'te var: "Alembic/
    Flask-Migrate (şimdilik hafif schema_upgrade.py yetiyor)").
  - Çok-kullanıcı dönüşümü tam olarak bu eşiği geçiyor: 15 tabloya
    `user_id` foreign key eklemek, bileşik unique constraint'leri
    değiştirmek/kaldırmak, gerekirse yeni bir `users` tablosu yaratmak —
    bunların hepsi `schema_upgrade.py`'nin kapsamının dışında. Bu yüzden
    V6'ya başlarken **Alembic/Flask-Migrate'e geçiş** ilk adım olmalı.
  - Mevcut (Berkcan'ın kendi) veri, yeni şemada bir "ilk kullanıcı" satırı
    olarak taşınmalı: `users` tablosuna Berkcan için tek bir satır
    eklenip, var olan tüm satırlara (tags, daily_tasks, transactions,
    habits, vb.) o kullanıcının id'si `user_id` olarak yazılan tek
    seferlik bir veri-taşıma migration'ı gerekir — hem SQLite (yerel/
    yedek) hem MySQL (PythonAnywhere canlı) için test edilmeli.

- [ ] **Dağıtım — karar noktası** → somut $0/minimum-maliyet cevabı için
      bkz. **`MALIYETSIZ_ROADMAP.md`** (hosting/DB/auth/e-posta için
      2026-09 itibariyle güncel ücretsiz seçenekler ve yükseltme eşikleri)
  - `DEPLOY.md` ve `wsgi_example.py`, PythonAnywhere'de **tek WSGI
    instance + tek veritabanı** (SQLite veya tek MySQL DB) varsayımıyla
    yazılmış; `BBA_USER`/`BBA_PASS`/`BBA_SECRET_KEY` WSGI dosyasına gömülü
    tek bir hesabı temsil ediyor. Çok-kullanıcı bir SaaS'a geçince bu
    model (tek instance, ortam değişkeninde sabit kimlik bilgisi)
    anlamsız kalıyor.
  - Cevaplandı (bkz. `MALIYETSIZ_ROADMAP.md`): PythonAnywhere ücretsiz
    planında (günde 100 CPU-sn, custom domain yok) kalınabilir ama CPU
    sınırı çok-kullanıcı trafiğinde beklenenden hızlı dolabilir; Render
    gerçek bir ücretsiz alternatif (soğuk başlangıç dezavantajıyla),
    Fly.io/Railway'in artık kalıcı ücretsiz katmanı yok. Karar Berkcan'a
    ait — büyümeden önce ödeme yapmama ilkesiyle, önce PythonAnywhere'de
    kalıp CPU sınırına yaklaşınca karar vermek önerildi.

**Not:** Yukarıdaki maddelerin TAMAMI 1 Ekim 2026'dan önce başlanmamalı —
önce mevcut tek-kullanıcı sürümüyle biriken gerçek kullanım verisi üzerinden
algoritma/kalite kalibrasyonu (V4/V4.5/V5 maddeleri) tamamlanmalı. Bu sıra
bilinçli: yanlış temel üzerine (kalibre edilmemiş Life Score/içgörü
mantığıyla) çok-kullanıcı mimarisi kurmak, hem daha büyük bir refactor
riski hem de mimariyi iki kez değiştirme riski taşır.

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
