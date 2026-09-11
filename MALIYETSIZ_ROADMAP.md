# BBA OS — Maliyetsiz / Minimum Maliyetli Yol Haritası

Bu döküman `ROADMAP.md`'deki **V6 — Çok Kullanıcı Dönüşümü** bölümünün
"Dağıtım — karar noktası" (henüz karar verilmemiş) maddesine somut, güncel
(2026-09) fiyat/limit verisiyle bir cevap veriyor: çok-kullanıcı bir "app"e
**$0'a yakın** bir maliyetle nereye kadar çıkılabilir, hangi eşiğe gelince
hangi bileşen için ödeme yapmak gerekir. **§8**, Google Play Store'a çıkma
ve kullanıcılardan ücret alma konusunu da aynı "minimum maliyet" ilkesiyle
ele alıyor.

**İlke:** Kullanıcı sayısı 0'ken/azken hiçbir şeye önceden para yatırma —
gerçek bir sınıra çarpınca (CPU, e-posta adedi, disk) o bileşeni yükselt.
"Büyümeden önce ödeme" tuzağına düşme.

## 1. Barındırma (Hosting)

**Mevcut durum — PythonAnywhere ücretsiz (Beginner) plan:** 1 web app,
1 web worker, 512 MB disk, **günde 100 CPU-saniyesi**, custom domain YOK
(sadece `kullaniciadi.pythonanywhere.com`), outbound internet sadece
whitelist'li sitelere. Developer plana ($10/ay) geçilince custom domain +
5.000 CPU-sn/gün açılıyor. ([PythonAnywhere Free Accounts Features](https://help.pythonanywhere.com/pages/FreeAccountsFeatures/), [Plans and pricing](https://www.pythonanywhere.com/pricing/))

**Risk:** `DashboardContext` her ana sayfa isteğinde ~10-20 sorgu atıyor.
Tek kullanıcıyla bile (Berkcan'ın kendi kullanımı) günlük CPU-saniyesi
tüketimini PythonAnywhere panelindeki "CPU usage" grafiğinden takip etmekte
fayda var — birkaç kullanıcı eklenince 100 sn/gün sınırı beklenenden hızlı
dolabilir (özellikle her sayfa yüklemesinde tetiklenen otomatik yedekleme
kontrolü de CPU tüketiyor).

**Ücretsiz alternatif — Render.com:** Gerçek anlamda $0 bir "free web
service" sunuyor, ama 15 dakika trafik yoksa uyuyor, sonraki istek 30-60
saniye "soğuk başlangıç" gecikmesi yaşıyor. ([Render vs Railway vs Fly.io pricing (2026)](https://dev.to/pavel-hostim/render-vs-railway-vs-flyio-pricing-compared-2026-2e5p))

**Elenen seçenekler:** Railway ve Fly.io'nun artık **kalıcı ücretsiz
katmanı yok** — ikisi de saniye bazlı kullanım ücreti alıyor, tabanda bile
kredi kartı/fatura gerektiriyor. ([Render vs Railway vs Fly.io pricing (2026)](https://dev.to/pavel-hostim/render-vs-railway-vs-flyio-pricing-compared-2026-2e5p)) "Maliyetsiz" hedefiyle
uyuşmadıkları için bu roadmap'ten çıkarıldı.

**Öneri:**
- İlk birkaç kullanıcı için **PythonAnywhere'de kal** — zaten kurulu, sıfır
  geçiş maliyeti/işi.
- CPU-saniyesi sınırına yaklaşınca (panelden izlenir) iki seçenek: (a)
  Developer plana geç ($10/ay, ilk gerçek/kabul edilebilir maliyet), ya da
  (b) Render'a taşı (soğuk başlangıç gecikmesi kullanıcı deneyimi açısından
  kabul edilebiliyorsa hâlâ $0).

**Güncelleme (2026-09-11):** Berkcan zaten Developer plana ($10/ay) geçmiş
durumda — bu roadmap'in önerdiği "ilk yükseltme eşiği" burası. Bu, custom
domain (aşağıdaki §5 ve §8'de önemli — Google Play/TWA için gerekiyor) ve
5.000 CPU-sn/gün açıyor. Bu adımdan sonrası (birden fazla kullanıcı, Play
Store dağıtımı) için ek hosting maliyeti şu an gerekmiyor; bir sonraki
gerçek eşik muhtemelen 5.000 CPU-sn/gün sınırına yaklaşmak olur.

## 2. Veritabanı

**Mevcut MySQL (PythonAnywhere'e dahil):** Zaten $0, taşımaya gerek yok —
V6'daki `user_id` refactor'ü bu veritabanı üzerinde olduğu gibi yapılabilir.

**⚠️ Tuzak — Render'a geçilirse:** Render'ın kendi "ücretsiz" Postgres'i
**90 gün sonra tamamen siliniyor** ([Render vs Railway vs Fly.io pricing (2026)](https://dev.to/pavel-hostim/render-vs-railway-vs-flyio-pricing-compared-2026-2e5p)) — Render'a geçilirse kesinlikle
Render'ın kendi veritabanı ÜRÜNÜ kullanılmamalı.

**Kalıcı ücretsiz Postgres alternatifleri (Render'a geçilirse ya da MySQL
dışına çıkılmak istenirse):**
- **Neon** — 0.5 GB depolama/proje, scale-to-zero, süresiz ücretsiz, kredi
  kartı gerekmiyor.
- **Supabase** — 500 MB Postgres + **50.000 aylık aktif kullanıcıya kadar
  ÜCRETSİZ auth** dahil, süresiz (1 haftadan uzun hareketsizlikte proje
  duraklatılıyor, panelden tek tıkla geri açılıyor).
([Database Free Tier Comparison 2026](https://agentdeals.dev/database-free-tier-comparison-2026), [Free PostgreSQL Hosting (2026)](https://swyftstack.com/blog/free-postgresql-hosting))

**Not:** PlanetScale (MySQL) 2024'te ücretsiz katmanını tamamen kaldırdı —
kalıcı ücretsiz bir MySQL barındırma seçeneği pratikte yok. Bu yüzden
mevcut PythonAnywhere MySQL'de kalmak muhtemelen en basit yol; Postgres'e
geçiş (Neon/Supabase) ancak Render'a taşınma kararıyla birlikte gündeme
gelmeli — SQLAlchemy motor-bağımsız yazıldığı için (`models.py` aynı kalır,
sadece bağlantı URI'si değişir) bu geçiş küçük bir iştir, ama
`schema_upgrade.py`'nin ham SQL kullanan kısımları (varsa dialect-özel
sözdizim) gözden geçirilmeli.

## 3. Auth (kullanıcı hesapları)

**Kendi yaz (önerilen, $0, ek bağımlılık yok):** `Flask-Login` +
`werkzeug.security.generate_password_hash/check_password_hash` — zaten
`ROADMAP.md` V6'da bu şekilde planlanmış, tamamen kod içinde, dış servise
bağımlı değil, projenin "tek dosyada oturan basit mimari" felsefesine en
uygun seçenek.

**Alternatif — Supabase Auth (50K MAU'ya kadar ücretsiz):** Hazır
kayıt/login/parola-sıfırlama/e-posta doğrulama sağlar, kendi auth kodu
yazma işini ortadan kaldırır — ama projeye yeni bir dış servis bağımlılığı
(Supabase SDK/API çağrıları, ayrı bir hesap) ekler.

**Öneri:** Küçük kullanıcı sayısında (< birkaç yüz) kendi yazman hem
maliyetsiz hem de mimariye daha uygun; Supabase Auth'u sadece Postgres'e
zaten geçmeyi düşünüyorsan (madde 2) "madem oradayız" mantığıyla
değerlendir, sadece auth için ayrı bir servise bağlanmaya değmez.

## 4. E-posta (şifre sıfırlama / doğrulama)

**Brevo ücretsiz:** Günde 300 e-posta (~9.000/ay), **süresiz**, kredi kartı
gerekmiyor, tam API erişimi dahil. ([Best Email API Services 2026 — Brevo](https://www.brevo.com/blog/best-email-api/), [Free Email API Comparison (2026)](https://www.agentmail.to/blog/free-email-api-for-developers))
Karşılaştırma: Resend 3.000/ay, Mailgun sadece 100/gün — Brevo bu üçü
arasında en cömert kalıcı ücretsiz seçenek.

**Daha da basit (v1 için):** E-posta doğrulamasını tamamen ATLA — sadece
kullanıcı adı + şifre ile kayıt, "şifremi unuttum" akışını ilk sürümde
manuel (Berkcan'a mesaj/e-posta ile ulaşma) çöz. Daha az iş, ama
ölçeklenmez ve biraz güvenlik/spam riski taşır.

**Öneri:** Brevo'nun ücretsiz katmanı zaten yeterince cömert (günde 300
e-posta, muhtemelen uzun süre yetecek); baştan entegre etmek ek maliyet
getirmiyor, "sonra ekleriz" diye erteleme gerekmiyor.

## 5. Alan adı (Domain)

`kullaniciadi.pythonanywhere.com` ya da `uygulama.onrender.com` ile kalmak
**tamamen ücretsiz**. Gerçek bir alan adı (ör. `bba-os.com`) yıllık ~$10-15
— bu roadmap'teki **tek neredeyse-kaçınılmaz küçük maliyet**, ama sadece
profesyonel görünüm/marka istendiğinde gerekli; teknik olarak ertelenebilir.

**Güncelleme:** Google Play Store'a çıkmak isteniyorsa (bkz. §8) gerçek bir
alan adı artık **zorunlu hale geliyor** — TWA (Trusted Web Activity)
paketleme, uygulamanın sahibi olduğunu kanıtlamak için domain üzerinde bir
doğrulama dosyası (`Digital Asset Links`) barındırmayı gerektiriyor, ve
`*.pythonanywhere.com` gibi paylaşılan bir alt alan adında bunu yapmak
mümkün ama pratik değil/güven vermiyor. Developer plan zaten custom domain
desteği veriyor, tek eksik ~$10-15/yıllık domain kaydı.

## 6. İzleme / Hata takibi

Opsiyonel: Sentry ücretsiz planı (aylık 5.000 hata, 1 proje) — ya da hiç
eklemeden mevcut `app.logger` + `/yedekle` ile idare etmek, ki bu zaten
$0 ve şu anki tek-kullanıcı ölçeğinde yeterli.

## 7. AI katmanı (ROADMAP.md V5'in son maddesi)

**Kesinlikle ertelenmeli.** Claude/OpenAI gibi LLM API'lerinin kalıcı,
cömert bir ücretsiz katmanı yok — her soru gerçek para. "Maliyetsiz"
hedefiyle doğrudan çelişiyor. `ROADMAP.md` zaten bunu "en son" olarak
işaretlemişti (Berkcan'ın kendi notu); bu roadmap o kararı teyit ediyor —
para kazanmaya başlamadan bu maddeye dokunulmamalı.

## 8. Google Play Store'a çıkmak + kullanıcılardan ücret almak

Bu, önceki 7 maddeden farklı bir eksen: artık "$0'a nasıl kalırım" değil,
"gelir elde etmek için hangi SIRAYLA ve hangi maliyetle ilerlemeliyim"
sorusu. **Sıralama önemli** — bir Play Store listesi, arkasında gerçek
kullanıcı hesabı/ödeme sistemi olmadan anlamsız; önce `ROADMAP.md`'nin
**V6 — Çok Kullanıcı Dönüşümü** bölümü (gerçek login, `user_id`) ve
aşağıdaki "web'de ödeme" adımı tamamlanmalı, Play Store paketleme EN SON
adım olmalı.

### 8.1 — Android/Play Store'a en ucuz yol: TWA (yeniden yazmak GEREKMİYOR)

BBA OS zaten bir PWA (`manifest.json` + `sw.js` mevcut) — bunu native
Android/iOS koduna sıfırdan yazmak yerine **Trusted Web Activity (TWA)**
ile ince bir Android kabuğuna sarmak yeterli: uygulama tarayıcı arayüzü
olmadan, tam ekran, mevcut web sitesini gösterir. ([MobiLoud: Publishing PWA to App Store/Play 2026](https://www.mobiloud.com/blog/publishing-pwa-app-store/), [Bubblewrap/TWA teknik rehber](https://medium.com/@abusomwansantos/from-pwa-to-play-store-a-technical-guide-to-bubblewrap-and-twa-b244d1a626e6))

**Gereksinimler (hepsi ücretsiz araçlarla karşılanıyor):**
- HTTPS + gerçek bir alan adı (bkz. §5 güncellemesi — Developer plan zaten
  destekliyor, sadece domain kaydı gerekiyor, ~$10-15/yıl).
- Geçerli bir Web Manifest (`name`, `icons`, `start_url`, `display`,
  renkler) — zaten var, gözden geçirilmeli.
- `Digital Asset Links` doğrulama dosyası (`/.well-known/assetlinks.json`)
  — domaine tek seferlik eklenen, $0 bir JSON dosyası.
- Lighthouse PWA skoru ≥ 80 — mevcut PWA kurulumunun buna uyup uymadığı
  kontrol edilmeli (Chrome DevTools'ta ücretsiz ölçülür).
- Paketleme aracı: **Bubblewrap** (Google, komut satırı) ya da
  **PWABuilder** (Microsoft, görsel arayüz) — ikisi de tamamen ücretsiz,
  açık kaynak. ([Bubblewrap resmi Android rehberi](https://developer.android.com/develop/ui/views/layout/webapps/guide-trusted-web-activities-version2))

**Google Play Geliştirici hesabı:** Tek seferlik **$25**, aylık/yıllık
ücret yok. Kişisel hesap (organizasyon değil) olarak açılırsa — 13
Kasım 2023'ten sonra açılan tüm kişisel hesaplar için — **her yeni
uygulama** yayına girmeden önce **12 test kullanıcısıyla 14 gün kapalı
test** şartı var (ek maliyet değil ama zaman/süreç maliyeti — göz ardı
edilmemeli, ilk yayın tarihini ~2 hafta geciktirir). Kimlik doğrulama
için resmi kimlik belgesi (ve bazen selfie) isteniyor. ([Google Play Developer hesap rehberi 2026](https://www.iconikai.com/blog/google-play-developer-account-fee-2026))

**Toplam Play Store'a çıkış maliyeti: $25 (tek seferlik) + ~$10-15/yıl
domain (zaten §5'te gerekli hale geldi) + Bubblewrap/PWABuilder $0.**

### 8.2 — Kullanıcılardan ücret almak: NEREDE tahsil ettiğin kritik

**⚠️ En önemli karar:** Android uygulamasının İÇİNDE bir "satın al/abone
ol" düğmesi koyarsan, Google Play Billing kullanman genelde ZORUNLU hale
gelir (dijital içerik/abonelik satışı Play Store politikası gereği).
2026-06-30 itibarıyla (ABD/İngiltere/AEA) yeni ücret yapısı: ([Android Developers Blog: Expanded billing 2026](https://android-developers.googleblog.com/2026/06/play-expanded-billing.html), [Google Play 2026 ücret değişiklikleri](https://pricepush.app/blog/google-play-subscription-fees-2026-real-math))

| Ödeme yolu (uygulama içinden) | Google'ın kesintisi (ilk $1M/yıl) |
|---|---|
| Google Play Billing (kendi ödeme sistemi) | **%15** (10% servis + 5% billing) |
| Alternatif faturalama / web linkine yönlendirme (uygulama içinden) | **%10** (sadece servis ücreti) |

($1M/yıl geliri geçince oranlar %20-25'e çıkıyor — BBA OS'in şu anki
ölçeğinde bu çok uzak bir eşik, şimdilik göz ardı edilebilir.)

**En ucuz ve en basit yol — ödemeyi uygulamanın DIŞINDA tut:**
Android/TWA uygulamasının içine HİÇ satın alma/abonelik akışı koyma.
Kullanıcı zaten web sitesinde (tarayıcıdan) hesap açıp ödemeyi orada
yapsın (Stripe Checkout ya da Paddle/LemonSqueezy) — Android uygulaması
sadece "giriş yap, zaten ödediysen içeriği gör" şeklinde çalışsın. Bu
durumda uygulama içinde bir satın alma akışı OLMADIĞI için Google Play
Billing'e tabi olma ihtimalin düşer, Google'a HİÇ komisyon ödemeden
(ne %10 ne %15) sadece kendi ödeme sağlayıcının kesintisini ödersin:
- **Stripe:** ~%2.9 + $0.30/işlem, aylık sabit ücret yok.
- **Paddle / LemonSqueezy** ("Merchant of Record"): ~%5, ama global
  KDV/vergi hesaplama ve fatura kesme işini senin yerine üstleniyor —
  tek başına uluslararası satış yapan biri için Stripe'a göre çok daha az
  bürokrasi, fiyat farkı bu yüzden makul.

**Not:** Bu politikalar Google tarafında sık değişiyor (yukarıdaki tablo
2026-06-30'da yürürlüğe giren, oldukça yeni bir değişiklik) ve bölgeye
göre farklılık gösterebiliyor — Play Store'a başvurmadan hemen önce
[Play Console'un güncel politika sayfasından](https://support.google.com/googleplay/android-developer/answer/112622) teyit edilmeli.

**Önerilen sıra:**
1. `ROADMAP.md` V6 — gerçek kullanıcı hesapları (`user_id`, login).
2. Web sitesinde ödeme/abonelik akışı (Stripe ya da Paddle/LemonSqueezy) —
   BURASI asıl "kullanıcılardan ücret alma" işinin gerçekleştiği yer.
3. Domain + HTTPS (zaten Developer planında var, sadece domain kaydı).
4. Bubblewrap/PWABuilder ile TWA paketleme, $25 tek seferlik Play
   Developer hesabı, 12-tester/14-gün süreci.
5. Android uygulamasında satın alma akışı YOK — sadece login; ödeme hep
   web'de kalır, Google'a komisyon gitmez.

*(Not: Bu roadmap sadece Google Play'i kapsıyor — Berkcan Apple App
Store'u da isterse TWA'nın iOS eşdeğeri yok, ayrı bir değerlendirme
[Capacitor gibi bir sarmalayıcı] gerekir; şimdilik istenmedi, bu yüzden
detaylandırılmadı.)*

## Özet tablo

| Bileşen | $0 / minimum seçenek | Ne zaman ücretliye geçilir |
|---|---|---|
| Barındırma | PythonAnywhere Developer $10/ay (zaten aktif) | 5.000 CPU-sn/gün sınırına yaklaşınca → daha üst plan ya da Render |
| Veritabanı | Mevcut PythonAnywhere MySQL (taşımaya gerek yok) | Sadece Render'a geçilirse: Neon/Supabase (Render'ın kendi ücretsiz DB'si 90 günde silinir, kullanma) |
| Auth | Kendi yaz: Flask-Login + werkzeug.security | Muhtemelen hiçbir zaman — bu $0 kalıcı bir çözüm |
| E-posta | Brevo ücretsiz (300/gün, süresiz) | Günlük 300 e-postaya (~300 aktif kayıt/reset/gün) yaklaşınca |
| Alan adı | Gerekli hale geldi (Play Store için) | ~$10-15/yıl, tek seferlik karar |
| İzleme | `app.logger` (mevcut) | Sentry ücretsiz plan, istenirse hemen eklenebilir ($0) |
| AI katmanı | — (yapılmıyor) | Ancak gerçek gelir/bütçe oluşunca |
| Play Store'a çıkış | Bubblewrap/PWABuilder $0 + $25 tek seferlik hesap | Sadece bir kere ödenir |
| Ödeme tahsilatı | Web'de Stripe (~%2.9+$0.30) ya da Paddle (~%5) | Uygulama-içi satın alma eklersen Google %10-15 keser |

**Sonuç:** Web tarafında toplam aylık sabit maliyet zaten $10 (PythonAnywhere
Developer) + isteğe bağlı ~$1/ay (yıllık domain). Play Store'a çıkış tek
seferlik ~$25-40 (domain + Play hesabı) ekliyor. Gerçek, tekrar eden
maliyet SADECE gelirle orantılı ödeme işlemci kesintisi (%3-5, web'de
kalırsan) — Google'a komisyon ödemeden bir "app" olarak Play Store'da
bulunmak teknik olarak mümkün.

---
*Bu döküman `ROADMAP.md` → V6 → "Dağıtım — karar noktası" maddesinin
detaylandırılmış hâlidir; oradaki genel soru işaretinin somut cevabı
burada. Fiyat/limit bilgileri 2026-09 itibariyledir, değişebilir — büyük
bir karar öncesi (özellikle hosting/DB taşıma) ilgili sağlayıcının güncel
sayfasından teyit edilmeli.*
