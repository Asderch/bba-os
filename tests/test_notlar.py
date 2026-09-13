"""Notlar artık bağımsız bir modül (/notlar) — eskiden İş Takip'in içindeydi
(/is/notlar), sidebar'da ayrı bir sekme gibi görünmesine rağmen aslında
İş Takip'in bir alt sayfasıydı. Bu testler taşımanın tamamlandığını doğrular:
yeni route'lar çalışıyor, eskileri artık yok."""


def test_notlar_index_ok(client):
    resp = client.get("/notlar/")
    assert resp.status_code == 200
    assert "Notlar" in resp.get_data(as_text=True)


def test_old_is_takip_notlar_routes_removed(client):
    assert client.get("/is/notlar").status_code == 404


def test_add_and_delete_note(client):
    html = client.get("/notlar/").get_data(as_text=True)
    assert "Henüz not almadın" in html

    client.post("/notlar/add", data={"content": "İlk notum"})
    html = client.get("/notlar/").get_data(as_text=True)
    assert "İlk notum" in html

    import app as appmod
    from models import Note
    with appmod.app.app_context():
        note = Note.query.filter_by(content="İlk notum").first()
        assert note is not None
        note_id = note.id

    client.post(f"/notlar/{note_id}/delete")
    html = client.get("/notlar/").get_data(as_text=True)
    assert "İlk notum" not in html


def test_add_note_empty_content_rejected(client):
    resp = client.post("/notlar/add", data={"content": "   "}, follow_redirects=True)
    assert resp.status_code == 200
    assert "boş olamaz" in resp.get_data(as_text=True)
