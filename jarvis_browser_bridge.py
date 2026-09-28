from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
import shutil
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright

HOST = "127.0.0.1"
PORT = 8765

pw = None
browser = None
context = None
page = None

def find_browser():
    candidates = [
        os.environ.get("JARVIS_BROWSER_EXECUTABLE"),
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        shutil.which("chrome"),
        shutil.which("google-chrome"),
        shutil.which("msedge"),
    ]

    for path in candidates:
        if path and os.path.exists(path):
            return path

    return None

def start_browser():
    global pw, browser, context, page

    if page:
        return page

    pw = sync_playwright().start()

    executable = find_browser()

    kwargs = {
        "headless": False,
        "args": [
            "--start-maximized",
            "--disable-popup-blocking"
        ]
    }

    if executable:
        kwargs["executable_path"] = executable

    context = pw.chromium.launch_persistent_context(
        os.path.abspath(".jarvis-browser-profile"),
        **kwargs
    )

    page = context.pages[0] if context.pages else context.new_page()
    page.bring_to_front()

    return page

class Handler(BaseHTTPRequestHandler):

    def cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")

    def json_response(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")

        self.send_response(status)
        self.cors()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.cors()
        self.end_headers()

    def do_GET(self):
        if self.path == "/health":
            self.json_response({
                "success": True,
                "service": "JARVIS Browser Bridge",
                "port": PORT
            })
            return

        if self.path == "/browser":
            try:
                p = start_browser()
                self.json_response({
                    "success": True,
                    "browser": p.url
                })
            except Exception as e:
                self.json_response({
                    "success": False,
                    "error": str(e)
                }, 500)
            return

        self.json_response({"success": False, "error": "Rota não encontrada"}, 404)

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            data = json.loads(self.rfile.read(length) or "{}")
        except Exception:
            data = {}

        try:
            p = start_browser()

            if self.path == "/open":
                url = data.get("url", "").strip()

                if not url:
                    raise Exception("URL não informada")

                if not url.startswith(("http://", "https://")):
                    url = "https://" + url

                response = p.goto(
                    url,
                    wait_until="domcontentloaded",
                    timeout=45000
                )

                p.bring_to_front()

                self.json_response({
                    "success": True,
                    "url": p.url,
                    "status": response.status if response else None
                })
                return

            if self.path == "/back":
                p.go_back()
                p.bring_to_front()
                self.json_response({"success": True})
                return

            if self.path == "/forward":
                p.go_forward()
                p.bring_to_front()
                self.json_response({"success": True})
                return

            if self.path == "/reload":
                p.reload()
                p.bring_to_front()
                self.json_response({"success": True})
                return

            if self.path == "/click-text":
                text = data.get("text", "").strip()

                if not text:
                    raise Exception("Texto não informado")

                p.get_by_text(text, exact=False).first.click(timeout=15000)
                p.bring_to_front()

                self.json_response({
                    "success": True,
                    "clicked": text
                })
                return

            if self.path == "/type":
                text = data.get("text", "")

                p.keyboard.type(text)
                p.bring_to_front()

                self.json_response({
                    "success": True,
                    "typed": text
                })
                return

            self.json_response({
                "success": False,
                "error": "Rota não encontrada"
            }, 404)

        except Exception as e:
            self.json_response({
                "success": False,
                "error": str(e)
            }, 500)

if __name__ == "__main__":
    print(f"JARVIS Browser Bridge: http://{HOST}:{PORT}")
    print("Bridge local pronto para clientes do JARVIS.")

    server = HTTPServer((HOST, PORT), Handler)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
