# Engineering Rules

1. Do not let runtime implementations drift across duplicate files.
If a shared store or service API changes, route handlers in `pyserver/app/main.py` must be updated in the same change, or the shared implementation must be used directly.

2. Every task route change needs a route-level regression test.
At minimum, add a backend test that proves the route returns a task payload instead of a `500 Internal Server Error`.

3. Frontend-selected model or API settings must be honored by backend task runners.
If the UI sends `model`, `apiKey`, or `baseUrl`, the task runner must either consume those values or the UI must stop exposing them.

4. Any Vue page that calls `invoke()` or `listen()` must explicitly import them from `src/tauri`.
The static guard in `tests/view-tauri-imports.test.mjs` is required and must stay in the default test flow.

5. Backend response shape changes must be treated as API contract changes.
If `invoke()` or `/api/*` starts returning an object where callers previously received a JSON string, update every affected caller in the same change and add a regression test for the compatibility layer.
