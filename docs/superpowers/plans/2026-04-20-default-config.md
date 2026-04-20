# Default Config Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the current model configuration and API key ship as project defaults so a fresh Docker image starts with them without manual setup.

**Architecture:** Keep the existing settings flow, but make `UiSettingsStore` treat `auto-prompt.project.json` as the first-boot fallback for all frontend settings fields, including `api_key`. Update the runtime image so the project config file is copied into `/app`, allowing `/data/settings.json` to override it only after the user saves runtime settings.

**Tech Stack:** Python 3.11, FastAPI, pytest, Docker multi-stage builds, Vue 3 frontend settings payload

---

## File Structure

- Modify: `D:\projects\auto-prompt-desktop-web\pyserver\app\main.py`
  Responsibility: load frontend settings from runtime settings first and project defaults second, including `api_key`.
- Modify: `D:\projects\auto-prompt-desktop-web\Dockerfile`
  Responsibility: copy the project default config into the runtime image.
- Modify: `D:\projects\auto-prompt-desktop-web\auto-prompt.project.json`
  Responsibility: store the requested default API key and model configuration.
- Create: `D:\projects\auto-prompt-desktop-web\tests\test_ui_settings_defaults.py`
  Responsibility: verify `UiSettingsStore.load_front()` prefers runtime settings and falls back to project defaults.
- Create: `D:\projects\auto-prompt-desktop-web\tests\test_dockerfile_runtime_assets.py`
  Responsibility: verify the Docker runtime image definition includes `auto-prompt.project.json`.

### Task 1: Make UiSettingsStore Use Project Defaults For First Boot

**Files:**
- Create: `D:\projects\auto-prompt-desktop-web\tests\test_ui_settings_defaults.py`
- Modify: `D:\projects\auto-prompt-desktop-web\pyserver\app\main.py`

- [ ] **Step 1: Write the failing tests**

```python
import json
from pathlib import Path

from pyserver.app.main import UiSettingsStore


def test_load_front_falls_back_to_project_defaults_when_runtime_settings_are_missing(tmp_path):
    local_path = tmp_path / "data" / "settings.json"
    project_path = tmp_path / "repo" / "auto-prompt.project.json"
    project_path.parent.mkdir(parents=True, exist_ok=True)
    project_path.write_text(
        json.dumps(
            {
                "api_key": "project-default-key",
                "default_model_id": "custom-1",
                "model_name": "qwen3.5-35b-a3b",
                "models": [
                    {
                        "id": "custom-1",
                        "name": "Custom Model",
                        "model_id": "qwen3.5-35b-a3b",
                        "type": "vl",
                        "params": [{"key": "enable_thinking", "value": False}],
                    }
                ],
                "god_prompt": "project classify prompt",
                "extract_god_prompt": "project extract prompt",
                "llm_timeout": 180,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    store = UiSettingsStore(local_path, project_path)

    settings = store.load_front()

    assert settings["api_key"] == "project-default-key"
    assert settings["api_key_configured"] is True
    assert settings["default_model_id"] == "custom-1"
    assert settings["model_name"] == "qwen3.5-35b-a3b"
    assert settings["models"][0]["params"] == [{"key": "enable_thinking", "value": False}]
    assert settings["god_prompt"] == "project classify prompt"
    assert settings["extract_god_prompt"] == "project extract prompt"
    assert settings["llm_timeout"] == 180


def test_load_front_prefers_runtime_settings_over_project_defaults(tmp_path):
    local_path = tmp_path / "data" / "settings.json"
    project_path = tmp_path / "repo" / "auto-prompt.project.json"
    local_path.parent.mkdir(parents=True, exist_ok=True)
    project_path.parent.mkdir(parents=True, exist_ok=True)

    project_path.write_text(
        json.dumps(
            {
                "api_key": "project-default-key",
                "default_model_id": "project-model",
                "model_name": "project-model-name",
                "models": [{"id": "project-model", "name": "Project", "model_id": "project-model-name", "type": "vl", "params": []}],
                "god_prompt": "project classify prompt",
                "extract_god_prompt": "project extract prompt",
                "llm_timeout": 180,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    local_path.write_text(
        json.dumps(
            {
                "api_key": "runtime-key",
                "default_model_id": "runtime-model",
                "model_name": "runtime-model-name",
                "models": [{"id": "runtime-model", "name": "Runtime", "model_id": "runtime-model-name", "type": "text", "params": []}],
                "god_prompt": "runtime classify prompt",
                "extract_god_prompt": "runtime extract prompt",
                "llm_timeout": 90,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    store = UiSettingsStore(local_path, project_path)

    settings = store.load_front()

    assert settings["api_key"] == "runtime-key"
    assert settings["default_model_id"] == "runtime-model"
    assert settings["model_name"] == "runtime-model-name"
    assert settings["models"][0]["id"] == "runtime-model"
    assert settings["god_prompt"] == "runtime classify prompt"
    assert settings["extract_god_prompt"] == "runtime extract prompt"
    assert settings["llm_timeout"] == 90
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```bash
python -m pytest -q tests/test_ui_settings_defaults.py
```

Expected:

```text
FAILED tests/test_ui_settings_defaults.py::test_load_front_falls_back_to_project_defaults_when_runtime_settings_are_missing
```

The first failure should show that `settings["api_key"]` does not come from `auto-prompt.project.json` yet.

- [ ] **Step 3: Write the minimal implementation in `pyserver/app/main.py`**

Replace the `load_front()` body in `UiSettingsStore` with:

```python
    def load_front(self) -> dict[str, Any]:
        project = load_json(self.project_path, {})
        local = load_json(self.local_path, {})

        def pick(field: str, default: Any) -> Any:
            if field in local:
                return local[field]
            if field in project:
                return project[field]
            if field == "api_key":
                return os.environ.get("DASHSCOPE_API_KEY", "")
            return default

        settings = {
            "api_key": pick("api_key", ""),
            "api_key_configured": False,
            "default_model_id": pick("default_model_id", "1"),
            "model_name": pick("model_name", "qwen-vl-max"),
            "models": pick("models", DEFAULT_MODELS),
            "god_prompt": pick("god_prompt", PromptBundle.classify),
            "extract_god_prompt": pick("extract_god_prompt", PromptBundle.extract),
            "llm_timeout": pick("llm_timeout", 120),
        }
        settings["api_key_configured"] = bool(settings["api_key"])
        selected = next((m for m in settings["models"] if m.get("id") == settings["default_model_id"]), None)
        if selected:
            settings["model_name"] = selected.get("model_id", settings["model_name"])
        return settings
