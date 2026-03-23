use serde::{Deserialize, Serialize};
use std::path::PathBuf;
use std::process::{Command, Stdio};
use std::io::{BufRead, BufReader};
use tauri::Window;
use super::llm_log::{append_log, next_id, LlmLogEntry};

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

#[tauri::command]
pub async fn read_factors(work_dir: String) -> Result<Vec<Factor>, String> {
    let work_path = PathBuf::from(&work_dir);
    let factors_path = work_path.join("factors.xlsx");

    if !factors_path.exists() {
        // Try to find any xlsx file
        let entries = std::fs::read_dir(&work_path).map_err(|e| e.to_string())?;
        let xlsx_file = entries
            .filter_map(|e| e.ok())
            .find(|e| {
                e.path()
                    .extension()
                    .map(|ext| ext == "xlsx" || ext == "xls")
                    .unwrap_or(false)
            });

        let factors_path = match xlsx_file {
            Some(file) => file.path(),
            None => return Err("未找到 factors.xlsx 文件".to_string()),
        };

        return parse_excel(&factors_path);
    }

    parse_excel(&factors_path)
}

fn parse_excel(path: &PathBuf) -> Result<Vec<Factor>, String> {
    let script = format!(
        r#"
import sys, json
try:
    import openpyxl
    wb = openpyxl.load_workbook(r'{}', read_only=True, data_only=True)
    ws = wb.active
    headers = [str(c.value or '').strip() for c in next(ws.iter_rows(min_row=1, max_row=1, values_only=False))]

    # 自动检测格式
    # 格式B（扩展）：A=事项名称, B=材料名称, D=要素字段名称
    # 格式A（简单）：A=材料名称, B=要素名称
    is_extended = '事项' in (headers[0] if headers else '') or \
                  (len(headers) > 1 and '材料名称' in headers[1])

    results = []
    if is_extended:
        # 扩展格式：B列材料名(col1), D列要素(col3), G列说明(col6)，跨行继承
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
            if not factor_name or '\n' in factor_name or len(factor_name) > 50:
                continue
            results.append({{
                'field_name': factor_name,
                'field_code': '',
                'description': factor_usage,
                'required': True,
                'data_type': 'string',
                'material': current_material,
            }})
    else:
        # 简单格式：A=材料名称(col0), B=要素名称(col1), C=说明(col2)
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
            if not factor_name:
                continue
            results.append({{
                'field_name': factor_name,
                'field_code': '',
                'description': factor_usage,
                'required': True,
                'data_type': 'string',
                'material': current_material or '',
            }})
    print(json.dumps(results, ensure_ascii=False))
except Exception as e:
    print(json.dumps([]), file=sys.stdout)
    print(str(e), file=sys.stderr)
"#,
        path.to_string_lossy().replace('\\', "\\\\")
    );

    let output = Command::new("python3")
        .arg("-c")
        .arg(&script)
        .output()
        .map_err(|e| format!("调用Python失败: {}", e))?;

    let stdout = String::from_utf8_lossy(&output.stdout);
    let factors: Vec<Factor> = serde_json::from_str(stdout.trim())
        .map_err(|e| format!("解析要素失败: {}", e))?;

    Ok(factors)
}

