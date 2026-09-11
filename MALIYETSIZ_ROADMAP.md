# BBA OS — Maliyetsiz / Minimum Maliyetli Yol Haritası

Bu döküman `ROADMAP.md`'deki **V6 — Çok Kullanıcı Dönüşümü** bölümünün
"Dağıtım — karar noktası" (henüz karar verilmemiş) maddesine somut, güncel
(2026-09) fiyat/limit verisiyle bir cevap veriyor: çok-kullanıcı bir "app"e
**$0'a yakın** bir maliyetle nereye kadar çıkılabilir, hangi eşiğe gelince
hangi bileşen için ödeme yapmak gerekir.

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

## Özet tablo

| Bileşen | $0 seçenek | Ne zaman ücretliye geçilir |
|---|---|---|
| Barındırma | PythonAnywhere ücretsiz (kalınabilir) | Günlük CPU-sn sınırına yaklaşınca → Developer $10/ay ya da Render'a taşı |
| Veritabanı | Mevcut PythonAnywhere MySQL (taşımaya gerek yok) | Sadece Render'a geçilirse: Neon/Supabase (Render'ın kendi ücretsiz DB'si 90 günde silinir, kullanma) |
| Auth | Kendi yaz: Flask-Login + werkzeug.security | Muhtemelen hiçbir zaman — bu $0 kalıcı bir çözüm |
| E-posta | Brevo ücretsiz (300/gün, süresiz) | Günlük 300 e-postaya (~300 aktif kayıt/reset/gün) yaklaşınca |
| Alan adı | `*.pythonanywhere.com` / `*.onrender.com` | İstenildiğinde (marka/profesyonellik), ~$10-15/yıl |
| İzleme | `app.logger` (mevcut) | Sentry ücretsiz plan, istenirse hemen eklenebilir ($0) |
| AI katmanı | — (yapılmıyor) | Ancak gerçek gelir/bütçe oluşunca |

**Sonuç:** Onlarca (muhtemelen yüze yakın) kullanıcıya kadar toplam
beklenen aylık maliyet **$0** (opsiyonel domain hariç). İlk gerçek fatura
muhtemelen PythonAnywhere CPU-saniyesi sınırına takılmaktan gelecek —
bu da ayda $10 gibi küçük bir adım, büyük bir sıçrama değil.

---
*Bu döküman `ROADMAP.md` → V6 → "Dağıtım — karar noktası" maddesinin
detaylandırılmış hâlidir; oradaki genel soru işaretinin somut cevabı
burada. Fiyat/limit bilgileri 2026-09 itibariyledir, değişebilir — büyük
bir karar öncesi (özellikle hosting/DB taşıma) ilgili sağlayıcının güncel
sayfasından teyit edilmeli.*
