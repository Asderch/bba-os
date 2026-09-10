import hmac
import os
import secrets
import shutil
from pathlib import Path
from urllib.parse import urlparse

from flask import Flask, render_template, send_file, abort, request, Response, session

from common import today_tr
from extensions import db

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "personal_os.db")
BACKUPS_DIR = Path(BASE_DIR) / "data" / "backups"
BACKUP_RETENTION_DAYS = 14

app = Flask(__name__)

# Ortam değişkeni tanımlıysa (PythonAnywhere'de WSGI dosyasında ayarlanır) MySQL
# kullan; tanımlı değilse (yerel/masaüstü kullanım) yerel SQLite dosyasına düş.
# Bu sayede aynı kod hem sunucuda (MySQL, hızlı) hem kendi bilgisayarında
# (SQLite, MySQL sunucusu kurmana gerek kalmadan) çalışıyor.
MYSQL_URI = os.environ.get("BBA_MYSQL_URI")
# BBA_DB_URI her şeyi ezer (test/geliştirme için tam SQLAlchemy URI'si).
DB_URI_OVERRIDE = os.environ.get("BBA_DB_URI")
if DB_URI_OVERRIDE:
    app.config["SQLALCHEMY_DATABASE_URI"] = DB_URI_OVERRIDE
elif MYSQL_URI:
    app.config["SQLALCHEMY_DATABASE_URI"] = MYSQL_URI
    # MySQL sunucusu boşta kalan bağlantıları sessizce kapatabiliyor
    # (wait_timeout). pool_pre_ping her kullanımdan önce ufak bir kontrol
    # yaparak "Lost connection" hatasını engelliyor; pool_recycle de
    # bağlantıları sunucunun zaman aşımından önce proaktif olarak
    # tazeliyor.
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_pre_ping": True,
        "pool_recycle": 280,
    }
else:
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DB_PATH}"

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Secret key: ortam değişkeninden oku. Tanımlı değilse (yerel/masaüstü) her
# başlatmada rastgele üret — sabit, tahmin edilebilir bir anahtar bırakmıyoruz.
# PythonAnywhere'de WSGI dosyasında BBA_SECRET_KEY ayarlanmalı (yoksa restart'ta
# oturumlar/flash mesajları geçersiz olur, güvenlik açığı değil).
app.secret_key = os.environ.get("BBA_SECRET_KEY") or secrets.token_hex(32)

db.init_app(app)


# ----------------------------------------------------------------------
# Basit tek kullanıcılık kimlik doğrulama (HTTP Basic Auth).
# BBA_USER ve BBA_PASS ortam değişkenleri tanımlıysa TÜM sayfalar bu ikisini
# ister. Tanımlı değilse (yerel geliştirme / masaüstü uygulaması) auth kapalı.
# PythonAnywhere gibi herkese açık bir ortamda bu ikisi MUTLAKA ayarlanmalı —
# aksi halde adresi bilen herkes tüm finans/maaş verisini görür ve /yedekle
# ile tüm veritabanını indirir.
_AUTH_USER = os.environ.get("BBA_USER")
_AUTH_PASS = os.environ.get("BBA_PASS")
if bool(_AUTH_USER) != bool(_AUTH_PASS):
    # Yalnızca biri set edilmiş → auth SESSİZCE kapalı kalır, tehlikeli.
    import warnings
    warnings.warn(
        "BBA_USER veya BBA_PASS'tan yalnızca biri ayarlı — kimlik doğrulama KAPALI. "
        "Herkese açık bir sunucuda ikisini de ayarla.",
        RuntimeWarning,
    )

_SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def _auth_ok():
    if not _AUTH_USER or not _AUTH_PASS:
        return True  # auth yapılandırılmamış - yerel kullanım
    auth = request.authorization
    if not auth or not auth.username or not auth.password:
        return False
    return (
        hmac.compare_digest(auth.username.encode("utf-8"), _AUTH_USER.encode("utf-8"))
        and hmac.compare_digest(auth.password.encode("utf-8"), _AUTH_PASS.encode("utf-8"))
    )


