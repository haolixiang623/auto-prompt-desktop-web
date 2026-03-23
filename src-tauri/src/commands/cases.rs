use serde::{Deserialize, Serialize};
use std::path::PathBuf;
use std::process::Command;
use std::io::{BufRead, BufReader};
use std::process::Stdio;
use tauri::Window;

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct Case {
    pub id: String,
    pub material_type: String,
    pub fields: Vec<CaseField>,
    pub source_file: String,
    pub prompt_preview: String,
    pub created_at: String,
    pub tags: Vec<String>,
    pub quality_score: Option<f64>,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct CaseField {
    pub field_name: String,
    pub description: String,
    pub extraction_rule: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct CaseLibrary {
    pub version: String,
    pub created_at: String,
    pub updated_at: String,
    pub cases: Vec<Case>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ImportResult {
    pub status: String,
    pub imported: usize,
    pub skipped: usize,
    pub failed: usize,
    pub total_cases: usize,
}

fn get_case_library_path() -> Result<PathBuf, String> {
    super::path_utils::case_library_path()
}

#[tauri::command]
pub async fn load_case_library() -> Result<serde_json::Value, String> {
    let library_path = get_case_library_path()?;

    if !library_path.exists() {
        return Ok(serde_json::json!({ "version": "1.0", "cases": [] }));
    }

    let content = std::fs::read_to_string(&library_path)
        .map_err(|e| format!("读取案例库失败: {}", e))?;

    let library: serde_json::Value = serde_json::from_str(&content)
        .map_err(|e| format!("解析案例库失败: {}", e))?;

    Ok(library)
}

#[tauri::command]
pub async fn search_cases(query: String) -> Result<serde_json::Value, String> {
    let library = load_case_library().await?;
    let query_lower = query.to_lowercase();

    let empty = vec![];
    let cases = library.get("cases").and_then(|c| c.as_array()).unwrap_or(&empty);

    let results: Vec<serde_json::Value> = cases
        .iter()
        .filter(|c| {
            let text = format!(
                "{} {} {} {}",
                c.get("material_name").or_else(|| c.get("material_type")).and_then(|v| v.as_str()).unwrap_or(""),
                c.get("factor_name").and_then(|v| v.as_str()).unwrap_or(""),
                c.get("extract_desc").or_else(|| c.get("prompt_preview")).and_then(|v| v.as_str()).unwrap_or(""),
                c.get("extraction_rule").and_then(|v| v.as_str()).unwrap_or(""),
            ).to_lowercase();
            text.contains(&query_lower)
        })
        .cloned()
        .collect();

    Ok(serde_json::json!({ "cases": results }))
}

#[tauri::command]
pub async fn import_cases(source_dir: Option<String>) -> Result<ImportResult, String> {
    let skill_path = get_skill_path("case-import/import_cases.py")?;

    let mut cmd = Command::new("python3");
    cmd.arg(&skill_path)
        .arg("import")
        .arg("--output-json");

    if let Some(dir) = source_dir {
        cmd.arg("--source-dir").arg(dir);
    }

    let output = cmd.output().map_err(|e| e.to_string())?;

    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        return Err(format!("Python脚本执行失败: {}", stderr));
    }

    let stdout = String::from_utf8_lossy(&output.stdout);
    let last_line = stdout.lines().last().unwrap_or("{}");

    let result: ImportResult = serde_json::from_str(last_line)
        .map_err(|e| format!("解析结果失败: {}", e))?;

    Ok(result)
}

#[tauri::command]
pub async fn import_case_library_json(source_path: String, overwrite: bool) -> Result<ImportResult, String> {
    // Read source JSON
    let content = std::fs::read_to_string(&source_path)
        .map_err(|e| format!("读取源文件失败: {}", e))?;

    // Parse source to validate
    let source: serde_json::Value = serde_json::from_str(&content)
        .map_err(|e| format!("源文件格式错误: {}", e))?;

    let source_cases = source.get("cases")
        .and_then(|c| c.as_array())
        .ok_or("源文件缺少 cases 字段")?;

    let library_path = get_case_library_path()?;

    if overwrite || !library_path.exists() {
        // Ensure parent directory exists
        if let Some(parent) = library_path.parent() {
            std::fs::create_dir_all(parent)
                .map_err(|e| format!("创建目录失败: {}", e))?;
        }
        std::fs::write(&library_path, &content)
            .map_err(|e| format!("写入案例库失败: {}", e))?;
        let count = source_cases.len();
        return Ok(ImportResult {
            status: "success".to_string(),
            imported: count,
            skipped: 0,
            failed: 0,
            total_cases: count,
        });
    }

    // Merge: append cases that don't exist yet (by factor_name+material_name)
    let existing_content = std::fs::read_to_string(&library_path).unwrap_or_default();
    let mut library: serde_json::Value = serde_json::from_str(&existing_content)
        .unwrap_or_else(|_| serde_json::json!({"version": "1.0", "cases": []}));

    let existing_cases = library.get_mut("cases")
        .and_then(|c| c.as_array_mut())
        .ok_or("现有案例库格式错误")?;

    let existing_keys: std::collections::HashSet<String> = existing_cases
        .iter()
        .map(|c| format!(
            "{}:{}",
            c.get("material_name").and_then(|v| v.as_str()).unwrap_or(""),
            c.get("factor_name").and_then(|v| v.as_str()).unwrap_or("")
        ))
        .collect();

    let mut imported = 0;
    let mut skipped = 0;
    for case in source_cases {
        let key = format!(
            "{}:{}",
            case.get("material_name").and_then(|v| v.as_str()).unwrap_or(""),
            case.get("factor_name").and_then(|v| v.as_str()).unwrap_or("")
        );
        if existing_keys.contains(&key) {
            skipped += 1;
        } else {
            existing_cases.push(case.clone());
            imported += 1;
        }
    }

    let total = existing_cases.len();
    let out = serde_json::to_string_pretty(&library).map_err(|e| e.to_string())?;
    std::fs::write(&library_path, out)
        .map_err(|e| format!("保存案例库失败: {}", e))?;

    Ok(ImportResult {
        status: "success".to_string(),
        imported,
        skipped,
        failed: 0,
        total_cases: total,
    })
}

#[tauri::command]
pub async fn delete_case(case_id: String) -> Result<(), String> {
    let library_path = get_case_library_path()?;

    let content = std::fs::read_to_string(&library_path)
        .map_err(|e| format!("读取案例库失败: {}", e))?;

    let mut library: serde_json::Value = serde_json::from_str(&content)
        .map_err(|e| format!("解析案例库失败: {}", e))?;

    let cases = library.get_mut("cases")
        .and_then(|c| c.as_array_mut())
        .ok_or("案例库格式错误")?;

    let initial_len = cases.len();
    cases.retain(|c| {
        c.get("id").and_then(|v| v.as_str()).unwrap_or("") != case_id
    });

    if cases.len() == initial_len {
        return Err("案例未找到".to_string());
    }

    let out = serde_json::to_string_pretty(&library).map_err(|e| e.to_string())?;
    std::fs::write(&library_path, out)
        .map_err(|e| format!("保存案例库失败: {}", e))?;

    Ok(())
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

#[tauri::command]
pub async fn import_cases_from_txt(
    file_paths: Vec<String>,
    window: Window,
) -> Result<TxtImportResult, String> {
    let skill_path = get_skill_path("case-import/import_cases.py")?;

    let mut cmd = Command::new("python3");
    cmd.arg(&skill_path)
        .arg("--files")
        .args(&file_paths)
        .stdout(Stdio::piped())
        .stderr(Stdio::piped());

    let mut child = cmd.spawn().map_err(|e| format!("启动Python进程失败: {}", e))?;

    let mut all_lines: Vec<String> = Vec::new();
    if let Some(stdout) = child.stdout.take() {
        let reader = BufReader::new(stdout);
        for line in reader.lines() {
            if let Ok(line) = line {
                if !line.starts_with("RESULTS_JSON:") {
                    let _ = window.emit("skill-log", &line);
                }
                all_lines.push(line);
            }
        }
    }

    let status = child.wait().map_err(|e| e.to_string())?;
    if !status.success() {
        return Err("Python脚本执行失败，请检查日志".to_string());
    }

    for line in &all_lines {
        if let Some(json_str) = line.strip_prefix("RESULTS_JSON:") {
            if let Ok(r) = serde_json::from_str::<TxtImportResult>(json_str) {
                return Ok(r);
            }
        }
    }

    Err("未能解析导入结果".to_string())
}

fn get_skill_path(skill_relative_path: &str) -> Result<PathBuf, String> {
    super::path_utils::resolve_skill_path(skill_relative_path)
}
