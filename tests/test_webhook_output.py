import importlib.util
import sys
import types
from pathlib import Path

# Minimal Flask stub for webhook tests
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
flask_stub.request = types.SimpleNamespace(headers={}, data=b"")
flask_stub.render_template = lambda *a, **k: None
sys.modules.setdefault("flask", flask_stub)

spec = importlib.util.spec_from_file_location(
    "app", Path(__file__).resolve().parents[1] / "web-bt" / "app.py"
)
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)

def test_webhook_returns_script_output(monkeypatch):
    def fake_run(cmd, *a, **k):
        assert cmd == ["bash", app.DEFAULT_WEBHOOK_SCRIPT]
        class Dummy:
            returncode = 0
            stdout = "deploy ok\n"
            stderr = ""
        return Dummy()
    monkeypatch.setattr(app.subprocess, "run", fake_run)
    req = types.SimpleNamespace(headers={"X-GitHub-Event": "push"}, data=b"")
    monkeypatch.setattr(app, "request", req)
    resp, code = app.github_webhook()
    assert code == 200
    assert resp == {"ok": True, "stdout": "deploy ok\n", "stderr": ""}


def test_webhook_handles_script_failure(monkeypatch):
    def fake_run(cmd, *a, **k):
        assert cmd == ["bash", app.DEFAULT_WEBHOOK_SCRIPT]
        class Dummy:
            returncode = 1
            stdout = ""
            stderr = "boom\n"
        return Dummy()
    monkeypatch.setattr(app.subprocess, "run", fake_run)
    req = types.SimpleNamespace(headers={"X-GitHub-Event": "push"}, data=b"")
    monkeypatch.setattr(app, "request", req)
    resp, code = app.github_webhook()
    assert code == 200
    assert resp == {"ok": False, "stdout": "", "stderr": "boom\n"}
