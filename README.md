# BBA OS

6 modülü (İş Takip, Bütçe Takip, Mesai Takip, Alışkanlık Takip, Analizler,
Notlar) tek bir Flask uygulaması ve tek bir veritabanında birleştiren
kişisel sistem.

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

## Modül

Uygulama 2026-10-31'de **sadece Mesai Takip**'e indirildi (diğer modüller —
İş, Bütçe, Alışkanlık, Sayaçlar, Analizler, Notlar, ana ekran — kaldırıldı;
git geçmişinde duruyor).

- **Mesai Takip** (`/mesai`, açılış sayfası) — fazla mesai ve izin kaydı,
  aylık net maaş (Profil), maaş/mesai hesaplama (Excel formülüne dayalı)

Eski, çok modüllü bir yedeği sadece-mesai veritabanına çevirmek için:
`python export_mesai_only.py ESKI_YEDEK.db data/personal_os.db`
(kaynağa dokunmaz, hedef varsa üzerine yazmaz).

## Veri Yedekleme

Sol menüdeki **"💾 Yedekler"** sayfasından otomatik günlük yedekleri
indirebilir, **"⬇️ Şimdi yedek al"** ile o anki canlı veritabanını
(`personal_os.db`, tüm modüllerin verisi) tek dosya olarak alabilirsin.
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
