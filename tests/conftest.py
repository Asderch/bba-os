import os
import sys
import tempfile

import pytest

_TMP = tempfile.mkdtemp()
# app.py import edilmeden ÖNCE ayarlanmalı — Flask-SQLAlchemy motoru import
# anındaki create_all() ile bağlanıyor, sonradan config değişikliği geçmiyor.
os.environ["BBA_DB_URI"] = f"sqlite:///{_TMP}/test.db"
os.environ.pop("BBA_MYSQL_URI", None)
os.environ.pop("BBA_USER", None)
os.environ.pop("BBA_PASS", None)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture()
def flask_app():
    import app as appmod

    appmod.app.config["TESTING"] = True
    with appmod.app.app_context():
        appmod.db.drop_all()
        appmod.db.create_all()
    return appmod.app


@pytest.fixture()
def client(flask_app):
    c = flask_app.test_client()
    c.environ_base["HTTP_ORIGIN"] = "http://localhost"
    return c
