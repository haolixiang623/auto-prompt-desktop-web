use std::fs;
use std::path::PathBuf;

use serde::{Deserialize, Serialize};

use crate::runtime::{ensure_parent_dir, RuntimeContext};

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct ModelParam {
    pub key: String,
    pub value: serde_json::Value,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct ModelConfig {
    pub id: String,
    pub name: String,
    pub model_id: String,
    #[serde(rename = "type")]
    pub model_type: String,
    #[serde(default)]
    pub params: Vec<ModelParam>,
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
    #[serde(default = "default_timeout")]
    pub llm_timeout: u64,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct DefaultGodPrompts {
    pub classify: String,
    pub extract: String,
}

#[derive(Debug, Clone)]
pub struct SettingsStore {
    path: PathBuf,
}

impl SettingsStore {
    pub fn new(path: PathBuf) -> Self {
        Self { path }
    }

    pub fn load(&self) -> Result<AppSettings, String> {
        if !self.path.exists() {
            return Ok(AppSettings::default());
        }

        let content = fs::read_to_string(&self.path).map_err(|error| format!("读取配置失败: {error}"))?;
        serde_json::from_str(&content).map_err(|error| format!("解析配置失败: {error}"))
    }

    pub fn save(&self, settings: &AppSettings) -> Result<(), String> {
        ensure_parent_dir(&self.path)?;
        let content =
            serde_json::to_string_pretty(settings).map_err(|error| format!("序列化配置失败: {error}"))?;
        fs::write(&self.path, content).map_err(|error| format!("保存配置失败: {error}"))
    }

    pub fn get_api_key(&self) -> Result<String, String> {
        let settings = self.load()?;
        if !settings.api_key.is_empty() {
            return Ok(settings.api_key);
        }

        std::env::var("DASHSCOPE_API_KEY").map_err(|_| "未配置 API Key，请在设置中添加".to_string())
    }

    pub fn get_model_config_by_id(&self, model_cfg_id: Option<String>) -> Result<Option<ModelConfig>, String> {
        let settings = self.load()?;
        let config_id = model_cfg_id.or_else(|| {
            if settings.default_model_id.is_empty() {
                None
            } else {
                Some(settings.default_model_id.clone())
            }
        });

        Ok(config_id.and_then(|id| settings.models.into_iter().find(|model| model.id == id)))
    }

    pub fn get_llm_timeout(&self) -> Result<u64, String> {
        let settings = self.load()?;
        Ok(if settings.llm_timeout == 0 { 120 } else { settings.llm_timeout })
    }

    pub fn default_god_prompts(&self) -> DefaultGodPrompts {
        DefaultGodPrompts {
            classify: default_classify_god_prompt(),
            extract: default_extract_god_prompt(),
        }
    }

    pub fn test_api_key(&self, runtime: &RuntimeContext, api_key: String) -> Result<(), String> {
        if api_key.is_empty() {
            return Err("API Key 不能为空".to_string());
        }

        let script = r#"
import os
import sys

api_key = os.environ.get('DASHSCOPE_API_KEY', '')
if not api_key:
    print('missing', file=sys.stderr)
    sys.exit(1)

try:
    from openai import OpenAI
    client = OpenAI(api_key=api_key, base_url='https://dashscope.aliyuncs.com/compatible-mode/v1')
    client.chat.completions.create(
        model='qwen-vl-max',
        messages=[{'role': 'user', 'content': 'hi'}],
        max_tokens=1,
    )
    print('ok')
except Exception as error:
    print(f'Error: {error}', file=sys.stderr)
    sys.exit(1)
"#;

        let output = std::process::Command::new(runtime.python_command())
            .arg("-c")
            .arg(script)
            .env("DASHSCOPE_API_KEY", api_key)
            .output()
            .map_err(|error| format!("启动Python失败: {error}"))?;

        let stdout = String::from_utf8_lossy(&output.stdout).trim().to_string();
        let stderr = String::from_utf8_lossy(&output.stderr).trim().to_string();

        if output.status.success() && stdout == "ok" {
            Ok(())
        } else {
            Err(format!("API验证失败: {stderr}"))
        }
    }
}

impl Default for AppSettings {
    fn default() -> Self {
        Self {
            api_key: String::new(),
            model_name: default_model_name(),
            default_model_id: "1".to_string(),
            models: default_models(),
            god_prompt: default_classify_god_prompt(),
            extract_god_prompt: default_extract_god_prompt(),
            llm_timeout: default_timeout(),
        }
    }
}

pub fn params_to_json(params: &[ModelParam]) -> String {
    if params.is_empty() {
        return "{}".to_string();
    }

    let map: serde_json::Map<String, serde_json::Value> =
        params.iter().map(|param| (param.key.clone(), param.value.clone())).collect();
    serde_json::to_string(&map).unwrap_or_else(|_| "{}".to_string())
}

fn default_model_name() -> String {
    "qwen-vl-max".to_string()
}

fn default_timeout() -> u64 {
    120
}

fn default_classify_god_prompt() -> String {
    "你是一个专业的提示词优化专家，擅长分析材料分类任务的特点并优化提示词。\n\n你的优化目标：\n1. 提升分类准确性：确保每个附件都能被正确归类到对应的材料类别\n2. 增强识别鲁棒性：处理各种格式、排版、质量的文档图片\n3. 优化输出结构：保证JSON格式规范、字段完整\n\n优化原则：\n- 保持模板中的占位符不变（如 $(material_list)）\n- 强化关键特征识别（标题、表格名称、盖章、文件编号等）\n- 针对识别错误给出具体改进建议\n- 保持模板的通用性，不要在模板中写入具体的材料名称示例\n- 输出完整优化后的模板，不添加额外说明".to_string()
}

fn default_extract_god_prompt() -> String {
    "你是一个专业的政务文档要素提取专家，擅长分析各类行政审批文档的结构特征。\n\n你的核心能力：\n1. 理解文档结构：识别标题、表格、盖章区、签名区等关键区域\n2. 泛化规则生成：基于样本文档生成适用于同类文档的通用提取规则\n3. 避免过拟合：不将样本中的具体数值写入规则，而是描述数据类型和位置特征\n\n生成规则时的要求：\n- 规则必须具备通用性，适用于同类型的所有文档\n- 禁止出现具体数值、金额、日期、名称、编号等样本特有内容\n- 基于结构特征描述（如\"位于文档抬头\"、\"表格第X列\"、\"盖章处下方\"）\n- 可描述数据类型（如\"数字\"、\"日期格式\"、\"中文名称\"），但不写具体值".to_string()
}

fn default_models() -> Vec<ModelConfig> {
    vec![
        ModelConfig {
            id: "1".to_string(),
            name: "Qwen VL Max".to_string(),
            model_id: "qwen-vl-max".to_string(),
            model_type: "vl".to_string(),
            params: vec![],
        },
        ModelConfig {
            id: "2".to_string(),
            name: "Qwen VL Plus".to_string(),
            model_id: "qwen-vl-plus".to_string(),
            model_type: "vl".to_string(),
            params: vec![],
        },
        ModelConfig {
            id: "3".to_string(),
            name: "Qwen2.5 VL 72B".to_string(),
            model_id: "qwen2.5-vl-72b-instruct".to_string(),
            model_type: "vl".to_string(),
            params: vec![],
        },
        ModelConfig {
            id: "4".to_string(),
            name: "Qwen Plus (文本)".to_string(),
            model_id: "qwen-plus".to_string(),
            model_type: "text".to_string(),
            params: vec![],
        },
        ModelConfig {
            id: "5".to_string(),
            name: "Qwen Max (文本)".to_string(),
            model_id: "qwen-max".to_string(),
            model_type: "text".to_string(),
            params: vec![],
        },
    ]
}
