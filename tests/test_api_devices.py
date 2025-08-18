import importlib.util
import sys
import types
from pathlib import Path

# Minimal Flask stub for api_devices tests
flask_stub = types.ModuleType("flask")

class _Flask:
    def __init__(self, *args, **kwargs):
        pass

    def route(self, *args, **kwargs):
        def decorator(func):
            return func
        return decorator

    get = route
    post = route

flask_stub.Flask = _Flask
flask_stub.jsonify = lambda obj=None, **k: obj
flask_stub.request = types.SimpleNamespace(args={})
flask_stub.render_template = lambda *a, **k: None
sys.modules.setdefault("flask", flask_stub)

spec = importlib.util.spec_from_file_location(
    "app", Path(__file__).resolve().parents[1] / "web-bt" / "app.py"
)
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)


def test_api_devices_logs_dropped(monkeypatch, capsys):
    monkeypatch.setattr(
        app, "list_devices", lambda: [{"mac": "AA:BB:CC:DD:EE:FF", "name": "Thing"}]
    )

    def fake_get_info(mac):
        return {
            "alias": "Thing",
            "class": "0x1234",
            "paired": False,
            "connected": False,
        }

    monkeypatch.setattr(app, "get_info", fake_get_info)
    monkeypatch.setattr(app, "is_audio_capable", lambda info: False)

    flask_stub.request.args = {"audio_only": "1"}
    resp = app.api_devices()
    assert resp == {
        "devices": [],
        "dropped": [{"mac": "AA:BB:CC:DD:EE:FF", "name": "Thing", "class": "0x1234"}],
    }
    out = capsys.readouterr().out
    assert "AA:BB:CC:DD:EE:FF" in out
    assert "Thing" in out
    assert "0x1234" in out


def test_api_devices_includes_available(monkeypatch):
    flask_stub.request.args = {"audio_only": "0"}
    monkeypatch.setattr(
        app,
        "list_devices",
        lambda: [
            {"mac": "AA:AA", "name": "Seen", "available": True},
            {"mac": "BB:BB", "name": "Gone", "available": False},
        ],
    )

    def fake_get_info(mac):
        return {"alias": mac, "class": "0x0000", "paired": False, "connected": False}

    monkeypatch.setattr(app, "get_info", fake_get_info)
    monkeypatch.setattr(app, "is_audio_capable", lambda info: True)

    data = app.api_devices()
    avail = {d["mac"]: d["available"] for d in data["devices"]}
    assert avail["AA:AA"] is True
    assert avail["BB:BB"] is False
