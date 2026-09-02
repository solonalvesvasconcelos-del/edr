"""
main.py - Endpoint Home (APK Kivy)

Um unico app, dois modos, escolhidos na primeira tela:
  - SERVIDOR: sobe o servidor HTTP, recebe reports, mostra IP pra abrir o painel
  - AGENTE:   coleta telemetria e envia ao servidor a cada N segundos

A escolha e o IP do servidor ficam salvos em config JSON no diretorio do app.
Somente dados tecnicos sao coletados. Uma notificacao/tela visivel deixa claro
que o app esta ativo.
"""

import json
import os
import threading
import time
import urllib.request
import uuid

from kivy.app import App
from kivy.clock import Clock, mainthread
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput

import telemetry

try:
    from kivy.utils import platform
    IS_ANDROID = platform == "android"
except Exception:
    IS_ANDROID = False


def app_dir():
    if IS_ANDROID:
        from jnius import autoclass
        ctx = autoclass("org.kivy.android.PythonActivity").mActivity
        return ctx.getFilesDir().getAbsolutePath()
    return os.path.dirname(os.path.abspath(__file__))


CONFIG = os.path.join(app_dir(), "endpoint_config.json")


def load_config():
    try:
        with open(CONFIG) as f:
            return json.load(f)
    except Exception:
        return {}


def save_config(cfg):
    try:
        with open(CONFIG, "w") as f:
            json.dump(cfg, f)
    except Exception:
        pass


def get_device_id(cfg):
    if "device_id" not in cfg:
        cfg["device_id"] = "ep-" + uuid.uuid4().hex[:10]
        save_config(cfg)
    return cfg["device_id"]


AMARELO = (0.976, 0.690, 0.0, 1)
CINZA_BG = (0.10, 0.11, 0.10, 1)
CARD = (0.17, 0.18, 0.17, 1)
TEXT = (0.91, 0.91, 0.90, 1)


