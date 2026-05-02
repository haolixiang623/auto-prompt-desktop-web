# Factor Prompt JSON Workflow Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the generation flow around per-factor `factor_prompt` editing, add a per-run case-library toggle plus configurable unmatched-factor profiles, and make JSON artifacts the primary output instead of editable full-prompt TXT files.

**Architecture:** Keep the Python generation script responsible for image analysis and factor-level prompt generation, but change its canonical output to a structured artifact JSON per material. The Vue generation screen should edit that artifact at the field level, the verify API should assemble a runtime prompt from the artifact template plus factor rows, and the final import JSON generator should consume artifact JSON first and only fall back to legacy TXT parsing for older workspaces.

**Tech Stack:** Vue 3 Composition API, FastAPI, Python CLI skills, JSON configuration, Node test runner, pytest

---

## File Map

- Modify: `auto-prompt.project.json`
- Modify: `src/views/GenerateView.vue`
- Modify: `src/views/SettingsView.vue`
- Modify: `pyserver/app/main.py`
- Modify: `skills/doc-extract-prompt-gen/generate_prompt.py`
- Modify: `skills/factor-json-generator/generate_factor_json.py`
- Modify: `skills/doc-extract-prompt-gen/skill.md`
- Modify: `skills/factor-json-generator/skill.md`
- Modify: `package.json`
- Create: `pyserver/app/factor_prompt_artifacts.py`
- Create: `tests/test_factor_prompt_settings.py`
- Create: `tests/test_generate_prompt_artifact_flow.py`
- Create: `tests/test_generate_factor_json_from_artifact.py`
- Create: `tests/generate-view-factor-prompt-editor.test.mjs`
- Create: `tests/generate-view-generate-options.test.mjs`
- Create: `tests/settings-view-extract-profile.test.mjs`

### Contract Decisions

- Canonical generation output file: `<material>--要素提示词.json`
- Optional derived preview file: `<material>--要素提取完整提示词.txt`
- Canonical editable field: `factors[].factor_prompt`
- Step 2 UI edits only artifact JSON fields, not freeform full-prompt text
- `/api/generate/prompt` request adds `useCaseLibrary` and `ruleProfileId`
- `/api/generate/verify` should accept `artifactFile` or inline `artifact`; keep `promptText` as a temporary fallback during migration
- Step 5 export should prefer artifact JSON and use TXT only as a legacy fallback

### Artifact Shape

```json
{
  "version": "1",
  "carriername": "营业证照",
  "template": {
    "prompt_template": "完整模板，含 $(factors)"
  },
  "meta": {
    "useCaseLibrary": true,
    "ruleProfileId": "gov-default",
    "modelCfgId": "fast",
    "generatedAt": "2026-04-30T12:00:00Z"
  },
  "factors": [
    {
      "index": 1,
      "factorname": "统一社会信用代码",
      "factortype": "1",
      "factoruse": "企业的唯一识别码",
      "factor_prompt": "识别18位字母数字组合，通常位于企业基本信息区域……",
      "source": "case_library"
    }
  ]
}
```

### Extract Profile Shape

```json
{
  "id": "gov-default",
  "name": "政务通用规则",
  "unmatchedStrategy": "ai_generate",
  "systemPrompt": "你是一个专业的政务文档要素提取专家……",
  "analysisPromptTemplate": "请结合以下要素上下文识别样本中的实际位置和结构特征：\n{{factor_context}}",
  "generationPromptTemplate": "基于识别结果为每个未命中要素生成可泛化的 factor_prompt。\n禁止写样本中的具体值。\n识别结果：\n{{analysis_result}}",
  "promptTemplate": "# 角色与核心指令\n...\n# 识别要素列表及规则\n$(factors)\n# 输出格式要求\n..."
}
```

## Chunk 1: Configuration And Contracts

### Task 1: Add Extract Profile Settings And Per-Run Options

**Files:**
- Modify: `auto-prompt.project.json`
- Modify: `pyserver/app/main.py`
- Modify: `src/views/SettingsView.vue`
- Create: `tests/test_factor_prompt_settings.py`
- Create: `tests/settings-view-extract-profile.test.mjs`

