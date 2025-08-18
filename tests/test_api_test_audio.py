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
flask_stub.request = types.SimpleNamespace(json={})
flask_stub.render_template = lambda *a, **k: None
sys.modules.setdefault("flask", flask_stub)

spec = importlib.util.spec_from_file_location(
    "app", Path(__file__).resolve().parents[1] / "web-bt" / "app.py",
)
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)


def test_api_test_audio_uses_aplay(monkeypatch):
    called = {}

    def fake_run(args, stdout=None, stderr=None, timeout=None):
        called["args"] = args
        class P:
            returncode = 0
            stdout = b"front center"
        return P()

    monkeypatch.setattr(app.subprocess, "run", fake_run)
    resp = app.api_test_audio()
    assert resp["ok"] is True
    assert called["args"][0] == "aplay"
    assert "/usr/share/sounds/alsa/Front_Center.wav" in called["args"]
