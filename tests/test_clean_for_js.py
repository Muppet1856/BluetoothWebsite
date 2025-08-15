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

clean_for_js = app.clean_for_js


def test_preserves_ansi_escape():
    sample = "\x1b[31mRed\x1b[0m\n"
    assert clean_for_js(sample) == sample
