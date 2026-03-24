use std::fs;
use std::net::SocketAddr;
use std::path::{Path, PathBuf};
use std::sync::Arc;

use axum::body::Body;
use axum::extract::{DefaultBodyLimit, Multipart, Path as AxumPath, Query, Request, State};
use axum::http::{header, HeaderMap, HeaderValue, StatusCode};
use axum::middleware::{self, Next};
use axum::response::{Html, IntoResponse, Response};
use axum::routing::{delete, get, post, put};
use axum::{Extension, Json, Router};
use serde::Deserialize;
use serde_json::Value;
use tower_http::cors::CorsLayer;
use tower_http::services::{ServeDir, ServeFile};
use tower_http::trace::TraceLayer;

use auto_prompt_web_server::auth::{AuthSession, AuthStore, UserProfile, UserRole};
use auto_prompt_web_server::config::{AppSettings, SettingsStore};
use auto_prompt_web_server::llm_logs::LlmLogStore;
use auto_prompt_web_server::ops;
use auto_prompt_web_server::paths::AppPaths;
use auto_prompt_web_server::runtime::RuntimeContext;
use auto_prompt_web_server::tasks::{Task, TaskKind, TaskStore};
use auto_prompt_web_server::workspace::{UploadManifestEntry, UploadedBlob, WorkspaceService};

#[derive(Clone)]
struct WebState {
    auth: AuthStore,
    paths: AppPaths,
    runtime: RuntimeContext,
    settings: SettingsStore,
    workspaces: WorkspaceService,
    tasks: TaskStore,
    llm_logs: LlmLogStore,
}

