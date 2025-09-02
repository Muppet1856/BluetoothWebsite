import importlib.util
import sys
import types
from pathlib import Path

# Minimal Flask stub
flask_stub = types.ModuleType("flask")

class _Flask:
    def __init__(self, *args, **kwargs):
        pass

    def route(self, *args, **kwargs):
        def decorator(func):
            return func
        return decorator

    get = post = route

flask_stub.Flask = _Flask
flask_stub.jsonify = lambda obj=None, **k: obj
flask_stub.request = types.SimpleNamespace(json={}, args={})
flask_stub.render_template = lambda *a, **k: None
sys.modules.setdefault("flask", flask_stub)

# Load the application module
spec = importlib.util.spec_from_file_location(
    "app", Path(__file__).resolve().parents[1] / "web-bt" / "app.py"
)
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)


def test_api_ap_get(monkeypatch):
    monkeypatch.setattr(app, "read_ap_ssid", lambda: "TestAP")
    assert app.api_ap_get() == {"ssid": "TestAP"}


def test_api_ap_set(monkeypatch):
    called = {}

    def fake_set(ssid):
        called["ssid"] = ssid

    monkeypatch.setattr(app, "set_ap_ssid", fake_set)
    flask_stub.request.json = {"ssid": "NewAP"}
    app.request.json = flask_stub.request.json
    resp = app.api_ap_set()
    assert resp == {"ok": True, "ssid": "NewAP"}
    assert called["ssid"] == "NewAP"


def test_api_wifi_list(monkeypatch):
    monkeypatch.setattr(app, "list_client_networks", lambda: (["a", "b"], True))
    assert app.api_wifi_list() == {"networks": ["a", "b"], "has_wifi": True}


def test_api_wifi_list_no_iface(monkeypatch):
    monkeypatch.setattr(app, "list_client_networks", lambda: ([], False))
    assert app.api_wifi_list() == {"networks": [], "has_wifi": False}


def test_api_wifi_connect(monkeypatch):
    called = {}

    def fake_connect(ssid):
        called["ssid"] = ssid

    monkeypatch.setattr(app, "connect_client", fake_connect)
    flask_stub.request.json = {"ssid": "Net1"}
    app.request.json = flask_stub.request.json
    resp = app.api_wifi_connect()
    assert resp == {"ok": True, "ssid": "Net1"}
    assert called["ssid"] == "Net1"


def test_api_wifi_info(monkeypatch):
    monkeypatch.setattr(
        app,
        "get_client_ip_info",
        lambda: {"ip": "1.2.3.4", "mask": "255.255.255.0", "gateway": "1.2.3.1"},
    )
    assert app.api_wifi_info() == {
        "ip": "1.2.3.4",
        "mask": "255.255.255.0",
        "gateway": "1.2.3.1",
    }


def test_index_contains_wifi_controls():
    index = Path(__file__).resolve().parents[1] / "web-bt" / "templates" / "index.html"
    html = index.read_text()
    assert 'id="apSsid"' in html
    assert 'id="scanWifiBtn"' in html
    assert 'id="wifiList"' in html
    assert 'id="wifiInfo"' in html
