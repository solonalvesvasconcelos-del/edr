"""
embedded_server.py - servidor HTTP em stdlib (sem Flask).

Roda dentro do APK no modo Servidor. Recebe POST dos agentes em /api/report,
serve o dashboard em / e a lista em /api/devices. Dados em memoria +
persistencia simples em JSON no diretorio do app.

Mantido em stdlib de proposito: menos dependencias = APK menor e build
mais confiavel no Buildozer.
"""

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

OFFLINE_AFTER = 180

_lock = threading.Lock()
_devices = {}          # device_id -> {name, last_seen, report}
_storage_path = None   # setado por start_server


def _persist():
    if not _storage_path:
        return
    try:
        with open(_storage_path, "w") as f:
            json.dump(_devices, f)
    except Exception:
        pass


def _load():
    global _devices
    if not _storage_path:
        return
    try:
        with open(_storage_path) as f:
            _devices = json.load(f)
    except Exception:
        _devices = {}


def ingest(data):
    device_id = data.get("device_id")
    if not device_id:
        return False
    with _lock:
        _devices[device_id] = {
            "name": data.get("name", device_id),
            "last_seen": time.time(),
            "report": data,
        }
        _persist()
    return True


def list_devices():
    now = time.time()
    out = []
    with _lock:
        for did, d in _devices.items():
            out.append({
                "device_id": did,
                "name": d["name"],
                "online": (now - d["last_seen"]) < OFFLINE_AFTER,
                "last_seen_ago": int(now - d["last_seen"]),
                "report": d["report"],
            })
    out.sort(key=lambda x: x["name"])
    return out


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass  # silencia log no console do app

    def _json(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/" or self.path.startswith("/index"):
            body = DASHBOARD_HTML.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/api/devices":
            self._json(list_devices())
        else:
            self._json({"error": "not found"}, 404)

    def do_POST(self):
        if self.path == "/api/report":
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length) if length else b"{}"
            try:
                data = json.loads(raw)
            except Exception:
                self._json({"error": "json invalido"}, 400)
                return
            ok = ingest(data)
            self._json({"ok": ok})
        else:
            self._json({"error": "not found"}, 404)


_httpd = None


def start_server(port=8080, storage_path=None):
    """Inicia o servidor numa thread. Retorna a instancia."""
    global _httpd, _storage_path
    _storage_path = storage_path
    _load()
    _httpd = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    t = threading.Thread(target=_httpd.serve_forever, daemon=True)
    t.start()
    return _httpd


def stop_server():
    global _httpd
    if _httpd:
        _httpd.shutdown()
        _httpd = None


DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Endpoint Home</title><style>
:root{--amarelo:#F9B000;--bg:#1a1c1a;--card-bg:#2b2e2b;--online:#3ecf6b;
--offline:#6b6e6b;--text:#e8e8e6;--muted:#9a9d99;}
*{box-sizing:border-box;margin:0;padding:0;}
body{font-family:-apple-system,"Segoe UI",Roboto,sans-serif;background:var(--bg);
color:var(--text);padding:16px;max-width:900px;margin:0 auto;}
header{display:flex;align-items:center;gap:12px;padding-bottom:16px;
border-bottom:2px solid var(--amarelo);margin-bottom:20px;}
header .dot{width:12px;height:12px;border-radius:50%;background:var(--amarelo);}
h1{font-size:20px;font-weight:600;}h1 span{color:var(--amarelo);}
.sub{color:var(--muted);font-size:12px;margin-top:2px;}
.grid{display:grid;gap:14px;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));}
.card{background:var(--card-bg);border-radius:12px;padding:16px;border:1px solid #ffffff10;}
.card-head{display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;}
.card-head .name{font-weight:600;font-size:15px;}
.status{display:flex;align-items:center;gap:6px;font-size:12px;}
.status .dot{width:8px;height:8px;border-radius:50%;}
.status.online .dot{background:var(--online);box-shadow:0 0 8px var(--online);}
.status.offline .dot{background:var(--offline);}
.status.online{color:var(--online);}.status.offline{color:var(--offline);}
.battery{display:flex;align-items:center;gap:10px;margin:10px 0;}
.batt-bar{flex:1;height:8px;border-radius:4px;background:#ffffff15;overflow:hidden;}
.batt-fill{height:100%;border-radius:4px;transition:width .4s;}
.rows{font-size:13px;}
.row{display:flex;justify-content:space-between;padding:5px 0;border-top:1px solid #ffffff08;}
.row .k{color:var(--muted);}.row .v{font-weight:500;text-align:right;}
.empty{text-align:center;color:var(--muted);padding:60px 20px;grid-column:1/-1;}
footer{text-align:center;color:var(--muted);font-size:11px;margin-top:24px;}
</style></head><body>
<header><div class="dot"></div><div>
<h1>Endpoint <span>Home</span></h1>
<div class="sub">Telemetria de dispositivo &middot; somente dados tecnicos</div>
</div></header>
<div id="grid" class="grid"><div class="empty">Aguardando dispositivos...</div></div>
<footer>Atualiza a cada 15s &middot; sem coleta de conteudo pessoal</footer>
<script>
function battColor(p){if(p==null)return'#6b6e6b';if(p<=15)return'#e74c3c';
if(p<=35)return'#F9B000';return'#3ecf6b';}
function ago(s){if(s<60)return s+'s atras';if(s<3600)return Math.floor(s/60)+'min atras';
return Math.floor(s/3600)+'h atras';}
function fmtB(mb){if(mb==null)return'-';if(mb>=1024)return(mb/1024).toFixed(1)+' GB';
return mb+' MB';}
async function load(){try{const r=await fetch('/api/devices');const devs=await r.json();
const g=document.getElementById('grid');
if(!devs.length){g.innerHTML='<div class="empty">Aguardando dispositivos...</div>';return;}
g.innerHTML=devs.map(d=>{const rep=d.report||{},b=rep.battery||{},w=rep.wifi||{},
s=rep.storage||{},dv=rep.device||{},apps=rep.apps||[],pct=b.percentage;
return `<div class="card"><div class="card-head"><div class="name">${d.name}</div>
<div class="status ${d.online?'online':'offline'}"><div class="dot"></div>
${d.online?'Online':'Offline'}</div></div>
<div class="battery"><span style="font-size:13px">Bateria</span>
<div class="batt-bar"><div class="batt-fill" style="width:${pct??0}%;
background:${battColor(pct)}"></div></div><strong>${pct!=null?pct+'%':'-'}</strong></div>
<div class="rows">
<div class="row"><span class="k">Carregando</span><span class="v">${b.charging?'Sim':'Nao'}</span></div>
<div class="row"><span class="k">Wi-Fi</span><span class="v">${w.ssid||'-'}</span></div>
<div class="row"><span class="k">IP</span><span class="v">${w.ip||'-'}</span></div>
<div class="row"><span class="k">Storage livre</span><span class="v">${fmtB(s.free_mb)}</span></div>
<div class="row"><span class="k">Modelo</span><span class="v">${dv.model||'-'}</span></div>
<div class="row"><span class="k">Android</span><span class="v">${dv.android||'-'}</span></div>
<div class="row"><span class="k">Ultimo report</span><span class="v">${ago(d.last_seen_ago)}</span></div>
<div class="row"><span class="k">Apps</span><span class="v">${apps.length||'-'}</span></div>
</div></div>`;}).join('');}catch(e){console.error(e);}}
load();setInterval(load,15000);
</script></body></html>"""
