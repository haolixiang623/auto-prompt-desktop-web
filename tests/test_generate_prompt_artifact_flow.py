import json
from pathlib import Path
from types import SimpleNamespace

from pyserver.app import main


def make_settings():
    return {
        "api_key": "fallback-key",
        "model_name": "default-model",
        "default_model_id": "default",
        "extract_god_prompt": "extract-god",
        "god_prompt": "classify-god",
        "llm_timeout": 120,
        "default_extract_profile_id": "gov-default",
        "extract_profiles": [
            {
                "id": "gov-default",
                "name": "政务通用规则",
                "unmatchedStrategy": "ai_generate",
                "systemPrompt": "你是政务专家",
                "analysisPromptTemplate": "分析：{{factor_context}}",
                "generationPromptTemplate": "生成：{{analysis_result}}",
                "promptTemplate": "HEAD\n$(factors)\nTAIL",
            }
        ],
        "models": [
            {
                "id": "default",
                "name": "Default",
                "model": "default-model",
                "base_url": "https://default.example/v1",
                "api_key": "",
                "type": "vl",
                "params": [],
            }
        ],
    }


def test_run_generate_prompt_returns_artifact_and_preview_prompt(tmp_path, monkeypatch):
    work_dir = tmp_path / "workspace"
    material_dir = work_dir / "营业证照"
    material_dir.mkdir(parents=True)
    (material_dir / "sample.jpg").write_bytes(b"fake-image")
    artifact_path = material_dir / "营业证照--要素提示词.json"
    artifact_path.write_text(
        json.dumps(
            {
                "version": "1",
                "carriername": "营业证照",
                "template": {"prompt_template": "HEAD\n$(factors)\nTAIL"},
                "meta": {
                    "useCaseLibrary": False,
                    "ruleProfileId": "gov-default",
                },
                "factors": [
                    {
                        "index": 1,
                        "factorname": "统一社会信用代码",
                        "factortype": "1",
                        "factoruse": "企业的唯一识别码",
                        "factor_prompt": "识别18位字母数字组合",
                        "source": "ai_generated",
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    captured = {}

    def fake_subprocess_run(args, **kwargs):
        captured["args"] = args
        captured["env"] = kwargs["env"]
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(main.subprocess, "run", fake_subprocess_run)
    monkeypatch.setattr(main, "_resolve_user_id_from_work_dir", lambda *_args, **_kwargs: "user-1")
    monkeypatch.setattr(main, "read_factors_script", lambda *_args, **_kwargs: [{"field_name": "统一社会信用代码"}])

    paths = SimpleNamespace(
        skills_dir=tmp_path / "skills",
        user_output_root=tmp_path / "outputs",
    )

    result = main.run_generate_prompt(
        paths,
        make_settings(),
        str(work_dir),
        "营业证照",
        model_cfg_id="default",
        use_case_library=False,
        rule_profile_id="gov-default",
    )

    assert captured["env"]["GENERATE_USE_CASE_LIBRARY"] == "0"
    assert json.loads(captured["env"]["GENERATE_RULE_PROFILE_JSON"])["id"] == "gov-default"
    assert result["artifact"]["factors"][0]["factor_prompt"] == "识别18位字母数字组合"
    assert result["artifact"]["factors"][0]["source"] == "ai_generated"
    assert result["artifact_file"].endswith("营业证照--要素提示词.json")
    assert "统一社会信用代码" in result["preview_prompt"]


def test_run_generate_prompt_rejects_unknown_extract_profile(tmp_path, monkeypatch):
    paths = SimpleNamespace(
        skills_dir=tmp_path / "skills",
        user_output_root=tmp_path / "outputs",
    )
    monkeypatch.setattr(main, "_resolve_user_id_from_work_dir", lambda *_args, **_kwargs: "user-1")

    try:
        main.run_generate_prompt(
            paths,
            make_settings(),
            str(tmp_path),
            "营业证照",
            use_case_library=True,
            rule_profile_id="missing-profile",
        )
    except ValueError as exc:
        assert "extract profile" in str(exc)
    else:
        raise AssertionError("expected run_generate_prompt to reject an unknown extract profile")
