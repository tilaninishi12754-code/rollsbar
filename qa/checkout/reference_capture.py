"""Render immutable Visual B16 source locally; no current baseline is updated."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import subprocess
import threading
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[2]
SHA='5e7836e22110ec076603bb1fa2b12f8bb90ee756'
SOURCE=subprocess.check_output(['git','show',SHA+':index.html'],cwd=ROOT)
OUT=ROOT/'qa/visual-results/checkout-parity'


class Handler(SimpleHTTPRequestHandler):
    def log_message(self,*args):pass
    def do_GET(self):
        if self.path=='/reference.html':
            self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.end_headers();self.wfile.write(SOURCE)
        else:super().do_GET()


server=ThreadingHTTPServer(('127.0.0.1',0),partial(Handler,directory=str(ROOT)))
threading.Thread(target=server.serve_forever,daemon=True).start()
try:
    OUT.mkdir(parents=True,exist_ok=True)
    with sync_playwright() as pw:
        browser=pw.chromium.launch(channel='chrome',headless=True)
        try:
            page=browser.new_page(viewport={'width':1440,'height':1000})
            page.goto(f'http://127.0.0.1:{server.server_port}/reference.html')
            page.evaluate("document.querySelector('#checkoutModal').classList.add('open');document.querySelector('#checkoutModal').setAttribute('aria-hidden','false')")
            for width in [1440,700,320]:
                page.set_viewport_size({'width':width,'height':1000 if width>700 else 844})
                page.screenshot(path=str(OUT/f'reference-b16-{width}.png'))
        finally:browser.close()
finally:server.shutdown();server.server_close()