#[tauri::command]
pub async fn generate_prompt(
    work_dir: String,
    material_name: Option<String>,
    model_cfg_id: Option<String>,
    window: Window,
) -> Result<GenerateResult, String> {
    let work_path = PathBuf::from(&work_dir);

    // 确定实际的材料目录：如果提供了材料名称，使用子目录；否则用根目录
    let material_dir = if let Some(ref name) = material_name {
        let sub = work_path.join(name);
        if sub.exists() {
            sub
        } else {
            work_path.clone()
        }
    } else {
        work_path.clone()
    };

    // 检查材料目录是否有图片或PDF文件
    let has_media = std::fs::read_dir(&material_dir)
        .map_err(|e| format!("无法读取材料目录: {}", e))?
        .filter_map(|e| e.ok())
        .any(|e| {
            if let Some(ext) = e.path().extension() {
                let ext = ext.to_string_lossy().to_lowercase();
                matches!(ext.as_str(), "jpg" | "jpeg" | "png" | "bmp" | "gif" | "webp" | "pdf")
            } else {
                false
            }
        });

    if !has_media {
        return Err(format!(
            "材料目录下缺少图片或PDF文件\n\n目录: {}\n\n请添加至少一张图片（jpg/png等）或PDF文件。",
            material_dir.display()
        ));
    }

    let skill_path = get_skill_path("doc-extract-prompt-gen/generate_prompt.py")?;

    let mut cmd = Command::new("python3");
    cmd.arg("-u");
    // Python脚本用法: generate_prompt.py <工作目录> [材料名称]
    // 当有材料名称时，脚本把 work_dir 当作材料子目录，从其 parent 找 factors.xlsx
    // 所以需要传材料子目录路径作为第一个参数
    let script_work_dir = if material_name.is_some() {
        material_dir.to_string_lossy().to_string()
    } else {
        work_dir.clone()
    };

    cmd.arg(&skill_path)
        .arg(&script_work_dir);

    // 如果提供了材料名称，作为第二个参数传递给 Python（用于过滤要素）
    if let Some(ref material) = material_name {
        cmd.arg(material);
    }

    let model_cfg = super::config::get_model_config_by_id(model_cfg_id).await;
    let extra_params = model_cfg.as_ref()
        .map(|m| super::config::params_to_json(&m.params))
        .unwrap_or_else(|| "{}".to_string());
    let extract_god_prompt = super::config::load_settings().await
        .map(|s| s.extract_god_prompt)
        .unwrap_or_default();

    let mut child = cmd
        .env("DASHSCOPE_API_KEY", get_api_key().await?)
        .env("GENERATE_EXTRA_PARAMS", &extra_params)
        .env("EXTRACT_GOD_PROMPT", &extract_god_prompt)
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|e| format!("启动Python进程失败: {}", e))?;

    // Stream stdout to frontend and collect lines
    let mut all_stdout_lines: Vec<String> = Vec::new();
    let child_ref = std::sync::Arc::new(std::sync::Mutex::new(Some(child)));

    // Create separate clones for each thread
    let child_clone_stdout = child_ref.clone();
    let child_clone_wait = child_ref.clone();

    let stdout_handle = std::thread::spawn(move || {
        let mut child_guard = child_clone_stdout.lock().unwrap();
        if let Some(ref mut child) = *child_guard {
            if let Some(stdout) = child.stdout.take() {
                let reader = BufReader::new(stdout);
                let mut lines = Vec::new();
                for line in reader.lines() {
                    if let Ok(line) = line {
                        lines.push(line);
                    }
                }
                return lines;
            }
        }
        Vec::new()
    });

    let stdout_lines = stdout_handle.join().unwrap_or_default();
    for line in &stdout_lines {
        let _ = window.emit("skill-log", line);
        all_stdout_lines.push(line.clone());
    }

    let timeout_secs = super::config::get_llm_timeout().await;
    let handle = std::thread::spawn(move || {
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
            return Err(format!("生成提示词超时（{}秒），请增加超时时间或检查网络连接", timeout_secs));
        }
    };

    if !status.success() {
        // Collect stderr if available
        return Err(format!("Python脚本执行失败，请检查日志输出"));
    }

    // Extract output file path from collected stdout
    let output_file = all_stdout_lines
        .iter()
        .find(|line| line.contains("已保存至:"))
        .and_then(|line| line.split("已保存至:").nth(1))
        .map(|s| s.trim().to_string())
        .unwrap_or_else(|| {
            // Fallback: construct default output path using material subdir name
            let dir_name = PathBuf::from(&script_work_dir)
                .file_name()
                .map(|n| n.to_string_lossy().to_string())
                .unwrap_or_else(|| "output".to_string());
            format!("{}/{}--要素提取完整提示词.txt", script_work_dir, dir_name)
        });

    // Try to read generated prompt file content for preview
    let output_path = PathBuf::from(&output_file);
    let prompt_content = std::fs::read_to_string(&output_path).ok();

    let result = GenerateResult {
        output_file,
        factors_count: 0,
        images_count: 0,
        prompt_template: prompt_content,
    };

    Ok(result)
}

