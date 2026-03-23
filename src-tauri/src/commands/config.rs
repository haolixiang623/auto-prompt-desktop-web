use serde::{Deserialize, Serialize};
use std::path::PathBuf;
use crate::commands::env_check::get_python_command;

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct ModelParam {
    pub key: String,
    pub value: serde_json::Value, // 支持 bool / string / number
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct ModelConfig {
    pub id: String,
    pub name: String,
    pub model_id: String,
    #[serde(rename = "type")]
    pub model_type: String, // "vl" | "text"
    #[serde(default)]
    pub params: Vec<ModelParam>, // 额外模型参数，如 enable_thinking: false
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct AppSettings {
    pub api_key: String,
    #[serde(default = "default_model_name")]
    pub model_name: String,
    #[serde(default)]
    pub default_model_id: String,
    #[serde(default = "default_models")]
    pub models: Vec<ModelConfig>,
    #[serde(default = "default_classify_god_prompt")]
    pub god_prompt: String,
    #[serde(default = "default_extract_god_prompt")]
    pub extract_god_prompt: String,
    /// LLM 调用超时时间（秒），默认 120 秒
    #[serde(default = "default_timeout")]
    pub llm_timeout: u64,
}

fn default_model_name() -> String {
    "qwen-vl-max".to_string()
}

fn default_timeout() -> u64 {
    120
}

fn default_classify_god_prompt() -> String {
    "你是一个专业的提示词优化专家，擅长分析材料分类任务的特点并优化提示词。

你的优化目标：
1. 提升分类准确性：确保每个附件都能被正确归类到对应的材料类别
2. 增强识别鲁棒性：处理各种格式、排版、质量的文档图片
3. 优化输出结构：保证JSON格式规范、字段完整

优化原则：
- 保持模板中的占位符不变（如 $(material_list)）
- 强化关键特征识别（标题、表格名称、盖章、文件编号等）
- 针对识别错误给出具体改进建议
- 保持模板的通用性，不要在模板中写入具体的材料名称示例
- 输出完整优化后的模板，不添加额外说明".to_string()
}

fn default_extract_god_prompt() -> String {
    "你是一个专业的政务文档要素提取专家，擅长分析各类行政审批文档的结构特征。\n\n你的核心能力：\n1. 理解文档结构：识别标题、表格、盖章区、签名区等关键区域\n2. 泛化规则生成：基于样本文档生成适用于同类文档的通用提取规则\n3. 避免过拟合：不将样本中的具体数值写入规则，而是描述数据类型和位置特征\n\n生成规则时的要求：\n- 规则必须具备通用性，适用于同类型的所有文档\n- 禁止出现具体数值、金额、日期、名称、编号等样本特有内容\n- 基于结构特征描述（如\"位于文档抬头\"、\"表格第X列\"、\"盖章处下方\"）\n- 可描述数据类型（如\"数字\"、\"日期格式\"、\"中文名称\"），但不写具体值".to_string()
}

fn default_models() -> Vec<ModelConfig> {
    vec![
        ModelConfig { id: "1".to_string(), name: "Qwen VL Max".to_string(), model_id: "qwen-vl-max".to_string(), model_type: "vl".to_string(), params: vec![] },
        ModelConfig { id: "2".to_string(), name: "Qwen VL Plus".to_string(), model_id: "qwen-vl-plus".to_string(), model_type: "vl".to_string(), params: vec![] },
        ModelConfig { id: "3".to_string(), name: "Qwen2.5 VL 72B".to_string(), model_id: "qwen2.5-vl-72b-instruct".to_string(), model_type: "vl".to_string(), params: vec![] },
        ModelConfig { id: "4".to_string(), name: "Qwen Plus (文本)".to_string(), model_id: "qwen-plus".to_string(), model_type: "text".to_string(), params: vec![] },
        ModelConfig { id: "5".to_string(), name: "Qwen Max (文本)".to_string(), model_id: "qwen-max".to_string(), model_type: "text".to_string(), params: vec![] },
    ]
}

/// 将 ModelConfig 的 params 序列化为 JSON 字符串，供 Python 脚本通过 --extra-params 接收
pub fn params_to_json(params: &[ModelParam]) -> String {
    if params.is_empty() {
        return "{}".to_string();
    }
    let map: serde_json::Map<String, serde_json::Value> = params
        .iter()
        .map(|p| (p.key.clone(), p.value.clone()))
        .collect();
    serde_json::to_string(&map).unwrap_or_else(|_| "{}".to_string())
}

/// 根据 model_cfg_id 获取 ModelConfig（含 params）
pub async fn get_model_config_by_id(model_cfg_id: Option<String>) -> Option<ModelConfig> {
    if let Ok(settings) = load_settings().await {
        let cfg_id = model_cfg_id.unwrap_or(settings.default_model_id.clone());
        return settings.models.into_iter().find(|m| m.id == cfg_id);
    }
    None
}

impl Default for AppSettings {
    fn default() -> Self {
        Self {
            api_key: String::new(),
            model_name: "qwen-vl-max".to_string(),
            default_model_id: "1".to_string(),
            models: default_models(),
            god_prompt: String::new(),
            extract_god_prompt: String::new(),
            llm_timeout: 120,
        }
    }
}

fn get_config_path() -> Result<PathBuf, String> {
    // Use user's config directory
    let config_dir = dirs::config_dir()
        .ok_or("无法获取配置目录")?
        .join("auto-prompt");

    // Create directory if it doesn't exist
    if !config_dir.exists() {
        std::fs::create_dir_all(&config_dir)
            .map_err(|e| format!("创建配置目录失败: {}", e))?;
    }

    Ok(config_dir.join("settings.json"))
}

#[derive(Debug, Serialize)]
pub struct DefaultGodPrompts {
    pub classify: String,
    pub extract: String,
}

#[tauri::command]
pub fn get_default_god_prompts() -> DefaultGodPrompts {
    DefaultGodPrompts {
        classify: default_classify_god_prompt(),
        extract: default_extract_god_prompt(),
    }
}

#[tauri::command]
pub async fn load_settings() -> Result<AppSettings, String> {
    let config_path = get_config_path()?;

    if !config_path.exists() {
        return Ok(AppSettings::default());
    }

    let content = std::fs::read_to_string(&config_path)
        .map_err(|e| format!("读取配置失败: {}", e))?;

    let settings: AppSettings = serde_json::from_str(&content)
        .map_err(|e| format!("解析配置失败: {}", e))?;

    Ok(settings)
}

#[tauri::command]
pub async fn save_settings(settings: AppSettings) -> Result<(), String> {
    let config_path = get_config_path()?;

    let content = serde_json::to_string_pretty(&settings)
        .map_err(|e| format!("序列化配置失败: {}", e))?;

    std::fs::write(&config_path, content)
        .map_err(|e| format!("保存配置失败: {}", e))?;

    Ok(())
}

// Get API key from settings or environment variable
pub async fn get_api_key() -> Result<String, String> {
    let settings = load_settings().await?;
    if !settings.api_key.is_empty() {
        return Ok(settings.api_key);
    }
    std::env::var("DASHSCOPE_API_KEY")
        .map_err(|_| "未配置 API Key，请在设置中添加".to_string())
}

// Get configured model name (legacy single model)
pub async fn get_model_name() -> String {
    load_settings().await
        .map(|s| if s.model_name.is_empty() { "qwen-vl-max".to_string() } else { s.model_name })
        .unwrap_or_else(|_| "qwen-vl-max".to_string())
}

// Sync fallback model name for contexts where async is not available
pub fn get_model_name_sync() -> String {
    "qwen-vl-max".to_string()
}

#[tauri::command]
pub async fn test_api_key(api_key: String) -> Result<(), String> {
    if api_key.is_empty() {
        return Err("API Key 不能为空".to_string());
    }
    let script = r#"
import sys, os
api_key = os.environ.get('DASHSCOPE_API_KEY', '')
if not api_key:
    print('missing', file=sys.stderr)
    sys.exit(1)
try:
    from openai import OpenAI
    client = OpenAI(api_key=api_key, base_url='https://dashscope.aliyuncs.com/compatible-mode/v1')
    resp = client.chat.completions.create(
        model='qwen-vl-max',
        messages=[{'role': 'user', 'content': 'hi'}],
        max_tokens=1
    )
    print('ok')
except Exception as e:
    print(f"Error: {str(e)}", file=sys.stderr)
    sys.exit(1)
"#;
    println!("Testing API key with qwen-vl-max model...");
    let output = std::process::Command::new(get_python_command())
        .arg("-c")
        .arg(script)
        .env("DASHSCOPE_API_KEY", &api_key)
        .output()
        .map_err(|e| format!("启动Python失败: {}", e))?;

    let stdout = String::from_utf8_lossy(&output.stdout).trim().to_string();
    let stderr = String::from_utf8_lossy(&output.stderr).trim().to_string();
    
    println!("API test stdout: {}", stdout);
    println!("API test stderr: {}", stderr);
    println!("API test exit code: {:?}", output.status.code());

    if output.status.success() && stdout == "ok" {
        Ok(())
    } else {
        Err(format!("API验证失败: {}", stderr))
    }
}

// Get model_id by model config id; if None, use default_model_id from settings
pub async fn get_model_id_by_id(model_cfg_id: Option<String>) -> String {
    if let Ok(settings) = load_settings().await {
        let cfg_id = model_cfg_id
            .or_else(|| if settings.default_model_id.is_empty() { None } else { Some(settings.default_model_id.clone()) });
        if let Some(ref id) = cfg_id {
            if let Some(m) = settings.models.iter().find(|m| &m.id == id) {
                return m.model_id.clone();
            }
        }
    }
    get_model_name().await
}

/// Get LLM timeout in seconds from settings
pub async fn get_llm_timeout() -> u64 {
    load_settings().await
        .map(|s| if s.llm_timeout == 0 { 120 } else { s.llm_timeout })
        .unwrap_or(120)
}
