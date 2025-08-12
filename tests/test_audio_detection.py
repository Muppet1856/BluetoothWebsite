import importlib.util
import sys
import types
from pathlib import Path

# Create a minimal stub for the flask module to avoid requiring Flask during tests.
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

is_audio_capable = app.is_audio_capable


def test_returns_true_for_audio_uuid():
    info = {"uuids": ["0000110b-0000-1000-8000-00805f9b34fb"]}
    assert is_audio_capable(info) is True


def test_returns_true_for_name_hint():
    info = {"uuids": []}
    assert is_audio_capable(info, name_hint="My SoundLink Device") is True


def test_returns_false_without_hints():
    info = {"uuids": ["1234", "abcd"]}
    assert is_audio_capable(info, name_hint="GenericDevice") is False