class Root(BoxLayout):
    def __init__(self, **kw):
        super().__init__(orientation="vertical", padding=20, spacing=14, **kw)
        self.cfg = load_config()
        self.device_id = get_device_id(self.cfg)
        self.agent_running = False
        self.server_running = False
        self._build_home()

    def _clear(self):
        self.clear_widgets()

    def _title(self, text):
        lbl = Label(text=text, font_size="22sp", bold=True, color=AMARELO,
                    size_hint_y=None, height=50)
        self.add_widget(lbl)

    def _build_home(self):
        self._clear()
        self._title("Endpoint Home")
        self.add_widget(Label(
            text="Escolha o papel deste aparelho.\nSomente dados tecnicos "
                 "sao coletados.",
            color=TEXT, halign="center", size_hint_y=None, height=60))

        b_srv = Button(text="Rodar como SERVIDOR\n(recebe e mostra o painel)",
                       background_color=AMARELO, color=(0, 0, 0, 1),
                       size_hint_y=None, height=90, font_size="16sp")
        b_srv.bind(on_press=lambda *_: self._build_server())
        self.add_widget(b_srv)

        b_ag = Button(text="Rodar como AGENTE\n(coleta e envia)",
                      background_color=CARD, color=TEXT,
                      size_hint_y=None, height=90, font_size="16sp")
        b_ag.bind(on_press=lambda *_: self._build_agent())
        self.add_widget(b_ag)

        self.add_widget(Label(
            text="ID deste dispositivo:\n" + self.device_id,
            color=(0.6, 0.6, 0.6, 1), font_size="11sp",
            halign="center", size_hint_y=None, height=50))

    # ---------------- SERVIDOR ----------------
    def _build_server(self):
        self._clear()
        self._title("Modo Servidor")
        import embedded_server as es
        if not self.server_running:
            storage = os.path.join(app_dir(), "endpoint_devices.json")
            es.start_server(port=8080, storage_path=storage)
            self.server_running = True

        ip = self._local_ip()
        self.add_widget(Label(
            text="Servidor ativo.\n\nAbra no navegador de qualquer\n"
                 "aparelho na mesma rede:",
            color=TEXT, halign="center", size_hint_y=None, height=110))
        self.add_widget(Label(text="http://%s:8080" % ip, color=AMARELO,
                              font_size="20sp", bold=True,
                              size_hint_y=None, height=50))
        self._status_lbl = Label(text="0 dispositivos reportando",
                                 color=(0.6, 0.6, 0.6, 1),
                                 size_hint_y=None, height=40)
        self.add_widget(self._status_lbl)

        back = Button(text="Voltar", size_hint_y=None, height=50,
                      background_color=CARD, color=TEXT)
        back.bind(on_press=lambda *_: self._build_home())
        self.add_widget(back)

        Clock.schedule_interval(self._refresh_server_status, 5)

    def _refresh_server_status(self, *_):
        if not self.server_running:
            return False
        try:
            import embedded_server as es
            n = len(es.list_devices())
            self._status_lbl.text = "%d dispositivo(s) reportando" % n
        except Exception:
            pass

    def _local_ip(self):
        import socket
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    # ---------------- AGENTE ----------------
    def _build_agent(self):
        self._clear()
        self._title("Modo Agente")
        self.add_widget(Label(
            text="URL do servidor (LAN ou nuvem):", color=TEXT,
            size_hint_y=None, height=30))
        self.url_input = TextInput(
            text=self.cfg.get("server_url", "https://SEU-APP.onrender.com"),
            multiline=False, size_hint_y=None, height=44, font_size="15sp")
        self.add_widget(self.url_input)

        self.add_widget(Label(text="Token de autenticacao:", color=TEXT,
                              size_hint_y=None, height=30))
        self.token_input = TextInput(
            text=self.cfg.get("auth_token", ""),
            multiline=False, size_hint_y=None, height=44, font_size="15sp",
            password=True)
        self.add_widget(self.token_input)

        self.add_widget(Label(text="Nome deste aparelho:", color=TEXT,
                              size_hint_y=None, height=30))
        self.name_input = TextInput(
            text=self.cfg.get("device_name", "Meu Aparelho"),
            multiline=False, size_hint_y=None, height=44, font_size="16sp")
        self.add_widget(self.name_input)

        self.agent_status = Label(text="Parado", color=(0.6, 0.6, 0.6, 1),
                                  size_hint_y=None, height=44)
        self.add_widget(self.agent_status)

        self.toggle_btn = Button(text="Iniciar envio", background_color=AMARELO,
                                 color=(0, 0, 0, 1), size_hint_y=None, height=60,
                                 font_size="16sp")
        self.toggle_btn.bind(on_press=self._toggle_agent)
        self.add_widget(self.toggle_btn)

        back = Button(text="Voltar", size_hint_y=None, height=50,
                      background_color=CARD, color=TEXT)
        back.bind(on_press=lambda *_: (self._stop_agent(), self._build_home()))
        self.add_widget(back)

    def _toggle_agent(self, *_):
        if self.agent_running:
            self._stop_agent()
            self.toggle_btn.text = "Iniciar envio"
        else:
            self.cfg["server_url"] = self.url_input.text.strip().rstrip("/")
            self.cfg["auth_token"] = self.token_input.text.strip()
            self.cfg["device_name"] = self.name_input.text.strip()
            save_config(self.cfg)
            self.agent_running = True
            self.toggle_btn.text = "Parar envio"
            threading.Thread(target=self._agent_loop, daemon=True).start()

    def _stop_agent(self):
        self.agent_running = False

    def _agent_loop(self):
        while self.agent_running:
            ok = self._send_once()
            self._set_agent_status(
                "Enviado %s" % time.strftime("%H:%M:%S") if ok
                else "Falha - servidor ligado? mesma rede?")
            for _ in range(60):
                if not self.agent_running:
                    break
                time.sleep(1)

    def _send_once(self):
        try:
            data = telemetry.collect(self.device_id, self.cfg["device_name"])
            url = self.cfg["server_url"] + "/api/report"
            req = urllib.request.Request(
                url, data=json.dumps(data).encode(),
                headers={
                    "Content-Type": "application/json",
                    "X-Auth-Token": self.cfg.get("auth_token", ""),
                })
            urllib.request.urlopen(req, timeout=15)
            return True
        except Exception:
            return False

    @mainthread
    def _set_agent_status(self, text):
        if hasattr(self, "agent_status"):
            self.agent_status.text = text


class EndpointApp(App):
    def build(self):
        from kivy.core.window import Window
        Window.clearcolor = CINZA_BG
        self.title = "Endpoint Home"
        if IS_ANDROID:
            self._request_permissions()
        return Root()

    def _request_permissions(self):
        try:
            from android.permissions import request_permissions, Permission
            request_permissions([
                Permission.ACCESS_WIFI_STATE,
                Permission.ACCESS_NETWORK_STATE,
                Permission.INTERNET,
                Permission.ACCESS_FINE_LOCATION,  # exigido p/ ler SSID no Android 9+
            ])
        except Exception:
            pass


if __name__ == "__main__":
    EndpointApp().run()
