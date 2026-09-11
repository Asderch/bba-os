"""CSRF koruması (Origin/Referer host doğrulaması) fail-closed regresyon testleri."""

# Var olan, gövde gerektirmeyen basit bir POST route: kimlik doğrulaması yok,
# CSRF muhafızından önce 4xx/5xx başka bir sebeple dönmeyecek bir uç nokta.
POST_PATH = "/butce/gelir-gizle"


def test_post_without_origin_or_referer_is_forbidden(flask_app):
    """Origin/Referer hiç yoksa (ör. no-referrer meta etiketiyle tarayıcı
    ikisini de düşürdüğünde) istek artık reddedilmeli (fail-closed)."""
    bare_client = flask_app.test_client()  # conftest'teki client fixture'ı KULLANILMIYOR
    bare_client.environ_base.pop("HTTP_ORIGIN", None)
    bare_client.environ_base.pop("HTTP_REFERER", None)
    resp = bare_client.post(POST_PATH, headers={})
    assert resp.status_code == 403


def test_post_with_wrong_host_origin_is_forbidden(flask_app):
    bare_client = flask_app.test_client()
    bare_client.environ_base.pop("HTTP_REFERER", None)
    resp = bare_client.post(POST_PATH, headers={"Origin": "http://evil.example.com"})
    assert resp.status_code == 403


def test_post_with_matching_host_origin_is_allowed(client):
    # conftest'teki `client` fixture'ı Origin: http://localhost enjekte ediyor,
    # bu da test client'ın varsayılan Host header'ı ("localhost") ile eşleşiyor.
    resp = client.post(POST_PATH)
    assert resp.status_code < 400
