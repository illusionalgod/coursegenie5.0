import openai
import importlib.util
import runpy
import types
import os

# Load test module source and avoid top-level dependency on pytest by
# wrapping its import in a try/except if pytest is missing.
test_path = os.path.join(os.path.dirname(__file__), 'test_chatbot_local.py')
with open(test_path, 'r', encoding='utf-8') as f:
    src = f.read()

# Replace a bare `import pytest` with a safe import
src = src.replace("import pytest", "try:\n    import pytest\nexcept Exception:\n    pytest = None")

# If pytest isn't available, remove the fixture decorator usage so the module
# can be executed directly. Replace the decorated fixture definition with a
# plain function signature.
src = src.replace("@pytest.fixture(autouse=True)\ndef patch_openai(monkeypatch):", "def patch_openai(monkeypatch=None):")

# Execute the modified source in a new module namespace
mod = types.ModuleType('test_chatbot_local_mod')
exec(compile(src, test_path, 'exec'), mod.__dict__)

# Patch openai with the fake helpers from the loaded module
openai.ChatCompletion.create = mod.fake_chat_completion_create
openai.Moderation.create = mod.fake_moderation_create

results = []

for name in ('test_get_response', 'test_get_moderation', 'test_chat_route', 'test_clear_chat', 'test_api_chat'):
    try:
        getattr(mod, name)()
        print(f"{name}: PASS")
        results.append((name, True, None))
    except AssertionError as e:
        print(f"{name}: FAIL - {e}")
        results.append((name, False, str(e)))
    except Exception as exc:
        print(f"{name}: ERROR - {exc}")
        results.append((name, False, str(exc)))

# Exit code 0 if all passed, 1 otherwise
if all(r[1] for r in results):
    raise SystemExit(0)
else:
    raise SystemExit(1)