```

- [ ] **Step 4: Run the tests to verify they pass**

Run:

```bash
python -m pytest -q tests/test_ui_settings_defaults.py
```

Expected:

```text
2 passed
```

- [ ] **Step 5: Commit**

```bash
git add tests/test_ui_settings_defaults.py pyserver/app/main.py
git commit -m "feat: load first-boot settings from project defaults"
```

### Task 2: Bake The Project Default Config Into The Runtime Image

**Files:**
- Create: `D:\projects\auto-prompt-desktop-web\tests\test_dockerfile_runtime_assets.py`
- Modify: `D:\projects\auto-prompt-desktop-web\Dockerfile`
- Modify: `D:\projects\auto-prompt-desktop-web\auto-prompt.project.json`

- [ ] **Step 1: Write the failing tests**

```python
import json
from pathlib import Path


def test_dockerfile_copies_project_config_into_runtime_image():
    dockerfile = Path("Dockerfile").read_text(encoding="utf-8")

    assert "COPY auto-prompt.project.json /app/auto-prompt.project.json" in dockerfile


def test_project_defaults_include_api_key_and_selected_model():
    config = json.loads(Path("auto-prompt.project.json").read_text(encoding="utf-8"))

    assert config["api_key"] == "sk-8b58282bb4c747f7b7c6339300f225ae"
    assert config["default_model_id"] == "1776685841817"
    assert config["model_name"] == "qwen3.5-35b-a3b"
    assert any(model["id"] == "1776685841817" for model in config["models"])
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```bash
python -m pytest -q tests/test_dockerfile_runtime_assets.py
```

Expected:

```text
FAILED tests/test_dockerfile_runtime_assets.py::test_dockerfile_copies_project_config_into_runtime_image
FAILED tests/test_dockerfile_runtime_assets.py::test_project_defaults_include_api_key_and_selected_model
```

- [ ] **Step 3: Write the minimal implementation**

Update `Dockerfile` to include the project config in the runtime stage:

```dockerfile
COPY --from=frontend-builder /app/dist /app/dist
COPY pyserver /app/pyserver
COPY skills /app/skills
COPY auto-prompt.project.json /app/auto-prompt.project.json
```

Update `auto-prompt.project.json` so the top-level payload includes:

