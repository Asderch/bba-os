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
