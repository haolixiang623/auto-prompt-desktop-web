use serde::{Deserialize, Serialize};
use std::path::PathBuf;
use std::process::Command;
use std::io::{BufRead, BufReader};
use std::process::Stdio;
use std::sync::{Arc, Mutex};
use std::thread;
use tauri::Window;
use chrono::Local;
use super::llm_log::{append_log, next_id, LlmLogEntry};

#[derive(Debug, Serialize, Deserialize)]
pub struct ReviewRuleResult {
    pub material: String,
    pub success: bool,
    pub output: String,
    pub error: String,
    pub keypoint_count: usize,
}

fn process_line(line: &str, window: &Window, all_lines: &Arc<Mutex<Vec<String>>>, is_stderr: bool) {
    // Parse LLM log entries
    if line.starts_with("__LLM_LOG__:") {
        let json_str = &line["__LLM_LOG__:".len()..];
        if let Ok(v) = serde_json::from_str::<serde_json::Value>(json_str) {
            append_log(LlmLogEntry {
                id: next_id(),
                time: Local::now().format("%Y-%m-%d %H:%M:%S").to_string(),
                model: v["model"].as_str().unwrap_or("").to_string(),
                scene: v["scene"].as_str().unwrap_or("审查规则生成").to_string(),
                prompt_summary: v["prompt_summary"].as_str().unwrap_or("").to_string(),
                response_summary: v["response_summary"].as_str().unwrap_or("").to_string(),
                elapsed_s: v["elapsed_s"].as_f64(),
                success: v["success"].as_bool().unwrap_or(true),
                error: v["error"].as_str().map(|s| s.to_string()),
            });
        }
    } else if !line.starts_with("RESULTS_JSON:") {
        // Emit to frontend for real-time display
        if is_stderr {
            let _ = window.emit("review-rule-log", format!("[stderr] {}", line));
        } else {
            let _ = window.emit("review-rule-log", line);
        }
    }

    // Store for later parsing
    if !is_stderr {
        if let Ok(mut lines) = all_lines.lock() {
            lines.push(line.to_string());
        }
    }
}

#[tauri::command]
pub async fn generate_review_rule(
    work_dir: String,
    use_llm: bool,
    api_key: Option<String>,
    base_url: Option<String>,
    model: Option<String>,
    window: Window,
) -> Result<Vec<ReviewRuleResult>, String> {
    let skill_path = get_skill_path("review-rule-generator/generate_review_rule.py")?;

    // Get timeout from settings
    let timeout = super::config::get_llm_timeout().await;

    // Get model config for extra params (like enable_thinking)
    let model_cfg = super::config::get_model_config_by_id(None).await;
    let extra_params = model_cfg.as_ref()
        .map(|m| super::config::params_to_json(&m.params))
        .unwrap_or_else(|| "{}".to_string());

    // Use python3 -u for unbuffered output (real-time streaming)
    let mut cmd = Command::new("python3");
    cmd.arg("-u")  // Unbuffered stdout/stderr
        .arg(&skill_path)
        .arg(&work_dir)
        .arg("--timeout")
        .arg(timeout.to_string())
        .env("GENERATE_EXTRA_PARAMS", &extra_params)
        .env("PYTHONUNBUFFERED", "1")  // Also set env var
        .stdout(Stdio::piped())
        .stderr(Stdio::piped());

    if use_llm {
        cmd.arg("--use-llm");
        if let Some(ref key) = api_key {
            if !key.is_empty() {
                cmd.arg("--api-key").arg(key);
            }
        }
        if let Some(ref url) = base_url {
            if !url.is_empty() {
                cmd.arg("--base-url").arg(url);
            }
        }
        if let Some(ref m) = model {
            if !m.is_empty() {
                cmd.arg("--model").arg(m);
            }
        }
    }

    let mut child = cmd
        .spawn()
        .map_err(|e| format!("启动Python进程失败: {}", e))?;

    let all_lines: Arc<Mutex<Vec<String>>> = Arc::new(Mutex::new(Vec::new()));

    // Take stdout and stderr
    let stdout = child.stdout.take();
    let stderr = child.stderr.take();

    // Spawn thread for stdout
    let all_lines_stdout = all_lines.clone();
    let window_stdout = window.clone();
    let stdout_handle = thread::spawn(move || {
        if let Some(stdout) = stdout {
            let reader = BufReader::new(stdout);
            for line in reader.lines().flatten() {
                process_line(&line, &window_stdout, &all_lines_stdout, false);
            }
        }
    });

    // Spawn thread for stderr
    let all_lines_stderr = all_lines.clone();
    let window_stderr = window.clone();
    let stderr_handle = thread::spawn(move || {
        if let Some(stderr) = stderr {
            let reader = BufReader::new(stderr);
            for line in reader.lines().flatten() {
                process_line(&line, &window_stderr, &all_lines_stderr, true);
            }
        }
    });

    // Wait for both threads to complete
    let _ = stdout_handle.join();
    let _ = stderr_handle.join();

    // Wait for child process
    let status = child.wait()
        .map_err(|e| format!("等待Python进程失败: {}", e))?;

    if !status.success() {
        // Still try to parse results
    }

    // Get collected lines
    let all_lines = all_lines.lock().unwrap();

    // Parse RESULTS_JSON line
    for line in all_lines.iter() {
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
            if let Ok(py_results) = serde_json::from_str::<Vec<PyResult>>(json_str) {
                return Ok(py_results.into_iter().map(|r| ReviewRuleResult {
                    material: r.material,
                    success: r.success,
                    output: r.output,
                    error: r.error,
                    keypoint_count: r.keypoint_count,
                }).collect());
            }
        }
    }

    // Fallback: scan for generated files
    let work_path = PathBuf::from(&work_dir);
    let mut results: Vec<ReviewRuleResult> = Vec::new();
    if let Ok(entries) = std::fs::read_dir(&work_path) {
        for entry in entries.filter_map(|e| e.ok()) {
            let path = entry.path();
            if path.is_dir() {
                let material = path.file_name()
                    .map(|n| n.to_string_lossy().to_string())
                    .unwrap_or_default();
                if material.starts_with('.') { continue; }
                let json_file = path.join(format!("{}--审查规则导入.json", material));
                if json_file.exists() {
                    results.push(ReviewRuleResult {
                        material,
                        success: true,
                        output: json_file.to_string_lossy().to_string(),
                        error: String::new(),
                        keypoint_count: 0,
                    });
                }
            } else if let Some(name) = path.file_name() {
                let name = name.to_string_lossy();
                if name.ends_with("--审查规则导入.json") {
                    let material = name.replace("--审查规则导入.json", "").to_string();
                    results.push(ReviewRuleResult {
                        material,
                        success: true,
                        output: path.to_string_lossy().to_string(),
                        error: String::new(),
                        keypoint_count: 0,
                    });
                }
            }
        }
    }

    Ok(results)
}

