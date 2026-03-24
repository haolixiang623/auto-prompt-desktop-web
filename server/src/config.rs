use std::fs;
use std::path::{Path, PathBuf};

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
    #[serde(default)]
    pub api_key_configured: bool,
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
    local_path: PathBuf,
    project_path: PathBuf,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
struct ProjectSettings {
    #[serde(default = "default_model_name")]
    model_name: String,
    #[serde(default)]
    default_model_id: String,
    #[serde(default = "default_models")]
    models: Vec<ModelConfig>,
    #[serde(default = "default_classify_god_prompt")]
    god_prompt: String,
    #[serde(default = "default_extract_god_prompt")]
    extract_god_prompt: String,
    #[serde(default = "default_timeout")]
    llm_timeout: u64,
}

#[derive(Debug, Serialize, Deserialize, Clone, Default)]
struct LocalSettings {
    #[serde(default)]
    api_key: String,
}

impl SettingsStore {
    pub fn new(local_path: PathBuf, project_path: PathBuf) -> Self {
        Self { local_path, project_path }
    }

    pub fn migrate_legacy_if_needed(&self) -> Result<(), String> {
        if self.project_path.exists() || !self.local_path.exists() {
            return Ok(());
        }

        let content = fs::read_to_string(&self.local_path).map_err(|error| format!("璇诲彇鏈湴閰嶇疆澶辫触: {error}"))?;
        let legacy = match serde_json::from_str::<AppSettings>(&content) {
            Ok(settings) => settings,
            Err(_) => return Ok(()),
        };

        self.save(&legacy)
    }

    pub fn load(&self) -> Result<AppSettings, String> {
        let project_settings = self.load_project_settings()?;
        let local_settings = self.load_local_settings()?;
        Ok(project_settings.into_app_settings(local_settings.api_key))
    }

    pub fn save(&self, settings: &AppSettings) -> Result<(), String> {
        let normalized = Self::normalize_app_settings(settings);
        self.save_project_settings(&ProjectSettings::from_app_settings(&normalized))?;
        self.save_local_settings(&LocalSettings {
            api_key: normalized.api_key.clone(),
        })
    }

    pub fn get_api_key(&self) -> Result<String, String> {
        let settings = self.load()?;
        if !settings.api_key.is_empty() {
            return Ok(settings.api_key);
        }

        std::env::var("DASHSCOPE_API_KEY").map_err(|_| "鏈厤缃?API Key锛岃鍦ㄨ缃腑娣诲姞".to_string())
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
            return Err("API Key 涓嶈兘涓虹┖".to_string());
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

        let output = runtime.python_process()
            .arg("-c")
            .arg(script)
            .env("DASHSCOPE_API_KEY", api_key)
            .output()
            .map_err(|error| format!("鍚姩Python澶辫触: {error}"))?;

        let stdout = String::from_utf8_lossy(&output.stdout).trim().to_string();
        let stderr = String::from_utf8_lossy(&output.stderr).trim().to_string();

        if output.status.success() && stdout == "ok" {
            Ok(())
        } else {
            Err(format!("API楠岃瘉澶辫触: {stderr}"))
        }
    }
    fn load_project_settings(&self) -> Result<ProjectSettings, String> {
        if self.project_path.exists() {
            return Self::read_project_settings_file(&self.project_path);
        }

        if self.local_path.exists() {
            let content = fs::read_to_string(&self.local_path).map_err(|error| format!("读取本地配置失败: {error}"))?;
            if let Ok(legacy) = serde_json::from_str::<AppSettings>(&content) {
                return Ok(ProjectSettings::from_app_settings(&legacy));
            }
        }

        Ok(ProjectSettings::default())
    }

    fn load_local_settings(&self) -> Result<LocalSettings, String> {
        if !self.local_path.exists() {
            return Ok(LocalSettings::default());
        }

        let content = fs::read_to_string(&self.local_path).map_err(|error| format!("读取本地配置失败: {error}"))?;
        if let Ok(settings) = serde_json::from_str::<LocalSettings>(&content) {
            return Ok(settings);
        }
        if let Ok(legacy) = serde_json::from_str::<AppSettings>(&content) {
            return Ok(LocalSettings {
                api_key: legacy.api_key,
            });
        }

        Err("解析本地配置失败".to_string())
    }

