# BBA OS

4 modülü (İş Takip, Bütçe Takip, Mesai Takip, Alışkanlık Takip) tek bir
Flask uygulaması ve tek bir veritabanında birleştiren kişisel sistem.

## Kurulum (kendi bilgisayarında)

```bash
cd bba-os
python -m venv venv
venv\Scripts\activate        # macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
python desktop.py             # masaüstü pencere
# veya: python app.py         # tarayıcıda http://127.0.0.1:5200
```

## Ortam değişkenleri

`.env.example` dosyasına bak. Özet:

| Değişken | Ne işe yarar |
|---|---|
| `BBA_USER` / `BBA_PASS` | İkisi de doluysa tüm sayfalar HTTP Basic Auth ister. **Herkese açık bir sunucuda (PythonAnywhere) zorunlu** — aksi halde adresi bilen herkes finans/maaş verisini görür. Yerelde boş bırakılırsa auth kapalıdır. |
| `BBA_SECRET_KEY` | Oturum imzalama. Boşsa her başlatmada rastgele üretilir. |
| `BBA_MYSQL_URI` | Doluysa MySQL, boşsa yerel SQLite (`data/personal_os.db`). |
| `BBA_DB_URI` | İç/test amaçlı SQLAlchemy URI, tanımlıysa `BBA_MYSQL_URI`/SQLite dahil her şeyi ezer. Normal kullanımda boş bırak. |
| `BBA_DEBUG` | `1` ise `python app.py` Werkzeug debugger'ı açar. Sunucuda ayarlama. |

## Modüller

- **İş Takip** (`/is`) — günlük işler (checkbox), terminli işler (tarih
  bazlı, aciliyet renkli), etiketler, notlar, geçmiş, istatistik
- **Bütçe Takip** (`/butce`) — gelir/gider takibi, kategori dağılım
  grafiği, gelir gizleme, abonelik takibi (otomatik gider kaydı ile)
- **Mesai Takip** (`/mesai`) — fazla mesai kaydı, maaş hesaplama
  (Excel formülüne dayalı)
- **Alışkanlık Takip** (`/aliskanlik`) — hedef koymadan işaretleme,
  "neden" açıklaması, etki puanı, hazır 8'li başlangıç seti

## Veri Yedekleme

Sol menüdeki **"💾 Yedekler"** sayfasından otomatik günlük yedekleri
indirebilir, **"⬇️ Şimdi yedek al"** ile o anki canlı veritabanını
(`personal_os.db`, 4 modülün de verisi) tek dosya olarak alabilirsin.
Her gün ilk ziyarette otomatik bir snapshot alınır, son 14 gün tutulur.

Düzenli olarak (örn. haftada bir), özellikle büyük bir değişiklikten
önce yedek almanı öneririm.

**Geri yükleme:** SQLite modunda `data/personal_os.db` dosyasını indirdiğin
yedekle değiştir ve uygulamayı yeniden başlat. (MySQL moduna geçtiysen
`BBA_MYSQL_URI` tanımlı olduğu sürece SQLite dosyası kullanılmaz.)

## Test

```bash
pip install -r requirements-dev.txt
pytest
```

## Yol Haritası

Uzun vadeli vizyon ve sıradaki geliştirme aşamaları için `ROADMAP.md`
dosyasına bak.

## Dağıtım

Uygulamayı PythonAnywhere'de yayına almak için `DEPLOY.md` dosyasına bak.
