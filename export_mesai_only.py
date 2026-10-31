r"""
Eski (tüm modüllü) bir yedeği, SADECE Mesai verisini içeren yeni bir SQLite
dosyasına dönüştürür. Kaynak dosyaya dokunmaz (salt okunur açılır); hedef
dosya zaten varsa üzerine YAZMAZ.

Kullanım:
    python export_mesai_only.py personal_os_yedek_2026-10-31.db data/personal_os.db

Mesai dışındaki tablolar (iş, bütçe, alışkanlık, sayaç, notlar, ayarlar)
yeni dosyaya hiç kopyalanmaz.
"""
import os
import sys

from sqlalchemy import create_engine

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from extensions import db  # noqa: E402
import models  # noqa: E402,F401  (sadece Mesai modellerini metadata'ya kaydeder)
import db_copy_tools  # noqa: E402


def main():
    if len(sys.argv) != 3:
        print("Kullanım: python export_mesai_only.py KAYNAK.db HEDEF.db")
        sys.exit(1)
    src, dst = sys.argv[1], sys.argv[2]
    if not os.path.exists(src):
        print(f"HATA: kaynak bulunamadı: {src}")
        sys.exit(1)
    if os.path.exists(dst):
        print(f"HATA: hedef zaten var, üzerine yazılmaz: {dst}")
        sys.exit(1)

    src_engine = create_engine(f"sqlite:///file:{os.path.abspath(src)}?mode=ro&uri=true")
    db_copy_tools.make_sqlite_snapshot(src_engine, db.metadata, dst)
    src_engine.dispose()

    out = create_engine(f"sqlite:///{dst}")
    with out.connect() as conn:
        for table in db.metadata.sorted_tables:
            n = conn.exec_driver_sql(f"SELECT COUNT(*) FROM {table.name}").scalar()
            print(f"  {table.name}: {n} satır")
    out.dispose()
    print(f"\nHazır: {dst}  (kaynak dosya değiştirilmedi)")


if __name__ == "__main__":
    main()
