# Dağıtım — PythonAnywhere

BBA OS'i PythonAnywhere'de yayına almak için kısa adımlar. Genel amaçlı
bir Flask dağıtım rehberi değil — sadece bu proje için gerekenler.

## 1. Kod nasıl yüklenir

PythonAnywhere Bash konsolunda:

```bash
git clone <repo-url> bba-os
```

(Git kullanmıyorsan Files sekmesinden dosyaları zip olarak yükleyip
konsoldan `unzip` ile açabilirsin.)

## 2. Bağımlılıkları kur

Bir virtualenv içinde, `requirements-web.txt` kullan (masaüstü paketi
`pywebview` yerine MySQL sürücüsü `PyMySQL` içerir):

```bash
cd bba-os
python3 -m venv venv
source venv/bin/activate
pip install -r requirements-web.txt
```

## 3. WSGI dosyasını düzenle

PythonAnywhere **Web** sekmesinde, uygulamanın WSGI configuration file
linkine tıkla (genelde `/var/www/<kullanıcı>_pythonanywhere_com_wsgi.py`)
ve içeriğini bu depodaki `wsgi_example.py` şablonuna göre uyarla:
proje yolunu `sys.path`'e ekle, gerekli ortam değişkenlerini
`os.environ[...]` ile ayarla, en altta `from app import app as application`
satırını bırak.

## 4. Ortam değişkenleri — ZORUNLU

`BBA_USER`, `BBA_PASS` ve `BBA_SECRET_KEY` WSGI dosyasında (veya Web
sekmesindeki "Environment variables" alanında, plana göre) mutlaka
ayarlanmalı. `BBA_USER`/`BBA_PASS` ayarlanmazsa uygulama herkese açık
kalır — adresi bilen herkes finans/maaş verisini görebilir. Tüm
değişkenlerin listesi ve açıklaması için `README.md`'deki "Ortam
değişkenleri" tablosuna ve `.env.example` dosyasına bak.

## 5. Static dosya eşlemesi

Web sekmesinde **Static files** bölümüne şu eşlemeyi ekle:

| URL | Directory |
|---|---|
| `/static/` | `/home/<kullanıcı>/bba-os/static/` |

## 6. MySQL'e geçiş (isteğe bağlı)

PythonAnywhere ücretsiz planda SQLite (`data/personal_os.db`) yeterlidir.
MySQL'e geçmek istersen:

1. PythonAnywhere **Databases** sekmesinden bir MySQL veritabanı oluştur.
2. Veritabanı BOŞKEN, bba-os klasöründen tek seferlik taşıma script'ini
   çalıştır:
   ```bash
   python migrate_to_mysql.py "mysql+pymysql://KULLANICI:PAROLA@KULLANICI.mysql.pythonanywhere-services.com/KULLANICI\$default"
   ```
3. Aynı URI'yi WSGI dosyanda `BBA_MYSQL_URI` ortam değişkenine ata
   (bkz. `wsgi_example.py`'deki yorum satırı).

## 7. Yeniden başlatma

Ortam değişkenlerini veya kodu her değiştirdiğinde, Web sekmesindeki
yeşil **Reload** butonuna basman gerekir — değişiklikler otomatik
yansımaz.
