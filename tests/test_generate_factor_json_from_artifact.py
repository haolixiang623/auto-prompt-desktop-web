import importlib.util
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "skills" / "factor-json-generator" / "generate_factor_json.py"

spec = importlib.util.spec_from_file_location("generate_factor_json", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_generate_import_json_prefers_artifact_over_txt(tmp_path):
    material_name = "营业证照"
    material_dir = tmp_path / material_name
    material_dir.mkdir()

    (material_dir / f"{material_name}--要素提取完整提示词.txt").write_text(
        "旧 TXT 内容\n# 识别要素列表\n\n## 1.统一社会信用代码\n旧规则\n",
        encoding="utf-8",
    )
    (material_dir / f"{material_name}--要素提示词.json").write_text(
        json.dumps(
            {
                "version": "1",
                "carriername": material_name,
                "template": {"prompt_template": "HEAD\n$(factors)\nTAIL"},
                "factors": [
                    {
                        "index": 1,
                        "factorname": "统一社会信用代码",
                        "factortype": "1",
                        "factoruse": "企业的唯一识别码",
                        "factor_prompt": "识别18位字母数字组合",
                        "source": "case_library",
                    },
                    {
                        "index": 2,
                        "factorname": "企业名称",
                        "factortype": "1",
                        "factoruse": "公司的完整法定名称",
                        "factor_prompt": "识别完整企业名称",
                        "source": "ai_generated",
                    },
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    factors_info = [
        ("统一社会信用代码", "企业的唯一识别码", "1"),
        ("企业名称", "公司的完整法定名称", "1"),
    ]

    result = module.generate_import_json(material_name, factors_info, str(material_dir), group_size=4)

    assert [factor["factor_prompt"] for factor in result["factors"]] == [
        "识别18位字母数字组合",
        "识别完整企业名称",
    ]
    assert result["promptGroups"][0]["prompt_template"] == "HEAD\n$(factors)\nTAIL"
