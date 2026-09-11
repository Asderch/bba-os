"""schema_upgrade: idempotent olmalı + eksik kolon/index'i tamamlamalı."""


def test_adds_missing_source_column_and_is_idempotent(flask_app):
    import app as appmod
    from extensions import db
    from sqlalchemy import inspect, text
    import schema_upgrade

    with appmod.app.app_context():
        engine = db.engine
        # source kolonunu düşürerek "eski" bir şema taklit et (SQLite: tabloyu
        # yeniden kur)
        with engine.begin() as conn:
            conn.execute(text("DROP TABLE transactions"))
            conn.execute(text(
                "CREATE TABLE transactions ("
                " id INTEGER PRIMARY KEY, entry_date DATE NOT NULL, kind VARCHAR(10) NOT NULL,"
                " category VARCHAR(50) NOT NULL, amount FLOAT NOT NULL, note VARCHAR(255),"
                " created_at DATETIME)"
            ))
        assert "source" not in {c["name"] for c in inspect(engine).get_columns("transactions")}

        schema_upgrade.run(db)
        assert "source" in {c["name"] for c in inspect(engine).get_columns("transactions")}

        # ikinci çağrı hata vermemeli
        schema_upgrade.run(db)
        assert "source" in {c["name"] for c in inspect(engine).get_columns("transactions")}


def test_added_columns_list_matches_models(flask_app):
    """_ADDED_COLUMNS'daki her kolon gerçekten modelde var mı (parite)."""
    import app as appmod
    from extensions import db
    import schema_upgrade

    with appmod.app.app_context():
        for table, column, _ in schema_upgrade._ADDED_COLUMNS:
            tbl = db.metadata.tables.get(table)
            assert tbl is not None, f"{table} tablosu modelde yok"
            assert column in tbl.columns, f"{table}.{column} modelde yok"


def test_added_columns_types_roughly_match_models(flask_app):
    """_ADDED_COLUMNS'daki SQL tipi, modeldeki kolon tipiyle kabaca uyumlu mu.

    Tam eşleşme aranmıyor (ör. "VARCHAR(64)" vs db.String(64)) — sadece basit
    bir kategori kontrolü: metinsel tipler String'e, boolean tipler
    Boolean'a, sayısal tipler Integer/Numeric'e karşılık gelmeli.
    """
    import app as appmod
    from extensions import db
    import schema_upgrade

    with appmod.app.app_context():
        for table, column, sql_type in schema_upgrade._ADDED_COLUMNS:
            tbl = db.metadata.tables.get(table)
            assert tbl is not None, f"{table} tablosu modelde yok"
            model_type_name = type(tbl.columns[column].type).__name__
            sql_type_upper = sql_type.upper()

            if "VARCHAR" in sql_type_upper or "TEXT" in sql_type_upper or "CHAR" in sql_type_upper:
                assert "String" in model_type_name or "Text" in model_type_name, (
                    f"{table}.{column}: SQL tipi '{sql_type}' metinsel ama model tipi {model_type_name}"
                )
            elif "BOOLEAN" in sql_type_upper or "BOOL" in sql_type_upper:
                assert "Bool" in model_type_name, (
                    f"{table}.{column}: SQL tipi '{sql_type}' boolean ama model tipi {model_type_name}"
                )
            elif "INT" in sql_type_upper:
                assert "Integer" in model_type_name, (
                    f"{table}.{column}: SQL tipi '{sql_type}' sayısal ama model tipi {model_type_name}"
                )
            elif "FLOAT" in sql_type_upper or "NUMERIC" in sql_type_upper or "REAL" in sql_type_upper:
                assert model_type_name in ("Float", "Numeric"), (
                    f"{table}.{column}: SQL tipi '{sql_type}' ondalıklı ama model tipi {model_type_name}"
                )
            # Tanınmayan bir SQL tipi kategorisi varsa heuristik sessizce atlar
            # (yanlış-pozitif üretmemek için) — yeni bir tip eklenirse buraya
            # bir dal daha eklenmeli.


def test_index_creation_block_creates_missing_index(flask_app):
    """schema_upgrade.run()'ın index bloğu: modelde index=True olan bir kolonun
    index'i eksikse (ör. eski bir DB'de) gerçekten oluşturuluyor mu."""
    import app as appmod
    from extensions import db
    from sqlalchemy import inspect
    import schema_upgrade

    with appmod.app.app_context():
        engine = db.engine
        table_obj = db.metadata.tables["transactions"]

        # Transaction.entry_date index=True ile tanımlı — modeldeki Index
        # nesnesini bul (sorgu "entry_date" kolonunu kapsayan index).
        target_index = None
        for index in table_obj.indexes:
            if any(col.name == "entry_date" for col in index.columns):
                target_index = index
                break
        assert target_index is not None, "modelde transactions.entry_date için index bulunamadı"

        # Var olan index'i düşürerek "eski" bir şemayı taklit et.
        with engine.begin() as conn:
            target_index.drop(bind=conn)
        have = {ix["name"] for ix in inspect(engine).get_indexes("transactions")}
        assert target_index.name not in have

        schema_upgrade.run(db)
        have = {ix["name"] for ix in inspect(engine).get_indexes("transactions")}
        assert target_index.name in have

        # ikinci çağrı hata vermemeli (idempotent)
        schema_upgrade.run(db)
        have = {ix["name"] for ix in inspect(engine).get_indexes("transactions")}
        assert target_index.name in have
