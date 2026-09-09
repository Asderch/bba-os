"""
İki SQLAlchemy motoru (SQLite <-> MySQL) arasında tüm tabloları, ID'leri
ve ilişkileri (foreign key) koruyarak kopyalayan ortak araç.

Kullanım alanları:
1. migrate_to_mysql.py - tek seferlik, SQLite'tan MySQL'e ilk taşıma
2. app.py'deki yedekleme fonksiyonları - MySQL canlıyken, her yedekte
   MySQL'deki güncel veriyi taşınabilir tek dosyalık bir SQLite
   "anlık görüntüsüne" (snapshot) döküyor (eskisi gibi tek dosya indirme
   deneyimi böylece MySQL'e geçtikten sonra da aynı kalıyor)
"""
from sqlalchemy import create_engine, MetaData, insert, text


def create_schema(dst_engine, sqlalchemy_metadata):
    """Hedef motorda, verilen SQLAlchemy metadata'sına göre tüm tabloları oluşturur."""
    sqlalchemy_metadata.create_all(bind=dst_engine)


def copy_all_tables(src_engine, dst_engine, sqlalchemy_metadata):
    """
    src_engine'deki tüm tabloları dst_engine'e, ID'leri ve foreign key
    sırasını koruyarak kopyalar. dst_engine'de tablolar önceden
    create_schema() ile oluşturulmuş olmalı ve BOŞ olmalı.
    Döndürdüğü değer: {tablo_adı: kopyalanan_satır_sayısı}
    """
    dst_meta = MetaData()
    dst_meta.reflect(bind=dst_engine)

    sonuc = {}
    with src_engine.connect() as sconn, dst_engine.begin() as mconn:
        for table in sqlalchemy_metadata.sorted_tables:
            rows = sconn.execute(table.select()).mappings().all()
            if not rows:
                sonuc[table.name] = 0
                continue

            dst_table = dst_meta.tables[table.name]
            mconn.execute(insert(dst_table), [dict(r) for r in rows])
            sonuc[table.name] = len(rows)

            # AUTO_INCREMENT sayacını mevcut en yüksek id'nin bir fazlasına
            # ayarla ki taşımadan sonraki yeni kayıtlar çakışmasın.
            # (SQLite'ta buna gerek yok - INTEGER PRIMARY KEY zaten eklenen
            # en yüksek id'den otomatik devam ediyor, sadece MySQL için gerekli.)
            if dst_engine.dialect.name == "mysql" and "id" in dst_table.columns:
                max_id = mconn.execute(text(f"SELECT MAX(id) FROM {table.name}")).scalar()
                if max_id is not None:
                    mconn.execute(text(f"ALTER TABLE {table.name} AUTO_INCREMENT = {max_id + 1}"))

    return sonuc


def make_sqlite_snapshot(src_engine, sqlalchemy_metadata, snapshot_path):
    """
    src_engine'deki (canlı) veriyi, belirtilen yoldaki YENİ bir SQLite
    dosyasına eksiksiz kopyalar. Bu dosya, mevcut /yedekle indirme
    deneyimini MySQL'e geçtikten sonra da aynı şekilde sürdürmek için
    kullanılıyor.
    """
    sqlite_engine = create_engine(f"sqlite:///{snapshot_path}")
    create_schema(sqlite_engine, sqlalchemy_metadata)
    copy_all_tables(src_engine, sqlite_engine, sqlalchemy_metadata)
    sqlite_engine.dispose()
