# 自动化测试体系（1-4阶段执行版）

## 目标

- 每次迭代后可执行一次带数据的自动化回归。
- 覆盖最近高频改动点：生成重试、分类校验、分类下载包、审查规则原因策略。
- 将测试拆分为快/中/慢层级，保证日常可跑、关键链路可验。

## 阶段划分

### 阶段1：快速单元与静态回归

- 命令：`npm run test:frontend`
- 覆盖：
  - 前端关键视图静态行为断言
  - 新增 `GenerateView` 单材料重试入口存在性测试

### 阶段2：后端接口集成测试

- 命令：
  - `python -m pytest -q tests/test_workdir_resolution.py tests/test_review_rule_task_route.py tests/test_classify_validation_and_download.py`
- 覆盖：
  - 工作区路径映射
  - 审查规则任务路由
  - 分类前校验与下载 ZIP 产物完整性

### 阶段3：Skills 数据回归测试

- 命令：
  - `python -m pytest -q tests/test_generate_prompt_exit_codes.py tests/test_generate_factor_json_dedup.py tests/test_review_rule_reason_policy.py`
- 覆盖：
  - 生成脚本异常退出码
  - factor-json 去重逻辑
  - 审查规则原因“Excel优先，空则空”策略

### 阶段4：可选 E2E 冒烟

- 命令：`RUN_E2E_SMOKE=1 npm run test:regression`
- 说明：
  - 默认跳过，避免每次本地迭代耗时过长
  - 需要时开启 Playwright 冒烟

## 一键执行

- 命令：`npm run test:regression`
- 脚本：`scripts/test-regression.sh`
- 顺序：阶段1 -> 阶段2 -> 阶段3 -> 阶段4（可选）

## 新增测试文件

- `tests/test_classify_validation_and_download.py`
- `tests/test_review_rule_reason_policy.py`
- `tests/generate-view-retry-single-material.test.mjs`

## 每次迭代建议流程

1. 本地开发完成后先跑：`npm run test:regression`
2. 若只改前端，至少跑：`npm run test:frontend`
3. 若改 pyserver/skills，至少跑阶段2+3
4. 回归失败时优先看新增测试点，再定位改动引入的行为变化