- [ ] **Step 1: Write the failing backend settings test**

Create `tests/test_factor_prompt_settings.py` covering:
- `UiSettingsStore.load_front()` returns `extract_profiles`
- `UiSettingsStore.load_front()` returns `default_extract_profile_id`
- missing config falls back to one built-in default profile
- legacy `extract_god_prompt` is migrated into the default profile `systemPrompt`

- [ ] **Step 2: Run the backend settings test to verify it fails**

Run: `python -m pytest -q tests/test_factor_prompt_settings.py`
Expected: FAIL because the store does not expose extract profiles yet

- [ ] **Step 3: Write the failing front-end settings view test**

Create `tests/settings-view-extract-profile.test.mjs` asserting `SettingsView.vue` contains:
- a default extract profile selector
- profile editing controls or a JSON editor block
- save payload fields for `extract_profiles` and `default_extract_profile_id`

- [ ] **Step 4: Run the front-end settings view test to verify it fails**

Run: `node --test tests/settings-view-extract-profile.test.mjs`
Expected: FAIL because the settings screen does not render extract profile controls

- [ ] **Step 5: Extend the settings contract**

In `pyserver/app/main.py`:
- add default extract profile data near `PromptBundle`
- extend `UiSettingsStore.FRONT_FIELDS` with `extract_profiles` and `default_extract_profile_id`
- migrate legacy `extract_god_prompt` into the default profile when loading old settings

In `auto-prompt.project.json`:
- add a starter `extract_profiles` array
- add `default_extract_profile_id`

- [ ] **Step 6: Add the settings UI**

In `src/views/SettingsView.vue`:
- load and persist `extract_profiles`
- load and persist `default_extract_profile_id`
- provide a compact editor suitable for power users
- keep the existing model config UI unchanged

- [ ] **Step 7: Re-run both focused settings tests**

Run: `python -m pytest -q tests/test_factor_prompt_settings.py`
Expected: PASS

Run: `node --test tests/settings-view-extract-profile.test.mjs`
Expected: PASS

## Chunk 2: Generation Artifact

### Task 2: Produce Structured Factor-Prompt Artifacts

**Files:**
- Create: `pyserver/app/factor_prompt_artifacts.py`
- Modify: `skills/doc-extract-prompt-gen/generate_prompt.py`
- Modify: `pyserver/app/main.py`
- Create: `tests/test_generate_prompt_artifact_flow.py`
- Modify: `tests/test_generate_prompt_no_local_case_library.py`
- Modify: `tests/test_model_config_param_propagation.py`

- [ ] **Step 1: Write the failing artifact flow tests**

Create `tests/test_generate_prompt_artifact_flow.py` covering:
- `/api/generate/prompt` input contract includes `useCaseLibrary` and `ruleProfileId`
- `run_generate_prompt()` returns an `artifact_file` and parsed `artifact`
- `artifact["factors"]` carries `factor_prompt` and `source`
- `artifact["template"]["prompt_template"]` exists even when the user never edits a full prompt

- [ ] **Step 2: Add a failing toggle test for case-library bypass**

Extend `tests/test_generate_prompt_no_local_case_library.py` so a no-library request proves:
- `lookup_cases_from_db()` is skipped entirely when `useCaseLibrary=false`
- all factors route through the unmatched strategy path

- [ ] **Step 3: Run the focused generation tests to verify they fail**

Run: `python -m pytest -q tests/test_generate_prompt_artifact_flow.py tests/test_generate_prompt_no_local_case_library.py tests/test_model_config_param_propagation.py`
Expected: FAIL because generation still returns TXT-first data and always checks the case library

- [ ] **Step 4: Implement artifact helpers**

Create `pyserver/app/factor_prompt_artifacts.py` with pure helpers for:
- `build_factor_lines(factors)`
- `build_preview_prompt(prompt_template, factors)`
- `normalize_factor_prompt_artifact(data)`
- `load_factor_prompt_artifact(path)`
- `save_factor_prompt_artifact(path, data)`

