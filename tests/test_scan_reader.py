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
    "app", Path(__file__).resolve().parents[1] / "web-bt" / "app.py"
)
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)


def test_scan_reader_marks_seen(monkeypatch):
    monkeypatch.setattr(app, "get_info", lambda mac: {})
    app.LAST_SEEN.clear()
    app._scan_reader(["[NEW] Device AA:BB:CC:DD:EE:FF Foo\n"])
    assert "AA:BB:CC:DD:EE:FF" in app.LAST_SEEN