#[derive(Clone, Debug)]
struct AuthContext {
    token: String,
    user: UserProfile,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
struct TaskQuery {
    page: Option<usize>,
    page_size: Option<usize>,
    path: Option<String>,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
struct TestKeyRequest {
    api_key: String,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
struct PackagesRequest {
    packages: Vec<String>,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
struct FileWriteRequest {
    path: String,
    content: String,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
struct CaseImportJsonRequest {
    source_path: String,
    overwrite: bool,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
struct CaseImportTxtRequest {
    file_paths: Vec<String>,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
struct LoginRequest {
    username: String,
    password: String,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
struct CreateUserRequest {
    name: String,
    username: String,
    password: String,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
struct ResetPasswordRequest {
    password: String,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
struct UpdateUserStatusRequest {
    active: bool,
}

#[tokio::main]
async fn main() {
    let runtime = RuntimeContext::discover();
    let paths = AppPaths::from_env();
    let settings = SettingsStore::new(
        paths.settings_path.clone(),
        runtime.repo_root.join("auto-prompt.project.json"),
    );
    let auth = AuthStore::new(paths.auth_db_path.clone());

    if let Err(error) = settings.migrate_legacy_if_needed() {
        eprintln!("failed to migrate settings: {error}");
    }
    if let Err(error) = auth.initialize() {
        panic!("failed to initialize auth store: {error}");
    }

    for dir in [&paths.data_dir, &paths.workspace_root, &paths.upload_root, &paths.task_root] {
        if let Err(error) = fs::create_dir_all(dir) {
            panic!("failed to create {}: {error}", dir.display());
        }
    }

    let state = WebState {
        auth,
        settings,
        workspaces: WorkspaceService::new(paths.clone()),
        tasks: TaskStore::new(paths.task_root.clone()),
        llm_logs: LlmLogStore::new(),
        runtime,
        paths,
    };

    let static_dir = state.runtime.frontend_dist_dir.clone();
    let index_file = static_dir.join("index.html");

    let protected_api = Router::new()
        .route("/api/auth/me", get(get_current_user))
        .route("/api/auth/logout", post(logout))
        .route("/api/workspaces", post(create_workspace))
        .route("/api/workspaces/:id", get(get_workspace))
        .route("/api/uploads", post(upload_files))
        .route("/api/tasks/:kind", post(start_task))
        .route("/api/task-runs/:id", get(get_task))
        .route("/api/task-runs/:id/logs", get(get_task_logs))
        .route("/api/settings", get(get_settings))
        .route("/api/settings/default-prompts", get(get_default_prompts))
        .route("/api/health", get(get_health))
        .route("/api/cases", get(get_cases))
        .route("/api/review-rules", get(get_review_rules))
        .route("/api/invoke/:command", post(invoke_direct))
        .route("/api/files/content", get(read_file_content).put(write_file_content))
        .route("/api/files/download", get(download_file))
        .route("/api/browse", get(browse_path))
        .layer(middleware::from_fn_with_state(state.clone(), require_auth));

    let admin_api = Router::new()
        .route("/api/users", get(list_users).post(create_user))
        .route("/api/users/:id/password", post(reset_user_password))
        .route("/api/users/:id/status", put(update_user_status))
        .route("/api/settings", put(update_settings))
        .route("/api/settings/test-key", post(test_api_key))
        .route("/api/health/install-packages", post(install_packages))
        .route("/api/health/install-python", post(install_python))
        .route("/api/cases/import-json", post(import_cases_json))
        .route("/api/cases/import-txt", post(import_cases_txt))
        .route("/api/cases/:id", delete(delete_case))
        .route("/api/review-rules", put(update_review_rules).delete(clear_review_rules))
        .route("/api/logs", get(get_logs).delete(clear_logs))
        .layer(middleware::from_fn(require_admin))
        .layer(middleware::from_fn_with_state(state.clone(), require_auth));

    let router = Router::new()
        .route("/api/auth/login", post(login))
        .merge(protected_api)
        .merge(admin_api)
        .fallback_service(
            ServeDir::new(static_dir)
                .append_index_html_on_directories(true)
                .fallback(ServeFile::new(index_file)),
        )
        .layer(DefaultBodyLimit::max(64 * 1024 * 1024))
        .layer(CorsLayer::permissive())
        .layer(TraceLayer::new_for_http())
        .with_state(state);

    let port = std::env::var("PORT")
        .ok()
        .and_then(|value| value.parse::<u16>().ok())
        .unwrap_or(3000);
    let addr = SocketAddr::from(([0, 0, 0, 0], port));
    println!("auto-prompt web server listening on http://{addr}");
    let listener = tokio::net::TcpListener::bind(addr).await.expect("bind server");
    axum::serve(listener, router).await.expect("serve app");
}

async fn login(
    State(state): State<WebState>,
    Json(body): Json<LoginRequest>,
) -> Result<Json<AuthSession>, (StatusCode, String)> {
    state
        .auth
        .authenticate(&body.username, &body.password)
        .map(Json)
        .map_err(unauthorized_error)
}

async fn get_current_user(Extension(auth): Extension<AuthContext>) -> Json<UserProfile> {
    Json(auth.user)
}

async fn logout(
    State(state): State<WebState>,
    Extension(auth): Extension<AuthContext>,
) -> Result<Json<Value>, (StatusCode, String)> {
    state.auth.revoke_session(&auth.token).map_err(server_error)?;
    Ok(Json(serde_json::json!({ "ok": true })))
}

async fn list_users(State(state): State<WebState>) -> Result<Json<Vec<UserProfile>>, (StatusCode, String)> {
    state.auth.list_users().map(Json).map_err(server_error)
}

async fn create_user(
    State(state): State<WebState>,
    Json(body): Json<CreateUserRequest>,
) -> Result<Json<UserProfile>, (StatusCode, String)> {
    state
        .auth
        .create_user(body.name, body.username, body.password, UserRole::User)
        .map(Json)
        .map_err(bad_request)
}

async fn reset_user_password(
    State(state): State<WebState>,
    AxumPath(user_id): AxumPath<String>,
    Json(body): Json<ResetPasswordRequest>,
) -> Result<Json<Value>, (StatusCode, String)> {
    state.auth.reset_password(&user_id, &body.password).map_err(bad_request)?;
    Ok(Json(serde_json::json!({ "ok": true })))
}

async fn update_user_status(
    State(state): State<WebState>,
    AxumPath(user_id): AxumPath<String>,
    Json(body): Json<UpdateUserStatusRequest>,
) -> Result<Json<Value>, (StatusCode, String)> {
    state.auth.set_user_active(&user_id, body.active).map_err(bad_request)?;
    Ok(Json(serde_json::json!({ "ok": true })))
}

async fn create_workspace(
    State(state): State<WebState>,
    Extension(auth): Extension<AuthContext>,
    mut multipart: Multipart,
) -> Result<Json<Value>, (StatusCode, String)> {
    let mut name = None;
    let mut manifest: Vec<UploadManifestEntry> = Vec::new();
    let mut raw_files: Vec<(String, Vec<u8>)> = Vec::new();

    while let Some(field) = multipart.next_field().await.map_err(internal_error)? {
        let field_name = field.name().unwrap_or_default().to_string();
        match field_name.as_str() {
            "name" => {
                name = Some(field.text().await.map_err(internal_error)?);
            }
            "manifest" => {
                let payload = field.text().await.map_err(internal_error)?;
                manifest = serde_json::from_str(&payload).map_err(bad_request)?;
            }
            "files" => {
                let file_name = field.file_name().unwrap_or("upload.bin").to_string();
                let bytes = field.bytes().await.map_err(internal_error)?;
                raw_files.push((file_name, bytes.to_vec()));
            }
            _ => {}
        }
    }

    if raw_files.is_empty() {
        return Err((StatusCode::BAD_REQUEST, "at least one file is required".to_string()));
    }

    let uploads = raw_files
        .into_iter()
        .enumerate()
        .map(|(index, (file_name, bytes))| UploadedBlob {
            relative_path: manifest
                .get(index)
                .map(|item| item.relative_path.clone())
                .unwrap_or_else(|| file_name.clone()),
            original_name: file_name,
            bytes,
        })
        .collect();

    let summary = state
        .workspaces
        .create_workspace(&auth.user.id, name, uploads)
        .map_err(server_error)?;
    Ok(Json(serde_json::to_value(summary).unwrap()))
}

async fn get_workspace(
    State(state): State<WebState>,
    Extension(auth): Extension<AuthContext>,
    AxumPath(workspace_id): AxumPath<String>,
) -> Result<Json<Value>, (StatusCode, String)> {
    let summary = state
        .workspaces
        .get_workspace(&auth.user.id, &workspace_id)
        .map_err(server_error)?;
    Ok(Json(serde_json::to_value(summary).unwrap()))
}

async fn upload_files(
    State(state): State<WebState>,
    Extension(auth): Extension<AuthContext>,
    mut multipart: Multipart,
) -> Result<Json<Value>, (StatusCode, String)> {
    let mut manifest: Vec<UploadManifestEntry> = Vec::new();
    let mut raw_files: Vec<(String, Vec<u8>)> = Vec::new();
    while let Some(field) = multipart.next_field().await.map_err(internal_error)? {
        match field.name().unwrap_or_default() {
            "manifest" => {
                let payload = field.text().await.map_err(internal_error)?;
                manifest = serde_json::from_str(&payload).map_err(bad_request)?;
            }
            "files" => {
                let file_name = field.file_name().unwrap_or("upload.bin").to_string();
                let bytes = field.bytes().await.map_err(internal_error)?;
                raw_files.push((file_name, bytes.to_vec()));
            }
            _ => {}
        }
    }
    let uploads = raw_files
        .into_iter()
        .enumerate()
        .map(|(index, (file_name, bytes))| UploadedBlob {
            relative_path: manifest
                .get(index)
                .map(|item| item.relative_path.clone())
                .unwrap_or_else(|| file_name.clone()),
            original_name: file_name,
            bytes,
        })
        .collect::<Vec<_>>();
    let paths = state
        .workspaces
        .save_temp_uploads(&auth.user.id, uploads)
        .map_err(server_error)?;
    Ok(Json(serde_json::json!({ "paths": paths })))
}

async fn start_task(
    State(state): State<WebState>,
    Extension(auth): Extension<AuthContext>,
    AxumPath(kind): AxumPath<String>,
    Json(payload): Json<Value>,
) -> Result<Json<Task>, (StatusCode, String)> {
    let task_kind = parse_task_kind(&kind)?;
    let sanitized_payload = sanitize_task_payload(&state, &auth.user, &kind, payload)?;
    let workspace_id = sanitized_payload
        .get("workspaceId")
        .and_then(Value::as_str)
        .map(ToOwned::to_owned)
        .or_else(|| derive_workspace_id_from_payload(&state, &auth.user, &sanitized_payload));
    let task = state
        .tasks
        .create(task_kind, auth.user.id.clone(), workspace_id);
    state.tasks.mark_running(&task.id, Some(5)).map_err(server_error)?;

    let app_state = state.clone();
    let task_id = task.id.clone();
    tokio::spawn(async move {
        run_task(app_state, kind, task_id, sanitized_payload).await;
    });

    Ok(Json(task))
}

async fn get_task(
    State(state): State<WebState>,
    Extension(auth): Extension<AuthContext>,
    AxumPath(task_id): AxumPath<String>,
) -> Result<Json<Task>, (StatusCode, String)> {
    state
        .tasks
        .get(&task_id, &auth.user.id)
        .map(Json)
        .ok_or_else(|| (StatusCode::NOT_FOUND, "task not found".to_string()))
}

async fn get_task_logs(
    State(state): State<WebState>,
    Extension(auth): Extension<AuthContext>,
    AxumPath(task_id): AxumPath<String>,
) -> Result<Json<Value>, (StatusCode, String)> {
    let logs = state
        .tasks
        .logs(&task_id, &auth.user.id)
        .ok_or_else(|| (StatusCode::NOT_FOUND, "task not found".to_string()))?;
    Ok(Json(serde_json::json!({ "logs": logs })))
}

async fn get_settings(
    State(state): State<WebState>,
    Extension(auth): Extension<AuthContext>,
) -> Result<Json<AppSettings>, (StatusCode, String)> {
    let mut settings = state.settings.load().map_err(server_error)?;
    settings.api_key_configured = !settings.api_key.is_empty();
    if !auth.user.role.is_admin() {
        settings.api_key.clear();
    }
    Ok(Json(settings))
}

async fn update_settings(
    State(state): State<WebState>,
    Json(settings): Json<AppSettings>,
) -> Result<Json<Value>, (StatusCode, String)> {
    state.settings.save(&settings).map_err(server_error)?;
    Ok(Json(serde_json::json!({ "ok": true })))
}

async fn get_default_prompts(State(state): State<WebState>) -> Json<Value> {
    Json(serde_json::to_value(ops::get_default_god_prompts(&state.settings)).unwrap())
}

async fn test_api_key(
    State(state): State<WebState>,
    Json(body): Json<TestKeyRequest>,
) -> Result<Json<Value>, (StatusCode, String)> {
    state
        .settings
        .test_api_key(&state.runtime, body.api_key)
        .map_err(server_error)?;
    Ok(Json(serde_json::json!({ "ok": true })))
}

async fn get_health(State(state): State<WebState>) -> Result<Json<Value>, (StatusCode, String)> {
    let health = ops::check_environment(&state.runtime).map_err(server_error)?;
    Ok(Json(serde_json::to_value(health).unwrap()))
}

async fn install_packages(
    State(state): State<WebState>,
    Json(body): Json<PackagesRequest>,
) -> Result<Json<Value>, (StatusCode, String)> {
    let result = ops::install_packages(&state.runtime, body.packages).map_err(server_error)?;
    Ok(Json(serde_json::to_value(result).unwrap()))
}

async fn install_python(State(_state): State<WebState>) -> Result<Json<Value>, (StatusCode, String)> {
    let result = ops::install_python().map_err(server_error)?;
    Ok(Json(serde_json::to_value(result).unwrap()))
}

async fn get_cases(State(state): State<WebState>) -> Result<Json<Value>, (StatusCode, String)> {
    let library = ops::load_case_library(&state.paths).map_err(server_error)?;
    Ok(Json(library))
}

async fn import_cases_json(
    State(state): State<WebState>,
    Extension(auth): Extension<AuthContext>,
    Json(body): Json<CaseImportJsonRequest>,
) -> Result<Json<Value>, (StatusCode, String)> {
    let source_path = ensure_user_path_allowed(&state, &auth.user, &body.source_path, false, PathScope::Uploads)?;
    let result = ops::import_case_library_json(
        &state.paths,
        source_path.to_string_lossy().to_string(),
        body.overwrite,
    )
    .map_err(server_error)?;
    Ok(Json(serde_json::to_value(result).unwrap()))
}

async fn import_cases_txt(
    State(state): State<WebState>,
    Extension(auth): Extension<AuthContext>,
    Json(body): Json<CaseImportTxtRequest>,
) -> Result<Json<Value>, (StatusCode, String)> {
    let mut file_paths = Vec::new();
    for path in body.file_paths {
        let file_path = ensure_user_path_allowed(&state, &auth.user, &path, false, PathScope::Uploads)?;
        file_paths.push(file_path.to_string_lossy().to_string());
    }
    let result = ops::import_cases_from_txt(&state.paths, file_paths).map_err(server_error)?;
    Ok(Json(serde_json::to_value(result).unwrap()))
}

async fn delete_case(
    State(state): State<WebState>,
    AxumPath(case_id): AxumPath<String>,
) -> Result<Json<Value>, (StatusCode, String)> {
    ops::delete_case(&state.paths, case_id).map_err(server_error)?;
    Ok(Json(serde_json::json!({ "ok": true })))
}

async fn get_review_rules(State(state): State<WebState>) -> Result<Json<Value>, (StatusCode, String)> {
    let library = ops::load_review_rule_library(&state.paths).map_err(server_error)?;
    Ok(Json(library))
}

async fn update_review_rules(
    State(state): State<WebState>,
    Json(body): Json<Value>,
) -> Result<Json<Value>, (StatusCode, String)> {
    ops::save_review_rule_library(&state.paths, body).map_err(server_error)?;
    Ok(Json(serde_json::json!({ "ok": true })))
}

async fn clear_review_rules(State(state): State<WebState>) -> Result<Json<Value>, (StatusCode, String)> {
    ops::clear_review_rule_library(&state.paths).map_err(server_error)?;
    Ok(Json(serde_json::json!({ "ok": true })))
}

async fn get_logs(
    State(state): State<WebState>,
    Query(query): Query<TaskQuery>,
) -> Json<Value> {
    Json(serde_json::to_value(ops::get_llm_logs(&state.llm_logs, query.page, query.page_size)).unwrap())
}

async fn clear_logs(State(state): State<WebState>) -> Json<Value> {
    ops::clear_llm_logs(&state.llm_logs);
    Json(serde_json::json!({ "ok": true }))
}

async fn invoke_direct(
    State(state): State<WebState>,
    Extension(auth): Extension<AuthContext>,
    AxumPath(command): AxumPath<String>,
    Json(args): Json<Value>,
) -> Result<Json<Value>, (StatusCode, String)> {
    let value = match command.as_str() {
        "read_factors" => {
            let work_dir = workspace_dir_arg(&state, &auth.user, &args, "workDir")?;
            serde_json::to_value(ops::read_factors(work_dir, &state.runtime).map_err(server_error)?).unwrap()
        }
        "get_materials" => {
            let work_dir = workspace_dir_arg(&state, &auth.user, &args, "workDir")?;
            serde_json::to_value(ops::get_materials(work_dir).map_err(server_error)?).unwrap()
        }
        "get_material_categories" => {
            let work_dir = workspace_dir_arg(&state, &auth.user, &args, "workDir")?;
            serde_json::to_value(ops::get_material_categories(work_dir, &state.runtime).map_err(server_error)?).unwrap()
        }
        "get_pending_files" => {
            let work_dir = workspace_dir_arg(&state, &auth.user, &args, "workDir")?;
            serde_json::to_value(ops::get_pending_files(work_dir).map_err(server_error)?).unwrap()
        }
        "read_json_file" => {
            let path = user_file_arg(&state, &auth.user, &args, "path", false, PathScope::WorkspaceOrUploads)?;
            serde_json::json!(ops::read_json_file(path).map_err(server_error)?)
        }
        "write_json_file" => {
            let path = user_file_arg(&state, &auth.user, &args, "path", true, PathScope::Workspace)?;
            let content = string_arg(&args, "content").map_err(bad_request)?;
            ops::write_json_file(path, content).map_err(server_error)?;
            serde_json::json!(null)
        }
        "write_file" => {
            let path = user_file_arg(&state, &auth.user, &args, "path", true, PathScope::Workspace)?;
            let content = string_arg(&args, "content").map_err(bad_request)?;
            ops::write_file(path, content).map_err(server_error)?;
            serde_json::json!(null)
        }
        "save_prompt_file" => {
            let file_path = user_file_arg(&state, &auth.user, &args, "filePath", true, PathScope::Workspace)?;
            let content = string_arg(&args, "content").map_err(bad_request)?;
            ops::save_prompt_file(file_path, content).map_err(server_error)?;
            serde_json::json!(null)
        }
        "read_file" => {
            let path = user_file_arg(&state, &auth.user, &args, "path", false, PathScope::WorkspaceOrUploads)?;
            serde_json::json!(ops::read_file(path).map_err(server_error)?)
        }
        "read_directory" => {
            let path = user_file_arg(&state, &auth.user, &args, "path", false, PathScope::WorkspaceOrUploads)?;
            serde_json::to_value(ops::read_directory(path).map_err(server_error)?).unwrap()
        }
        "search_cases" => {
            let query = string_arg(&args, "query").map_err(bad_request)?;
            ops::search_cases(&state.paths, query).map_err(server_error)?
        }
        other => return Err((StatusCode::NOT_FOUND, format!("unsupported command: {other}"))),
    };

    Ok(Json(value))
}

async fn read_file_content(
    State(state): State<WebState>,
    Extension(auth): Extension<AuthContext>,
    Query(query): Query<TaskQuery>,
) -> Result<Json<Value>, (StatusCode, String)> {
    let path = query
        .path
        .ok_or_else(|| (StatusCode::BAD_REQUEST, "missing path".to_string()))?;
    let content = ops::read_file(
        ensure_user_path_allowed(&state, &auth.user, &path, false, PathScope::WorkspaceOrUploads)?
            .to_string_lossy()
            .to_string(),
    )
    .map_err(server_error)?;
    Ok(Json(serde_json::json!({ "content": content })))
}

async fn write_file_content(
    State(state): State<WebState>,
    Extension(auth): Extension<AuthContext>,
    Json(body): Json<FileWriteRequest>,
) -> Result<Json<Value>, (StatusCode, String)> {
    let path = ensure_user_path_allowed(&state, &auth.user, &body.path, true, PathScope::Workspace)?;
    ops::write_file(path.to_string_lossy().to_string(), body.content).map_err(server_error)?;
    Ok(Json(serde_json::json!({ "ok": true })))
}

async fn download_file(
    State(state): State<WebState>,
    Extension(auth): Extension<AuthContext>,
    Query(query): Query<TaskQuery>,
) -> Result<Response, (StatusCode, String)> {
    let path = query
        .path
        .ok_or_else(|| (StatusCode::BAD_REQUEST, "missing path".to_string()))?;
    let file_path = ensure_user_path_allowed(&state, &auth.user, &path, false, PathScope::WorkspaceOrUploads)?;
    if !file_path.exists() {
        return Err((StatusCode::NOT_FOUND, "file not found".to_string()));
    }
    if file_path.is_dir() {
        return Ok(render_browse_response(&file_path));
    }
    let bytes = tokio::fs::read(&file_path).await.map_err(internal_error)?;
    let filename = file_path
        .file_name()
        .and_then(|name| name.to_str())
        .unwrap_or("artifact.bin");
    let mut response = Response::new(Body::from(bytes));
    response
        .headers_mut()
        .insert(header::CONTENT_TYPE, HeaderValue::from_static("application/octet-stream"));
    response.headers_mut().insert(
        header::CONTENT_DISPOSITION,
        HeaderValue::from_str(&format!("inline; filename=\"{filename}\"")).map_err(internal_error)?,
    );
    Ok(response)
}

async fn browse_path(
    State(state): State<WebState>,
    Extension(auth): Extension<AuthContext>,
    Query(query): Query<TaskQuery>,
) -> Result<Response, (StatusCode, String)> {
    let path = query
        .path
        .ok_or_else(|| (StatusCode::BAD_REQUEST, "missing path".to_string()))?;
    let target = ensure_user_path_allowed(&state, &auth.user, &path, false, PathScope::WorkspaceOrUploads)?;
    if !target.exists() {
        return Err((StatusCode::NOT_FOUND, "path not found".to_string()));
    }
    if target.is_file() {
        return download_file(
            State(state),
            Extension(auth),
            Query(TaskQuery {
                page: None,
                page_size: None,
                path: Some(target.to_string_lossy().to_string()),
            }),
        )
        .await;
    }
    Ok(render_browse_response(&target))
}

async fn require_auth(
    State(state): State<WebState>,
    mut request: Request,
    next: Next,
) -> Response {
    let token = match request_token(&request) {
        Some(token) => token,
        None => return unauthorized_error("missing auth token").into_response(),
    };

    match state.auth.current_user(&token) {
        Ok(Some(user)) => {
            request.extensions_mut().insert(AuthContext { token, user });
            next.run(request).await
        }
        Ok(None) => unauthorized_error("invalid or expired session").into_response(),
        Err(error) => server_error(error).into_response(),
    }
}

async fn require_admin(request: Request, next: Next) -> Response {
    let auth = match request.extensions().get::<AuthContext>().cloned() {
        Some(auth) => auth,
        None => return unauthorized_error("missing auth context").into_response(),
    };

    if !auth.user.role.is_admin() {
        return (StatusCode::FORBIDDEN, "admin access required".to_string()).into_response();
    }

    next.run(request).await
}

async fn run_task(state: WebState, kind: String, task_id: String, payload: Value) {
    let result = run_task_result(state.clone(), kind, task_id.clone(), payload).await;
    match result {
        Ok(value) => {
            let _ = state.tasks.complete(&task_id, value);
        }
        Err(error) => {
            let _ = state.tasks.fail(&task_id, error.clone());
            let _ = state.tasks.append_log(&task_id, format!("[error] {error}"));
        }
    }
}

async fn run_task_result(
    state: WebState,
    kind: String,
    task_id: String,
    payload: Value,
) -> Result<Value, String> {
    let logger_task_id = task_id.clone();
    let task_store = state.tasks.clone();
    let logger: ops::Logger = Arc::new(move |line| {
        let _ = task_store.append_log(&logger_task_id, line);
    });

    match kind.as_str() {
        "generate" => {
            let runtime = state.runtime.clone();
            let settings = state.settings.clone();
            let payload = payload.clone();
            let logger = logger.clone();
            tokio::task::spawn_blocking(move || {
                ops::generate_prompt(
                    &runtime,
                    &settings,
                    string_arg(&payload, "workDir")?,
                    optional_string_arg(&payload, "materialName"),
                    optional_string_arg(&payload, "modelCfgId"),
                    logger,
                )
                .and_then(|result| serde_json::to_value(result).map_err(|error| error.to_string()))
            })
            .await
            .map_err(|error| error.to_string())?
        }
        "verify-extraction" => {
            let runtime = state.runtime.clone();
            let settings = state.settings.clone();
            let llm_logs = state.llm_logs.clone();
            let payload = payload.clone();
            let logger = logger.clone();
            tokio::task::spawn_blocking(move || {
                ops::verify_extraction(
                    &runtime,
                    &settings,
                    &llm_logs,
                    string_arg(&payload, "materialDir")?,
                    string_arg(&payload, "promptText")?,
                    optional_string_arg(&payload, "modelCfgId"),
                    logger,
                )
                .and_then(|result| serde_json::to_value(result).map_err(|error| error.to_string()))
            })
            .await
            .map_err(|error| error.to_string())?
        }
        "classify" => {
            let runtime = state.runtime.clone();
            let settings = state.settings.clone();
            let llm_logs = state.llm_logs.clone();
            let payload = payload.clone();
            let logger = logger.clone();
            tokio::task::spawn_blocking(move || {
                ops::classify_materials(
                    &runtime,
                    &settings,
                    &llm_logs,
                    string_arg(&payload, "workDir")?,
                    u32_arg(&payload, "maxRounds").unwrap_or(2),
                    optional_string_arg(&payload, "modelCfgId"),
                    logger,
                )
                .and_then(|result| serde_json::to_value(result).map_err(|error| error.to_string()))
            })
            .await
            .map_err(|error| error.to_string())?
        }
        "test-classify-prompt" => {
            let runtime = state.runtime.clone();
            let settings = state.settings.clone();
            let payload = payload.clone();
            let logger = logger.clone();
            tokio::task::spawn_blocking(move || {
                ops::test_classify_prompt(
                    &runtime,
                    &settings,
                    string_arg(&payload, "workDir")?,
                    string_arg(&payload, "promptType")?,
                    string_arg(&payload, "promptContent")?,
                    optional_string_arg(&payload, "modelCfgId"),
                    logger,
                )
                .and_then(|result| serde_json::to_value(result).map_err(|error| error.to_string()))
            })
            .await
            .map_err(|error| error.to_string())?
        }
        "factor-json" => {
            let runtime = state.runtime.clone();
            let payload = payload.clone();
            let logger = logger.clone();
            tokio::task::spawn_blocking(move || {
                ops::generate_factor_json(
                    &runtime,
                    string_arg(&payload, "workDir")?,
                    optional_u32_arg(&payload, "groupSize"),
                    logger,
                )
                .and_then(|result| serde_json::to_value(result).map_err(|error| error.to_string()))
            })
            .await
            .map_err(|error| error.to_string())?
        }
        "review-rule" => {
            let runtime = state.runtime.clone();
            let settings = state.settings.clone();
            let llm_logs = state.llm_logs.clone();
            let payload = payload.clone();
            let logger = logger.clone();
            tokio::task::spawn_blocking(move || {
                let api_key = optional_string_arg(&payload, "apiKey")
                    .filter(|value| !value.is_empty())
                    .or_else(|| settings.get_api_key().ok());
                let base_url = optional_string_arg(&payload, "baseUrl")
                    .filter(|value| !value.is_empty())
                    .or(Some("https://dashscope.aliyuncs.com/compatible-mode/v1".to_string()));
                let model = optional_string_arg(&payload, "model")
                    .filter(|value| !value.is_empty())
                    .or_else(|| settings.load().ok().map(|value| value.model_name));
                ops::generate_review_rule(
                    &runtime,
                    &settings,
                    &llm_logs,
                    string_arg(&payload, "workDir")?,
                    bool_arg(&payload, "useLlm").unwrap_or(false),
                    api_key,
                    base_url,
                    model,
                    logger,
                )
                .and_then(|result| serde_json::to_value(result).map_err(|error| error.to_string()))
            })
            .await
            .map_err(|error| error.to_string())?
        }
        "regenerate-keypoint" => {
            let settings = state.settings.clone();
            let payload = payload.clone();
            let timeout = optional_u64_arg(&payload, "timeout").or_else(|| settings.get_llm_timeout().ok());
            let api_key = optional_string_arg(&payload, "apiKey")
                .filter(|value| !value.is_empty())
                .or_else(|| settings.get_api_key().ok());
            let base_url = optional_string_arg(&payload, "baseUrl")
                .filter(|value| !value.is_empty())
                .or(Some("https://dashscope.aliyuncs.com/compatible-mode/v1".to_string()));
            let model = optional_string_arg(&payload, "model")
                .filter(|value| !value.is_empty())
                .or_else(|| settings.load().ok().map(|value| value.model_name));
            ops::regenerate_keypoint(
                string_arg(&payload, "kpname").unwrap_or_default(),
                string_arg(&payload, "ruleDesc").unwrap_or_default(),
                string_arg(&payload, "materialName").unwrap_or_default(),
                string_arg(&payload, "targetRule").unwrap_or_default(),
                api_key,
                base_url,
                model,
                timeout,
            )
            .await
            .and_then(|result| serde_json::to_value(result).map_err(|error| error.to_string()))
        }
        other => Err(format!("unsupported task kind: {other}")),
    }
}

fn sanitize_task_payload(
    state: &WebState,
    user: &UserProfile,
    kind: &str,
    mut payload: Value,
) -> Result<Value, (StatusCode, String)> {
    match kind {
        "generate" | "classify" | "factor-json" | "review-rule" | "test-classify-prompt" => {
            let work_dir = string_arg(&payload, "workDir").map_err(bad_request)?;
            let canonical = ensure_user_path_allowed(state, user, &work_dir, false, PathScope::Workspace)?;
            payload["workDir"] = Value::String(canonical.to_string_lossy().to_string());
        }
        "verify-extraction" => {
            let material_dir = string_arg(&payload, "materialDir").map_err(bad_request)?;
            let canonical = ensure_user_path_allowed(state, user, &material_dir, false, PathScope::Workspace)?;
            payload["materialDir"] = Value::String(canonical.to_string_lossy().to_string());
        }
        "regenerate-keypoint" => {}
        other => return Err((StatusCode::BAD_REQUEST, format!("unsupported task kind: {other}"))),
    }

    Ok(payload)
}

fn derive_workspace_id_from_payload(state: &WebState, user: &UserProfile, payload: &Value) -> Option<String> {
    let work_dir = payload
        .get("workDir")
        .and_then(Value::as_str)
        .or_else(|| payload.get("materialDir").and_then(Value::as_str))?;
    derive_workspace_id_from_path(state, user, Path::new(work_dir))
}

fn derive_workspace_id_from_path(state: &WebState, user: &UserProfile, path: &Path) -> Option<String> {
    let canonical_path = canonicalize_path(path, false).ok()?;
    let canonical_root = fs::canonicalize(state.paths.user_workspace_root(&user.id)).ok()?;
    let relative = canonical_path.strip_prefix(canonical_root).ok()?;
    relative
        .components()
        .next()
        .and_then(|component| component.as_os_str().to_str())
        .map(ToOwned::to_owned)
}

fn workspace_dir_arg(
    state: &WebState,
    user: &UserProfile,
    args: &Value,
    key: &str,
) -> Result<String, (StatusCode, String)> {
    let path = string_arg(args, key).map_err(bad_request)?;
    Ok(
        ensure_user_path_allowed(state, user, &path, false, PathScope::Workspace)?
            .to_string_lossy()
            .to_string(),
    )
}

fn user_file_arg(
    state: &WebState,
    user: &UserProfile,
    args: &Value,
    key: &str,
    for_write: bool,
    scope: PathScope,
) -> Result<String, (StatusCode, String)> {
    let path = string_arg(args, key).map_err(bad_request)?;
    Ok(
        ensure_user_path_allowed(state, user, &path, for_write, scope)?
            .to_string_lossy()
            .to_string(),
    )
}

#[derive(Clone, Copy)]
enum PathScope {
    Workspace,
    Uploads,
    WorkspaceOrUploads,
}

fn ensure_user_path_allowed(
    state: &WebState,
    user: &UserProfile,
    path: &str,
    for_write: bool,
    scope: PathScope,
) -> Result<PathBuf, (StatusCode, String)> {
    let candidate = canonicalize_path(Path::new(path), for_write).map_err(bad_request)?;

    let mut allowed_roots = Vec::new();
    match scope {
        PathScope::Workspace => allowed_roots.push(state.paths.user_workspace_root(&user.id)),
        PathScope::Uploads => allowed_roots.push(state.paths.user_upload_root(&user.id)),
        PathScope::WorkspaceOrUploads => {
            allowed_roots.push(state.paths.user_workspace_root(&user.id));
            allowed_roots.push(state.paths.user_upload_root(&user.id));
        }
    }

    for root in allowed_roots {
        if let Ok(canonical_root) = fs::canonicalize(&root) {
            if candidate.starts_with(&canonical_root) {
                return Ok(candidate);
            }
        }
    }

    Err((StatusCode::FORBIDDEN, "path is outside the current user's scope".to_string()))
}

fn canonicalize_path(path: &Path, for_write: bool) -> Result<PathBuf, String> {
    if path.exists() {
        return fs::canonicalize(path).map_err(|error| format!("failed to resolve path: {error}"));
    }

    if !for_write {
        return Err("path does not exist".to_string());
    }

    let parent = path.parent().ok_or_else(|| "path must have a parent directory".to_string())?;
    let canonical_parent =
        fs::canonicalize(parent).map_err(|error| format!("failed to resolve parent directory: {error}"))?;
    let file_name = path.file_name().ok_or_else(|| "path must include a file name".to_string())?;
    Ok(canonical_parent.join(file_name))
}

fn bearer_token(headers: &HeaderMap) -> Option<String> {
    let auth_header = headers.get(header::AUTHORIZATION)?.to_str().ok()?;
    auth_header
        .strip_prefix("Bearer ")
        .map(str::trim)
        .filter(|token| !token.is_empty())
        .map(ToOwned::to_owned)
}

fn request_token(request: &Request) -> Option<String> {
    bearer_token(request.headers()).or_else(|| {
        let query = request.uri().query()?;
        query
            .split('&')
            .find_map(|pair| pair.split_once('='))
            .filter(|(key, _)| *key == "authToken")
            .and_then(|(_, value)| urlencoding::decode(value).ok())
            .map(|value| value.into_owned())
            .filter(|token| !token.is_empty())
    })
}

fn parse_task_kind(kind: &str) -> Result<TaskKind, (StatusCode, String)> {
    match kind {
        "generate" => Ok(TaskKind::Generate),
        "classify" => Ok(TaskKind::Classify),
        "review-rule" => Ok(TaskKind::ReviewRule),
        "factor-json" => Ok(TaskKind::FactorJson),
        "verify-extraction" => Ok(TaskKind::VerifyExtraction),
        "test-classify-prompt" => Ok(TaskKind::TestClassifyPrompt),
        "regenerate-keypoint" => Ok(TaskKind::RegenerateKeypoint),
        _ => Err((StatusCode::BAD_REQUEST, format!("unknown task kind: {kind}"))),
    }
}

fn string_arg(args: &Value, key: &str) -> Result<String, String> {
    args.get(key)
        .and_then(Value::as_str)
        .map(ToOwned::to_owned)
        .ok_or_else(|| format!("missing parameter: {key}"))
}

fn optional_string_arg(args: &Value, key: &str) -> Option<String> {
    args.get(key).and_then(Value::as_str).map(ToOwned::to_owned)
}

fn u32_arg(args: &Value, key: &str) -> Result<u32, String> {
    args.get(key)
        .and_then(Value::as_u64)
        .map(|value| value as u32)
        .ok_or_else(|| format!("missing parameter: {key}"))
}

fn optional_u32_arg(args: &Value, key: &str) -> Option<u32> {
    args.get(key).and_then(Value::as_u64).map(|value| value as u32)
}

fn optional_u64_arg(args: &Value, key: &str) -> Option<u64> {
    args.get(key).and_then(Value::as_u64)
}

fn bool_arg(args: &Value, key: &str) -> Result<bool, String> {
    args.get(key)
        .and_then(Value::as_bool)
        .ok_or_else(|| format!("missing parameter: {key}"))
}

fn bad_request(error: impl ToString) -> (StatusCode, String) {
    (StatusCode::BAD_REQUEST, error.to_string())
}

fn unauthorized_error(error: impl ToString) -> (StatusCode, String) {
    (StatusCode::UNAUTHORIZED, error.to_string())
}

fn server_error(error: impl ToString) -> (StatusCode, String) {
    (StatusCode::INTERNAL_SERVER_ERROR, error.to_string())
}

fn internal_error(error: impl ToString) -> (StatusCode, String) {
    (StatusCode::INTERNAL_SERVER_ERROR, error.to_string())
}

fn render_browse_response(target: &PathBuf) -> Response {
    let mut items = Vec::new();
    if let Ok(entries) = fs::read_dir(target) {
        for entry in entries.flatten() {
            let child_path = entry.path();
            let label = child_path.file_name().and_then(|name| name.to_str()).unwrap_or("");
            let href = format!("/api/browse?path={}", urlencoding::encode(&child_path.to_string_lossy()));
            items.push(format!("<li><a href=\"{href}\">{label}</a></li>"));
        }
    }
    let html = format!(
        "<!doctype html><html><head><meta charset=\"utf-8\"><title>{}</title></head><body><h1>{}</h1><ul>{}</ul></body></html>",
        target.display(),
        target.display(),
        items.join("")
    );
    Html(html).into_response()
}
