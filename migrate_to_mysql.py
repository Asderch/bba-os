r"""
Tek seferlik taşıma script'i: mevcut SQLite verisini (data/personal_os.db)
yeni bir MySQL veritabanına, ID'leri ve ilişkileri koruyarak kopyalar.

Kullanım (PythonAnywhere Bash konsolunda, bba-os klasörünün içinden):

    python migrate_to_mysql.py "mysql+pymysql://KULLANICI:PAROLA@HOST/VERITABANI"

Örnek (PythonAnywhere'in kendi isimlendirmesiyle; KULLANICI ve PAROLA'yı
kendi bilgilerinle değiştir, parolayı komuta yazmak yerine mümkünse
ortam değişkeninden ver):

    python migrate_to_mysql.py "mysql+pymysql://KULLANICI:PAROLA@KULLANICI.mysql.pythonanywhere-services.com/KULLANICI\$default"

ÖNEMLİ: MySQL veritabanı BOŞ olmalı (ilk kurulum). Script tabloları
kendisi oluşturuyor, üzerine yazmıyor — eğer tablolar zaten doluysa
hata verir, veri bozulmaz ama script durur.
"""
import os
import sys

from sqlalchemy import create_engine

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from extensions import db
from flask import Flask
import models  # noqa - tüm modelleri db.metadata'ya kaydeder
import db_copy_tools

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SQLITE_PATH = os.path.join(BASE_DIR, "data", "personal_os.db")


def main():
    if len(sys.argv) < 2:
        print("Kullanım: python migrate_to_mysql.py \"mysql+pymysql://kullanici:parola@host/veritabani\"")
        sys.exit(1)

    mysql_uri = sys.argv[1]

    if not os.path.exists(SQLITE_PATH):
        print(f"HATA: {SQLITE_PATH} bulunamadı. Taşınacak bir SQLite dosyası yok.")
        sys.exit(1)

    print(f"Kaynak: {SQLITE_PATH}")
    print(f"Hedef:  {mysql_uri.split('@')[-1] if '@' in mysql_uri else mysql_uri}")
    onay = input("Devam etmek istiyor musun? (evet/hayır): ").strip().lower()
    if onay not in ("evet", "e", "yes", "y"):
        print("İptal edildi.")
        sys.exit(0)

    # Flask app'i geçici olarak kurup tüm model tanımlarının (db.metadata)
    # yüklenmesini sağlıyoruz - gerçek bir web sunucusu başlatmıyoruz.
    tmp_app = Flask(__name__)
    tmp_app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{SQLITE_PATH}"
    db.init_app(tmp_app)

    sqlite_engine = create_engine(f"sqlite:///{SQLITE_PATH}")
    mysql_engine = create_engine(mysql_uri)

    print("\nMySQL tarafında tablolar oluşturuluyor...")
    db_copy_tools.create_schema(mysql_engine, db.metadata)

    print("Veri kopyalanıyor...\n")
    sonuc = db_copy_tools.copy_all_tables(sqlite_engine, mysql_engine, db.metadata)

    print("Taşıma tamamlandı:")
    for tablo, sayi in sonuc.items():
        print(f"  {tablo}: {sayi} satır")

    print("\nŞimdi WSGI dosyana şu satırı eklemen gerekiyor (import app'ten ÖNCE):")
    print(f'  os.environ["BBA_MYSQL_URI"] = "{mysql_uri}"')
    print("\nSonra Web sekmesinden Reload yap.")


if __name__ == "__main__":
    main()
