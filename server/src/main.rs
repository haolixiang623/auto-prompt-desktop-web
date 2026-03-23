use std::fs;
use std::net::SocketAddr;
use std::path::PathBuf;
use std::sync::Arc;

use axum::body::Body;
use axum::extract::{DefaultBodyLimit, Multipart, Path as AxumPath, Query, State};
use axum::http::{header, HeaderValue, StatusCode};
use axum::response::{Html, IntoResponse, Response};
use axum::routing::{delete, get, post};
use axum::{Json, Router};
use serde::Deserialize;
use serde_json::Value;
use tower_http::cors::CorsLayer;
use tower_http::services::{ServeDir, ServeFile};
use tower_http::trace::TraceLayer;

use auto_prompt_web_server::config::{AppSettings, SettingsStore};
use auto_prompt_web_server::llm_logs::LlmLogStore;
use auto_prompt_web_server::ops;
use auto_prompt_web_server::paths::AppPaths;
use auto_prompt_web_server::runtime::RuntimeContext;
use auto_prompt_web_server::tasks::{Task, TaskKind, TaskStore};
use auto_prompt_web_server::workspace::{UploadManifestEntry, UploadedBlob, WorkspaceService};

#[derive(Clone)]
struct WebState {
    paths: AppPaths,
    runtime: RuntimeContext,
    settings: SettingsStore,
    workspaces: WorkspaceService,
    tasks: TaskStore,
    llm_logs: LlmLogStore,
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

#[tokio::main]
async fn main() {
    let runtime = RuntimeContext::discover();
    let paths = AppPaths::from_env();
    for dir in [&paths.data_dir, &paths.workspace_root, &paths.upload_root, &paths.task_root] {
        if let Err(error) = fs::create_dir_all(dir) {
            panic!("failed to create {}: {error}", dir.display());
        }
    }

    let state = WebState {
        settings: SettingsStore::new(paths.settings_path.clone()),
        workspaces: WorkspaceService::new(paths.clone()),
        tasks: TaskStore::new(paths.task_root.clone()),
        llm_logs: LlmLogStore::new(),
        runtime,
        paths,
    };

    let static_dir = state.runtime.frontend_dist_dir.clone();
    let index_file = static_dir.join("index.html");
    let router = Router::new()
        .route("/api/workspaces", post(create_workspace))
        .route("/api/workspaces/:id", get(get_workspace))
        .route("/api/uploads", post(upload_files))
        .route("/api/tasks/:kind", post(start_task))
        .route("/api/task-runs/:id", get(get_task))
        .route("/api/task-runs/:id/logs", get(get_task_logs))
        .route("/api/settings", get(get_settings).put(update_settings))
        .route("/api/settings/default-prompts", get(get_default_prompts))
        .route("/api/settings/test-key", post(test_api_key))
        .route("/api/health", get(get_health))
        .route("/api/health/install-packages", post(install_packages))
        .route("/api/health/install-python", post(install_python))
        .route("/api/cases", get(get_cases))
        .route("/api/cases/import-json", post(import_cases_json))
        .route("/api/cases/import-txt", post(import_cases_txt))
        .route("/api/cases/:id", delete(delete_case))
        .route("/api/review-rules", get(get_review_rules).put(update_review_rules).delete(clear_review_rules))
        .route("/api/logs", get(get_logs).delete(clear_logs))
        .route("/api/invoke/:command", post(invoke_direct))
        .route("/api/files/content", get(read_file_content).put(write_file_content))
        .route("/api/files/download", get(download_file))
        .route("/api/browse", get(browse_path))
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

async fn create_workspace(
    State(state): State<WebState>,
    mut multipart: Multipart,
) -> Result<Json<Value>, (StatusCode, String)> {
    let mut name = None;
    let mut manifest: Vec<UploadManifestEntry> = Vec::new();
    let mut raw_files: Vec<(String, Vec<u8>)> = Vec::new();

    while let Some(field) = multipart
        .next_field()
        .await
        .map_err(internal_error)?
    {
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
        return Err((StatusCode::BAD_REQUEST, "至少需要上传一个文件".to_string()));
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
        .create_workspace(name, uploads)
        .map_err(server_error)?;
    Ok(Json(serde_json::to_value(summary).unwrap()))
}

async fn get_workspace(
    State(state): State<WebState>,
    AxumPath(workspace_id): AxumPath<String>,
) -> Result<Json<Value>, (StatusCode, String)> {
    let summary = state.workspaces.get_workspace(&workspace_id).map_err(server_error)?;
    Ok(Json(serde_json::to_value(summary).unwrap()))
}

async fn upload_files(
    State(state): State<WebState>,
    mut multipart: Multipart,
) -> Result<Json<Value>, (StatusCode, String)> {
    let mut manifest: Vec<UploadManifestEntry> = Vec::new();
    let mut raw_files: Vec<(String, Vec<u8>)> = Vec::new();
    while let Some(field) = multipart
        .next_field()
        .await
        .map_err(internal_error)?
    {
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
    let paths = state.workspaces.save_temp_uploads(uploads).map_err(server_error)?;
    Ok(Json(serde_json::json!({ "paths": paths })))
}

async fn start_task(
    State(state): State<WebState>,
    AxumPath(kind): AxumPath<String>,
    Json(payload): Json<Value>,
) -> Result<Json<Task>, (StatusCode, String)> {
    let task_kind = parse_task_kind(&kind)?;
    let workspace_id = payload
        .get("workspaceId")
        .and_then(Value::as_str)
        .map(ToOwned::to_owned);
    let task = state.tasks.create(task_kind, workspace_id);
    state.tasks.mark_running(&task.id, Some(5)).map_err(server_error)?;

    let app_state = state.clone();
    let task_id = task.id.clone();
    tokio::spawn(async move {
        run_task(app_state, kind, task_id, payload).await;
    });

    Ok(Json(task))
}

async fn get_task(
    State(state): State<WebState>,
    AxumPath(task_id): AxumPath<String>,
) -> Result<Json<Task>, (StatusCode, String)> {
    state
        .tasks
        .get(&task_id)
        .map(Json)
        .ok_or_else(|| (StatusCode::NOT_FOUND, "任务不存在".to_string()))
}

async fn get_task_logs(
    State(state): State<WebState>,
    AxumPath(task_id): AxumPath<String>,
) -> Result<Json<Value>, (StatusCode, String)> {
    let logs = state
        .tasks
        .logs(&task_id)
        .ok_or_else(|| (StatusCode::NOT_FOUND, "任务不存在".to_string()))?;
    Ok(Json(serde_json::json!({ "logs": logs })))
}

async fn get_settings(State(state): State<WebState>) -> Result<Json<AppSettings>, (StatusCode, String)> {
    state.settings.load().map(Json).map_err(server_error)
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
    Json(body): Json<CaseImportJsonRequest>,
) -> Result<Json<Value>, (StatusCode, String)> {
    let result = ops::import_case_library_json(&state.paths, body.source_path, body.overwrite).map_err(server_error)?;
    Ok(Json(serde_json::to_value(result).unwrap()))
}

async fn import_cases_txt(
    State(state): State<WebState>,
    Json(body): Json<CaseImportTxtRequest>,
) -> Result<Json<Value>, (StatusCode, String)> {
    let result = ops::import_cases_from_txt(&state.paths, body.file_paths).map_err(server_error)?;
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
    AxumPath(command): AxumPath<String>,
    Json(args): Json<Value>,
) -> Result<Json<Value>, (StatusCode, String)> {
    let value = match command.as_str() {
        "read_factors" => {
            let work_dir = string_arg(&args, "workDir").map_err(bad_request)?;
            serde_json::to_value(ops::read_factors(work_dir, &state.runtime).map_err(server_error)?).unwrap()
        }
        "get_materials" => {
            let work_dir = string_arg(&args, "workDir").map_err(bad_request)?;
            serde_json::to_value(ops::get_materials(work_dir).map_err(server_error)?).unwrap()
        }
        "get_material_categories" => {
            let work_dir = string_arg(&args, "workDir").map_err(bad_request)?;
            serde_json::to_value(ops::get_material_categories(work_dir, &state.runtime).map_err(server_error)?).unwrap()
        }
        "get_pending_files" => {
            let work_dir = string_arg(&args, "workDir").map_err(bad_request)?;
            serde_json::to_value(ops::get_pending_files(work_dir).map_err(server_error)?).unwrap()
        }
        "read_json_file" => {
            let path = string_arg(&args, "path").map_err(bad_request)?;
            serde_json::json!(ops::read_json_file(path).map_err(server_error)?)
        }
        "write_json_file" => {
            let path = string_arg(&args, "path").map_err(bad_request)?;
            let content = string_arg(&args, "content").map_err(bad_request)?;
            ops::write_json_file(path, content).map_err(server_error)?;
            serde_json::json!(null)
        }
        "write_file" => {
            let path = string_arg(&args, "path").map_err(bad_request)?;
            let content = string_arg(&args, "content").map_err(bad_request)?;
            ops::write_file(path, content).map_err(server_error)?;
            serde_json::json!(null)
        }
        "save_prompt_file" => {
            let file_path = string_arg(&args, "filePath").map_err(bad_request)?;
            let content = string_arg(&args, "content").map_err(bad_request)?;
            ops::save_prompt_file(file_path, content).map_err(server_error)?;
            serde_json::json!(null)
        }
        "read_file" => {
            let path = string_arg(&args, "path").map_err(bad_request)?;
            serde_json::json!(ops::read_file(path).map_err(server_error)?)
        }
        "read_directory" => {
            let path = string_arg(&args, "path").map_err(bad_request)?;
            serde_json::to_value(ops::read_directory(path).map_err(server_error)?).unwrap()
        }
        "search_cases" => {
            let query = string_arg(&args, "query").map_err(bad_request)?;
            ops::search_cases(&state.paths, query).map_err(server_error)?
        }
        other => return Err((StatusCode::NOT_FOUND, format!("不支持的命令: {other}"))),
    };

    Ok(Json(value))
}

async fn read_file_content(
    State(_state): State<WebState>,
    Query(query): Query<TaskQuery>,
) -> Result<Json<Value>, (StatusCode, String)> {
    let path = query.path.ok_or_else(|| (StatusCode::BAD_REQUEST, "缺少 path 参数".to_string()))?;
    let content = ops::read_file(path).map_err(server_error)?;
    Ok(Json(serde_json::json!({ "content": content })))
}

async fn write_file_content(
    State(_state): State<WebState>,
    Json(body): Json<FileWriteRequest>,
) -> Result<Json<Value>, (StatusCode, String)> {
    ops::write_file(body.path, body.content).map_err(server_error)?;
    Ok(Json(serde_json::json!({ "ok": true })))
}

async fn download_file(
    Query(query): Query<TaskQuery>,
) -> Result<Response, (StatusCode, String)> {
    let path = query.path.ok_or_else(|| (StatusCode::BAD_REQUEST, "缺少 path 参数".to_string()))?;
    let file_path = PathBuf::from(&path);
    if !file_path.exists() {
        return Err((StatusCode::NOT_FOUND, "文件不存在".to_string()));
    }
    if file_path.is_dir() {
        return Ok(render_browse_response(&file_path));
    }
    let bytes = tokio::fs::read(&file_path).await.map_err(internal_error)?;
    let filename = file_path.file_name().and_then(|name| name.to_str()).unwrap_or("artifact.bin");
    let mut response = Response::new(Body::from(bytes));
    response.headers_mut().insert(
        header::CONTENT_TYPE,
        HeaderValue::from_static("application/octet-stream"),
    );
    response.headers_mut().insert(
        header::CONTENT_DISPOSITION,
        HeaderValue::from_str(&format!("inline; filename=\"{filename}\"")).map_err(internal_error)?,
    );
    Ok(response)
}

async fn browse_path(
    Query(query): Query<TaskQuery>,
) -> Result<Response, (StatusCode, String)> {
    let path = query.path.ok_or_else(|| (StatusCode::BAD_REQUEST, "缺少 path 参数".to_string()))?;
    let target = PathBuf::from(&path);
    if !target.exists() {
        return Err((StatusCode::NOT_FOUND, "路径不存在".to_string()));
    }
    if target.is_file() {
        return download_file(Query(TaskQuery { page: None, page_size: None, path: Some(path) })).await;
    }
    Ok(render_browse_response(&target))
}

async fn run_task(state: WebState, kind: String, task_id: String, payload: Value) {
    let result = run_task_result(state.clone(), kind, task_id.clone(), payload).await;
    match result {
        Ok(value) => {
            let _ = state.tasks.complete(&task_id, value);
        }
        Err(error) => {
            let _ = state.tasks.fail(&task_id, error.clone());
            let _ = state.tasks.append_log(&task_id, format!("[错误] {error}"));
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
                ops::generate_factor_json(&runtime, string_arg(&payload, "workDir")?, optional_u32_arg(&payload, "groupSize"), logger)
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
                ops::generate_review_rule(
                    &runtime,
                    &settings,
                    &llm_logs,
                    string_arg(&payload, "workDir")?,
                    bool_arg(&payload, "useLlm").unwrap_or(false),
                    optional_string_arg(&payload, "apiKey"),
                    optional_string_arg(&payload, "baseUrl"),
                    optional_string_arg(&payload, "model"),
                    logger,
                )
                .and_then(|result| serde_json::to_value(result).map_err(|error| error.to_string()))
            })
            .await
            .map_err(|error| error.to_string())?
        }
        "regenerate-keypoint" => ops::regenerate_keypoint(
            string_arg(&payload, "kpname").unwrap_or_default(),
            string_arg(&payload, "ruleDesc").unwrap_or_default(),
            string_arg(&payload, "materialName").unwrap_or_default(),
            string_arg(&payload, "targetRule").unwrap_or_default(),
            optional_string_arg(&payload, "apiKey"),
            optional_string_arg(&payload, "baseUrl"),
            optional_string_arg(&payload, "model"),
            optional_u64_arg(&payload, "timeout"),
        )
        .await
        .and_then(|result| serde_json::to_value(result).map_err(|error| error.to_string())),
        other => Err(format!("不支持的任务类型: {other}")),
    }
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
        _ => Err((StatusCode::BAD_REQUEST, format!("未知任务类型: {kind}"))),
    }
}

fn string_arg(args: &Value, key: &str) -> Result<String, String> {
    args.get(key)
        .and_then(Value::as_str)
        .map(ToOwned::to_owned)
        .ok_or_else(|| format!("缺少参数: {key}"))
}

fn optional_string_arg(args: &Value, key: &str) -> Option<String> {
    args.get(key).and_then(Value::as_str).map(ToOwned::to_owned)
}

fn u32_arg(args: &Value, key: &str) -> Result<u32, String> {
    args.get(key)
        .and_then(Value::as_u64)
        .map(|value| value as u32)
        .ok_or_else(|| format!("缺少参数: {key}"))
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
        .ok_or_else(|| format!("缺少参数: {key}"))
}

fn bad_request(error: impl ToString) -> (StatusCode, String) {
    (StatusCode::BAD_REQUEST, error.to_string())
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
