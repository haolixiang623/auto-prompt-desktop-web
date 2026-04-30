import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from pyserver.app import main


def make_settings():
    return {
        "api_key": "fallback-key",
        "model_name": "default-model",
        "default_model_id": "default",
        "extract_god_prompt": "extract-god",
        "god_prompt": "classify-god",
        "llm_timeout": 120,
        "models": [
            {
                "id": "default",
                "name": "Default",
                "model": "default-model",
                "base_url": "https://default.example/v1",
                "api_key": "",
                "type": "vl",
                "params": [],
            },
            {
                "id": "fast",
                "name": "Fast",
                "model": "fast-model",
                "base_url": "https://fast.example/v1",
                "api_key": "fast-key",
                "type": "vl",
                "params": [
                    {"key": "enable_thinking", "value": False},
                    {"key": "thinking_budget", "value": 128},
                ],
            },
        ],
    }


def test_run_generate_prompt_uses_selected_model_and_extra_params(tmp_path, monkeypatch):
    work_dir = tmp_path / "workspace"
    material_dir = work_dir / "营业证照"
    material_dir.mkdir(parents=True)
    (material_dir / "sample.jpg").write_bytes(b"fake-image")
    expected_prompt = "生成后的提示词"
    generated_prompt_path = material_dir / "营业证照--要素提取完整提示词.txt"
    generated_prompt_path.write_text(expected_prompt, encoding="utf-8")

    captured = {}

    def fake_subprocess_run(args, **kwargs):
        captured["args"] = args
        captured["env"] = kwargs["env"]
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(main.subprocess, "run", fake_subprocess_run)
    monkeypatch.setattr(main, "_resolve_user_id_from_work_dir", lambda *_args, **_kwargs: "user-1")
    monkeypatch.setattr(main, "read_factors_script", lambda *_args, **_kwargs: [{"field_name": "姓名"}])

    paths = SimpleNamespace(
        skills_dir=tmp_path / "skills",
        user_output_root=tmp_path / "outputs",
    )

    result = main.run_generate_prompt(
        paths,
        make_settings(),
        str(work_dir),
        "营业证照",
        model_cfg_id="fast",
    )

    assert captured["env"]["MODEL_NAME"] == "fast-model"
    assert captured["env"]["OPENAI_API_KEY"] == "fast-key"
    assert captured["env"]["OPENAI_BASE_URL"] == "https://fast.example/v1"
    assert json.loads(captured["env"]["GENERATE_EXTRA_PARAMS"]) == {
        "enable_thinking": False,
        "thinking_budget": 128,
    }
    assert result["prompt_template"] == expected_prompt
    assert Path(result["output_file"]).read_text(encoding="utf-8") == expected_prompt


def test_run_classify_uses_selected_model_and_extra_params(tmp_path, monkeypatch):
    captured = {}
    work_dir = tmp_path / "workspace"
    work_dir.mkdir()

    def fake_run_lines(cmd, env, cwd, log_cb=None):
        captured["cmd"] = cmd
        captured["env"] = env
        captured["cwd"] = cwd
        (work_dir / "classification_report.json").write_text("{}", encoding="utf-8")
        return []

    monkeypatch.setattr(main, "run_lines", fake_run_lines)

    paths = SimpleNamespace(skills_dir=tmp_path)

    main.run_classify(
        paths,
        make_settings(),
        str(work_dir),
        2,
        model_cfg_id="fast",
    )

    assert captured["env"]["CLASSIFY_MODEL_NAME"] == "fast-model"
    assert captured["env"]["OPENAI_API_KEY"] == "fast-key"
    assert captured["env"]["OPENAI_BASE_URL"] == "https://fast.example/v1"
    assert json.loads(captured["env"]["CLASSIFY_EXTRA_PARAMS"]) == {
        "enable_thinking": False,
        "thinking_budget": 128,
    }


def test_run_review_rule_uses_selected_model_and_extra_params(tmp_path, monkeypatch):
    captured = {}

    def fake_run_lines(cmd, env, cwd, log_cb=None):
        captured["cmd"] = cmd
        captured["env"] = env
        captured["cwd"] = cwd
        return ["RESULTS_JSON:[]"]

    monkeypatch.setattr(main, "run_lines", fake_run_lines)

    paths = SimpleNamespace(skills_dir=tmp_path)

    result = main.run_review_rule(
        paths,
        make_settings(),
        "/tmp/workspace",
        True,
        model_cfg_id="fast",
        api_key="legacy-key-should-be-ignored",
        base_url="https://legacy.example/v1",
        model="legacy-model",
    )

    assert result == []
    assert "--model" in captured["cmd"]
    assert captured["cmd"][captured["cmd"].index("--model") + 1] == "fast-model"
    assert captured["cmd"][captured["cmd"].index("--api-key") + 1] == "fast-key"
    assert captured["cmd"][captured["cmd"].index("--base-url") + 1] == "https://fast.example/v1"
    assert json.loads(captured["env"]["GENERATE_EXTRA_PARAMS"]) == {
        "enable_thinking": False,
        "thinking_budget": 128,
    }


