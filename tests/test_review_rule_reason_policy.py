from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "skills" / "review-rule-generator" / "generate_review_rule.py"
SPEC = spec_from_file_location("generate_review_rule", MODULE_PATH)
generate_review_rule = module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(generate_review_rule)


def test_rule2_group_fail_reason_keeps_empty_when_excel_empty():
    result = generate_review_rule.build_keypoint_rule2(
        kpname="姓名一致",
        rule_desc="#材料A-姓名#与#材料B-姓名#一致",
        passreason="",
        nopassreason="",
        material_name="材料A",
        ordernum=None,
        exclude_situations="",
    )

    groups = result["review_conditions"]["groups"]
    assert groups
    assert groups[0]["groupFailReason"] == ""


def test_process_material_rules_uses_excel_reason_over_llm(monkeypatch):
    def fake_llm(*_args, **_kwargs):
        return {
            "review_rule": "2",
            "review_rule_text": "LLM推理文案",
            "content": "",
            "passreason": "来自LLM通过",
            "nopassreason": "来自LLM不通过",
            "review_conditions": {"groups": []},
        }

    monkeypatch.setattr(generate_review_rule, "call_llm_for_rule", fake_llm)

    keypoints = generate_review_rule.process_material_rules(
        material_name="材料A",
        keypoints_info=[
            {
                "kpname": "要点1",
                "rule_desc": "#材料A-姓名#与#材料B-姓名#一致",
                "passreason": "来自Excel通过",
                "nopassreason": "来自Excel不通过",
                "ordernum": None,
                "exclude_situations": "",
                "special_note": "",
            }
        ],
        use_llm=True,
        api_key="x",
        base_url="https://example.invalid/v1",
        model="demo",
        timeout=3,
    )

    assert keypoints[0]["passreason"] == "来自Excel通过"
    assert keypoints[0]["nopassreason"] == "来自Excel不通过"


def test_process_material_rules_builds_variable_condition_for_builtin_date():
    keypoints = generate_review_rule.process_material_rules(
        material_name="营业证照",
        keypoints_info=[
            {
                "factor_name": "有效期月份",
                "kpname": "月份校验",
                "rule_desc": "需要晚于#当前日期#的月份",
                "passreason": "",
                "nopassreason": "",
                "ordernum": None,
                "exclude_situations": "",
                "special_note": "",
            }
        ],
        use_llm=False,
    )

    result = keypoints[0]
    assert result["review_rule"] == "3"
    assert 'input.get("营业证照:有效期月份")' in result["review_rule_js"]
    assert 'input.get("系统变量:当前日期")' in result["review_rule_js"]


def test_build_keypoint_rule1_replaces_builtin_variable_placeholder():
    result = generate_review_rule.build_keypoint_rule1(
        kpname="月份校验",
        rule_desc="需要晚于#当前日期#的月份",
        passreason="",
        nopassreason="",
        material_name="营业证照",
        ordernum=None,
        exclude_situations="",
    )

    assert "$系统变量:当前日期$" in result["content"]
