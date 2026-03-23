use serde::{Deserialize, Serialize};
use std::path::PathBuf;
use std::process::{Command, Stdio};
use std::io::{BufRead, BufReader};
use tauri::Window;
use super::llm_log::{append_log, next_id, LlmLogEntry};

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
    // computed fields for frontend
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

#[tauri::command]
pub async fn get_material_categories(work_dir: String) -> Result<Vec<String>, String> {
    let work_path = PathBuf::from(&work_dir);

    // Try to find factors file (xlsx or csv)
    let factors_path = ["factors.xlsx", "factors.xls", "factors.csv"]
        .iter()
        .map(|name| work_path.join(name))
        .find(|p| p.exists());

    if let Some(ref fpath) = factors_path {
        // Use Python to read material names from factors file
        let script = format!(
            r#"
import sys
try:
    import openpyxl
    wb = openpyxl.load_workbook(r'{}', read_only=True, data_only=True)
    ws = wb.active
    seen = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if row and row[0] and str(row[0]).strip():
            name = str(row[0]).strip()
            if name not in seen:
                seen.append(name)
    print('\n'.join(seen))
except Exception as e:
    sys.exit(str(e))
"#,
            fpath.to_string_lossy().replace('\\', "\\\\")
        );

        let output = Command::new(&super::env_check::get_python_command())
            .arg("-c")
            .arg(&script)
            .output()
            .map_err(|e| format!("调用Python失败: {}", e))?;

        if output.status.success() {
            let stdout = String::from_utf8_lossy(&output.stdout);
            let names: Vec<String> = stdout
                .lines()
                .map(|l| l.trim().to_string())
                .filter(|l| !l.is_empty())
                .collect();
            if !names.is_empty() {
                return Ok(names);
            }
        }
    }

    // Fallback: scan subdirectories (excluding reserved names)
    let mut categories = Vec::new();
    if let Ok(entries) = std::fs::read_dir(&work_path) {
        for entry in entries.filter_map(|e| e.ok()) {
            let path = entry.path();
            if path.is_dir() {
                if let Some(name) = path.file_name() {
                    let name = name.to_string_lossy().to_string();
                    if !name.starts_with('.')
                        && name != "已分类"
                        && name != "待分类"
                        && name != "已分类材料"
                        && name != "待分类材料"
                    {
                        categories.push(name);
                    }
                }
            }
        }
    }

    if categories.is_empty() {
        return Err("未找到 factors.xlsx 或事项名称子目录".to_string());
    }

    categories.sort();
    Ok(categories)
}

#[tauri::command]
pub async fn get_pending_files(work_dir: String) -> Result<Vec<FileInfo>, String> {
    let work_path = PathBuf::from(&work_dir);
    // Support both 待分类材料 and 待分类 directory names
    let pending_dir = if work_path.join("待分类材料").exists() {
        work_path.join("待分类材料")
    } else if work_path.join("待分类").exists() {
        work_path.join("待分类")
    } else {
        work_path.clone()
    };

    let target_dir = pending_dir;

    let mut files = Vec::new();

    let entries = std::fs::read_dir(&target_dir).map_err(|e| e.to_string())?;

    for entry in entries {
        if let Ok(entry) = entry {
            let path = entry.path();
            if path.is_file() {
                let file_name = entry.file_name().to_string_lossy().to_string();
                // Skip system/hidden files
                if file_name.starts_with('.') || file_name == "Thumbs.db" || file_name == "desktop.ini" {
                    continue;
                }
                let metadata = entry.metadata().map_err(|e| e.to_string())?;
                files.push(FileInfo {
                    name: file_name,
                    path: path.to_string_lossy().to_string(),
                    size: metadata.len(),
                });
            }
        }
    }

    Ok(files)
}

