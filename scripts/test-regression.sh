#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "== Phase 1: Fast unit/static checks =="
npm run test:frontend

echo "== Phase 2: Backend API integration tests =="
python -m pytest -q \
  tests/test_workdir_resolution.py \
  tests/test_review_rule_task_route.py \
  tests/test_classify_validation_and_download.py \
  tests/test_model_config_param_propagation.py

echo "== Phase 3: Skills data regression tests =="
python -m pytest -q \
  tests/test_generate_prompt_exit_codes.py \
  tests/test_generate_factor_json_dedup.py \
  tests/test_review_rule_reason_policy.py

echo "== Phase 4: Optional E2E smoke =="
if [[ "${RUN_E2E_SMOKE:-0}" == "1" ]]; then
  npx playwright test tests/e2e --reporter=line
else
  echo "Skipped. Set RUN_E2E_SMOKE=1 to enable."
fi

echo "Regression pipeline completed."
