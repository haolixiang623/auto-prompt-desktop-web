use serde::{Deserialize, Serialize};
use std::path::PathBuf;
use std::process::Command;
use std::io::{BufRead, BufReader};
use std::process::Stdio;
use tauri::Window;

#[derive(Debug, Serialize, Deserialize)]
pub struct FactorJsonResult {
    pub material: String,
    pub success: bool,
    pub output: String,
    pub error: String,
    pub factor_count: usize,
    pub group_count: usize,
}

#[tauri::command]
pub async fn generate_factor_json(
    work_dir: String,
    group_size: Option<u32>,
    window: Window,
) -> Result<Vec<FactorJsonResult>, String> {
    let skill_path = get_skill_path("factor-json-generator/generate_factor_json.py")?;
    let gs = group_size.unwrap_or(4).to_string();

    let mut child = Command::new("python3")
        .arg(&skill_path)
        .arg(&work_dir)
        .arg("--group-size")
        .arg(&gs)
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|e| format!("启动Python进程失败: {}", e))?;

    let mut all_lines: Vec<String> = Vec::new();
    if let Some(stdout) = child.stdout.take() {
        let reader = BufReader::new(stdout);
        for line in reader.lines() {
            if let Ok(line) = line {
                // Don't emit the RESULTS_JSON line to the log
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

    // Prefer structured RESULTS_JSON line from Python output
    for line in &all_lines {
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
                factor_count: usize,
                #[serde(default)]
                group_count: usize,
            }
            if let Ok(py_results) = serde_json::from_str::<Vec<PyResult>>(json_str) {
                return Ok(py_results.into_iter().map(|r| FactorJsonResult {
                    material: r.material,
                    success: r.success,
                    output: r.output,
                    error: r.error,
                    factor_count: r.factor_count,
                    group_count: r.group_count,
                }).collect());
            }
        }
    }

    // Fallback: scan work_dir for generated files
    let work_path = PathBuf::from(&work_dir);
    let mut results: Vec<FactorJsonResult> = Vec::new();
    if let Ok(entries) = std::fs::read_dir(&work_path) {
        for entry in entries.filter_map(|e| e.ok()) {
            let path = entry.path();
            if path.is_dir() {
                let material = path.file_name()
                    .map(|n| n.to_string_lossy().to_string())
                    .unwrap_or_default();
                if material.starts_with('.') { continue; }
                let json_file = path.join(format!("{}--要素信息录入.json", material));
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
    }

    Ok(results)
}

#[tauri::command]
pub async fn read_json_file(path: String) -> Result<String, String> {
    std::fs::read_to_string(&path)
        .map_err(|e| format!("读取文件失败: {}", e))
}

#[tauri::command]
pub async fn open_in_finder(path: String) -> Result<(), String> {
    #[cfg(target_os = "macos")]
    {
        Command::new("open")
            .arg("-R")
            .arg(&path)
            .spawn()
            .map_err(|e| format!("打开文件管理器失败: {}", e))?;
    }
    #[cfg(target_os = "windows")]
    {
        Command::new("explorer")
            .arg(format!("/select,{}", path))
            .spawn()
            .map_err(|e| format!("打开文件管理器失败: {}", e))?;
    }
    Ok(())
}

fn get_skill_path(skill_relative_path: &str) -> Result<PathBuf, String> {
    super::path_utils::resolve_skill_path(skill_relative_path)
}
