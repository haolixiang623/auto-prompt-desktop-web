import importlib.util
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "skills" / "factor-json-generator" / "generate_factor_json.py"

spec = importlib.util.spec_from_file_location("generate_factor_json", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_generate_import_json_deduplicates_identical_factor_name_and_prompt(tmp_path):
    material_name = "测试材料"
    material_dir = tmp_path / material_name
    material_dir.mkdir()

    prompt_file = material_dir / f"{material_name}--要素提取完整提示词.txt"
    prompt_file.write_text(
        "请提取以下要素\n# 识别要素列表\n\n## 1.姓名\n提取姓名\n\n## 2.身份证号\n提取身份证号\n",
        encoding="utf-8",
    )

    factors_info = [
        ("姓名", "用途1", "1"),
        ("身份证号", "用途2", "1"),
        ("姓名", "用途3", "1"),
    ]

    result = module.generate_import_json(material_name, factors_info, str(material_dir), group_size=4)

    assert [factor["factorname"] for factor in result["factors"]] == ["姓名", "身份证号"]
    assert [factor["factor_prompt"] for factor in result["factors"]] == ["提取姓名", "提取身份证号"]
    assert result["promptGroups"][0]["factors"] == ["姓名", "身份证号"]