#[tauri::command]
pub async fn classify_materials(
    work_dir: String,
    max_rounds: u32,
    model_cfg_id: Option<String>,
    window: Window,
) -> Result<ClassificationReport, String> {
    let skill_path = get_skill_path("material-classifier/classify_materials.py")?;

    let model_cfg = super::config::get_model_config_by_id(model_cfg_id).await;
    let model_id = model_cfg.as_ref()
        .map(|m| m.model_id.clone())
        .unwrap_or_else(|| super::config::get_model_name_sync());
    let extra_params = model_cfg.as_ref()
        .map(|m| super::config::params_to_json(&m.params))
        .unwrap_or_else(|| "{}".to_string());
    let god_prompt = super::config::load_settings().await
        .map(|s| s.god_prompt)
        .unwrap_or_default();
    let _ = window.emit("skill-log", format!("[分类] 使用模型: {}", model_id));
    if extra_params != "{}" {
        let _ = window.emit("skill-log", format!("[分类] 额外参数: {}", extra_params));
    }

    let mut child = Command::new(&super::env_check::get_python_command())
        .arg("-u")
        .arg(&skill_path)
        .arg(&work_dir)
        .arg(max_rounds.to_string())
        .env("DASHSCOPE_API_KEY", get_api_key().await?)
        .env("CLASSIFY_MODEL_NAME", &model_id)
        .env("CLASSIFY_EXTRA_PARAMS", &extra_params)
        .env("CLASSIFY_GOD_PROMPT", &god_prompt)
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|e| format!("启动Python进程失败: {}", e))?;

    // Capture both stdout and stderr using threads to avoid deadlock
    use std::thread;

    let child_ref = std::sync::Arc::new(std::sync::Mutex::new(Some(child)));

    // Create separate clones for each thread
    let child_clone_stdout = child_ref.clone();
    let child_clone_stderr = child_ref.clone();
    let child_clone_wait = child_ref.clone();

    let stdout_handle = {
        let window_clone = window.clone();
        Some(thread::spawn(move || {
            let mut child_guard = child_clone_stdout.lock().unwrap();
            if let Some(ref mut child) = *child_guard {
                if let Some(stdout) = child.stdout.take() {
                    let reader = BufReader::new(stdout);
                    let mut lines = Vec::new();
                    for line in reader.lines() {
                        if let Ok(line) = line {
                            // Parse individual LLM call logs emitted by Python
                            if line.starts_with("__LLM_LOG__:") {
                                let json_str = &line["__LLM_LOG__:".len()..];
                                if let Ok(v) = serde_json::from_str::<serde_json::Value>(json_str) {
                                    use crate::commands::llm_log::{append_log, next_id, LlmLogEntry};
                                    append_log(LlmLogEntry {
                                        id: next_id(),
                                        time: chrono::Local::now().format("%Y-%m-%d %H:%M:%S").to_string(),
                                        model: v["model"].as_str().unwrap_or("").to_string(),
                                        scene: v["scene"].as_str().unwrap_or("材料分类").to_string(),
                                        prompt_summary: v["prompt_summary"].as_str().unwrap_or("").to_string(),
                                        response_summary: v["response_summary"].as_str().unwrap_or("").to_string(),
                                        elapsed_s: v["elapsed_s"].as_f64(),
                                        success: v["success"].as_bool().unwrap_or(true),
                                        error: v["error"].as_str().map(|s| s.to_string()),
                                    });
                                }
                                // don't emit __LLM_LOG__ lines to UI
                            } else {
                                let _ = window_clone.emit("skill-log", &line);
                            }
                            lines.push(line);
                        }
                    }
                    return lines;
                }
            }
            Vec::new()
        }))
    };

    let stderr_handle = {
        let window_clone = window.clone();
        Some(thread::spawn(move || {
            let mut child_guard = child_clone_stderr.lock().unwrap();
            if let Some(ref mut child) = *child_guard {
                if let Some(stderr) = child.stderr.take() {
                    let reader = BufReader::new(stderr);
                    let mut lines = Vec::new();
                    for line in reader.lines() {
                        if let Ok(line) = line {
                            let _ = window_clone.emit("skill-log", format!("[错误] {}", line));
                            lines.push(line);
                        }
                    }
                    return lines;
                }
            }
            Vec::new()
        }))
    };

    let timeout_secs = super::config::get_llm_timeout().await;
    let handle = thread::spawn(move || {
        let mut child_guard = child_clone_wait.lock().unwrap();
        if let Some(ref mut child) = *child_guard {
            child.wait()
        } else {
            Ok(std::process::ExitStatus::default())
        }
    });

    let status = match handle.join() {
        Ok(Ok(s)) => s,
        _ => {
            let mut child_guard = child_ref.lock().unwrap();
            if let Some(ref mut child) = *child_guard {
                let _ = child.kill();
                let _ = child.wait();
            }
            return Err(format!("材料分类超时（{}秒），请增加超时时间或检查网络连接", timeout_secs));
        }
    };

    let all_lines = stdout_handle.map(|h| h.join().unwrap_or_default()).unwrap_or_default();
    let stderr_lines = stderr_handle.map(|h| h.join().unwrap_or_default()).unwrap_or_default();

    if !status.success() {
        let error_detail = if !stderr_lines.is_empty() {
            stderr_lines.join("\n")
        } else {
            "未知错误，请检查日志输出".to_string()
        };
        return Err(format!("Python脚本执行失败: {}", error_detail));
    }

    // Check if API key error occurred (script exits 0 but with error message)
    let has_api_error = all_lines.iter().any(|l| l.contains("DASHSCOPE_API_KEY") || l.contains("API Key"));
    if has_api_error {
        return Err("未配置API密钥，请前往【设置】页面配置 DASHSCOPE_API_KEY".to_string());
    }

    // Read the classification_report.json file generated by the script
    let report_path = PathBuf::from(&work_dir).join("classification_report.json");
    if !report_path.exists() {
        return Err("分类未完成，未生成报告文件，请检查日志输出".to_string());
    }

    let report_content = std::fs::read_to_string(&report_path)
        .map_err(|e| format!("读取报告文件失败: {}", e))?;

    let mut result: ClassificationReport = serde_json::from_str(&report_content)
        .map_err(|e| format!("解析报告失败: {}", e))?;

    // Fill computed fields
    result.total_files = result.image_count;
    result.categories = result.material_names.clone();
    result.classified_dir = result.base_dir.as_ref()
        .map(|d| format!("{}/已分类材料", d));

    // Read optimized prompts from work_dir (only exist when AI has run optimization)
    // Fallback to skills/ template so "current prompt" reflects what was actually used
    let extract_latest_path = PathBuf::from(&work_dir).join("最新分类信息提取提示词.txt");
    let mut extract_prompt = std::fs::read_to_string(&extract_latest_path)
        .ok()
        .or_else(|| get_skill_path("material-classifier/分类信息提取提示词模板.txt").ok()
            .and_then(|p| std::fs::read_to_string(p).ok()));

    let aggregate_latest_path = PathBuf::from(&work_dir).join("最新分类附件归集提示词.txt");
    let mut aggregate_prompt = std::fs::read_to_string(&aggregate_latest_path)
        .ok()
        .or_else(|| get_skill_path("material-classifier/分类附件归集提示词模板.txt").ok()
            .and_then(|p| std::fs::read_to_string(p).ok()));

    // Replace $(material_list) placeholder with actual material names
    if let Some(ref names) = result.material_names {
        let material_list_text = names.iter()
            .map(|n| format!("- {}", n))
            .collect::<Vec<_>>()
            .join("\n");

        if let Some(ref mut prompt) = extract_prompt {
            *prompt = prompt.replace("$(material_list)", &material_list_text);
        }
        if let Some(ref mut prompt) = aggregate_prompt {
            *prompt = prompt.replace("$(material_list)", &material_list_text);
        }
    }

    result.final_extract_prompt = extract_prompt;
    result.final_aggregate_prompt = aggregate_prompt;

    // Locate skill templates from project skills/ dir (read-only)
    let ext_tmpl = get_skill_path("material-classifier/分类信息提取提示词模板.txt").ok();
    result.extract_template_path = ext_tmpl.as_ref().map(|p| p.to_string_lossy().to_string());
    result.extract_template_content = ext_tmpl.as_ref()
        .and_then(|p| std::fs::read_to_string(p).ok())
        .map(|content| {
            // Replace $(material_list) placeholder with actual material names
            if let Some(ref names) = result.material_names {
                let material_list_text = names.iter()
                    .map(|n| format!("- {}", n))
                    .collect::<Vec<_>>()
                    .join("\n");
                content.replace("$(material_list)", &material_list_text)
            } else {
                content
            }
        });

    let agg_tmpl = get_skill_path("material-classifier/分类附件归集提示词模板.txt").ok();
    result.aggregate_template_path = agg_tmpl.as_ref().map(|p| p.to_string_lossy().to_string());
    result.aggregate_template_content = agg_tmpl.as_ref()
        .and_then(|p| std::fs::read_to_string(p).ok())
        .map(|content| {
            // Replace $(material_list) placeholder with actual material names
            if let Some(ref names) = result.material_names {
                let material_list_text = names.iter()
                    .map(|n| format!("- {}", n))
                    .collect::<Vec<_>>()
                    .join("\n");
                content.replace("$(material_list)", &material_list_text)
            } else {
                content
            }
        });

    append_log(LlmLogEntry {
        id: next_id(),
        time: chrono::Local::now().format("%Y-%m-%d %H:%M:%S").to_string(),
        model: model_id.clone(),
        scene: "材料分类-汇总".to_string(),
        prompt_summary: format!("文件数: {}，类别数: {}，迭代轮次: {}/{}",
            result.total_files.unwrap_or(0),
            result.categories.as_ref().map_or(0, |v| v.len()),
            result.iterations_run.unwrap_or(1),
            max_rounds),
        response_summary: format!("成功归集: {} 个文件，提取提示词来源: {}，归集提示词来源: {}",
            result.step2_summary.as_ref().and_then(|s| s.get("classified_count")).and_then(|v| v.as_u64()).unwrap_or(0),
            result.extract_prompt_source.as_deref().unwrap_or("原始模板"),
            result.aggregate_prompt_source.as_deref().unwrap_or("原始模板")),
        elapsed_s: None,
        success: true,
        error: None,
    });
    Ok(result)
}

