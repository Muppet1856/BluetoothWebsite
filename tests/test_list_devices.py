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
flask_stub.jsonify = lambda *a, **k: None
flask_stub.request = None
flask_stub.render_template = lambda *a, **k: None
sys.modules.setdefault("flask", flask_stub)

spec = importlib.util.spec_from_file_location(
    "app", Path(__file__).resolve().parents[1] / "web-bt" / "app.py"
)
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)


def test_list_devices_includes_paired(monkeypatch):
    def fake_run_bctl(cmds, timeout=30):
        assert "devices" in cmds
        assert "paired-devices" in cmds
        return 0, "Device AA:BB:CC:DD:EE:FF MySpeaker\n", ""

    monkeypatch.setattr(app, "run_bctl", fake_run_bctl)
    devices = app.list_devices()
    assert devices == [{"mac": "AA:BB:CC:DD:EE:FF", "name": "MySpeaker"}]
