use serde::{Deserialize, Serialize};
use std::path::PathBuf;

#[derive(Debug, Serialize, Deserialize)]
pub struct SkillInfo {
    pub name: String,
    pub path: String,
    pub files: Vec<String>,
    pub description: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ImportSkillResult {
    pub success: bool,
    pub message: String,
    pub files_copied: usize,
    pub files_overwritten: usize,
}

fn get_skills_root() -> Result<PathBuf, String> {
    super::path_utils::ensure_user_skills_root()
}

#[tauri::command]
pub async fn list_skills() -> Result<Vec<SkillInfo>, String> {
    let skills_root = get_skills_root()?;
    let mut skills = Vec::new();

    let descriptions = [
        ("doc-extract-prompt-gen", "生成文档要素提取提示词"),
        ("material-classifier", "材料自动分类"),
        ("case-import", "案例导入"),
        ("factor-json-generator", "要素JSON生成"),
    ];

    let entries = std::fs::read_dir(&skills_root)
        .map_err(|e| format!("读取skills目录失败: {}", e))?;

    for entry in entries.filter_map(|e| e.ok()) {
        let path = entry.path();
        if !path.is_dir() {
            continue;
        }
        let name = path.file_name()
            .map(|n| n.to_string_lossy().to_string())
            .unwrap_or_default();
        if name.starts_with('.') {
            continue;
        }

        let desc = descriptions.iter()
            .find(|(n, _)| *n == name.as_str())
            .map(|(_, d)| d.to_string())
            .unwrap_or_else(|| "自定义skill".to_string());

        let mut files = Vec::new();
        if let Ok(file_entries) = std::fs::read_dir(&path) {
            for fe in file_entries.filter_map(|e| e.ok()) {
                if fe.path().is_file() {
                    files.push(fe.file_name().to_string_lossy().to_string());
                }
            }
        }
        files.sort();

        skills.push(SkillInfo {
            name,
            path: path.to_string_lossy().to_string(),
            files,
            description: desc,
        });
    }

    skills.sort_by(|a, b| a.name.cmp(&b.name));
    Ok(skills)
}

#[tauri::command]
pub async fn import_skill_files(
    source_dir: String,
    skill_name: String,
    overwrite: bool,
) -> Result<ImportSkillResult, String> {
    let skills_root = get_skills_root()?;
    let target_dir = skills_root.join(&skill_name);

    if !target_dir.exists() {
        std::fs::create_dir_all(&target_dir)
            .map_err(|e| format!("创建skill目录失败: {}", e))?;
    }

    let source_path = PathBuf::from(&source_dir);
    if !source_path.exists() {
        return Err(format!("源目录不存在: {}", source_dir));
    }

    let mut files_copied = 0usize;
    let mut files_overwritten = 0usize;
    let mut skipped = 0usize;

    let entries = std::fs::read_dir(&source_path)
        .map_err(|e| format!("读取源目录失败: {}", e))?;

    for entry in entries.filter_map(|e| e.ok()) {
        let src = entry.path();
        if !src.is_file() {
            continue;
        }
        let fname = entry.file_name();
        let dst = target_dir.join(&fname);

        if dst.exists() {
            if overwrite {
                std::fs::copy(&src, &dst)
                    .map_err(|e| format!("覆盖文件失败 {:?}: {}", fname, e))?;
                files_overwritten += 1;
            } else {
                skipped += 1;
            }
        } else {
            std::fs::copy(&src, &dst)
                .map_err(|e| format!("复制文件失败 {:?}: {}", fname, e))?;
            files_copied += 1;
        }
    }

    Ok(ImportSkillResult {
        success: true,
        message: format!(
            "导入完成：新增 {} 个，覆盖 {} 个，跳过 {} 个",
            files_copied, files_overwritten, skipped
        ),
        files_copied,
        files_overwritten,
    })
}