#[derive(Debug, Serialize, Deserialize)]
pub struct TestPromptResult {
    pub r#type: String,
    pub pass: bool,
    pub issues: Vec<String>,
    pub attachments: Option<Vec<serde_json::Value>>,
    pub plan: Option<Vec<serde_json::Value>>,
    pub summary: Option<serde_json::Value>,
    pub error: Option<String>,
}

#[tauri::command]
pub async fn test_classify_prompt(
    work_dir: String,
    prompt_type: String,
    prompt_content: String,
    model_cfg_id: Option<String>,
    window: Window,
) -> Result<TestPromptResult, String> {
    use std::thread;

    let skill_path = get_skill_path("material-classifier/classify_materials.py")?;

    let model_cfg = super::config::get_model_config_by_id(model_cfg_id).await;
    let model_id = model_cfg.as_ref()
        .map(|m| m.model_id.clone())
        .unwrap_or_else(|| super::config::get_model_name_sync());
    let extra_params = model_cfg.as_ref()
        .map(|m| super::config::params_to_json(&m.params))
        .unwrap_or_else(|| "{}".to_string());

    // Write prompt content to a temp file
    let tmp_path = PathBuf::from(&work_dir).join(format!(".test_prompt_{}.txt", &prompt_type));
    std::fs::write(&tmp_path, &prompt_content).map_err(|e| format!("写入临时文件失败: {}", e))?;

    let mut child = Command::new(&super::env_check::get_python_command())
        .arg("-u")
        .arg(&skill_path)
        .arg(format!("--test-prompt={}", prompt_type))
        .arg(format!("--prompt-file={}", tmp_path.to_string_lossy()))
        .arg(&work_dir)
        .env("DASHSCOPE_API_KEY", get_api_key().await?)
        .env("CLASSIFY_MODEL_NAME", &model_id)
        .env("CLASSIFY_EXTRA_PARAMS", &extra_params)
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|e| format!("启动Python进程失败: {}", e))?;

    let child_ref = std::sync::Arc::new(std::sync::Mutex::new(Some(child)));

    // Create separate clones for each thread
    let child_clone_stdout = child_ref.clone();
    let child_clone_stderr = child_ref.clone();
    let child_clone_wait = child_ref.clone();

    let stdout_handle = {
        let window_clone = window.clone();
        Some(thread::spawn(move || {
            let mut child_guard = child_clone_stdout.lock().unwrap();
            if let Some(ref mut child) = *child_guard {
                if let Some(stdout) = child.stdout.take() {
                    let reader = BufReader::new(stdout);
                    let mut lines = Vec::new();
                    for line in reader.lines() {
                        if let Ok(line) = line {
                            if !line.starts_with("TEST_RESULT_JSON:") {
                                let _ = window_clone.emit("skill-log", &line);
                            }
                            lines.push(line);
                        }
                    }
                    return lines;
                }
            }
            Vec::new()
        }))
    };

    let stderr_handle = {
        let window_clone = window.clone();
        Some(thread::spawn(move || {
            let mut child_guard = child_clone_stderr.lock().unwrap();
            if let Some(ref mut child) = *child_guard {
                if let Some(stderr) = child.stderr.take() {
                    let reader = BufReader::new(stderr);
                    let mut lines = Vec::new();
                    for line in reader.lines() {
                        if let Ok(line) = line {
                            let _ = window_clone.emit("skill-log", format!("[错误] {}", line));
                            lines.push(line);
                        }
                    }
                    return lines;
                }
            }
            Vec::new()
        }))
    };

    let timeout_secs = super::config::get_llm_timeout().await;
    let handle = thread::spawn(move || {
        let mut child_guard = child_clone_wait.lock().unwrap();
        if let Some(ref mut child) = *child_guard {
            child.wait()
        } else {
            Ok(std::process::ExitStatus::default())
        }
    });

    let status = match handle.join() {
        Ok(Ok(s)) => s,
        _ => {
            let mut child_guard = child_ref.lock().unwrap();
            if let Some(ref mut child) = *child_guard {
                let _ = child.kill();
                let _ = child.wait();
            }
            return Err(format!("测试执行超时（{}秒），请增加超时时间或检查网络连接", timeout_secs));
        }
    };

    let all_lines = stdout_handle.map(|h| h.join().unwrap_or_default()).unwrap_or_default();
    let stderr_lines = stderr_handle.map(|h| h.join().unwrap_or_default()).unwrap_or_default();

    // Clean up temp file
    let _ = std::fs::remove_file(&tmp_path);

    if !status.success() {
        let detail = if !stderr_lines.is_empty() { stderr_lines.join("\n") } else { "未知错误".to_string() };
        return Err(format!("测试执行失败: {}", detail));
    }

    // Find result line
    for line in &all_lines {
        if let Some(json_str) = line.strip_prefix("TEST_RESULT_JSON:") {
            if let Ok(r) = serde_json::from_str::<TestPromptResult>(json_str) {
                return Ok(r);
            }
        }
    }

    Err("未能解析测试结果".to_string())
}

#[tauri::command]
pub async fn open_classified_dir(work_dir: String) -> Result<(), String> {
    let classified_dir = PathBuf::from(&work_dir).join("已分类材料");

    #[cfg(target_os = "macos")]
    {
        Command::new("open")
            .arg(&classified_dir)
            .spawn()
            .map_err(|e| e.to_string())?;
    }

    #[cfg(target_os = "windows")]
    {
        Command::new("explorer")
            .arg(&classified_dir)
            .spawn()
            .map_err(|e| e.to_string())?;
    }

    #[cfg(target_os = "linux")]
    {
        Command::new("xdg-open")
            .arg(&classified_dir)
            .spawn()
            .map_err(|e| e.to_string())?;
    }

    Ok(())
}

fn get_skill_path(skill_relative_path: &str) -> Result<PathBuf, String> {
    super::path_utils::resolve_skill_path(skill_relative_path)
}

async fn get_api_key() -> Result<String, String> {
    super::config::get_api_key().await
}