fn get_skill_path(skill_relative_path: &str) -> Result<PathBuf, String> {
    super::path_utils::resolve_skill_path(skill_relative_path)
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

#[tauri::command]
pub async fn verify_extraction(
    material_dir: String,
    prompt_text: String,
    model_cfg_id: Option<String>,
    window: Window,
) -> Result<VerifyResult, String> {
    let dir_path = PathBuf::from(&material_dir);

    // Find first image or PDF in the directory
    let entries: Vec<_> = std::fs::read_dir(&dir_path)
        .map_err(|e| format!("无法读取材料目录: {}", e))?
        .filter_map(|e| e.ok())
        .collect();

    let image_entry = entries.iter().find(|e| {
        if let Some(ext) = e.path().extension() {
            let ext = ext.to_string_lossy().to_lowercase();
            matches!(ext.as_str(), "jpg" | "jpeg" | "png" | "bmp" | "gif" | "webp")
        } else { false }
    });

    let pdf_entry = entries.iter().find(|e| {
        e.path().extension()
            .map(|ext| ext.to_string_lossy().to_lowercase() == "pdf")
            .unwrap_or(false)
    });

    // Determine the actual image path to use (convert PDF if needed)
    let (image_path, _converted_tmp) = if let Some(img) = image_entry {
        (img.path(), None)
    } else if let Some(pdf) = pdf_entry {
        // Convert first page of PDF to PNG using Python/PyMuPDF
        let pdf_path = pdf.path();
        let out_png = dir_path.join("__verify_img_tmp__.png");
        let convert_script = format!(
            r#"import fitz, sys
doc = fitz.open(r'{pdf}')
page = doc[0]
pix = page.get_pixmap(matrix=fitz.Matrix(2,2))
pix.save(r'{out}')
doc.close()
print('ok')
"#,
            pdf = pdf_path.to_string_lossy().replace('\\', "\\\\"),
            out = out_png.to_string_lossy().replace('\\', "\\\\"),
        );
        let conv = Command::new("python3")
            .arg("-c").arg(&convert_script)
            .output()
            .map_err(|e| format!("PDF转图片失败: {}", e))?;
        if !conv.status.success() {
            let err = String::from_utf8_lossy(&conv.stderr);
            return Err(format!("PDF转换失败（需安装 pymupdf: pip install pymupdf）: {}", err));
        }
        let _ = window.emit("skill-log", format!("[验证] PDF已转为图片: {}", out_png.display()));
        (out_png.clone(), Some(out_png))
    } else {
        return Err("材料目录中未找到图片或PDF文件".to_string());
    };

    let image_name = image_path.file_name()
        .map(|n| n.to_string_lossy().to_string())
        .unwrap_or_default();

    let _ = window.emit("skill-log", format!("[验证] 使用图片: {}", image_name));

    // Write prompt to a temp file to avoid shell escaping issues
    let tmp_prompt = dir_path.join("__verify_prompt_tmp__.txt");
    std::fs::write(&tmp_prompt, &prompt_text)
        .map_err(|e| format!("写入临时提示词文件失败: {}", e))?;

    let model_cfg = super::config::get_model_config_by_id(model_cfg_id).await;
    let model_name = model_cfg.as_ref()
        .map(|m| m.model_id.clone())
        .unwrap_or_else(|| super::config::get_model_name_sync());
    let extra_params = model_cfg.as_ref()
        .map(|m| super::config::params_to_json(&m.params))
        .unwrap_or_else(|| "{}".to_string());
    let _ = window.emit("skill-log", format!("[验证] 使用模型: {}", model_name));
    if extra_params != "{}" {
        let _ = window.emit("skill-log", format!("[验证] 额外参数: {}", extra_params));
    }

    let script = format!(
        r#"
import sys, os, base64, json, time

def main():
    api_key = os.environ.get('DASHSCOPE_API_KEY', '')
    if not api_key:
        print('[验证错误] 未配置 DASHSCOPE_API_KEY', file=sys.stderr)
        sys.exit(1)
    model_name = os.environ.get('VERIFY_MODEL_NAME', 'qwen-vl-max')
    extra_raw = os.environ.get('VERIFY_EXTRA_PARAMS', '{{}}')
    try:
        all_params = json.loads(extra_raw)
    except Exception:
        all_params = {{}}
    _BODY_PARAMS = {{'enable_thinking', 'thinking_budget', 'translation_options', 'vl_high_resolution_images', 'search_options'}}
    extra = {{k: v for k, v in all_params.items() if k not in _BODY_PARAMS}}
    body = {{k: v for k, v in all_params.items() if k in _BODY_PARAMS}}
    if body:
        extra['extra_body'] = body
    from openai import OpenAI
    client = OpenAI(api_key=api_key, base_url='https://dashscope.aliyuncs.com/compatible-mode/v1')
    prompt_path = r'{prompt_path}'
    image_path = r'{image_path}'
    with open(prompt_path, 'r', encoding='utf-8') as f:
        prompt = f.read()
    print('[验证] 提示词长度: ' + str(len(prompt)) + ' 字符', file=sys.stderr)
    print('[验证] ===== 使用的提示词 =====', file=sys.stderr)
    print(prompt, file=sys.stderr)
    print('[验证] ===== 提示词结束 =====', file=sys.stderr)
    with open(image_path, 'rb') as f:
        b64 = base64.b64encode(f.read()).decode('utf-8')
    ext = os.path.splitext(image_path)[1].lower().lstrip('.')
    if ext == 'jpg':
        ext = 'jpeg'
    print('[验证] 调用模型: ' + model_name + ('，额外参数: ' + str(extra) if extra else '') + '，图片格式: ' + ext, file=sys.stderr)
    img_url = 'data:image/' + ext + ';base64,' + b64
    messages = [
        {{"role": "user", "content": [
            {{"type": "text", "text": prompt}},
            {{"type": "image_url", "image_url": {{"url": img_url}}}}
        ]}}
    ]
    t0 = time.time()
    resp = client.chat.completions.create(model=model_name, messages=messages, **extra)
    elapsed = time.time() - t0
    content = resp.choices[0].message.content
    print('[验证] 收到响应: ' + str(len(content)) + ' 字符，耗时 ' + f'{{elapsed:.1f}}s', file=sys.stderr)
    print('[验证] ===== 模型原始返回 =====', file=sys.stderr)
    print(content, file=sys.stderr)
    print('[验证] ===== 返回结束 =====', file=sys.stderr)
    print('__ELAPSED__' + f'{{elapsed:.1f}}')
    print(content)

try:
    main()
except Exception as e:
    import traceback
    print('[验证错误] ' + str(e), file=sys.stderr)
    traceback.print_exc(file=sys.stderr)
    sys.exit(1)
"#,
        prompt_path = tmp_prompt.to_string_lossy().replace('\\', "\\\\"),
        image_path = image_path.to_string_lossy().replace('\\', "\\\\"),
    );

    let mut child = Command::new(&super::env_check::get_python_command())
        .arg("-c")
        .arg(&script)
        .env("DASHSCOPE_API_KEY", get_api_key().await?)
        .env("VERIFY_MODEL_NAME", &model_name)
        .env("VERIFY_EXTRA_PARAMS", &extra_params)
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|e| format!("启动Python失败: {}", e))?;

    // Read stderr and stdout concurrently to avoid deadlock
    let mut stdout_text = String::new();
    let mut stderr_text = String::new();

    let child_ref = std::sync::Arc::new(std::sync::Mutex::new(Some(child)));

    // Create separate clones for each thread
    let child_clone_stderr = child_ref.clone();
    let child_clone_stdout = child_ref.clone();
    let child_clone_wait = child_ref.clone();
    let window_for_stderr = window.clone();

    let stderr_handle = std::thread::spawn(move || {
        let mut child_guard = child_clone_stderr.lock().unwrap();
        if let Some(ref mut child) = *child_guard {
            if let Some(stderr) = child.stderr.take() {
                let window_clone = window_for_stderr.clone();
                let reader = BufReader::new(stderr);
                let mut text = String::new();
                for line in reader.lines() {
                    if let Ok(line) = line {
                        let _ = window_clone.emit("skill-log", &line);
                        text.push_str(&line);
                        text.push('\n');
                    }
                }
                return text;
            }
        }
        String::new()
    });

    let stdout_handle = std::thread::spawn(move || {
        let mut child_guard = child_clone_stdout.lock().unwrap();
        if let Some(ref mut child) = *child_guard {
            if let Some(stdout) = child.stdout.take() {
                let mut text = String::new();
                let reader = BufReader::new(stdout);
                for line in reader.lines() {
                    if let Ok(line) = line {
                        text.push_str(&line);
                        text.push('\n');
                    }
                }
                return text;
            }
        }
        String::new()
    });

    stdout_text = stdout_handle.join().unwrap_or_default();
    stderr_text = stderr_handle.join().unwrap_or_default();

    let timeout_secs = super::config::get_llm_timeout().await;
    let handle = std::thread::spawn(move || {
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
            return Err(format!("验证提取超时（{}秒），请增加超时时间或检查网络连接", timeout_secs));
        }
    };

    // Clean up temp file
    let _ = std::fs::remove_file(&tmp_prompt);

    if status.success() {
        // Extract __ELAPSED__ marker line
        let elapsed = stdout_text.lines()
            .find(|l| l.starts_with("__ELAPSED__"))
            .map(|l| l.trim_start_matches("__ELAPSED__").to_string());
        let text = stdout_text.lines()
            .filter(|l| !l.starts_with("__ELAPSED__"))
            .collect::<Vec<_>>()
            .join("\n")
            .trim()
            .to_string();
        let elapsed_msg = elapsed.as_deref().unwrap_or("?");
        let _ = window.emit("skill-log", format!("[验证] 提取完成，共 {} 字符输出，耗时 {}s", text.len(), elapsed_msg));
        append_log(LlmLogEntry {
            id: next_id(),
            time: chrono::Local::now().format("%Y-%m-%d %H:%M:%S").to_string(),
            model: model_name.clone(),
            scene: "验证提取".to_string(),
            prompt_summary: prompt_text.chars().take(2000).collect(),
            response_summary: text.chars().take(2000).collect(),
            elapsed_s: elapsed.as_deref().and_then(|s| s.parse::<f64>().ok()),
            success: true,
            error: None,
        });
        Ok(VerifyResult {
            image_file: image_name,
            extraction_output: text,
            success: true,
            error: None,
            elapsed,
        })
    } else {
        let err = stderr_text.trim().to_string();
        let _ = window.emit("skill-log", format!("[验证失败] {}", err));
        append_log(LlmLogEntry {
            id: next_id(),
            time: chrono::Local::now().format("%Y-%m-%d %H:%M:%S").to_string(),
            model: model_name.clone(),
            scene: "验证提取".to_string(),
            prompt_summary: prompt_text.chars().take(2000).collect(),
            response_summary: String::new(),
            elapsed_s: None,
            success: false,
            error: Some(err.chars().take(500).collect()),
        });
        Ok(VerifyResult {
            image_file: image_name,
            extraction_output: String::new(),
            success: false,
            error: Some(err),
            elapsed: None,
        })
    }
}