- [ ] **Step 5: Refactor the generation script**

In `skills/doc-extract-prompt-gen/generate_prompt.py`:
- read `GENERATE_USE_CASE_LIBRARY`
- read `GENERATE_RULE_PROFILE_JSON`
- replace hardcoded unmatched prompts with profile-provided templates
- collapse generated `rule` + `format` into one `factor_prompt`
- emit `<material>--要素提示词.json`
- optionally emit derived preview TXT for compatibility

- [ ] **Step 6: Refactor the API-side runner**

In `pyserver/app/main.py`:
- change `run_generate_prompt()` to accept `use_case_library` and `rule_profile_id`
- pass the selected profile JSON to the script via env
- return `artifact_file`, `artifact`, `preview_prompt`, and counts

- [ ] **Step 7: Keep model-selection propagation intact**

Update `tests/test_model_config_param_propagation.py` expectations so generation still forwards:
- selected model id
- selected API key
- selected base URL
- selected extra params

- [ ] **Step 8: Re-run the focused generation tests**

Run: `python -m pytest -q tests/test_generate_prompt_artifact_flow.py tests/test_generate_prompt_no_local_case_library.py tests/test_model_config_param_propagation.py`
Expected: PASS

## Chunk 3: Verify And Export Around Artifacts

### Task 3: Make Verify And Import JSON Consume Artifacts First

**Files:**
- Modify: `pyserver/app/main.py`
- Modify: `skills/factor-json-generator/generate_factor_json.py`
- Create: `tests/test_generate_factor_json_from_artifact.py`
- Modify: `tests/test_generate_factor_json_dedup.py`

- [ ] **Step 1: Write the failing export tests**

Create `tests/test_generate_factor_json_from_artifact.py` covering:
- artifact JSON is preferred over TXT when both exist
- `factors[].factor_prompt` comes from the artifact
- `promptGroups[].prompt_template` comes from the artifact template
- legacy TXT still works when the artifact is absent

- [ ] **Step 2: Run the export tests to verify they fail**

Run: `python -m pytest -q tests/test_generate_factor_json_from_artifact.py tests/test_generate_factor_json_dedup.py`
Expected: FAIL because the export path still reads TXT first

- [ ] **Step 3: Update verify-route behavior**

In `pyserver/app/main.py`:
- let `/api/generate/verify` accept `artifactFile` or inline `artifact`
- build the runtime verification prompt from artifact data with `build_preview_prompt(...)`
- keep `promptText` fallback for one release so existing callers do not break mid-refactor

- [ ] **Step 4: Update export behavior**

In `skills/factor-json-generator/generate_factor_json.py`:
- load artifact JSON if present
- map artifact factors directly into `factor_prompt`
- use `artifact.template.prompt_template` for generated `promptGroups`
- keep TXT parsing only as a fallback for old workspaces

- [ ] **Step 5: Normalize the no-TXT behavior**

For new artifact-based workspaces:
- always generate `promptGroups` when an artifact template exists
- keep the old “factors only” branch only for legacy workspaces with neither artifact nor TXT

- [ ] **Step 6: Re-run the focused export tests**

Run: `python -m pytest -q tests/test_generate_factor_json_from_artifact.py tests/test_generate_factor_json_dedup.py`
Expected: PASS

## Chunk 4: Field-Centric GenerateView

### Task 4: Replace Freeform Prompt Editing With Factor-Level Editing

**Files:**
- Modify: `src/views/GenerateView.vue`
- Create: `tests/generate-view-factor-prompt-editor.test.mjs`
- Create: `tests/generate-view-generate-options.test.mjs`

- [ ] **Step 1: Write the failing Step 2 editor test**

Create `tests/generate-view-factor-prompt-editor.test.mjs` asserting `GenerateView.vue` now renders:
- a factor list or factor table for the active material
- editable controls bound to `factor_prompt`
- source badges such as `提示词库`, `AI生成`, `人工修改`
- a read-only preview area instead of a primary freeform prompt textarea

- [ ] **Step 2: Write the failing generation-options test**