@app.before_request
def _guard_request():
    # 1) Kimlik doğrulama
    if not _auth_ok():
        return Response(
            "Giriş gerekli.", 401,
            {"WWW-Authenticate": 'Basic realm="BBA OS"'},
        )

    # 2) Basit CSRF koruması (Flask-WTF'siz): güvenli olmayan metotlarda isteğin
    #    kendi sitemizden geldiğini Origin/Referer host'undan doğrula. Tarayıcı
    #    çapraz-site bir POST'ta bu başlıkları her zaman gönderir; curl/masaüstü
    #    istemcisi ikisini de göndermeyebilir — o durumda izin veriyoruz.
    if request.method not in _SAFE_METHODS:
        source = request.headers.get("Origin") or request.headers.get("Referer")
        if source and urlparse(source).netloc != request.host:
            abort(403)
    return None

# Blueprint'leri kaydet
from blueprints.is_takip import bp as is_takip_bp
from blueprints.butce import bp as butce_bp
from blueprints.mesai import bp as mesai_bp
from blueprints.aliskanlik import bp as aliskanlik_bp

app.register_blueprint(is_takip_bp)
app.register_blueprint(butce_bp)
app.register_blueprint(mesai_bp)
app.register_blueprint(aliskanlik_bp)


PARA_MASK = "••••••"


@app.context_processor
def _inject_privacy():
    """Gelir gizleme: session'da tutulan bir bayrak. True iken şablonlar gelir/
    net/maaş rakamlarını sunucu tarafında maskeler — gerçek değer HTML'e hiç
    girmez (eski sürüm data-real attribute'unda düz metin tutuyordu)."""
    gizli = session.get("gelir_gizli", True)

    def para_gizle(value, suffix=" ₺"):
        """Gizli modda '••••••', aksi halde '1234.56 ₺'. None -> '—'."""
        if gizli:
            return PARA_MASK
        if value is None:
            return "—"
        return f"{value:.2f}{suffix}"

    return {"gelir_gizli": gizli, "PARA_MASK": PARA_MASK, "para_gizle": para_gizle}


@app.route("/")
def root():
    try:
        _auto_backup_if_needed()
    except Exception as exc:  # yedekleme bir FS hatası verirse ana sayfa çökmesin
        app.logger.warning("Otomatik yedek alınamadı: %s", exc)

    from common import today_tr, now_tr
    import dashboard_logic as dash

    ctx = dash.DashboardContext(today_tr())
    home = dash.build_home_context(ctx, now_tr())

    return render_template(
        "home.html",
        module_theme="home", module_index_endpoint="root", module_brand_name="BBA OS",
        **home,
    )


def _active_sqlite_path():
    """Uygulamanın gerçekten kullandığı SQLite dosyasının yolu (BBA_DB_URI ile
    değiştirilmiş olabilir); MySQL modunda None."""
    url = db.engine.url
    if url.get_backend_name() != "sqlite" or not url.database:
        return None
    return url.database


def _is_sqlite():
    return _active_sqlite_path() is not None


@app.route("/yedekle")
def backup():
    """Tüm verinin (4 modülün de) bulunduğu tek veritabanı dosyasını indirir (o anki canlı hali)."""
    if not _is_sqlite():
        # MySQL modunda "canlı dosya" diye bir şey yok - önce taşınabilir
        # tek dosyalık bir SQLite anlık görüntüsü oluşturup onu indiriyoruz.
        # Eşzamanlı indirmelerin birbirini bozmaması için her istek kendi
        # geçici dosyasına yazar.
        import tempfile
        from io import BytesIO
        fd, snapshot_path = tempfile.mkstemp(suffix=".db", dir=os.path.join(BASE_DIR, "data"))
        os.close(fd)
        try:
            _make_mysql_snapshot(snapshot_path)
            with open(snapshot_path, "rb") as fh:
                data = fh.read()
        finally:
            try:
                os.remove(snapshot_path)
            except OSError:
                pass
        filename = f"personal_os_yedek_{today_tr().isoformat()}.db"
        return send_file(
            BytesIO(data), as_attachment=True, download_name=filename,
            mimetype="application/octet-stream",
        )

    sqlite_path = _active_sqlite_path()
    filename = f"personal_os_yedek_{today_tr().isoformat()}.db"
    if not sqlite_path or not os.path.exists(sqlite_path):
        abort(404)
    return send_file(sqlite_path, as_attachment=True, download_name=filename)


