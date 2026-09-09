"""
Hafif, idempotent şema güncelleyici.

`db.create_all()` yeni tabloları oluşturur ama VAR OLAN bir tabloya sonradan
eklenen kolon/index'i eklemez. Bu modül o boşluğu doldurur: her açılışta
çalışır, eksik kolonları `ALTER TABLE ADD COLUMN` ile, eksik index'leri
`CREATE INDEX` ile tamamlar. Hepsi "zaten varsa dokunma" mantığında.

Not: Şema çok büyürse Alembic/Flask-Migrate'e geçmek gerekir; bu, tek
kullanıcılık bu uygulamanın mevcut ölçeği için yeterli ve CLI adımı
gerektirmiyor.
"""
from sqlalchemy import inspect, text


# (tablo, kolon, SQL tipi) — var olan DB'lerde eksikse eklenecek kolonlar.
_ADDED_COLUMNS = [
    ("transactions", "source", "VARCHAR(64)"),
]


def run(db):
    engine = db.engine
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    with engine.begin() as conn:
        # 1) Eksik kolonlar
        for table, column, coltype in _ADDED_COLUMNS:
            if table not in existing_tables:
                continue
            cols = {c["name"] for c in inspector.get_columns(table)}
            if column not in cols:
                conn.execute(text(f'ALTER TABLE {table} ADD COLUMN {column} {coltype}'))

        # 2) Eksik index'ler (modeldeki index=True / Index(...) tanımları)
        for table_obj in db.metadata.sorted_tables:
            if table_obj.name not in existing_tables:
                continue  # create_all zaten index'leriyle oluşturur
            have = {ix["name"] for ix in inspector.get_indexes(table_obj.name)}
            for index in table_obj.indexes:
                if index.name not in have:
                    try:
                        index.create(bind=conn)
                    except Exception:
                        pass  # yarış / lehçe farkı - kritik değil
