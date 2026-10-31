"""schema_upgrade: idempotent olmalı + eksik index'i tamamlamalı."""


def test_run_is_idempotent_on_current_schema(flask_app):
    import app as appmod
    from extensions import db
    import schema_upgrade

    with appmod.app.app_context():
        schema_upgrade.run(db)
        schema_upgrade.run(db)


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


def test_index_creation_block_creates_missing_index(flask_app):
    """schema_upgrade.run()'ın index bloğu: modelde index=True olan bir kolonun
    index'i eksikse (ör. eski bir DB'de) gerçekten oluşturuluyor mu."""
    import app as appmod
    from extensions import db
    from sqlalchemy import inspect
    import schema_upgrade

    with appmod.app.app_context():
        engine = db.engine
        table_obj = db.metadata.tables["overtime_entries"]

        target_index = None
        for index in table_obj.indexes:
            if any(col.name == "entry_date" for col in index.columns):
                target_index = index
                break
        assert target_index is not None

        with engine.begin() as conn:
            target_index.drop(bind=conn)
        have = {ix["name"] for ix in inspect(engine).get_indexes("overtime_entries")}
        assert target_index.name not in have

        schema_upgrade.run(db)
        have = {ix["name"] for ix in inspect(engine).get_indexes("overtime_entries")}
        assert target_index.name in have

        schema_upgrade.run(db)
        have = {ix["name"] for ix in inspect(engine).get_indexes("overtime_entries")}
        assert target_index.name in have