Create `tests/generate-view-generate-options.test.mjs` asserting `GenerateView.vue` includes:
- a `优先使用提示词库` checkbox with default enabled
- a rule profile selector for unmatched-factor generation
- request payload fields `useCaseLibrary` and `ruleProfileId`

- [ ] **Step 3: Run the focused front-end tests to verify they fail**

Run: `node --test tests/generate-view-factor-prompt-editor.test.mjs tests/generate-view-generate-options.test.mjs`
Expected: FAIL because Step 2 still centers on one large editable prompt textarea

- [ ] **Step 4: Refactor Step 1 controls**

In `src/views/GenerateView.vue`:
- add `useCaseLibrary` state defaulting to `true`
- add `selectedRuleProfileId` state loaded from `/api/settings`
- include both fields in each `/api/generate/prompt` request

- [ ] **Step 5: Refactor Step 2 result state**

Replace TXT-centric state with artifact-centric state:
- `batchResults[materialName].artifact`
- `batchResults[materialName].artifact_file`
- `batchResults[materialName].preview_prompt`
- remove `editablePrompt` as the source of truth

- [ ] **Step 6: Add field-level editing**

Render per-factor editing controls with:
- factor name
- factor use or context
- source badge
- multiline editor bound to `artifact.factors[i].factor_prompt`

Keep the full prompt only as a derived preview block or collapsed drawer.

- [ ] **Step 7: Replace save behavior**

Swap `/api/generate/save-prompt` usage for artifact persistence:
- save the updated artifact JSON
- regenerate the preview prompt locally or from the server response
- preserve edits when switching materials

- [ ] **Step 8: Update Step 3 verify entry**

When verifying:
- send `artifactFile` or inline `artifact`
- stop sending `promptText` from the UI once the new route is wired

- [ ] **Step 9: Re-run the focused front-end tests**

Run: `node --test tests/generate-view-factor-prompt-editor.test.mjs tests/generate-view-generate-options.test.mjs`
Expected: PASS

## Chunk 5: Migration, Docs, And Full Verification

### Task 5: Document The New Workflow And Verify End-To-End

**Files:**
- Modify: `skills/doc-extract-prompt-gen/skill.md`
- Modify: `skills/factor-json-generator/skill.md`
- Modify: `package.json`

- [ ] **Step 1: Update skill docs**

Document the new flow:
- generation emits `--要素提示词.json`
- users edit per-factor prompts instead of a complete TXT
- export prefers artifact JSON and falls back to TXT only for legacy folders

- [ ] **Step 2: Update package test coverage**

Add the new pytest files to `test:backend` in `package.json` so CI covers:
- settings profile contract
- artifact generation
- artifact-first import export

- [ ] **Step 3: Run focused front-end coverage**

Run: `node --test tests/settings-view-extract-profile.test.mjs tests/generate-view-factor-prompt-editor.test.mjs tests/generate-view-generate-options.test.mjs tests/generate-view-selected-factors.test.mjs tests/generate-view-retry-single-material.test.mjs`
Expected: PASS

- [ ] **Step 4: Run focused back-end coverage**

Run: `python -m pytest -q tests/test_factor_prompt_settings.py tests/test_generate_prompt_artifact_flow.py tests/test_generate_prompt_no_local_case_library.py tests/test_generate_factor_json_from_artifact.py tests/test_generate_factor_json_dedup.py tests/test_model_config_param_propagation.py`
Expected: PASS

- [ ] **Step 5: Run the existing regression subset**

Run: `npm run test:backend`
Expected: PASS

- [ ] **Step 6: Run the app build**

Run: `npm run build`
Expected: PASS

### Task 6: Optional Follow-Up After Main Delivery

**Files:**
- Modify later if needed: `src/views/GenerateView.vue`
- Modify later if needed: `pyserver/app/main.py`

- [ ] **Step 1: Decide whether per-factor regenerate is needed**

Do not implement in the main change unless the field editor lands cleanly first.

- [ ] **Step 2: If needed, add a narrow follow-up**

Use a separate plan for:
- regenerate one factor only
- restore one factor from the case library
- audit trail for manual edits

