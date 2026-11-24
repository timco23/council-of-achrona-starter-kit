"""Debatviewer: toont trace.json en verdict.json live in je browser, als zitting in de raadszaal.

Start met `uv run viewer` (leest de root van deze repo) of `uv run viewer <map-of-trace.json>`.
Poort via VIEWER_PORT (standaard 8100).
"""
import http.server
import os
import sys
import webbrowser
from pathlib import Path

ROOT = Path(__file__).parent


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    doel = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT
    map_ = doel.parent if doel.is_file() else doel
    port = int(os.getenv("VIEWER_PORT", "8100"))

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            pad = self.path.split("?")[0]
            if pad in ("/", "/index.html"):
                return self.stuur(ROOT / "viewer.html", "text/html; charset=utf-8")
            if pad in ("/trace.json", "/verdict.json"):
                return self.stuur(map_ / pad[1:], "application/json; charset=utf-8")
            # Renders uit visualisatie/renders (avatars, raadszaal, feest, schermposities van de figuren);
            # alleen .png en .json met een eenvoudige naam.
            naam = pad.removeprefix("/beelden/")
            soort = {"png": "image/png", "json": "application/json; charset=utf-8"}.get(naam.rsplit(".", 1)[-1])
            if pad.startswith("/beelden/") and soort and naam.count(".") == 1 and naam.replace("_", "").replace(".", "").isalnum():
                return self.stuur(ROOT / "visualisatie" / "renders" / naam, soort, cache=soort == "image/png")
            # De 3D-zaal (three.js): visualisatie/web/zaal.glb, scene.json en figuren/<model>.glb.
            if pad.startswith("/3d/"):
                delen = pad.removeprefix("/3d/").split("/")
                soort = {"glb": "model/gltf-binary", "json": "application/json; charset=utf-8"}.get(delen[-1].rsplit(".", 1)[-1])
                if soort and len(delen) <= 2 and all(d and d.replace("_", "").replace(".", "").isalnum() and d.count(".") <= 1 for d in delen):
                    return self.stuur(ROOT / "visualisatie" / "web" / Path(*delen), soort, cache=soort == "model/gltf-binary")
            self.send_error(404)

        def stuur(self, bestand, soort, cache=False):
            if not bestand.exists():
                return self.send_error(404)
            data = bestand.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", soort)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "max-age=3600" if cache else "no-store")
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *args):
            pass

    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), Handler)
    url = f"http://127.0.0.1:{port}/"
    print(f"Debatviewer op {url} (leest {map_}). Stop met Ctrl+C.")
    webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
