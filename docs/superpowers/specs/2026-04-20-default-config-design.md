# Default Model Config And API Key Design

## Goal

Make the current model configuration and API key available as project defaults so a newly built Docker image can start without requiring manual configuration in the Settings page.

## Scope

This change covers only default configuration bootstrap behavior for:

- `api_key`
- `default_model_id`
- `model_name`
- `models`
- existing prompt and timeout fields already supported by the frontend settings payload

This change does not alter per-user runtime overrides, authentication, or the settings UI workflow.

## Current Behavior

- The frontend saves settings through `PUT /api/settings`.
- The backend writes saved settings to `/data/settings.json`.
- The backend also reads fallback defaults from `auto-prompt.project.json`.
- The Docker image currently does not copy `auto-prompt.project.json` into `/app`, so image-only first boot cannot rely on that file as a fallback.
- As a result, first boot behavior depends on whether `/data/settings.json` already exists in the mounted Docker volume.

## Chosen Approach

Use `auto-prompt.project.json` as the canonical project default configuration file.

Implementation details:

1. Update `auto-prompt.project.json` with the current desired default API key and model configuration.
2. Update the Docker build so `auto-prompt.project.json` is copied into `/app`.
3. Keep backend precedence unchanged:
   - first use `/data/settings.json` when present
   - otherwise fall back to `/app/auto-prompt.project.json`

## Why This Approach

- It matches the requested behavior with minimal code change.
- It preserves the current runtime override model.
- It avoids introducing a second default-settings file or migration path.

## Tradeoffs

- The API key will be stored in a repository file and baked into the Docker image.
- Anyone with access to the repository or built image can recover the key.
- This is acceptable only because the user explicitly requested image-level defaults.

## File Changes

### `auto-prompt.project.json`

- Write the requested default API key.
- Write the requested default model list and selected default model.

### `Dockerfile`

- Copy `auto-prompt.project.json` into the runtime image at `/app/auto-prompt.project.json`.

## Runtime Flow

1. Container starts.
2. Backend constructs app paths with `AUTO_PROMPT_REPO_ROOT=/app`.
3. `UiSettingsStore` attempts to load `/data/settings.json`.
4. If runtime settings exist, they win.
5. If runtime settings do not exist, the backend reads `/app/auto-prompt.project.json`.
6. Settings page shows these defaults immediately on first boot.

## Error Handling

- If `auto-prompt.project.json` is missing from the image, fallback defaults remain the hardcoded backend defaults.
- If the project config file is malformed JSON, the backend should continue using its existing in-code defaults rather than crashing.

## Verification Plan

- Build the Docker image after updating `Dockerfile`.
- Remove the existing app data volume or start with a fresh volume.
- Start the container.
- Confirm `/api/settings` returns the configured API key state, model list, selected default model, and timeout values from `auto-prompt.project.json`.
- Confirm the Settings page loads those values without manual input.
- Confirm that saving new values in the UI writes `/data/settings.json` and overrides the project defaults on subsequent restarts.
