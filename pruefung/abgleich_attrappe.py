#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Attrappe der GitHub-Contents-API fuer test_abgleich.py (ab 0.62.4, B-A-02).

BEHELF: Statt api.github.com antwortet dieser kleine HTTP-Server auf
127.0.0.1. Er ahmt genau die Aufrufe nach, die fisi_sync.py macht:
  GET  /repos/<o>/<r>/contents/lernstand.json.gz   (JSON mit sha + base64,
       ab "gross" wie GitHub ab 1 MB: content leer, Rohdaten per Accept raw)
  GET  /repos/<o>/<r>                               (Repo vorhanden?)
  GET  /user                                        (Committer-Name)
  PUT  /repos/<o>/<r>/contents/lernstand.json.gz    (mit sha; falscher sha
       -> 409, fehlender sha bei vorhandener Datei -> 422, wie GitHub)
Kein TLS, kein echtes Token: Die Attrappe prueft nur, dass ein
"Bearer"-Kopf mitkommt. Steuerung fuer Fehlerfaelle ueber
POST /_ctl (JSON), Zustand ueber GET /_state und GET /_log.

Steuerschluessel (POST /_ctl, alle optional, "reset": true setzt alles zurueck):
  get_status      int    HTTP-Code fuer GET contents (z.B. 401, 403, 500)
  repo_status     int    HTTP-Code fuer GET /repos/<o>/<r>
  put_status      int    HTTP-Code fuer PUT (z.B. 409, 422, 500)
  put_status_n    int    nur die naechsten n PUTs mit put_status beantworten
  get_body        str    "abgeschnitten" | "kein_json" | "liste" | "html"
  content_b64     str    eigener Inhalt (base64) statt der gespeicherten Datei
  get_delay       float  Sekunden warten vor der GET-contents-Antwort
  put_hang        str    "vor_speichern" | "nach_speichern": PUT haengt 600 s
  fremd_pro_get   int    nach jedem GET contents legt "ein anderes Geraet"
                         so viele neue Eintraege in die Datei (sha aendert sich)
  gross           bool   content leer + encoding "none" (wie GitHub ab 1 MB)
  datum_versatz   float  Sekunden, um die die Uhrzeit im Date-Kopf von der
                         echten Zeit abweicht (Serverzeit im Test vorgeben)
  ohne_datum      bool   Antworten ganz ohne Date-Kopf

