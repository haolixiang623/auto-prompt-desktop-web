import json

from pyserver.app import main


def test_ui_settings_store_exposes_default_extract_profiles(tmp_path):
    local_path = tmp_path / "settings.json"
    project_path = tmp_path / "project.json"
    local_path.write_text("{}", encoding="utf-8")
    project_path.write_text("{}", encoding="utf-8")

    store = main.UiSettingsStore(local_path, project_path)
    settings = store.load_front()

    assert settings["extract_profiles"]
    assert settings["default_extract_profile_id"]
    default_profile = next(
        profile
        for profile in settings["extract_profiles"]
        if profile["id"] == settings["default_extract_profile_id"]
    )
    assert default_profile["unmatchedStrategy"] == "ai_generate"
    assert "{{factor_list}}" in default_profile["analysisPromptTemplate"]
    assert "请以JSON格式返回" in default_profile["analysisPromptTemplate"]
    assert "{{factor_context}}" in default_profile["generationPromptTemplate"]
    assert "{{analysis_result}}" in default_profile["generationPromptTemplate"]
    assert "请以JSON格式返回" in default_profile["generationPromptTemplate"]
    assert "$(factors)" in default_profile["promptTemplate"]
    assert settings["review_rule_builtin_variables"]
    assert settings["review_rule_builtin_variables"][0]["token"] == "当前日期"
    assert settings["review_rule_builtin_variables"][0]["dataType"] == "date"


def test_ui_settings_store_migrates_legacy_extract_god_prompt_into_default_profile(tmp_path):
    local_path = tmp_path / "settings.json"
    project_path = tmp_path / "project.json"
    local_path.write_text(
        json.dumps(
            {
                "extract_god_prompt": "旧版提取系统提示词",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    project_path.write_text("{}", encoding="utf-8")

    store = main.UiSettingsStore(local_path, project_path)
    settings = store.load_front()
    default_profile = next(
        profile
        for profile in settings["extract_profiles"]
        if profile["id"] == settings["default_extract_profile_id"]
    )

    assert default_profile["systemPrompt"] == "旧版提取系统提示词"


def test_normalize_extract_profile_migrates_broken_default_templates():
    profile = main.normalize_extract_profile(
        {
            "id": "gov-default",
            "name": "政务通用规则",
            "analysisPromptTemplate": "请结合以下要素上下文识别样本文档中每个要素的实际位置、结构特征和可见值：\n{{factor_context}}",
            "generationPromptTemplate": "基于识别结果为每个未命中要素生成可泛化的 factor_prompt，禁止写样本中的具体值。\n识别结果：\n{{analysis_result}}",
        }
    )

    assert "{{factor_list}}" in profile["analysisPromptTemplate"]
    assert "请以JSON格式返回" in profile["analysisPromptTemplate"]
    assert "{{factor_context}}" in profile["generationPromptTemplate"]
    assert "{{analysis_result}}" in profile["generationPromptTemplate"]
    assert "请以JSON格式返回" in profile["generationPromptTemplate"]


def test_ui_settings_store_normalizes_review_rule_builtin_variables(tmp_path):
    local_path = tmp_path / "settings.json"
    project_path = tmp_path / "project.json"
    local_path.write_text(
        json.dumps(
            {
                "review_rule_builtin_variables": [
                    "当前日期",
                    {
                        "token": "当前月份",
                        "name": "当前月份",
                        "dataType": "string",
                        "placeholder": "$系统变量:当前月份$",
                    },
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    project_path.write_text("{}", encoding="utf-8")

    store = main.UiSettingsStore(local_path, project_path)
    settings = store.load_front()

    assert [item["token"] for item in settings["review_rule_builtin_variables"]] == ["当前日期", "当前月份"]
    assert settings["review_rule_builtin_variables"][1]["placeholder"] == "$系统变量:当前月份$"
