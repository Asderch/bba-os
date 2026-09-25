"""
Hafif, idempotent şema güncelleyici.

`db.create_all()` yeni tabloları oluşturur ama VAR OLAN bir tabloya sonradan
eklenen kolon/index'i eklemez. Bu modül o boşluğu doldurur: her açılışta
çalışır, eksik kolonları `ALTER TABLE ADD COLUMN` ile, eksik index'leri
`CREATE INDEX` ile tamamlar. Hepsi "zaten varsa dokunma" mantığında ve
tek tek try/except ile korunuyor — bir DDL adımı patlasa bile (ör. iki
worker yarışı) uygulama yine ayağa kalkar, sadece loglar.

SINIRLAR:
- Kolon TİPİ değiştiremez (Float -> Numeric gibi). Onun için Alembic gerekir.
- `_ADDED_COLUMNS` elle tutulan, models.py'ye paralel bir listedir; yeni bir
  kolon eklerken buraya da eklemek gerekir (test bu pariteyi kontrol ediyor).
Şema büyümeye devam ederse Alembic/Flask-Migrate'e geçilmeli.
"""
import logging

from sqlalchemy import inspect, text

log = logging.getLogger(__name__)

# (tablo, kolon, SQL tipi) — var olan DB'lerde eksikse eklenecek kolonlar.
_ADDED_COLUMNS = [
    ("transactions", "source", "VARCHAR(64)"),
    ("daily_tasks", "active", "BOOLEAN DEFAULT 1"),
    ("habits", "target", "VARCHAR(60)"),
]


def run(db):
    engine = db.engine
    existing_tables = set(inspect(engine).get_table_names())

    # 1) Eksik kolonlar — her biri ayrı transaction + ayrı try/except
    for table, column, coltype in _ADDED_COLUMNS:
        if table not in existing_tables:
            continue
        try:
            cols = {c["name"] for c in inspect(engine).get_columns(table)}
            if column in cols:
                continue
            with engine.begin() as conn:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {coltype}"))
            log.info("schema_upgrade: %s.%s kolonu eklendi", table, column)
        except Exception as exc:  # yarış / lehçe farkı / zaten var — uygulama çökmesin
            log.warning("schema_upgrade: %s.%s eklenemedi: %s", table, column, exc)

    # 2) Eksik index'ler (modeldeki index=True / Index(...) tanımları)
    for table_obj in db.metadata.sorted_tables:
        if table_obj.name not in existing_tables:
            continue  # create_all zaten index'leriyle oluşturur
        try:
            have = {ix["name"] for ix in inspect(engine).get_indexes(table_obj.name)}
        except Exception:
            continue
        for index in table_obj.indexes:
            if index.name in have:
                continue
            try:
                with engine.begin() as conn:
                    index.create(bind=conn)
                log.info("schema_upgrade: %s index'i oluşturuldu", index.name)
            except Exception as exc:
                log.warning("schema_upgrade: %s index'i oluşturulamadı: %s", index.name, exc)