Als Modul: start_server() -> (server, port). Nur 127.0.0.1, keine echten
Zugangsdaten, keine Verbindung nach aussen.
"""

import base64
import copy
import gzip
import hashlib
import json
import sys
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

FILE = "lernstand.json.gz"


class State:
    def __init__(self):
        self.lock = threading.RLock()
        self.reset()

    def reset(self):
        self.raw = None          # gespeicherte Datei (gzip-Bytes)
        self.sha = None
        self.commits = 0
        self.ctl = {}
        self.log = []

    def data(self):
        if self.raw is None:
            return None
        return json.loads(gzip.decompress(self.raw).decode("utf-8"))

    def store(self, raw):
        self.raw = raw
        self.sha = hashlib.sha1(b"blob %d\0" % len(raw) + raw).hexdigest()
        self.commits += 1

    def inject_foreign(self, count):
        """Ein anderes Geraet laedt zwischendurch hoch (neue card_events)."""
        data = self.data()
        if data is None:
            return
        columns = data["columns"]["card_events"]
        rows = data["tables"].setdefault("card_events", [])
        for _ in range(count):
            values = {"timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                      "category": "Fremd", "question": "fremd-%s" % uuid.uuid4().hex[:8],
                      "mode": "karte", "correct": 1}
            rows.append([uuid.uuid4().hex] + [values.get(c) for c in columns])
        payload = gzip.compress(json.dumps(data, ensure_ascii=False,
                                           separators=(",", ":")).encode("utf-8"), mtime=0)
        self.store(payload)


STATE = State()


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def date_time_string(self, timestamp=None):
        if timestamp is None:
            timestamp = time.time() + float(STATE.ctl.get("datum_versatz", 0) or 0)
        return BaseHTTPRequestHandler.date_time_string(self, timestamp)

    def send_response(self, code, message=None):
        if not STATE.ctl.get("ohne_datum"):
            return BaseHTTPRequestHandler.send_response(self, code, message)
        self.log_request(code)
        self.send_response_only(code, message)
        self.send_header("Server", self.version_string())
        return None

    def log_message(self, *args):
        pass

    def _send(self, code, body=b"", ctype="application/json", length=None):
        # Erst protokollieren, dann antworten: Sobald der Client die Antwort
        # hat, steht sie schon in STATE.log (sonst Wettlauf mit dem Test, B-G-28)
        with STATE.lock:
            STATE.log.append((self.command, self.path, code))
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body) if length is None else length))
        self.send_header("Connection", "close")
        self.end_headers()
        try:
            self.wfile.write(body)
            self.wfile.flush()
        except OSError:
            pass
        self.close_connection = True

    def _json(self, code, obj):
        self._send(code, json.dumps(obj).encode("utf-8"))

    def _is_file(self):
        parts = self.path.split("?")[0].strip("/").split("/")
        return len(parts) == 5 and parts[0] == "repos" and parts[3] == "contents" \
            and parts[4] == FILE

    def _is_repo(self):
        parts = self.path.split("?")[0].strip("/").split("/")
        return len(parts) == 3 and parts[0] == "repos"

    def do_GET(self):
        if self.path == "/_state":
            with STATE.lock:
                return self._json(200, {"sha": STATE.sha, "commits": STATE.commits,
                                        "data": STATE.data()})
        if self.path == "/_log":
            with STATE.lock:
                return self._json(200, STATE.log)
        if not self.headers.get("Authorization", "").startswith("Bearer "):
            return self._json(401, {"message": "Bad credentials"})
        ctl = dict(STATE.ctl)
        if self.path == "/user":
            return self._json(200, {"login": "pruef-attrappe", "id": 1})
        if self._is_repo():
            code = ctl.get("repo_status", 200)
            return self._json(code, {"full_name": "x/y"} if code == 200 else
                              {"message": "Not Found"})
        if not self._is_file():
            return self._json(404, {"message": "Not Found"})
        if ctl.get("get_delay"):
            time.sleep(float(ctl["get_delay"]))
        if ctl.get("get_status"):
            return self._json(int(ctl["get_status"]), {"message": "Attrappe"})
        body_kind = ctl.get("get_body")
        if body_kind == "abgeschnitten":
            body = b'{"sha": "abc", "encoding": "base64", "content": "H4sI'
            return self._send(200, body, length=len(body) + 500)
        if body_kind == "kein_json":
            return self._send(200, b"<<< kein JSON >>>")
        if body_kind == "html":
            return self._send(200, b"<html><body>Captive Portal</body></html>",
                              ctype="text/html")
        if body_kind == "liste":
            return self._send(200, b"[1, 2, 3]")
        with STATE.lock:
            raw, sha = STATE.raw, STATE.sha
            if ctl.get("content_b64") is not None:
                raw = base64.b64decode(ctl["content_b64"])
                sha = sha or "0" * 40
            if raw is None:
                return self._json(404, {"message": "Not Found"})
            if "raw" in self.headers.get("Accept", ""):
                result = (200, raw, "application/octet-stream")
            elif ctl.get("gross"):
                result = (200, json.dumps({"sha": sha, "encoding": "none",
                                           "content": "", "size": len(raw)}).encode(),
                          "application/json")
            else:
                b64 = base64.b64encode(raw).decode("ascii")
                # GitHub bricht base64 alle 60 Zeichen um
                b64 = "\n".join(b64[i:i + 60] for i in range(0, len(b64), 60)) + "\n"
                result = (200, json.dumps({"sha": sha, "encoding": "base64",
                                           "content": b64, "size": len(raw)}).encode(),
                          "application/json")
            if ctl.get("fremd_pro_get") and "raw" not in self.headers.get("Accept", ""):
                answer = result
                self._send(*answer[:2], ctype=answer[2])
                STATE.inject_foreign(int(ctl["fremd_pro_get"]))
                return None
        return self._send(result[0], result[1], ctype=result[2])

    def do_POST(self):
        if self.path != "/_ctl":
            return self._json(404, {})
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length) or b"{}")
        with STATE.lock:
            if body.pop("reset", False):
                STATE.reset()
            if body.pop("clear_ctl", False):
                STATE.ctl = {}
            if "set_file" in body:
                STATE.store(base64.b64decode(body.pop("set_file")))
            STATE.ctl.update(body)
        return self._json(200, {"ok": True})

    def do_PUT(self):
        if not self.headers.get("Authorization", "").startswith("Bearer "):
            return self._json(401, {"message": "Bad credentials"})
        if not self._is_file():
            return self._json(404, {"message": "Not Found"})
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length))
        # Steuerwerte unter der Sperre lesen und put_status_n dort
        # herunterzaehlen (gleichzeitige PUTs, ThreadingHTTPServer). Die
        # Antwort geht erst ausserhalb der Sperre raus, und put_hang schlaeft
        # nie unter der Sperre.
        forced = None
        with STATE.lock:
            ctl = STATE.ctl
            if ctl.get("put_status"):
                n = ctl.get("put_status_n")
                if n is None or n > 0:
                    if n is not None:
                        ctl["put_status_n"] = n - 1
                    forced = int(ctl["put_status"])
            hang = ctl.get("put_hang")
        if forced is not None:
            return self._json(forced, {"message": "Attrappe"})
        if hang == "vor_speichern":
            with STATE.lock:
                STATE.log.append(("PUT", self.path, "haengt_vor_speichern"))
            time.sleep(600)
        with STATE.lock:
            if STATE.raw is not None:
                if "sha" not in body:
                    code = 422
                elif body["sha"] != STATE.sha:
                    code = 409
                else:
                    code = 0
            else:
                code = 0
            if code:
                pass
            else:
                STATE.store(base64.b64decode(body["content"]))
                if hang == "nach_speichern":
                    STATE.log.append(("PUT", self.path, "gespeichert_haengt"))
        if code:
            return self._json(code, {"message": "sha does not match" if code == 409
                                     else "Invalid request. \"sha\" wasn't supplied."})
        if hang == "nach_speichern":
            time.sleep(600)
        return self._json(200, {"content": {"sha": STATE.sha}})


def start_server(port=0):
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.daemon_threads = True
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, server.server_address[1]


if __name__ == "__main__":
    port = int(sys.argv[sys.argv.index("--port") + 1]) if "--port" in sys.argv else 0
    srv, real = start_server(port)
    print(real, flush=True)
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        srv.shutdown()
