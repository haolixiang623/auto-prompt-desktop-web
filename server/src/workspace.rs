use std::fs;
use std::path::{Component, Path, PathBuf};

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use uuid::Uuid;

use crate::paths::AppPaths;
use crate::runtime::ensure_parent_dir;

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct WorkspaceFile {
    pub relative_path: String,
    pub size: u64,
    pub is_dir: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct WorkspaceSummary {
    pub id: String,
    pub name: String,
    pub root_path: String,
    pub created_at: DateTime<Utc>,
    pub files: Vec<WorkspaceFile>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct UploadManifestEntry {
    pub relative_path: String,
}

#[derive(Debug, Clone)]
pub struct UploadedBlob {
    pub original_name: String,
    pub relative_path: String,
    pub bytes: Vec<u8>,
}

#[derive(Debug, Clone)]
pub struct WorkspaceService {
    paths: AppPaths,
}

impl WorkspaceService {
    pub fn new(paths: AppPaths) -> Self {
        Self { paths }
    }

    pub fn create_workspace(&self, name: Option<String>, uploads: Vec<UploadedBlob>) -> Result<WorkspaceSummary, String> {
        let id = Uuid::new_v4().to_string();
        let root = self.paths.workspace_root.join(&id);
        fs::create_dir_all(&root).map_err(|error| format!("创建工作区失败: {error}"))?;
        let shared_prefix = shared_workspace_prefix(&uploads);

        for upload in uploads {
            let relative_source = strip_workspace_prefix(&upload.relative_path, shared_prefix.as_deref());
            let relative_path = sanitize_relative_path(relative_source)?;
            let target_path = root.join(relative_path);
            ensure_parent_dir(&target_path)?;
            fs::write(&target_path, upload.bytes).map_err(|error| format!("保存上传文件失败: {error}"))?;
        }

        self.get_workspace(&id).map(|mut summary| {
            summary.name = name.unwrap_or_else(|| format!("workspace-{id}"));
            summary
        })
    }

    pub fn save_temp_uploads(&self, uploads: Vec<UploadedBlob>) -> Result<Vec<String>, String> {
        let upload_root = self.paths.upload_root.join(Uuid::new_v4().to_string());
        fs::create_dir_all(&upload_root).map_err(|error| format!("创建上传目录失败: {error}"))?;

        let mut stored_paths = Vec::new();
        for upload in uploads {
            let relative_path = sanitize_relative_path(&upload.relative_path)?;
            let file_path = upload_root.join(relative_path);
            ensure_parent_dir(&file_path)?;
            fs::write(&file_path, upload.bytes).map_err(|error| format!("保存上传文件失败: {error}"))?;
            stored_paths.push(file_path.to_string_lossy().to_string());
        }

        Ok(stored_paths)
    }

    pub fn get_workspace(&self, workspace_id: &str) -> Result<WorkspaceSummary, String> {
        let root = self.paths.workspace_root.join(workspace_id);
        if !root.exists() {
            return Err("工作区不存在".to_string());
        }

        let metadata = fs::metadata(&root).map_err(|error| format!("读取工作区失败: {error}"))?;
        let created_at = metadata
            .created()
            .or_else(|_| metadata.modified())
            .map(DateTime::<Utc>::from)
            .unwrap_or_else(|_| Utc::now());

        Ok(WorkspaceSummary {
            id: workspace_id.to_string(),
            name: format!("workspace-{workspace_id}"),
            root_path: root.to_string_lossy().to_string(),
            created_at,
            files: scan_files(&root)?,
        })
    }
}

fn scan_files(root: &Path) -> Result<Vec<WorkspaceFile>, String> {
    let mut files = Vec::new();
    scan_dir(root, root, &mut files)?;
    files.sort_by(|left, right| left.relative_path.cmp(&right.relative_path));
    Ok(files)
}

fn scan_dir(root: &Path, current: &Path, files: &mut Vec<WorkspaceFile>) -> Result<(), String> {
    let entries = fs::read_dir(current).map_err(|error| error.to_string())?;
    for entry in entries.flatten() {
        let path = entry.path();
        let metadata = entry.metadata().map_err(|error| error.to_string())?;
        let relative_path = path
            .strip_prefix(root)
            .unwrap_or(&path)
            .to_string_lossy()
            .replace('\\', "/");

        files.push(WorkspaceFile {
            relative_path,
            size: metadata.len(),
            is_dir: metadata.is_dir(),
        });

        if metadata.is_dir() {
            scan_dir(root, &path, files)?;
        }
    }

    Ok(())
}

fn sanitize_relative_path(relative_path: &str) -> Result<PathBuf, String> {
    let path = PathBuf::from(relative_path.replace('\\', "/"));
    if path.is_absolute() {
        return Err("上传路径不能是绝对路径".to_string());
    }

    let invalid = path.components().any(|component| matches!(component, Component::ParentDir));
    if invalid {
        return Err("上传路径不能包含 ..".to_string());
    }

    Ok(path)
}

fn shared_workspace_prefix(uploads: &[UploadedBlob]) -> Option<String> {
    let mut prefix = None;

    for upload in uploads {
        let normalized = upload.relative_path.replace('\\', "/");
        let mut parts = normalized.split('/').filter(|part| !part.is_empty());
        let first = parts.next()?;
        if parts.next().is_none() {
            return None;
        }

        match &prefix {
            Some(existing) if existing != first => return None,
            Some(_) => {}
            None => prefix = Some(first.to_string()),
        }
    }

    prefix
}

fn strip_workspace_prefix<'a>(relative_path: &'a str, prefix: Option<&str>) -> &'a str {
    match prefix {
        Some(prefix) => relative_path
            .strip_prefix(prefix)
            .and_then(|value| value.strip_prefix('/').or(Some(value)))
            .filter(|value| !value.is_empty())
            .unwrap_or(relative_path),
        None => relative_path,
    }
}

#[cfg(test)]
mod tests {
    use super::{shared_workspace_prefix, strip_workspace_prefix, UploadedBlob};

    fn upload(path: &str) -> UploadedBlob {
        UploadedBlob {
            original_name: path.to_string(),
            relative_path: path.to_string(),
            bytes: vec![],
        }
    }

    #[test]
    fn detects_shared_top_level_directory_for_workspace_uploads() {
        let uploads = vec![
            upload("doc-workspace/factors.xlsx"),
            upload("doc-workspace/营业执照/sample.png"),
        ];

        let prefix = shared_workspace_prefix(&uploads);

        assert_eq!(prefix.as_deref(), Some("doc-workspace"));
        assert_eq!(strip_workspace_prefix("doc-workspace/factors.xlsx", prefix.as_deref()), "factors.xlsx");
        assert_eq!(
            strip_workspace_prefix("doc-workspace/营业执照/sample.png", prefix.as_deref()),
            "营业执照/sample.png"
        );
    }

    #[test]
    fn skips_prefix_stripping_for_mixed_upload_roots() {
        let uploads = vec![
            upload("a/factors.xlsx"),
            upload("b/sample.png"),
        ];

        assert_eq!(shared_workspace_prefix(&uploads), None);
        assert_eq!(strip_workspace_prefix("a/factors.xlsx", None), "a/factors.xlsx");
    }
}