    fn save_project_settings(&self, settings: &ProjectSettings) -> Result<(), String> {
        ensure_parent_dir(&self.project_path)?;
        let content = serde_json::to_string_pretty(settings).map_err(|error| format!("序列化项目配置失败: {error}"))?;
        fs::write(&self.project_path, content).map_err(|error| format!("保存项目配置失败: {error}"))
    }

    fn save_local_settings(&self, settings: &LocalSettings) -> Result<(), String> {
        ensure_parent_dir(&self.local_path)?;
        let content = serde_json::to_string_pretty(settings).map_err(|error| format!("序列化本地配置失败: {error}"))?;
        fs::write(&self.local_path, content).map_err(|error| format!("保存本地配置失败: {error}"))
    }

    fn read_project_settings_file(path: &Path) -> Result<ProjectSettings, String> {
        let content = fs::read_to_string(path).map_err(|error| format!("读取项目配置失败: {error}"))?;
        serde_json::from_str::<ProjectSettings>(&content)
            .or_else(|_| serde_json::from_str::<AppSettings>(&content).map(|settings| ProjectSettings::from_app_settings(&settings)))
            .map_err(|error| format!("解析项目配置失败: {error}"))
    }

    fn normalize_app_settings(settings: &AppSettings) -> AppSettings {
        let mut normalized = settings.clone();
        normalized.api_key_configured = !normalized.api_key.is_empty();
        if let Some(default_model) = normalized
            .models
            .iter()
            .find(|model| model.id == normalized.default_model_id)
        {
            normalized.model_name = default_model.model_id.clone();
        } else if normalized.default_model_id.is_empty() && !normalized.models.is_empty() {
            normalized.default_model_id = normalized.models[0].id.clone();
            normalized.model_name = normalized.models[0].model_id.clone();
        }

        if normalized.model_name.is_empty() {
            normalized.model_name = default_model_name();
        }

        normalized
    }
}

impl Default for AppSettings {
    fn default() -> Self {
        Self {
            api_key: String::new(),
            api_key_configured: false,
            model_name: default_model_name(),
            default_model_id: "1".to_string(),
            models: default_models(),
            god_prompt: default_classify_god_prompt(),
            extract_god_prompt: default_extract_god_prompt(),
            llm_timeout: default_timeout(),
        }
    }
}
impl Default for ProjectSettings {
    fn default() -> Self {
        Self {
            model_name: default_model_name(),
            default_model_id: "1".to_string(),
            models: default_models(),
            god_prompt: default_classify_god_prompt(),
            extract_god_prompt: default_extract_god_prompt(),
            llm_timeout: default_timeout(),
        }
    }
}

impl ProjectSettings {
    fn from_app_settings(settings: &AppSettings) -> Self {
        Self {
            model_name: settings.model_name.clone(),
            default_model_id: settings.default_model_id.clone(),
            models: settings.models.clone(),
            god_prompt: settings.god_prompt.clone(),
            extract_god_prompt: settings.extract_god_prompt.clone(),
            llm_timeout: settings.llm_timeout,
        }
    }

    fn into_app_settings(self, api_key: String) -> AppSettings {
        let api_key_configured = !api_key.is_empty();
        AppSettings {
            api_key,
            api_key_configured,
            model_name: self.model_name,
            default_model_id: self.default_model_id,
            models: self.models,
            god_prompt: self.god_prompt,
            extract_god_prompt: self.extract_god_prompt,
            llm_timeout: self.llm_timeout,
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
    r#"你是一个专业的提示词优化专家，擅长分析材料分类任务并优化提示词。

优化目标：
1. 提升分类准确性，确保附件被归入正确材料类别。
2. 增强识别鲁棒性，适配不同格式、排版和质量的文档。
3. 优化输出结构，保证 JSON 结果稳定、字段完整。

优化原则：
- 保持模板中的占位符不变，例如 $(material_list)。
- 强化标题、表格名、盖章、编号等关键特征的识别。
- 针对识别错误给出具体改进建议。
- 保持模板通用，不写入具体材料名称示例。
- 输出完整优化后的模板，不要附加额外说明。"#.to_string()
}

fn default_extract_god_prompt() -> String {
    r#"你是一个专业的政务文档要素提取专家，擅长分析样本文档并生成可泛化的提取提示词。

核心能力：
1. 理解文档结构，识别标题、表格、盖章区、签名区等关键区域。
2. 基于样本抽象通用规则，适配同类文档的后续提取。
3. 避免过拟合，不把样本中的具体值直接写进规则。

生成要求：
- 规则必须具备通用性，适用于同类型文档。
- 不要写入具体金额、日期、名称、编号等样本专有内容。
- 可以描述位置特征、结构特征和数据类型特征。
- 输出完整可用的提取提示词，不添加额外解释。"#.to_string()
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
            name: "Qwen Plus (鏂囨湰)".to_string(),
            model_id: "qwen-plus".to_string(),
            model_type: "text".to_string(),
            params: vec![],
        },
        ModelConfig {
            id: "5".to_string(),
            name: "Qwen Max (鏂囨湰)".to_string(),
            model_id: "qwen-max".to_string(),
            model_type: "text".to_string(),
            params: vec![],
        },
    ]
}

