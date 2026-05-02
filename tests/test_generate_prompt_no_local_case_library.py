import json
import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "skills" / "doc-extract-prompt-gen" / "generate_prompt.py"


def load_generate_prompt_module():
    spec = spec_from_file_location("generate_prompt", MODULE_PATH)
    module = module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_generate_prompt_does_not_touch_local_case_library(monkeypatch, tmp_path):
    generate_prompt = load_generate_prompt_module()

    work_dir = tmp_path / "示例材料"
    work_dir.mkdir()
    (work_dir / "factors.csv").write_text(
        "要素名称,要素提取说明,提取规则说明\n姓名,申请人姓名,保持原格式\n",
        encoding="utf-8",
    )
    image_path = work_dir / "sample.jpg"
    image_path.write_bytes(b"fake-image")

    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("legacy local case library path should not be used")

    monkeypatch.setattr(generate_prompt, "load_case_library", fail_if_called, raising=False)
    monkeypatch.setattr(generate_prompt, "match_cases_with_qwen", fail_if_called, raising=False)
    monkeypatch.setattr(generate_prompt, "add_cases_to_library", fail_if_called, raising=False)
    monkeypatch.setattr(generate_prompt, "lookup_cases_from_db", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(generate_prompt, "get_images_in_dir", lambda *_args, **_kwargs: [str(image_path)])
    monkeypatch.setattr(generate_prompt, "get_qwen_client", lambda: object())
    monkeypatch.setattr(
        generate_prompt,
        "analyze_image_with_qwen",
        lambda *_args, **_kwargs: json.dumps(
            {"factors": [{"name": "姓名", "value": "张三", "exists": True}]},
            ensure_ascii=False,
        ),
    )
    monkeypatch.setattr(
        generate_prompt,
        "generate_smart_rules",
        lambda *_args, **_kwargs: json.dumps(
            {
                "factors": [
                    {
                        "name": "姓名",
                        "rule": "根据姓名字段标签提取中文姓名文本",
                        "format": "保持原格式",
                    }
                ]
            },
            ensure_ascii=False,
        ),
    )
    monkeypatch.setattr(generate_prompt, "validate_final_prompt", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(generate_prompt, "load_template", lambda *_args, **_kwargs: "HEAD\n$(factors)\nTAIL")
    monkeypatch.setattr(sys, "argv", ["generate_prompt.py", str(work_dir)])

    exit_code = generate_prompt.main()

    assert exit_code == 0
    output_path = work_dir / f"{work_dir.name}--要素提取完整提示词.txt"
    assert output_path.exists()
    output_text = output_path.read_text(encoding="utf-8")
    assert "根据姓名字段标签提取中文姓名文本" in output_text
    assert "保持原格式" in output_text


def test_generate_prompt_skips_db_lookup_when_case_library_disabled(monkeypatch, tmp_path):
    generate_prompt = load_generate_prompt_module()

    work_dir = tmp_path / "示例材料"
    work_dir.mkdir()
    (work_dir / "factors.csv").write_text(
        "要素名称,要素提取说明,提取规则说明\n姓名,申请人姓名,保持原格式\n",
        encoding="utf-8",
    )
    image_path = work_dir / "sample.jpg"
    image_path.write_bytes(b"fake-image")

    monkeypatch.setenv("GENERATE_USE_CASE_LIBRARY", "0")
    monkeypatch.setenv(
        "GENERATE_RULE_PROFILE_JSON",
        json.dumps(
            {
                "id": "gov-default",
                "name": "政务通用规则",
                "unmatchedStrategy": "ai_generate",
                "systemPrompt": "你是政务专家",
                "analysisPromptTemplate": "分析：{{factor_context}}",
                "generationPromptTemplate": "生成：{{analysis_result}}",
                "promptTemplate": "HEAD\n$(factors)\nTAIL",
            },
            ensure_ascii=False,
        ),
    )

    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("db lookup should be skipped when the case library toggle is disabled")

    monkeypatch.setattr(generate_prompt, "lookup_cases_from_db", fail_if_called)
    monkeypatch.setattr(generate_prompt, "get_images_in_dir", lambda *_args, **_kwargs: [str(image_path)])
    monkeypatch.setattr(generate_prompt, "get_qwen_client", lambda: object())
    monkeypatch.setattr(
        generate_prompt,
        "analyze_image_with_qwen",
        lambda *_args, **_kwargs: json.dumps(
            {"factors": [{"name": "姓名", "value": "张三", "exists": True}]},
            ensure_ascii=False,
        ),
    )
    monkeypatch.setattr(
        generate_prompt,
        "generate_smart_rules",
        lambda *_args, **_kwargs: json.dumps(
            {
                "factors": [
                    {
                        "name": "姓名",
                        "rule": "根据姓名字段标签提取中文姓名文本",
                        "format": "保持原格式",
                    }
                ]
            },
            ensure_ascii=False,
        ),
    )
    monkeypatch.setattr(generate_prompt, "validate_final_prompt", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(generate_prompt, "load_template", lambda *_args, **_kwargs: "HEAD\n$(factors)\nTAIL")
    monkeypatch.setattr(sys, "argv", ["generate_prompt.py", str(work_dir)])

    exit_code = generate_prompt.main()

    assert exit_code == 0