def test_run_verify_extraction_passes_dashscope_extra_body(monkeypatch, tmp_path):
    captured = {}
    material_dir = tmp_path / "material"
    material_dir.mkdir()

    class FakeCompletions:
        def create(self, **kwargs):
            captured["kwargs"] = kwargs
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content="ok"))]
            )

    class FakeChat:
        def __init__(self):
            self.completions = FakeCompletions()

    class FakeOpenAI:
        def __init__(self, **kwargs):
            captured["client_kwargs"] = kwargs
            self.chat = FakeChat()

    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(OpenAI=FakeOpenAI))
    monkeypatch.setattr(main, "find_media_file", lambda *_args, **_kwargs: material_dir / "sample.jpg")
    monkeypatch.setattr(main, "base64_image", lambda *_args, **_kwargs: "ZmFrZQ==")

    result = main.run_verify_extraction(
        material_dir,
        "请提取",
        "fast-model",
        "test-key",
        base_url="https://fast.example/v1",
        extra_params={"enable_thinking": False, "thinking_budget": 128},
    )

    assert result["success"] is True
    assert captured["client_kwargs"]["base_url"] == "https://fast.example/v1"
    assert captured["client_kwargs"]["api_key"] == "test-key"
    assert captured["kwargs"]["extra_body"] == {
        "enable_thinking": False,
        "thinking_budget": 128,
    }


def test_ui_settings_store_migrates_legacy_model_entries_to_openai_format(tmp_path):
    local_path = tmp_path / "settings.json"
    project_path = tmp_path / "project.json"
    local_path.write_text(
        json.dumps(
            {
                "api_key": "legacy-key",
                "default_model_id": "1",
                "model_name": "qwen-vl-max",
                "models": [
                    {
                        "id": "1",
                        "name": "Legacy Qwen",
                        "model_id": "qwen-vl-max",
                        "type": "vl",
                        "params": [{"key": "enable_thinking", "value": False}],
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    project_path.write_text("{}", encoding="utf-8")

    store = main.UiSettingsStore(local_path, project_path)
    settings = store.load_front()
    model = settings["models"][0]

    assert model["model"] == "qwen-vl-max"
    assert model["base_url"] == main.DASHSCOPE_COMPAT_BASE_URL
    assert model["api_key"] == ""
    assert "model_id" not in model

    persisted = json.loads(local_path.read_text(encoding="utf-8"))
    assert persisted["models"][0]["model"] == "qwen-vl-max"
    assert "model_id" not in persisted["models"][0]


def test_test_model_connection_uses_openai_compatible_settings(monkeypatch):
    captured = {}

    class FakeCompletions:
        def create(self, **kwargs):
            captured["kwargs"] = kwargs
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content="OK"))]
            )

    class FakeChat:
        def __init__(self):
            self.completions = FakeCompletions()

    class FakeOpenAI:
        def __init__(self, **kwargs):
            captured["client_kwargs"] = kwargs
            self.chat = FakeChat()

    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(OpenAI=FakeOpenAI))

    result = main.test_model_connection(
        {
            "id": "fast",
            "name": "Fast",
            "model": "fast-model",
            "base_url": "https://fast.example/v1",
            "api_key": "fast-key",
            "params": [{"key": "enable_thinking", "value": False}],
        },
        fallback_api_key="fallback-key",
        timeout=15,
    )

    assert result["ok"] is True
    assert captured["client_kwargs"] == {
        "api_key": "fast-key",
        "base_url": "https://fast.example/v1",
        "timeout": 15.0,
    }
    assert captured["kwargs"]["model"] == "fast-model"
    assert captured["kwargs"]["messages"] == [{"role": "user", "content": "Reply with OK only."}]
    assert captured["kwargs"]["max_tokens"] == 16
    assert captured["kwargs"]["temperature"] == 0
    assert captured["kwargs"]["extra_body"] == {"enable_thinking": False}