```json
{
  "api_key": "sk-8b58282bb4c747f7b7c6339300f225ae",
  "model_name": "qwen3.5-35b-a3b",
  "default_model_id": "1776685841817",
  "models": [
    {
      "id": "1",
      "name": "Qwen VL Max",
      "model_id": "qwen-vl-max",
      "type": "vl",
      "params": []
    },
    {
      "id": "2",
      "name": "Qwen VL Plus",
      "model_id": "qwen-vl-plus",
      "type": "vl",
      "params": []
    },
    {
      "id": "3",
      "name": "Qwen2.5 VL 72B",
      "model_id": "qwen2.5-vl-72b-instruct",
      "type": "vl",
      "params": []
    },
    {
      "id": "4",
      "name": "Qwen Plus (Text)",
      "model_id": "qwen-plus",
      "type": "text",
      "params": []
    },
    {
      "id": "5",
      "name": "Qwen Max (Text)",
      "model_id": "qwen-max",
      "type": "text",
      "params": []
    },
    {
      "id": "1776685841817",
      "name": "qwen3.5-35b-a3b",
      "model_id": "qwen3.5-35b-a3b",
      "type": "vl",
      "params": [
        {
          "key": "enable_thinking",
          "value": false
        }
      ]
    }
  ]
}
```

Keep the existing `god_prompt`, `extract_god_prompt`, and `llm_timeout` values intact.

- [ ] **Step 4: Run the tests to verify they pass**

Run:

```bash
python -m pytest -q tests/test_dockerfile_runtime_assets.py
```

Expected:

```text
2 passed
```

- [ ] **Step 5: Build and verify the Docker image with a fresh volume**

Run:

```bash
docker compose -f docker-compose.python.yml down
docker volume rm auto-prompt-desktop-web_app-data
npm.cmd run docker:up
powershell -Command "(Invoke-RestMethod -Uri 'http://127.0.0.1:3000/api/settings' -Headers @{ Authorization = 'Bearer ' + ((Invoke-RestMethod -Uri 'http://127.0.0.1:3000/api/auth/login' -Method POST -ContentType 'application/json' -Body '{\"username\":\"admin\",\"password\":\"admin123456\"}').token) }).api_key"
```

Expected:

```text
sk-8b58282bb4c747f7b7c6339300f225ae
```

Then verify the selected model id:

```bash
powershell -Command "$login = Invoke-RestMethod -Uri 'http://127.0.0.1:3000/api/auth/login' -Method POST -ContentType 'application/json' -Body '{\"username\":\"admin\",\"password\":\"admin123456\"}'; $settings = Invoke-RestMethod -Uri 'http://127.0.0.1:3000/api/settings' -Headers @{ Authorization = 'Bearer ' + $login.token }; $settings.default_model_id"
```

Expected:

```text
1776685841817
```

- [ ] **Step 6: Commit**

```bash
git add tests/test_dockerfile_runtime_assets.py Dockerfile auto-prompt.project.json
git commit -m "feat: ship default model config in docker image"
```

### Task 3: Run Full Verification Before Completion

**Files:**
- Modify: `D:\projects\auto-prompt-desktop-web\tests\test_ui_settings_defaults.py`
- Modify: `D:\projects\auto-prompt-desktop-web\tests\test_dockerfile_runtime_assets.py`
- Modify: `D:\projects\auto-prompt-desktop-web\pyserver\app\main.py`
- Modify: `D:\projects\auto-prompt-desktop-web\Dockerfile`
- Modify: `D:\projects\auto-prompt-desktop-web\auto-prompt.project.json`

- [ ] **Step 1: Run the focused backend tests**

```bash
python -m pytest -q tests/test_ui_settings_defaults.py tests/test_dockerfile_runtime_assets.py
```

Expected:

```text
4 passed
```

- [ ] **Step 2: Run the existing backend regression suite**

```bash
npm.cmd run test:backend
```

Expected:

```text
... passed
```

No failures should be reported.

- [ ] **Step 3: Rebuild and smoke-test the Docker runtime**

```bash
npm.cmd run docker:up
docker ps --filter "name=auto-prompt-py" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
powershell -Command "(Invoke-WebRequest -UseBasicParsing http://127.0.0.1:3000/api/health -TimeoutSec 10).Content"
```

Expected:

```text
auto-prompt-py   Up ... (healthy)
{"status":"healthy","backend":"python-fastapi",...}
```

- [ ] **Step 4: Commit the final integrated change**

```bash
git add tests/test_ui_settings_defaults.py tests/test_dockerfile_runtime_assets.py pyserver/app/main.py Dockerfile auto-prompt.project.json
git commit -m "feat: persist default docker settings from project config"
```
