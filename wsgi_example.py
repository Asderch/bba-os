"""
PythonAnywhere WSGI dosyası ÖRNEĞİ.

PythonAnywhere Web sekmesindeki gerçek WSGI dosyasına (genelde
/var/www/<kullanıcı>_pythonanywhere_com_wsgi.py) bu içeriği uyarlayarak kopyala.
"""
import os
import sys

project_home = '/home/KULLANICI_ADIN/bba-os'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# --- Ortam değişkenleri (gerçek değerlerle değiştir) ---
os.environ['BBA_USER'] = 'kullanici-adin'
os.environ['BBA_PASS'] = 'guclu-bir-parola'
os.environ['BBA_SECRET_KEY'] = 'rastgele-uzun-bir-anahtar'
# MySQL kullanacaksan (PythonAnywhere ücretsiz planda SQLite de olur):
# os.environ['BBA_MYSQL_URI'] = 'mysql+pymysql://KULLANICI:PAROLA@KULLANICI.mysql.pythonanywhere-services.com/KULLANICI$default'

from app import app as application