def _make_mysql_snapshot(target_path):
    """MySQL'deki canlı veriyi, verilen yola tek dosyalık bir SQLite kopyası olarak döker."""
    import db_copy_tools
    if os.path.exists(target_path):
        os.remove(target_path)
    db_copy_tools.make_sqlite_snapshot(db.engine, db.metadata, target_path)


def _auto_backup_if_needed():
    """V1: Her gün ilk ziyarette otomatik bir yedek snapshot'ı alır, eski yedekleri budar."""
    if app.config.get("TESTING"):
        return
    BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
    today_str = today_tr().isoformat()
    target = BACKUPS_DIR / f"personal_os_{today_str}.db"

    if not target.exists():
        # Önce geçici dosyaya yaz, sonra atomik olarak yerine koy — iki
        # eşzamanlı "ilk istek" birbirinin yarım yedeğini görmesin.
        tmp = target.with_suffix(f".db.tmp-{os.getpid()}")
        sqlite_path = _active_sqlite_path()
        if not sqlite_path:
            _make_mysql_snapshot(str(tmp))
            os.replace(tmp, target)
        elif os.path.exists(sqlite_path):
            shutil.copy2(sqlite_path, tmp)
            os.replace(tmp, target)

    all_backups = sorted(BACKUPS_DIR.glob("personal_os_*.db"))
    if len(all_backups) > BACKUP_RETENTION_DAYS:
        for old in all_backups[:-BACKUP_RETENTION_DAYS]:
            old.unlink()


@app.route("/yedekler")
def backup_history():
    """V1: Otomatik alınan günlük yedeklerin listesi."""
    files = sorted(BACKUPS_DIR.glob("personal_os_*.db"), reverse=True) if BACKUPS_DIR.exists() else []
    backups = [{"filename": f.name, "date": f.stem.replace("personal_os_", "")} for f in files]
    return render_template(
        "backup_history.html", backups=backups, retention_days=BACKUP_RETENTION_DAYS,
        module_theme="home", module_index_endpoint="root", module_brand_name="BBA OS",
    )


@app.route("/yedekler/<filename>")
def download_backup(filename):
    from werkzeug.utils import secure_filename
    if (
        filename != secure_filename(filename)
        or not filename.startswith("personal_os_")
        or not filename.endswith(".db")
    ):
        abort(404)
    path = BACKUPS_DIR / filename
    if not path.exists():
        abort(404)
    return send_file(path, as_attachment=True, download_name=filename)


@app.errorhandler(403)
def _forbidden(e):
    return render_template(
        "error.html", code=403, message="Bu istek reddedildi.",
        module_theme="home", module_index_endpoint="root", module_brand_name="BBA OS",
    ), 403


@app.errorhandler(404)
def _not_found(e):
    return render_template(
        "error.html", code=404, message="Sayfa bulunamadı.",
        module_theme="home", module_index_endpoint="root", module_brand_name="BBA OS",
    ), 404


@app.errorhandler(500)
def _server_error(e):
    return render_template(
        "error.html", code=500, message="Bir şeyler ters gitti.",
        module_theme="home", module_index_endpoint="root", module_brand_name="BBA OS",
    ), 500


with app.app_context():
    os.makedirs(os.path.join(BASE_DIR, "data"), exist_ok=True)
    import models  # noqa - tüm modellerin db.create_all() tarafından görülmesi için
    db.create_all()
    import schema_upgrade
    try:
        schema_upgrade.run(db)  # var olan DB'lere eksik kolon/index'leri ekle
    except Exception as exc:  # şema güncellemesi uygulamanın açılmasını engellemesin
        app.logger.error("schema_upgrade başarısız: %s", exc)


if __name__ == "__main__":
    # debug yalnızca BBA_DEBUG=1 iken; aksi halde kapalı (Werkzeug debugger
    # açıkta kalmasın). Masaüstü için desktop.py zaten debug=False kullanıyor.
    app.run(
        host="127.0.0.1", port=5200,
        debug=os.environ.get("BBA_DEBUG") == "1",
    )
