import threading
import webview

from app import app


def run_flask():
    app.run(host="127.0.0.1", port=5200, debug=False, use_reloader=False)


if __name__ == "__main__":
    t = threading.Thread(target=run_flask, daemon=True)
    t.start()

    webview.create_window("BBA OS", "http://127.0.0.1:5200", width=1100, height=850, min_size=(700, 600))
    webview.start()
