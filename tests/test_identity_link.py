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
flask_stub.jsonify = lambda *a, **k: k.get("data", a[0] if a else None)
flask_stub.request = types.SimpleNamespace(args={})
flask_stub.render_template = lambda *a, **k: None
sys.modules.setdefault("flask", flask_stub)

spec = importlib.util.spec_from_file_location(
    "app", Path(__file__).resolve().parents[1] / "web-bt" / "app.py"
)
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)


def test_random_device_links_to_fixed(monkeypatch):
    devices_output = (
        "Device AA:AA:AA:AA:AA:01 (random) Foo\n"
        "Device BB:BB:BB:BB:BB:01 Foo\n"
    )

    def fake_run_bctl(cmds, timeout=30):
        if cmds == ["devices", "paired-devices"]:
            return 0, devices_output, ""
        if cmds == ["info AA:AA:AA:AA:AA:01"]:
            return 0, "Identity Address: BB:BB:BB:BB:BB:01 (public)\nAlias: Foo\n", ""
        if cmds == ["info BB:BB:BB:BB:BB:01"]:
            return 0, "Alias: Foo\n", ""
        return 0, "", ""

    monkeypatch.setattr(app, "run_bctl", fake_run_bctl)

    devices = app.list_devices()
    macs = {d["mac"] for d in devices}
    assert {
        "AA:AA:AA:AA:AA:01",
        "BB:BB:BB:BB:BB:01",
    } == macs

    info = app.get_info("AA:AA:AA:AA:AA:01")
    assert info["identity"] == "BB:BB:BB:BB:BB:01"