#[tauri::command]
pub async fn write_json_file(path: String, content: String) -> Result<(), String> {
    std::fs::write(&path, content.as_bytes())
        .map_err(|e| format!("写入文件失败: {}", e))
}

fn get_skill_path(skill_relative_path: &str) -> Result<PathBuf, String> {
    super::path_utils::resolve_skill_path(skill_relative_path)
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

#[tauri::command]
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
    // 构造提示词让 LLM 只生成这一个要点
    let prompt = format!(r#"你是一个审查规则分析专家。请根据以下审查要点规则说明，生成符合导入规范的审查规则JSON。

## 审查背景
- 材料名称: {}
- 审查要点名称: {}
- 审查要点规则说明: {}

## 要求
- 必须使用审查方式: {} (1=大模型, 2=规则对比, 3=Groovy脚本)
- review_rule_text: 简洁的审查规则文本描述
- content: 当review_rule=1时，填写LLM提示词；否则为空
- review_conditions: 当review_rule=2时，填写规则对比条件JSON
- review_rule_js: 当review_rule=3时，填写Groovy脚本

## 输出格式（严格JSON，无多余内容）
{{
  "review_rule": "{}",
  "review_rule_text": "...",
  "content": "...",
  "review_conditions": null,
  "review_rule_js": "",
  "passreason": "...",
  "nopassreason": "..."
}}"#,
        material_name,
        kpname,
        rule_desc,
        target_rule,
        target_rule
    );

    let timeout = timeout.unwrap_or(120);

    // 调用 LLM
    let client = reqwest::Client::new();

    let payload = serde_json::json!({
        "model": model.clone().unwrap_or_else(|| "qwen-plus".to_string()),
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "max_tokens": 2000,
    });

    let response = client
        .post(format!("{}/chat/completions", base_url.unwrap_or_else(|| "https://dashscope.aliyuncs.com/compatible-mode/v1".to_string())))
        .header("Content-Type", "application/json")
        .header("Authorization", format!("Bearer {}", api_key.unwrap_or_default()))
        .json(&payload)
        .timeout(std::time::Duration::from_secs(timeout))
        .send()
        .await
        .map_err(|e| format!("LLM 调用失败: {}", e))?;

    let resp_json: serde_json::Value = response
        .json()
        .await
        .map_err(|e| format!("解析响应失败: {}", e))?;

    let content = resp_json["choices"][0]["message"]["content"]
        .as_str()
        .ok_or("无法获取响应内容")?;

    // 提取 JSON 部分
    let json_match = regex::Regex::new(r"\{.*\}").ok()
        .and_then(|re| re.find(content))
        .ok_or("响应中未找到 JSON")?;

    let result: KeypointRuleResult = serde_json::from_str(json_match.as_str())
        .map_err(|e| format!("解析结果失败: {}", e))?;

    Ok(result)
}
