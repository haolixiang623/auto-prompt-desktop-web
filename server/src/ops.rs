use std::collections::HashSet;
use std::fs;
use std::io::{BufRead, BufReader};
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use std::sync::Arc;
use std::thread;
use std::time::Duration;

use chrono::Local;
use regex::Regex;
use serde::{Deserialize, Serialize};
use serde_json::Value;

use crate::config::{params_to_json, DefaultGodPrompts, SettingsStore};
use crate::llm_logs::{LlmLogEntry, LlmLogPage, LlmLogStore};
use crate::paths::AppPaths;
use crate::runtime::{ensure_parent_dir, RuntimeContext};

pub type Logger = Arc<dyn Fn(String) + Send + Sync>;

#[derive(Debug, Serialize, Deserialize)]
pub struct Factor {
    pub field_name: String,
    pub field_code: String,
    pub description: String,
    pub required: bool,
    pub data_type: String,
    #[serde(default)]
    pub material: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct GenerateResult {
    pub output_file: String,
    pub factors_count: usize,
    pub images_count: usize,
    pub prompt_template: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct VerifyResult {
    pub image_file: String,
    pub extraction_output: String,
    pub success: bool,
    pub error: Option<String>,
    #[serde(default)]
    pub elapsed: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct MaterialInfo {
    pub name: String,
    pub path: String,
    pub image_count: usize,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct FileInfo {
    pub name: String,
    pub path: String,
    pub size: u64,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ClassificationReport {
    pub run_time: Option<String>,
    pub base_dir: Option<String>,
    pub material_names: Option<Vec<String>>,
    pub image_count: Option<usize>,
    pub iterations_run: Option<usize>,
    pub extract_prompt_source: Option<String>,
    pub aggregate_prompt_source: Option<String>,
    pub step1_result: Option<Vec<serde_json::Value>>,
    pub step2_plan: Option<Vec<serde_json::Value>>,
    pub step2_summary: Option<serde_json::Value>,
    pub total_files: Option<usize>,
    pub categories: Option<Vec<String>>,
    pub classified_dir: Option<String>,
    pub final_extract_prompt: Option<String>,
    pub final_aggregate_prompt: Option<String>,
    pub extract_template_path: Option<String>,
    pub aggregate_template_path: Option<String>,
    pub extract_template_content: Option<String>,
    pub aggregate_template_content: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct TestPromptResult {
    #[serde(rename = "type")]
    pub kind: String,
    pub pass: bool,
    pub issues: Vec<String>,
    pub attachments: Option<Vec<serde_json::Value>>,
    pub plan: Option<Vec<serde_json::Value>>,
    pub summary: Option<serde_json::Value>,
    pub error: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct FactorJsonResult {
    pub material: String,
    pub success: bool,
    #[serde(default)]
    pub output: String,
    #[serde(default)]
    pub error: String,
    #[serde(default)]
    pub factor_count: usize,
    #[serde(default)]
    pub group_count: usize,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ReviewRuleResult {
    pub material: String,
    pub success: bool,
    pub output: String,
    pub error: String,
    pub keypoint_count: usize,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct KeypointRuleResult {
    pub review_rule: String,
    pub review_rule_text: Option<String>,
    pub content: Option<String>,
    pub review_conditions: Option<serde_json::Value>,
    pub review_rule_js: Option<String>,
    pub passreason: Option<String>,
    pub nopassreason: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct PythonInfo {
    pub available: bool,
    pub version: String,
    pub installable: bool,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct PackageStatus {
    pub name: String,
    pub display_name: String,
    pub installed: bool,
    pub version: String,
    pub description: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct EnvStatus {
    pub python: PythonInfo,
    pub packages: Vec<PackageStatus>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct InstallResult {
    pub success: bool,
    pub output: String,
    pub requires_restart: bool,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ImportResult {
    pub status: String,
    pub imported: usize,
    pub skipped: usize,
    pub failed: usize,
    pub total_cases: usize,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct TxtImportResult {
    pub status: String,
    pub imported: usize,
    pub skipped: usize,
    pub failed: usize,
    pub total_cases: usize,
    pub file_results: Vec<serde_json::Value>,
}

pub fn emit_log(logger: &Logger, line: impl Into<String>) {
    (logger)(line.into());
}

pub fn read_json_file(path: String) -> Result<String, String> {
    fs::read_to_string(path).map_err(|error| format!("读取文件失败: {error}"))
}

pub fn write_json_file(path: String, content: String) -> Result<(), String> {
    ensure_parent_dir(Path::new(&path))?;
    fs::write(path, content.as_bytes()).map_err(|error| format!("写入文件失败: {error}"))
}

pub fn write_file(path: String, content: String) -> Result<(), String> {
    ensure_parent_dir(Path::new(&path))?;
    fs::write(path, content).map_err(|error| format!("写入文件失败: {error}"))
}

pub fn save_prompt_file(file_path: String, content: String) -> Result<(), String> {
    write_file(file_path, content)
}

pub fn read_file(path: String) -> Result<String, String> {
    fs::read_to_string(path).map_err(|error| error.to_string())
}

pub fn read_directory(path: String) -> Result<Vec<serde_json::Value>, String> {
    let entries = fs::read_dir(path).map_err(|error| error.to_string())?;
    let mut result = Vec::new();
    for entry in entries.flatten() {
        let metadata = entry.metadata().map_err(|error| error.to_string())?;
        result.push(serde_json::json!({
            "name": entry.file_name().to_string_lossy().to_string(),
            "path": entry.path().to_string_lossy().to_string(),
            "is_file": metadata.is_file(),
            "is_dir": metadata.is_dir(),
            "size": if metadata.is_file() { Some(metadata.len()) } else { None::<u64> },
        }));
    }
    Ok(result)
}

pub fn get_default_god_prompts(settings: &SettingsStore) -> DefaultGodPrompts {
    settings.default_god_prompts()
}

pub fn get_llm_logs(log_store: &LlmLogStore, page: Option<usize>, page_size: Option<usize>) -> LlmLogPage {
    log_store.page(page.unwrap_or(1), page_size.unwrap_or(20))
}

pub fn clear_llm_logs(log_store: &LlmLogStore) {
    log_store.clear();
}

fn append_llm_log_from_line(log_store: &LlmLogStore, line: &str, default_scene: &str) -> bool {
    let normalized = line.trim_start_matches('\u{feff}');
    let Some(marker_index) = normalized.find("__LLM_LOG__:") else {
        return false;
    };
    let json_str = &normalized[(marker_index + "__LLM_LOG__:".len())..];
    let Ok(value) = serde_json::from_str::<serde_json::Value>(json_str) else {
        return false;
    };

    log_store.append(LlmLogEntry::now(
        value["model"].as_str().unwrap_or("").to_string(),
        value["scene"].as_str().unwrap_or(default_scene).to_string(),
        value["prompt_summary"].as_str().unwrap_or("").to_string(),
        value["response_summary"].as_str().unwrap_or("").to_string(),
        value["elapsed_s"].as_f64(),
        value["success"].as_bool().unwrap_or(true),
        value["error"].as_str().map(ToOwned::to_owned),
    ));
    true
}

pub fn check_environment(runtime: &RuntimeContext) -> Result<EnvStatus, String> {
    let python_info = check_python_availability(runtime);
    let python_cmd = runtime.python_command();
    let packages_meta = vec![
        ("openai", "OpenAI SDK", "AI 模型 API 调用，提示词生成与验证的核心依赖"),
        ("openpyxl", "openpyxl", "Excel 文件读写，用于解析 factors.xlsx 要素表"),
        ("pymupdf", "PyMuPDF (fitz)", "PDF 渲染与图片转换，支持 PDF 格式样本"),
    ];

    let mut packages = Vec::new();
    for (pkg_name, display_name, description) in packages_meta {
        let script = format!("import importlib.metadata; print(importlib.metadata.version('{pkg_name}'))");
        let result = Command::new(&python_cmd).arg("-c").arg(&script).output();
        let status = match result {
            Ok(output) if output.status.success() => PackageStatus {
                name: pkg_name.to_string(),
                display_name: display_name.to_string(),
                installed: true,
                version: String::from_utf8_lossy(&output.stdout).trim().to_string(),
                description: description.to_string(),
            },
            _ => PackageStatus {
                name: pkg_name.to_string(),
                display_name: display_name.to_string(),
                installed: false,
                version: String::new(),
                description: description.to_string(),
            },
        };
        packages.push(status);
    }

    Ok(EnvStatus { python: python_info, packages })
}

pub fn install_packages(runtime: &RuntimeContext, packages: Vec<String>) -> Result<InstallResult, String> {
    if packages.is_empty() {
        return Ok(InstallResult {
            success: true,
            output: "无需安装任何包".to_string(),
            requires_restart: false,
        });
    }

    let python_cmd = runtime.python_command();
    let mut cmd = Command::new(&python_cmd);
    cmd.arg("-m").arg("pip").arg("install");
    for package in packages {
        cmd.arg(package);
    }

    let output = cmd.output().map_err(|error| format!("执行 pip 失败: {error}"))?;
    Ok(InstallResult {
        success: output.status.success(),
        output: combine_output(&output.stdout, &output.stderr),
        requires_restart: false,
    })
}

pub fn install_python() -> Result<InstallResult, String> {
    Err("Web 版默认通过容器或系统 Python 运行，当前不支持在线安装 Python".to_string())
}

pub fn load_case_library(paths: &AppPaths) -> Result<serde_json::Value, String> {
    if !paths.case_library_path.exists() {
        return Ok(serde_json::json!({ "version": "1.0", "cases": [] }));
    }
    let content = fs::read_to_string(&paths.case_library_path)
        .map_err(|error| format!("读取案例库失败: {error}"))?;
    serde_json::from_str(&content).map_err(|error| format!("解析案例库失败: {error}"))
}

pub fn load_review_rule_library(paths: &AppPaths) -> Result<serde_json::Value, String> {
    if !paths.review_rule_library_path.exists() {
        return Ok(serde_json::json!([]));
    }

    let content = fs::read_to_string(&paths.review_rule_library_path)
        .map_err(|error| format!("读取审查规则库失败: {error}"))?;
    let value: Value =
        serde_json::from_str(&content).map_err(|error| format!("解析审查规则库失败: {error}"))?;

    if value.is_array() {
        Ok(value)
    } else {
        Err("审查规则库格式错误，必须为数组".to_string())
    }
}

pub fn save_review_rule_library(paths: &AppPaths, rules: Value) -> Result<(), String> {
    if !rules.is_array() {
        return Err("审查规则库格式错误，必须为数组".to_string());
    }

    ensure_parent_dir(&paths.review_rule_library_path)?;
    let content = serde_json::to_string_pretty(&rules).map_err(|error| error.to_string())?;
    fs::write(&paths.review_rule_library_path, content)
        .map_err(|error| format!("保存审查规则库失败: {error}"))
}

pub fn clear_review_rule_library(paths: &AppPaths) -> Result<(), String> {
    save_review_rule_library(paths, serde_json::json!([]))
}

pub fn search_cases(paths: &AppPaths, query: String) -> Result<serde_json::Value, String> {
    let library = load_case_library(paths)?;
    let query_lower = query.to_lowercase();
    let empty = vec![];
    let cases = library.get("cases").and_then(|value| value.as_array()).unwrap_or(&empty);
    let filtered: Vec<Value> = cases
        .iter()
        .filter(|case_item| {
            let text = format!(
                "{} {} {} {}",
                case_item.get("material_name").or_else(|| case_item.get("material_type")).and_then(Value::as_str).unwrap_or(""),
                case_item.get("factor_name").and_then(Value::as_str).unwrap_or(""),
                case_item.get("extract_desc").or_else(|| case_item.get("prompt_preview")).and_then(Value::as_str).unwrap_or(""),
                case_item.get("extraction_rule").and_then(Value::as_str).unwrap_or("")
            )
            .to_lowercase();
            text.contains(&query_lower)
        })
        .cloned()
        .collect();
    Ok(serde_json::json!({ "cases": filtered }))
}

pub fn import_case_library_json(paths: &AppPaths, source_path: String, overwrite: bool) -> Result<ImportResult, String> {
    let content = fs::read_to_string(&source_path).map_err(|error| format!("读取源文件失败: {error}"))?;
    let mut source: serde_json::Value =
        serde_json::from_str(&content).map_err(|error| format!("源文件格式错误: {error}"))?;
    normalize_case_ids(source.get_mut("cases").and_then(Value::as_array_mut));

    let source_cases = source
        .get("cases")
        .and_then(Value::as_array)
        .ok_or("源文件缺少 cases 字段")?;

    if overwrite || !paths.case_library_path.exists() {
        ensure_parent_dir(&paths.case_library_path)?;
        fs::write(&paths.case_library_path, serde_json::to_string_pretty(&source).unwrap())
            .map_err(|error| format!("写入案例库失败: {error}"))?;
        let count = source_cases.len();
        return Ok(ImportResult {
            status: "success".to_string(),
            imported: count,
            skipped: 0,
            failed: 0,
            total_cases: count,
        });
    }

    let existing_content = fs::read_to_string(&paths.case_library_path).unwrap_or_default();
    let mut library: serde_json::Value =
        serde_json::from_str(&existing_content).unwrap_or_else(|_| serde_json::json!({"version":"1.0","cases":[]}));
    normalize_case_ids(library.get_mut("cases").and_then(Value::as_array_mut));
    let mut imported = 0;
    let mut skipped = 0;
    let total_cases = {
        let existing_cases = library
            .get_mut("cases")
            .and_then(Value::as_array_mut)
            .ok_or("现有案例库格式错误")?;
        let existing_keys: HashSet<String> = existing_cases.iter().map(case_key).collect();

        for case_item in source_cases {
            let key = case_key(case_item);
            if existing_keys.contains(&key) {
                skipped += 1;
            } else {
                existing_cases.push(case_item.clone());
                imported += 1;
            }
        }
        existing_cases.len()
    };

    fs::write(&paths.case_library_path, serde_json::to_string_pretty(&library).unwrap())
        .map_err(|error| format!("保存案例库失败: {error}"))?;

    Ok(ImportResult {
        status: "success".to_string(),
        imported,
        skipped,
        failed: 0,
        total_cases,
    })
}

pub fn delete_case(paths: &AppPaths, case_id: String) -> Result<(), String> {
    let content = fs::read_to_string(&paths.case_library_path).map_err(|error| format!("读取案例库失败: {error}"))?;
    let mut library: serde_json::Value = serde_json::from_str(&content).map_err(|error| format!("解析案例库失败: {error}"))?;
    let cases = library.get_mut("cases").and_then(Value::as_array_mut).ok_or("案例库格式错误")?;
    let initial_len = cases.len();
    cases.retain(|case_item| case_item.get("id").and_then(Value::as_str).unwrap_or("") != case_id);
    if cases.len() == initial_len {
        return Err("案例未找到".to_string());
    }
    fs::write(&paths.case_library_path, serde_json::to_string_pretty(&library).unwrap())
        .map_err(|error| format!("保存案例库失败: {error}"))
}

pub fn import_cases_from_txt(paths: &AppPaths, file_paths: Vec<String>) -> Result<TxtImportResult, String> {
    let mut library = load_case_library(paths)?;
    if library.get("cases").is_none() {
        library["cases"] = serde_json::json!([]);
    }
    let mut imported = 0;
    let mut skipped = 0;
    let mut failed = 0;
    let mut file_results = Vec::new();
    let total_cases = {
        let cases = library.get_mut("cases").and_then(Value::as_array_mut).ok_or("案例库格式错误")?;
        normalize_case_ids(Some(cases));
        let existing_keys: HashSet<String> = cases.iter().map(case_key).collect();
        let mut seen = existing_keys.clone();

        for file_path in file_paths {
            match parse_prompt_file_to_cases(&file_path) {
                Ok(new_cases) if !new_cases.is_empty() => {
                    let mut added = 0;
                    let mut skipped_for_file = 0;
                    for case_item in new_cases {
                        let key = case_key(&case_item);
                        if seen.contains(&key) {
                            skipped += 1;
                            skipped_for_file += 1;
                        } else {
                            seen.insert(key);
                            cases.push(case_item);
                            imported += 1;
                            added += 1;
                        }
                    }
                    file_results.push(serde_json::json!({
                        "file": Path::new(&file_path).file_name().and_then(|name| name.to_str()).unwrap_or(""),
                        "added": added,
                        "skipped": skipped_for_file
                    }));
                }
                Ok(_) => {
                    failed += 1;
                    file_results.push(serde_json::json!({
                        "file": Path::new(&file_path).file_name().and_then(|name| name.to_str()).unwrap_or(""),
                        "added": 0,
                        "skipped": 0,
                        "error": "未能解析出要素"
                    }));
                }
                Err(error) => {
                    failed += 1;
                    file_results.push(serde_json::json!({
                        "file": Path::new(&file_path).file_name().and_then(|name| name.to_str()).unwrap_or(""),
                        "added": 0,
                        "skipped": 0,
                        "error": error
                    }));
                }
            }
        }
        cases.len()
    };

    ensure_parent_dir(&paths.case_library_path)?;
    fs::write(&paths.case_library_path, serde_json::to_string_pretty(&library).unwrap())
        .map_err(|error| format!("保存案例库失败: {error}"))?;

    Ok(TxtImportResult {
        status: "success".to_string(),
        imported,
        skipped,
        failed,
        total_cases,
        file_results,
    })
}

pub fn read_factors(work_dir: String, runtime: &RuntimeContext) -> Result<Vec<Factor>, String> {
    let work_path = PathBuf::from(&work_dir);
    let factors_path = if work_path.join("factors.xlsx").exists() {
        work_path.join("factors.xlsx")
    } else {
        fs::read_dir(&work_path)
            .map_err(|error| error.to_string())?
            .filter_map(Result::ok)
            .find(|entry| {
                entry
                    .path()
                    .extension()
                    .map(|ext| ext == "xlsx" || ext == "xls")
                    .unwrap_or(false)
            })
            .map(|entry| entry.path())
            .ok_or("未找到 factors.xlsx 文件".to_string())?
    };

    let script = format!(
        r#"
import json, openpyxl
wb = openpyxl.load_workbook(r'{path}', read_only=True, data_only=True)
ws = wb.active
headers = [str(c.value or '').strip() for c in next(ws.iter_rows(min_row=1, max_row=1, values_only=False))]
is_extended = '事项' in (headers[0] if headers else '') or (len(headers) > 1 and '材料名称' in headers[1])
results = []
if is_extended:
    current_material = None
    for row in ws.iter_rows(min_row=2, values_only=True):
        raw_mat = row[1] if len(row) > 1 else None
        if raw_mat:
            s = str(raw_mat).strip()
            if s and '\n' not in s and len(s) < 60:
                current_material = s
        if not current_material:
            continue
        factor_name = str(row[3]).strip() if len(row) > 3 and row[3] else ''
        factor_usage = str(row[6]).strip() if len(row) > 6 and row[6] else ''
        if factor_name and '\n' not in factor_name and len(factor_name) <= 50:
            results.append({{'field_name': factor_name, 'field_code': '', 'description': factor_usage, 'required': True, 'data_type': 'string', 'material': current_material}})
else:
    current_material = None
    for row in ws.iter_rows(min_row=2, values_only=True):
        if not any(row):
            continue
        raw_mat = row[0] if row[0] else None
        if raw_mat:
            s = str(raw_mat).strip()
            if s and '\n' not in s and len(s) < 60:
                current_material = s
        factor_name = str(row[1]).strip() if len(row) > 1 and row[1] else ''
        factor_usage = str(row[2]).strip() if len(row) > 2 and row[2] else ''
        if factor_name:
            results.append({{'field_name': factor_name, 'field_code': '', 'description': factor_usage, 'required': True, 'data_type': 'string', 'material': current_material or ''}})
print(json.dumps(results, ensure_ascii=False))
"#,
        path = factors_path.to_string_lossy().replace('\\', "\\\\"),
    );

    let output = runtime.python_process()
        .arg("-c")
        .arg(script)
        .output()
        .map_err(|error| format!("调用Python失败: {error}"))?;

    serde_json::from_str::<Vec<Factor>>(String::from_utf8_lossy(&output.stdout).trim())
        .map_err(|error| format!("解析要素失败: {error}"))
}

pub fn get_materials(work_dir: String) -> Result<Vec<MaterialInfo>, String> {
    let work_path = PathBuf::from(&work_dir);
    let entries = fs::read_dir(&work_path).map_err(|error| format!("无法读取工作目录: {error}"))?;
    let mut materials = Vec::new();
    for entry in entries.flatten() {
        let path = entry.path();
        if path.is_dir() {
            let image_count = fs::read_dir(&path)
                .map_err(|error| format!("无法读取子目录: {error}"))?
                .filter_map(Result::ok)
                .filter(|file| {
                    file.path()
                        .extension()
                        .map(|ext| matches!(ext.to_string_lossy().to_lowercase().as_str(), "jpg" | "jpeg" | "png" | "bmp" | "gif" | "webp" | "pdf"))
                        .unwrap_or(false)
                })
                .count();
            if image_count > 0 {
                materials.push(MaterialInfo {
                    name: path.file_name().unwrap_or_default().to_string_lossy().to_string(),
                    path: path.to_string_lossy().to_string(),
                    image_count,
                });
            }
        }
    }
    materials.sort_by(|left, right| left.name.cmp(&right.name));
    Ok(materials)
}

pub fn get_material_categories(work_dir: String, runtime: &RuntimeContext) -> Result<Vec<String>, String> {
    let work_path = PathBuf::from(&work_dir);
    let factors_path = ["factors.xlsx", "factors.xls", "factors.csv"]
        .iter()
        .map(|name| work_path.join(name))
        .find(|path| path.exists());

    if let Some(path) = factors_path {
        let script = format!(
            r#"
import openpyxl
wb = openpyxl.load_workbook(r'{path}', read_only=True, data_only=True)
ws = wb.active
seen = []
for row in ws.iter_rows(min_row=2, values_only=True):
    if row and row[0] and str(row[0]).strip():
        name = str(row[0]).strip()
        if name not in seen:
            seen.append(name)
print('\n'.join(seen))
"#,
            path = path.to_string_lossy().replace('\\', "\\\\"),
        );
        let output = runtime.python_process()
            .arg("-c")
            .arg(script)
            .output()
            .map_err(|error| format!("调用Python失败: {error}"))?;
        if output.status.success() {
            let names: Vec<String> = String::from_utf8_lossy(&output.stdout)
                .lines()
                .map(str::trim)
                .filter(|line| !line.is_empty())
                .map(ToOwned::to_owned)
                .collect();
            if !names.is_empty() {
                return Ok(names);
            }
        }
    }

    let mut categories = Vec::new();
    for entry in fs::read_dir(&work_path).map_err(|error| error.to_string())?.flatten() {
        let path = entry.path();
        if path.is_dir() {
            let name = path.file_name().unwrap_or_default().to_string_lossy().to_string();
            if !name.starts_with('.') && !["已分类", "待分类", "已分类材料", "待分类材料"].contains(&name.as_str()) {
                categories.push(name);
            }
        }
    }
    if categories.is_empty() {
        return Err("未找到 factors.xlsx 或事项名称子目录".to_string());
    }
    categories.sort();
    Ok(categories)
}

pub fn get_pending_files(work_dir: String) -> Result<Vec<FileInfo>, String> {
    let work_path = PathBuf::from(&work_dir);
    let pending_dir = if work_path.join("待分类材料").exists() {
        work_path.join("待分类材料")
    } else if work_path.join("待分类").exists() {
        work_path.join("待分类")
    } else {
        work_path.clone()
    };

    let mut files = Vec::new();
    for entry in fs::read_dir(&pending_dir).map_err(|error| error.to_string())?.flatten() {
        let path = entry.path();
        if path.is_file() {
            let file_name = entry.file_name().to_string_lossy().to_string();
            if file_name.starts_with('.') || file_name == "Thumbs.db" || file_name == "desktop.ini" {
                continue;
            }
            let metadata = entry.metadata().map_err(|error| error.to_string())?;
            files.push(FileInfo {
                name: file_name,
                path: path.to_string_lossy().to_string(),
                size: metadata.len(),
            });
        }
    }
    Ok(files)
}

pub fn generate_factor_json(
    runtime: &RuntimeContext,
    work_dir: String,
    group_size: Option<u32>,
    logger: Logger,
) -> Result<Vec<FactorJsonResult>, String> {
    let skill_path = runtime.resolve_skill_path("factor-json-generator/generate_factor_json.py")?;
    let mut child = runtime.python_process()
        .arg(skill_path)
        .arg(&work_dir)
        .arg("--group-size")
        .arg(group_size.unwrap_or(4).to_string())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|error| format!("启动Python进程失败: {error}"))?;

    let mut lines = Vec::new();
    if let Some(stdout) = child.stdout.take() {
        for line in BufReader::new(stdout).lines().flatten() {
            if !line.starts_with("RESULTS_JSON:") {
                emit_log(&logger, line.clone());
            }
            lines.push(line);
        }
    }

    let status = child.wait().map_err(|error| error.to_string())?;
    if !status.success() {
        return Err("Python脚本执行失败，请检查日志".to_string());
    }

    for line in &lines {
        if let Some(json_str) = line.strip_prefix("RESULTS_JSON:") {
            return serde_json::from_str::<Vec<FactorJsonResult>>(json_str).map_err(|error| error.to_string());
        }
    }

    let mut results = Vec::new();
    for entry in fs::read_dir(&work_dir).map_err(|error| error.to_string())?.flatten() {
        let path = entry.path();
        if path.is_dir() {
            let material = path.file_name().unwrap_or_default().to_string_lossy().to_string();
            let json_file = path.join(format!("{material}--要素信息录入.json"));
            if json_file.exists() {
                results.push(FactorJsonResult {
                    material,
                    success: true,
                    output: json_file.to_string_lossy().to_string(),
                    error: String::new(),
                    factor_count: 0,
                    group_count: 0,
                });
            }
        }
    }
    Ok(results)
}

pub fn generate_prompt(
    runtime: &RuntimeContext,
    settings: &SettingsStore,
    work_dir: String,
    material_name: Option<String>,
    model_cfg_id: Option<String>,
    logger: Logger,
) -> Result<GenerateResult, String> {
    let work_path = PathBuf::from(&work_dir);
    let material_dir = material_name
        .as_ref()
        .map(|name| work_path.join(name))
        .filter(|path| path.exists())
        .unwrap_or_else(|| work_path.clone());
    let has_media = fs::read_dir(&material_dir)
        .map_err(|error| format!("无法读取材料目录: {error}"))?
        .filter_map(Result::ok)
        .any(|entry| {
            entry
                .path()
                .extension()
                .map(|ext| matches!(ext.to_string_lossy().to_lowercase().as_str(), "jpg" | "jpeg" | "png" | "bmp" | "gif" | "webp" | "pdf"))
                .unwrap_or(false)
        });
    if !has_media {
        return Err(format!("材料目录下缺少图片或PDF文件\n\n目录: {}", material_dir.display()));
    }

    let skill_path = runtime.resolve_skill_path("doc-extract-prompt-gen/generate_prompt.py")?;
    let script_work_dir = material_name.as_ref().map(|_| material_dir.to_string_lossy().to_string()).unwrap_or_else(|| work_dir.clone());
    let model_cfg = settings.get_model_config_by_id(model_cfg_id)?;
    let extra_params = model_cfg
        .as_ref()
        .map(|model| params_to_json(&model.params))
        .unwrap_or_else(|| "{}".to_string());
    let extract_god_prompt = settings.load().map(|s| s.extract_god_prompt).unwrap_or_default();

    let mut cmd = runtime.python_process();
    cmd.arg("-u").arg(skill_path).arg(&script_work_dir);
    if let Some(material) = &material_name {
        cmd.arg(material);
    }
    let mut child = cmd
        .env("DASHSCOPE_API_KEY", settings.get_api_key()?)
        .env("GENERATE_EXTRA_PARAMS", &extra_params)
        .env("EXTRACT_GOD_PROMPT", &extract_god_prompt)
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|error| format!("启动Python进程失败: {error}"))?;

    let stdout = child.stdout.take().ok_or("无法读取进程输出")?;
    let handle = thread::spawn(move || BufReader::new(stdout).lines().flatten().collect::<Vec<_>>());
    let lines = handle.join().unwrap_or_default();
    for line in &lines {
        emit_log(&logger, line.clone());
    }

    let timeout_secs = settings.get_llm_timeout().unwrap_or(120);
    let status = child.wait().map_err(|error| error.to_string())?;
    if !status.success() {
        return Err(format!("生成提示词失败，请检查日志输出（超时设置 {timeout_secs} 秒）"));
    }

    let output_file = lines
        .iter()
        .find(|line| line.contains("已保存至:"))
        .and_then(|line| line.split("已保存至:").nth(1))
        .map(|line| line.trim().to_string())
        .unwrap_or_else(|| {
            let dir_name = PathBuf::from(&script_work_dir)
                .file_name()
                .map(|name| name.to_string_lossy().to_string())
                .unwrap_or_else(|| "output".to_string());
            format!("{script_work_dir}/{dir_name}--要素提取完整提示词.txt")
        });

    Ok(GenerateResult {
        output_file: output_file.clone(),
        factors_count: 0,
        images_count: 0,
        prompt_template: fs::read_to_string(output_file).ok(),
    })
}

pub fn verify_extraction(
    runtime: &RuntimeContext,
    settings: &SettingsStore,
    llm_logs: &LlmLogStore,
    material_dir: String,
    prompt_text: String,
    model_cfg_id: Option<String>,
    logger: Logger,
) -> Result<VerifyResult, String> {
    let dir_path = PathBuf::from(&material_dir);
    let entries: Vec<_> = fs::read_dir(&dir_path).map_err(|error| format!("无法读取材料目录: {error}"))?.flatten().collect();
    let image_entry = entries.iter().find(|entry| {
        entry
            .path()
            .extension()
            .map(|ext| matches!(ext.to_string_lossy().to_lowercase().as_str(), "jpg" | "jpeg" | "png" | "bmp" | "gif" | "webp"))
            .unwrap_or(false)
    });
    let pdf_entry = entries.iter().find(|entry| {
        entry
            .path()
            .extension()
            .map(|ext| ext.to_string_lossy().to_lowercase() == "pdf")
            .unwrap_or(false)
    });

    let image_path = if let Some(entry) = image_entry {
        entry.path()
    } else if let Some(entry) = pdf_entry {
        let pdf_path = entry.path();
        let out_png = dir_path.join("__verify_img_tmp__.png");
        let convert_script = format!(
            "import fitz; doc = fitz.open(r'{pdf}'); page = doc[0]; pix = page.get_pixmap(matrix=fitz.Matrix(2,2)); pix.save(r'{out}'); doc.close(); print('ok')",
            pdf = pdf_path.to_string_lossy().replace('\\', "\\\\"),
            out = out_png.to_string_lossy().replace('\\', "\\\\"),
        );
        let conversion = runtime.python_process()
            .arg("-c")
            .arg(convert_script)
            .output()
            .map_err(|error| format!("PDF转图片失败: {error}"))?;
        if !conversion.status.success() {
            return Err(format!("PDF转换失败: {}", String::from_utf8_lossy(&conversion.stderr)));
        }
        emit_log(&logger, format!("[验证] PDF已转为图片: {}", out_png.display()));
        out_png
    } else {
        return Err("材料目录中未找到图片或PDF文件".to_string());
    };

    let image_name = image_path.file_name().unwrap_or_default().to_string_lossy().to_string();
    emit_log(&logger, format!("[验证] 使用图片: {image_name}"));

    let tmp_prompt = dir_path.join("__verify_prompt_tmp__.txt");
    fs::write(&tmp_prompt, &prompt_text).map_err(|error| format!("写入临时提示词文件失败: {error}"))?;
    let model_cfg = settings.get_model_config_by_id(model_cfg_id)?;
    let model_name = model_cfg
        .as_ref()
        .map(|model| model.model_id.clone())
        .unwrap_or_else(|| settings.load().map(|s| s.model_name).unwrap_or_else(|_| "qwen-vl-max".to_string()));
    let extra_params = model_cfg
        .as_ref()
        .map(|model| params_to_json(&model.params))
        .unwrap_or_else(|| "{}".to_string());

    let script = format!(r#"
import base64, json, os, sys, time
from openai import OpenAI

api_key = os.environ.get('DASHSCOPE_API_KEY', '')
if not api_key:
    print('[验证错误] 未配置 DASHSCOPE_API_KEY', file=sys.stderr)
    sys.exit(1)

model_name = os.environ.get('VERIFY_MODEL_NAME', 'qwen-vl-max')
all_params = json.loads(os.environ.get('VERIFY_EXTRA_PARAMS', '{{}}'))
body_keys = {{'enable_thinking', 'thinking_budget', 'translation_options', 'vl_high_resolution_images', 'search_options'}}
extra = {{k: v for k, v in all_params.items() if k not in body_keys}}
body = {{k: v for k, v in all_params.items() if k in body_keys}}
if body:
    extra['extra_body'] = body

with open(r'{prompt_path}', 'r', encoding='utf-8') as f:
    prompt = f.read()
with open(r'{image_path}', 'rb') as f:
    b64 = base64.b64encode(f.read()).decode('utf-8')
ext = os.path.splitext(r'{image_path}')[1].lower().lstrip('.')
if ext == 'jpg':
    ext = 'jpeg'
client = OpenAI(api_key=api_key, base_url='https://dashscope.aliyuncs.com/compatible-mode/v1')
t0 = time.time()
resp = client.chat.completions.create(
    model=model_name,
    messages=[{{'role': 'user', 'content': [{{'type': 'text', 'text': prompt}}, {{'type': 'image_url', 'image_url': {{'url': 'data:image/' + ext + ';base64,' + b64}}}}]}}],
    **extra
)
elapsed = time.time() - t0
print('__ELAPSED__' + f'{{elapsed:.1f}}')
print(resp.choices[0].message.content)
"#,
        prompt_path = tmp_prompt.to_string_lossy().replace('\\', "\\\\"),
        image_path = image_path.to_string_lossy().replace('\\', "\\\\"),
    );

    let mut child = runtime.python_process()
        .arg("-c")
        .arg(script)
        .env("DASHSCOPE_API_KEY", settings.get_api_key()?)
        .env("VERIFY_MODEL_NAME", &model_name)
        .env("VERIFY_EXTRA_PARAMS", &extra_params)
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|error| format!("启动Python失败: {error}"))?;

    let stdout = child.stdout.take().ok_or("无法读取验证输出")?;
    let stderr = child.stderr.take().ok_or("无法读取验证错误")?;
    let stderr_logger = logger.clone();
    let stderr_handle = thread::spawn(move || {
        let mut text = String::new();
        for line in BufReader::new(stderr).lines().flatten() {
            emit_log(&stderr_logger, line.clone());
            text.push_str(&line);
            text.push('\n');
        }
        text
    });
    let stdout_handle = thread::spawn(move || {
        let mut text = String::new();
        for line in BufReader::new(stdout).lines().flatten() {
            text.push_str(&line);
            text.push('\n');
        }
        text
    });

    let stdout_text = stdout_handle.join().unwrap_or_default();
    let stderr_text = stderr_handle.join().unwrap_or_default();
    let status = child.wait().map_err(|error| error.to_string())?;
    let _ = fs::remove_file(tmp_prompt);

    if status.success() {
        let elapsed = stdout_text
            .lines()
            .find(|line| line.starts_with("__ELAPSED__"))
            .map(|line| line.trim_start_matches("__ELAPSED__").to_string());
        let text = stdout_text
            .lines()
            .filter(|line| !line.starts_with("__ELAPSED__"))
            .collect::<Vec<_>>()
            .join("\n")
            .trim()
            .to_string();
        llm_logs.append(LlmLogEntry::now(
            model_name,
            "验证提取".to_string(),
            prompt_text.chars().take(2000).collect(),
            text.chars().take(2000).collect(),
            elapsed.as_deref().and_then(|value| value.parse::<f64>().ok()),
            true,
            None,
        ));
        Ok(VerifyResult { image_file: image_name, extraction_output: text, success: true, error: None, elapsed })
    } else {
        let error = stderr_text.trim().to_string();
        llm_logs.append(LlmLogEntry::now(
            model_name,
            "验证提取".to_string(),
            prompt_text.chars().take(2000).collect(),
            String::new(),
            None,
            false,
            Some(error.clone()),
        ));
        Ok(VerifyResult { image_file: image_name, extraction_output: String::new(), success: false, error: Some(error), elapsed: None })
    }
}

pub fn classify_materials(
    runtime: &RuntimeContext,
    settings: &SettingsStore,
    llm_logs: &LlmLogStore,
    work_dir: String,
    max_rounds: u32,
    model_cfg_id: Option<String>,
    logger: Logger,
) -> Result<ClassificationReport, String> {
    let skill_path = runtime.resolve_skill_path("material-classifier/classify_materials.py")?;
    let model_cfg = settings.get_model_config_by_id(model_cfg_id)?;
    let model_id = model_cfg
        .as_ref()
        .map(|model| model.model_id.clone())
        .unwrap_or_else(|| settings.load().map(|s| s.model_name).unwrap_or_else(|_| "qwen-vl-max".to_string()));
    let extra_params = model_cfg
        .as_ref()
        .map(|model| params_to_json(&model.params))
        .unwrap_or_else(|| "{}".to_string());
    let god_prompt = settings.load().map(|s| s.god_prompt).unwrap_or_default();
    emit_log(&logger, format!("[分类] 使用模型: {model_id}"));
    if extra_params != "{}" {
        emit_log(&logger, format!("[分类] 额外参数: {extra_params}"));
    }

    let mut child = runtime.python_process()
        .arg("-u")
        .arg(skill_path)
        .arg(&work_dir)
        .arg(max_rounds.to_string())
        .env("DASHSCOPE_API_KEY", settings.get_api_key()?)
        .env("CLASSIFY_MODEL_NAME", &model_id)
        .env("CLASSIFY_EXTRA_PARAMS", &extra_params)
        .env("CLASSIFY_GOD_PROMPT", &god_prompt)
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|error| format!("启动Python进程失败: {error}"))?;

    let stdout = child.stdout.take().ok_or("无法读取分类输出")?;
    let stderr = child.stderr.take().ok_or("无法读取分类错误")?;
    let stdout_logger = logger.clone();
    let stderr_logger = logger.clone();
    let llm_log_store = llm_logs.clone();
    let _stderr_llm_log_store = llm_logs.clone();
    let stdout_handle = thread::spawn(move || {
        let mut lines = Vec::new();
        for line in BufReader::new(stdout).lines().flatten() {
            if append_llm_log_from_line(&llm_log_store, &line, "鏉愭枡鍒嗙被") {
                lines.push(line);
                continue;
            }
            if let Some(json_str) = line.strip_prefix("__LLM_LOG__:") {
                if let Ok(value) = serde_json::from_str::<serde_json::Value>(json_str) {
                    llm_log_store.append(LlmLogEntry::now(
                        value["model"].as_str().unwrap_or("").to_string(),
                        value["scene"].as_str().unwrap_or("材料分类").to_string(),
                        value["prompt_summary"].as_str().unwrap_or("").to_string(),
                        value["response_summary"].as_str().unwrap_or("").to_string(),
                        value["elapsed_s"].as_f64(),
                        value["success"].as_bool().unwrap_or(true),
                        value["error"].as_str().map(ToOwned::to_owned),
                    ));
                }
            } else {
                emit_log(&stdout_logger, line.clone());
            }
            lines.push(line);
        }
        lines
    });
    let stderr_handle = thread::spawn(move || {
        let mut lines = Vec::new();
        for line in BufReader::new(stderr).lines().flatten() {
            emit_log(&stderr_logger, format!("[错误] {line}"));
            lines.push(line);
        }
        lines
    });
    let status = child.wait().map_err(|error| error.to_string())?;
    let lines = stdout_handle.join().unwrap_or_default();
    let errors = stderr_handle.join().unwrap_or_default();
    if !status.success() {
        return Err(format!("Python脚本执行失败: {}", errors.join("\n")));
    }
    if lines.iter().any(|line| line.contains("DASHSCOPE_API_KEY") || line.contains("API Key")) {
        return Err("未配置API密钥，请前往【设置】页面配置 DASHSCOPE_API_KEY".to_string());
    }

    let report_path = PathBuf::from(&work_dir).join("classification_report.json");
    let report_content = fs::read_to_string(&report_path).map_err(|error| format!("读取报告文件失败: {error}"))?;
    let mut result: ClassificationReport =
        serde_json::from_str(&report_content).map_err(|error| format!("解析报告失败: {error}"))?;
    result.total_files = result.image_count;
    result.categories = result.material_names.clone();
    result.classified_dir = result.base_dir.as_ref().map(|dir| format!("{dir}/已分类材料"));

    let extract_latest_path = PathBuf::from(&work_dir).join("最新分类信息提取提示词.txt");
    let aggregate_latest_path = PathBuf::from(&work_dir).join("最新分类附件归集提示词.txt");
    let extract_template_path = runtime.resolve_skill_path("material-classifier/分类信息提取提示词模板.txt").ok();
    let aggregate_template_path = runtime.resolve_skill_path("material-classifier/分类附件归集提示词模板.txt").ok();
    let mut extract_prompt = fs::read_to_string(&extract_latest_path)
        .ok()
        .or_else(|| extract_template_path.as_ref().and_then(|path| fs::read_to_string(path).ok()));
    let mut aggregate_prompt = fs::read_to_string(&aggregate_latest_path)
        .ok()
        .or_else(|| aggregate_template_path.as_ref().and_then(|path| fs::read_to_string(path).ok()));
    if let Some(names) = &result.material_names {
        let material_list_text = names.iter().map(|name| format!("- {name}")).collect::<Vec<_>>().join("\n");
        if let Some(prompt) = &mut extract_prompt {
            *prompt = prompt.replace("$(material_list)", &material_list_text);
        }
        if let Some(prompt) = &mut aggregate_prompt {
            *prompt = prompt.replace("$(material_list)", &material_list_text);
        }
    }
    result.final_extract_prompt = extract_prompt;
    result.final_aggregate_prompt = aggregate_prompt;
    result.extract_template_path = extract_template_path.as_ref().map(|path| path.to_string_lossy().to_string());
    result.aggregate_template_path = aggregate_template_path.as_ref().map(|path| path.to_string_lossy().to_string());
    result.extract_template_content = extract_template_path
        .as_ref()
        .and_then(|path| fs::read_to_string(path).ok())
        .map(|content| replace_material_placeholder(content, result.material_names.as_ref()));
    result.aggregate_template_content = aggregate_template_path
        .as_ref()
        .and_then(|path| fs::read_to_string(path).ok())
        .map(|content| replace_material_placeholder(content, result.material_names.as_ref()));

    Ok(result)
}

pub fn test_classify_prompt(
    runtime: &RuntimeContext,
    settings: &SettingsStore,
    work_dir: String,
    prompt_type: String,
    prompt_content: String,
    model_cfg_id: Option<String>,
    logger: Logger,
) -> Result<TestPromptResult, String> {
    let skill_path = runtime.resolve_skill_path("material-classifier/classify_materials.py")?;
    let model_cfg = settings.get_model_config_by_id(model_cfg_id)?;
    let model_id = model_cfg
        .as_ref()
        .map(|model| model.model_id.clone())
        .unwrap_or_else(|| settings.load().map(|s| s.model_name).unwrap_or_else(|_| "qwen-vl-max".to_string()));
    let extra_params = model_cfg
        .as_ref()
        .map(|model| params_to_json(&model.params))
        .unwrap_or_else(|| "{}".to_string());
    let tmp_path = PathBuf::from(&work_dir).join(format!(".test_prompt_{prompt_type}.txt"));
    fs::write(&tmp_path, &prompt_content).map_err(|error| format!("写入临时文件失败: {error}"))?;

    let mut child = runtime.python_process()
        .arg("-u")
        .arg(skill_path)
        .arg(format!("--test-prompt={prompt_type}"))
        .arg(format!("--prompt-file={}", tmp_path.to_string_lossy()))
        .arg(&work_dir)
        .env("DASHSCOPE_API_KEY", settings.get_api_key()?)
        .env("CLASSIFY_MODEL_NAME", &model_id)
        .env("CLASSIFY_EXTRA_PARAMS", &extra_params)
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|error| format!("启动Python进程失败: {error}"))?;
    let stdout = child.stdout.take().ok_or("无法读取测试输出")?;
    let stderr = child.stderr.take().ok_or("无法读取测试错误")?;
    let stdout_logger = logger.clone();
    let stderr_logger = logger.clone();
    let stdout_handle = thread::spawn(move || {
        let mut lines = Vec::new();
        for line in BufReader::new(stdout).lines().flatten() {
            if !line.starts_with("TEST_RESULT_JSON:") {
                emit_log(&stdout_logger, line.clone());
            }
            lines.push(line);
        }
        lines
    });
    let stderr_handle = thread::spawn(move || {
        let mut lines = Vec::new();
        for line in BufReader::new(stderr).lines().flatten() {
            emit_log(&stderr_logger, format!("[错误] {line}"));
            lines.push(line);
        }
        lines
    });
    let status = child.wait().map_err(|error| error.to_string())?;
    let lines = stdout_handle.join().unwrap_or_default();
    let errors = stderr_handle.join().unwrap_or_default();
    let _ = fs::remove_file(tmp_path);
    if !status.success() {
        return Err(format!("测试执行失败: {}", errors.join("\n")));
    }
    for line in &lines {
        if let Some(json_str) = line.strip_prefix("TEST_RESULT_JSON:") {
            return serde_json::from_str(json_str).map_err(|error| error.to_string());
        }
    }
    Err("未能解析测试结果".to_string())
}

pub fn generate_review_rule(
    runtime: &RuntimeContext,
    settings: &SettingsStore,
    llm_logs: &LlmLogStore,
    work_dir: String,
    use_llm: bool,
    api_key: Option<String>,
    base_url: Option<String>,
    model: Option<String>,
    logger: Logger,
) -> Result<Vec<ReviewRuleResult>, String> {
    let skill_path = runtime.resolve_skill_path("review-rule-generator/generate_review_rule.py")?;
    let timeout = settings.get_llm_timeout().unwrap_or(120);
    let extra_params = settings
        .get_model_config_by_id(None)?
        .as_ref()
        .map(|model| params_to_json(&model.params))
        .unwrap_or_else(|| "{}".to_string());

    let mut cmd = runtime.python_process();
    cmd.arg("-u")
        .arg(skill_path)
        .arg(&work_dir)
        .arg("--timeout")
        .arg(timeout.to_string())
        .env("GENERATE_EXTRA_PARAMS", &extra_params)
        .env("PYTHONUNBUFFERED", "1")
        .stdout(Stdio::piped())
        .stderr(Stdio::piped());
    if use_llm {
        cmd.arg("--use-llm");
        if let Some(key) = api_key.filter(|value| !value.is_empty()) {
            cmd.arg("--api-key").arg(key);
        }
        if let Some(url) = base_url.filter(|value| !value.is_empty()) {
            cmd.arg("--base-url").arg(url);
        }
        if let Some(model_name) = model.filter(|value| !value.is_empty()) {
            cmd.arg("--model").arg(model_name);
        }
    }

    let mut child = cmd.spawn().map_err(|error| format!("启动Python进程失败: {error}"))?;
    let stdout = child.stdout.take().ok_or("无法读取审查规则输出")?;
    let stderr = child.stderr.take().ok_or("无法读取审查规则错误")?;
    let stdout_logger = logger.clone();
    let stderr_logger = logger.clone();
    let llm_log_store = llm_logs.clone();
    let stderr_llm_log_store = llm_logs.clone();
    let stdout_handle = thread::spawn(move || {
        let mut lines = Vec::new();
        for line in BufReader::new(stdout).lines().flatten() {
            if append_llm_log_from_line(&llm_log_store, &line, "瀹℃煡瑙勫垯鐢熸垚") {
                lines.push(line);
                continue;
            }
            if let Some(json_str) = line.strip_prefix("__LLM_LOG__:") {
                if let Ok(value) = serde_json::from_str::<serde_json::Value>(json_str) {
                    llm_log_store.append(LlmLogEntry::now(
                        value["model"].as_str().unwrap_or("").to_string(),
                        value["scene"].as_str().unwrap_or("审查规则生成").to_string(),
                        value["prompt_summary"].as_str().unwrap_or("").to_string(),
                        value["response_summary"].as_str().unwrap_or("").to_string(),
                        value["elapsed_s"].as_f64(),
                        value["success"].as_bool().unwrap_or(true),
                        value["error"].as_str().map(ToOwned::to_owned),
                    ));
                }
            } else if !line.starts_with("RESULTS_JSON:") {
                emit_log(&stdout_logger, line.clone());
            }
            lines.push(line);
        }
        lines
    });
    let stderr_handle = thread::spawn(move || {
        for line in BufReader::new(stderr).lines().flatten() {
            if append_llm_log_from_line(&stderr_llm_log_store, &line, "瀹℃煡瑙勫垯鐢熸垚") {
                continue;
            }
            if let Some(json_str) = line.strip_prefix("__LLM_LOG__:") {
                if let Ok(value) = serde_json::from_str::<serde_json::Value>(json_str) {
                    stderr_llm_log_store.append(LlmLogEntry::now(
                        value["model"].as_str().unwrap_or("").to_string(),
                        value["scene"].as_str().unwrap_or("瀹℃煡瑙勫垯鐢熸垚").to_string(),
                        value["prompt_summary"].as_str().unwrap_or("").to_string(),
                        value["response_summary"].as_str().unwrap_or("").to_string(),
                        value["elapsed_s"].as_f64(),
                        value["success"].as_bool().unwrap_or(true),
                        value["error"].as_str().map(ToOwned::to_owned),
                    ));
                    continue;
                }
            }
            emit_log(&stderr_logger, format!("[stderr] {line}"));
        }
    });
    let status = child.wait().map_err(|error| format!("等待Python进程失败: {error}"))?;
    let lines = stdout_handle.join().unwrap_or_default();
    let _ = stderr_handle.join();
    if !status.success() {
        // still allow fallback file scan
    }
    for line in &lines {
        if let Some(json_str) = line.strip_prefix("RESULTS_JSON:") {
            #[derive(Deserialize)]
            struct PyResult {
                material: String,
                success: bool,
                #[serde(default)]
                output: String,
                #[serde(default)]
                error: String,
                #[serde(default)]
                keypoint_count: usize,
            }
            let results = serde_json::from_str::<Vec<PyResult>>(json_str).map_err(|error| error.to_string())?;
            return Ok(results
                .into_iter()
                .map(|result| ReviewRuleResult {
                    material: result.material,
                    success: result.success,
                    output: result.output,
                    error: result.error,
                    keypoint_count: result.keypoint_count,
                })
                .collect());
        }
    }

    let mut results = Vec::new();
    for entry in fs::read_dir(&work_dir).map_err(|error| error.to_string())?.flatten() {
        let path = entry.path();
        if path.is_dir() {
            let material = path.file_name().unwrap_or_default().to_string_lossy().to_string();
            let json_file = path.join(format!("{material}--审查规则导入.json"));
            if json_file.exists() {
                results.push(ReviewRuleResult {
                    material,
                    success: true,
                    output: json_file.to_string_lossy().to_string(),
                    error: String::new(),
                    keypoint_count: 0,
                });
            }
        } else if path
            .file_name()
            .map(|name| name.to_string_lossy().ends_with("--审查规则导入.json"))
            .unwrap_or(false)
        {
            let filename = path.file_name().unwrap_or_default().to_string_lossy().to_string();
            results.push(ReviewRuleResult {
                material: filename.replace("--审查规则导入.json", ""),
                success: true,
                output: path.to_string_lossy().to_string(),
                error: String::new(),
                keypoint_count: 0,
            });
        }
    }
    Ok(results)
}

pub async fn regenerate_keypoint(
    kpname: String,
    rule_desc: String,
    material_name: String,
    target_rule: String,
    api_key: Option<String>,
    base_url: Option<String>,
    model: Option<String>,
    timeout: Option<u64>,
) -> Result<KeypointRuleResult, String> {
    let prompt = format!(
        r#"你是一个审查规则分析专家。请根据以下审查要点规则说明，生成符合导入规范的审查规则JSON。

## 审查背景
- 材料名称: {material_name}
- 审查要点名称: {kpname}
- 审查要点规则说明: {rule_desc}

## 要求
- 必须使用审查方式: {target_rule} (1=大模型, 2=规则对比, 3=Groovy脚本)
- review_rule_text: 简洁的审查规则文本描述
- content: 当review_rule=1时，填写LLM提示词；否则为空
- review_conditions: 当review_rule=2时，填写规则对比条件JSON
- review_rule_js: 当review_rule=3时，填写Groovy脚本

## 输出格式（严格JSON，无多余内容）
{{
  "review_rule": "{target_rule}",
  "review_rule_text": "...",
  "content": "...",
  "review_conditions": null,
  "review_rule_js": "",
  "passreason": "...",
  "nopassreason": "..."
}}"#
    );

    let client = reqwest::Client::new();
    let payload = serde_json::json!({
        "model": model.unwrap_or_else(|| "qwen-plus".to_string()),
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "max_tokens": 2000,
    });
    let response = client
        .post(format!(
            "{}/chat/completions",
            base_url.unwrap_or_else(|| "https://dashscope.aliyuncs.com/compatible-mode/v1".to_string())
        ))
        .header("Content-Type", "application/json")
        .header("Authorization", format!("Bearer {}", api_key.unwrap_or_default()))
        .json(&payload)
        .timeout(Duration::from_secs(timeout.unwrap_or(120)))
        .send()
        .await
        .map_err(|error| format!("LLM 调用失败: {error}"))?;
    let response_json: serde_json::Value = response.json().await.map_err(|error| format!("解析响应失败: {error}"))?;
    let content = response_json["choices"][0]["message"]["content"]
        .as_str()
        .ok_or("无法获取响应内容")?;
    let json_match = Regex::new(r"\{[\s\S]*\}")
        .ok()
        .and_then(|regex| regex.find(content))
        .ok_or("响应中未找到 JSON")?;
    serde_json::from_str(json_match.as_str()).map_err(|error| format!("解析结果失败: {error}"))
}

fn combine_output(stdout: &[u8], stderr: &[u8]) -> String {
    let stdout = String::from_utf8_lossy(stdout).to_string();
    let stderr = String::from_utf8_lossy(stderr).to_string();
    if stderr.trim().is_empty() {
        stdout.trim().to_string()
    } else if stdout.trim().is_empty() {
        stderr.trim().to_string()
    } else {
        format!("{}\n{}", stdout.trim(), stderr.trim())
    }
}

fn check_python_availability(runtime: &RuntimeContext) -> PythonInfo {
    let python_cmd = runtime.python_command();
    if let Ok(output) = Command::new(&python_cmd).arg("--version").output() {
        if output.status.success() {
            let stdout = String::from_utf8_lossy(&output.stdout).trim().to_string();
            let stderr = String::from_utf8_lossy(&output.stderr).trim().to_string();
            return PythonInfo {
                available: true,
                version: if stdout.is_empty() { stderr } else { stdout },
                installable: false,
            };
        }
    }
    PythonInfo {
        available: false,
        version: String::new(),
        installable: false,
    }
}

fn replace_material_placeholder(content: String, material_names: Option<&Vec<String>>) -> String {
    if let Some(names) = material_names {
        let material_list_text = names.iter().map(|name| format!("- {name}")).collect::<Vec<_>>().join("\n");
        content.replace("$(material_list)", &material_list_text)
    } else {
        content
    }
}

fn case_key(case_item: &Value) -> String {
    format!(
        "{}:{}",
        case_item.get("material_name").and_then(Value::as_str).unwrap_or(""),
        case_item.get("factor_name").and_then(Value::as_str).unwrap_or("")
    )
}

fn normalize_case_ids(cases: Option<&mut Vec<Value>>) {
    if let Some(items) = cases {
        for case_item in items {
            if case_item.get("id").and_then(Value::as_str).unwrap_or("").is_empty() {
                case_item["id"] = Value::String(uuid::Uuid::new_v4().to_string());
            }
        }
    }
}

fn parse_prompt_file_to_cases(file_path: &str) -> Result<Vec<Value>, String> {
    let content = fs::read_to_string(file_path).map_err(|error| format!("读取文件失败: {error}"))?;
    let section_regex = Regex::new(r"(?s)# 识别要素列表及规则\s*\n(.*?)(?:\n# |\z)").map_err(|error| error.to_string())?;
    let factor_regex = Regex::new(r"(?s)##\s*\d+[\.、]([^\n]+)\n(.*?)(?=\n##\s*\d+[\.、]|\n# |\z)").map_err(|error| error.to_string())?;
    let material_name = Path::new(file_path)
        .file_name()
        .and_then(|name| name.to_str())
        .unwrap_or("通用")
        .replace("--要素提取完整提示词.txt", "")
        .replace(".txt", "");

    let Some(section) = section_regex
        .captures(&content)
        .and_then(|captures| captures.get(1))
        .map(|match_item| match_item.as_str().to_string())
    else {
        return Ok(Vec::new());
    };

    let mut cases = Vec::new();
    for captures in factor_regex.captures_iter(&section) {
        let factor_name = captures.get(1).map(|value| value.as_str().trim()).unwrap_or("");
        let rule_text = captures.get(2).map(|value| value.as_str().trim()).unwrap_or("");
        if factor_name.is_empty() {
            continue;
        }
        let parts: Vec<&str> = Regex::new(r"[，。](?=[^，。]*$)")
            .unwrap()
            .split(rule_text)
            .collect();
        let (extraction_rule, format_requirement) = if parts.len() == 2 {
            (format!("{}。", parts[0].trim()), parts[1].trim().to_string())
        } else {
            (rule_text.to_string(), "保持原格式".to_string())
        };
        cases.push(serde_json::json!({
            "id": uuid::Uuid::new_v4().to_string(),
            "material_name": material_name,
            "factor_name": factor_name,
            "extract_desc": "",
            "rule_desc": "",
            "extraction_rule": extraction_rule,
            "format_requirement": format_requirement,
            "source": "imported",
            "created_at": Local::now().format("%Y-%m-%d %H:%M:%S").to_string(),
            "tags": [],
            "source_file": Path::new(file_path).file_name().and_then(|name| name.to_str()).unwrap_or("")
        }));
    }
    Ok(cases)
}

#[cfg(test)]
mod tests {
    use super::FactorJsonResult;

    #[test]
    fn factor_json_result_accepts_success_payload_without_error_field() {
        let payload = r#"[{
            "material":"营业执照",
            "success":true,
            "output":"/tmp/out.json",
            "factor_count":2,
            "group_count":1
        }]"#;

        let results = serde_json::from_str::<Vec<FactorJsonResult>>(payload).unwrap();

        assert_eq!(results.len(), 1);
        assert!(results[0].success);
        assert_eq!(results[0].error, "");
        assert_eq!(results[0].factor_count, 2);
        assert_eq!(results[0].group_count, 1);
    }

    #[test]
    fn factor_json_result_accepts_failure_payload_without_output_counts() {
        let payload = r#"[{
            "material":"营业执照",
            "success":false,
            "error":"材料目录不存在"
        }]"#;

        let results = serde_json::from_str::<Vec<FactorJsonResult>>(payload).unwrap();

        assert_eq!(results.len(), 1);
        assert!(!results[0].success);
        assert_eq!(results[0].output, "");
        assert_eq!(results[0].factor_count, 0);
        assert_eq!(results[0].group_count, 0);
    }
}
