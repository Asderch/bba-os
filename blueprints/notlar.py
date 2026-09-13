"""Notlar — bağımsız, tüm modüllerden erişilen serbest not defteri.

Önceden İş Takip modülünün içine gömülüydü (`/is/notlar`), sidebar'da ayrı
bir sekme gibi görünmesine rağmen aslında İş Takip'in bir alt sayfasıydı.
Notların İş'e özgü bir kavramı yok (herhangi bir konuda tutulabilir), bu
yüzden kendi bağımsız modülüne taşındı.
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash

from extensions import db
from models import Note

bp = Blueprint("notlar", __name__, url_prefix="/notlar")


@bp.context_processor
def inject_module_info():
    return {
        "module_theme": "notlar",
        "module_index_endpoint": "notlar.index",
        "module_brand_name": "Notlar",
    }


@bp.route("/")
def index():
    notes = Note.query.order_by(Note.created_at.desc()).all()
    return render_template("notlar/index.html", notes=notes)


@bp.route("/add", methods=["POST"])
def add_note():
    content = request.form.get("content", "").strip()
    if not content:
        flash("Not boş olamaz.")
        return redirect(url_for("notlar.index"))
    db.session.add(Note(content=content))
    db.session.commit()
    return redirect(url_for("notlar.index"))


@bp.route("/<int:note_id>/delete", methods=["POST"])
def delete_note(note_id):
    note = Note.query.get_or_404(note_id)
    db.session.delete(note)
    db.session.commit()
    return redirect(url_for("notlar.index"))