#[tauri::command]
pub async fn save_prompt_file(
    file_path: String,
    content: String,
) -> Result<(), String> {
    std::fs::write(&file_path, &content)
        .map_err(|e| format!("保存文件失败: {}", e))
}

#[derive(Debug, Serialize, Deserialize)]
pub struct MaterialInfo {
    pub name: String,
    pub path: String,
    pub image_count: usize,
}

#[tauri::command]
pub async fn get_materials(work_dir: String) -> Result<Vec<MaterialInfo>, String> {
    let work_path = PathBuf::from(&work_dir);
    let mut materials = Vec::new();

    let entries = std::fs::read_dir(&work_path).map_err(|e| format!("无法读取工作目录: {}", e))?;

    for entry in entries {
        if let Ok(entry) = entry {
            let path = entry.path();
            if path.is_dir() {
                // 统计目录中的图片文件数量
                let image_count = std::fs::read_dir(&path)
                    .map_err(|e| format!("无法读取子目录: {}", e))?
                    .filter_map(|e| e.ok())
                    .filter(|e| {
                        if let Some(ext) = e.path().extension() {
                            let ext = ext.to_string_lossy().to_lowercase();
                            matches!(ext.as_str(), "jpg" | "jpeg" | "png" | "bmp" | "gif" | "webp")
                        } else {
                            false
                        }
                    })
                    .count();

                // 统计目录中的PDF文件数量
                let pdf_count = std::fs::read_dir(&path)
                    .map(|rd| rd.filter_map(|e| e.ok()).filter(|e| {
                        e.path().extension()
                            .map(|ext| ext.to_string_lossy().to_lowercase() == "pdf")
                            .unwrap_or(false)
                    }).count())
                    .unwrap_or(0);

                // 只包含有图片或PDF的子目录
                if image_count > 0 || pdf_count > 0 {
                    if let Some(name) = path.file_name() {
                        materials.push(MaterialInfo {
                            name: name.to_string_lossy().to_string(),
                            path: path.to_string_lossy().to_string(),
                            image_count: image_count + pdf_count,
                        });
                    }
                }
            }
        }
    }

    materials.sort_by(|a, b| a.name.cmp(&b.name));
    Ok(materials)
}

async fn get_api_key() -> Result<String, String> {
    super::config::get_api_key().await
}
