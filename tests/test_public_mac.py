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

    get = route
    post = route

flask_stub.Flask = _Flask
flask_stub.jsonify = lambda obj=None, **k: obj
flask_stub.request = types.SimpleNamespace(args={})
flask_stub.render_template = lambda *a, **k: None
sys.modules.setdefault("flask", flask_stub)

spec = importlib.util.spec_from_file_location(
    "app", Path(__file__).resolve().parents[1] / "web-bt" / "app.py",
)
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)


def test_random_address_replaced_with_identity(monkeypatch):
    monkeypatch.setattr(
        app,
        "list_devices",
        lambda: [{"mac": "AA:AA:AA:AA:AA:01", "name": "Foo", "type": "random"}],
    )

    def fake_get_info(mac):
        return {
            "alias": "Foo",
            "class": "0x000400",
            "paired": False,
            "connected": False,
            "identity": "BB:BB:BB:BB:BB:01",
        }

    monkeypatch.setattr(app, "get_info", fake_get_info)
    flask_stub.request.args = {"audio_only": "0"}
    data = app.api_devices()
    assert data["devices"][0]["mac"] == "BB:BB:BB:BB:BB:01"