#[cfg(test)]
mod tests {
    use super::{AppSettings, ModelConfig, ModelParam, SettingsStore};
    use crate::runtime::ensure_parent_dir;
    use std::fs;
    use std::path::PathBuf;
    use uuid::Uuid;

    fn temp_paths() -> (PathBuf, PathBuf, PathBuf) {
        let root = std::env::temp_dir().join(format!("auto-prompt-config-tests-{}", Uuid::new_v4()));
        let local = root.join("local").join("settings.json");
        let project = root.join("workspace").join("auto-prompt.project.json");
        (root, local, project)
    }

    fn sample_settings() -> AppSettings {
        AppSettings {
            api_key: "secret-key".to_string(),
            api_key_configured: true,
            model_name: "qwen-vl-max".to_string(),
            default_model_id: "custom".to_string(),
            models: vec![ModelConfig {
                id: "custom".to_string(),
                name: "Shared Model".to_string(),
                model_id: "qwen3.5-35b-a3b".to_string(),
                model_type: "vl".to_string(),
                params: vec![ModelParam {
                    key: "enable_thinking".to_string(),
                    value: serde_json::json!(false),
                }],
            }],
            god_prompt: "classify".to_string(),
            extract_god_prompt: "extract".to_string(),
            llm_timeout: 180,
        }
    }

    #[test]
    fn save_splits_project_and_local_settings() {
        let (root, local_path, project_path) = temp_paths();
        let store = SettingsStore::new(local_path.clone(), project_path.clone());
        let settings = sample_settings();

        store.save(&settings).unwrap();

        let local_content = fs::read_to_string(&local_path).unwrap();
        let project_content = fs::read_to_string(&project_path).unwrap();

        assert!(local_content.contains("secret-key"));
        assert!(!project_content.contains("secret-key"));
        assert!(project_content.contains("Shared Model"));

        let loaded = store.load().unwrap();
        assert_eq!(loaded.api_key, "secret-key");
        assert!(loaded.api_key_configured);
        assert_eq!(loaded.default_model_id, "custom");
        assert_eq!(loaded.model_name, "qwen3.5-35b-a3b");
        assert_eq!(loaded.models.len(), 1);

        let _ = fs::remove_dir_all(root);
    }

    #[test]
    fn migrate_legacy_settings_promotes_shared_config_to_project_file() {
        let (root, local_path, project_path) = temp_paths();
        let legacy = sample_settings();
        ensure_parent_dir(&local_path).unwrap();
        fs::write(&local_path, serde_json::to_string_pretty(&legacy).unwrap()).unwrap();

        let store = SettingsStore::new(local_path.clone(), project_path.clone());
        store.migrate_legacy_if_needed().unwrap();

        assert!(project_path.exists());

        let local_content = fs::read_to_string(&local_path).unwrap();
        let project_content = fs::read_to_string(&project_path).unwrap();
        assert!(local_content.contains("secret-key"));
        assert!(!local_content.contains("Shared Model"));
        assert!(project_content.contains("Shared Model"));

        let loaded = store.load().unwrap();
        assert_eq!(loaded.api_key, "secret-key");
        assert!(loaded.api_key_configured);
        assert_eq!(loaded.model_name, "qwen3.5-35b-a3b");
        assert_eq!(loaded.models[0].model_id, "qwen3.5-35b-a3b");

        let _ = fs::remove_dir_all(root);
    }
}
