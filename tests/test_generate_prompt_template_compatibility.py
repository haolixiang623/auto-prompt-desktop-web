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


def test_render_profile_template_supports_factor_context_and_factor_list_aliases():
    generate_prompt = load_generate_prompt_module()

    template = "分析要素：\n{{factor_context}}\n---\n{{factor_list}}"

    rendered_from_factor_list = generate_prompt.render_profile_template(
        template,
        {"factor_list": "1. 统一社会信用代码"},
    )
    rendered_from_factor_context = generate_prompt.render_profile_template(
        template,
        {"factor_context": "1. 企业名称"},
    )

    assert "{{factor_context}}" not in rendered_from_factor_list
    assert "{{factor_list}}" not in rendered_from_factor_list
    assert "1. 统一社会信用代码" in rendered_from_factor_list

    assert "{{factor_context}}" not in rendered_from_factor_context
    assert "{{factor_list}}" not in rendered_from_factor_context
    assert "1. 企业名称" in rendered_from_factor_context


def test_default_prompt_templates_require_json_output():
    generate_prompt = load_generate_prompt_module()

    assert "{{factor_list}}" in generate_prompt.DEFAULT_ANALYSIS_PROMPT_TEMPLATE
    assert "请以JSON格式返回" in generate_prompt.DEFAULT_ANALYSIS_PROMPT_TEMPLATE
    assert "{{factor_context}}" in generate_prompt.DEFAULT_RULE_PROMPT_TEMPLATE
    assert "{{analysis_result}}" in generate_prompt.DEFAULT_RULE_PROMPT_TEMPLATE
    assert "请以JSON格式返回" in generate_prompt.DEFAULT_RULE_PROMPT_TEMPLATE
