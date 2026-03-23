use serde::{Deserialize, Serialize};
use std::path::PathBuf;

#[derive(Debug, Serialize, Deserialize)]
pub struct DirEntry {
    pub name: String,
    pub path: String,
    pub is_file: bool,
    pub is_dir: bool,
    pub size: Option<u64>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct DialogFilter {
    pub name: String,
    pub extensions: Vec<String>,
}

#[tauri::command]
pub async fn read_directory(path: String) -> Result<Vec<DirEntry>, String> {
    let path = PathBuf::from(&path);
    let entries = std::fs::read_dir(&path).map_err(|e| e.to_string())?;

    let mut result = Vec::new();
    for entry in entries {
        if let Ok(entry) = entry {
            let metadata = entry.metadata().map_err(|e| e.to_string())?;
            result.push(DirEntry {
                name: entry.file_name().to_string_lossy().to_string(),
                path: entry.path().to_string_lossy().to_string(),
                is_file: metadata.is_file(),
                is_dir: metadata.is_dir(),
                size: if metadata.is_file() {
                    Some(metadata.len())
                } else {
                    None
                },
            });
        }
    }

    Ok(result)
}

#[tauri::command]
pub async fn read_file(path: String) -> Result<String, String> {
    std::fs::read_to_string(&path).map_err(|e| e.to_string())
}

#[tauri::command]
pub async fn write_file(path: String, content: String) -> Result<(), String> {
    std::fs::write(&path, content).map_err(|e| e.to_string())
}

/// 目录选择器 - 使用 rfd 阻塞式 API 在独立线程执行，彻底解决 macOS 死锁问题
#[tauri::command]
pub async fn select_directory() -> Result<Option<String>, String> {
    let result = tokio::task::spawn_blocking(|| {
        rfd::FileDialog::new().pick_folder()
    })
    .await
    .map_err(|e| e.to_string())?;

    Ok(result.map(|p| p.to_string_lossy().to_string()))
}

/// 单文件选择器 - 使用 rfd 阻塞式 API 在独立线程执行，彻底解决 macOS 死锁问题
#[tauri::command]
pub async fn select_file(
    filters: Option<Vec<DialogFilter>>,
) -> Result<Option<String>, String> {
    let filters = filters.unwrap_or_default();
    let result = tokio::task::spawn_blocking(move || {
        let mut dialog = rfd::FileDialog::new();
        for f in &filters {
            let exts: Vec<&str> = f.extensions.iter().map(|s| s.as_str()).collect();
            dialog = dialog.add_filter(&f.name, &exts);
        }
        dialog.pick_file()
    })
    .await
    .map_err(|e| e.to_string())?;

    Ok(result.map(|p| p.to_string_lossy().to_string()))
}

/// 多文件选择器 - 使用 rfd 阻塞式 API 在独立线程执行，彻底解决 macOS 死锁问题
#[tauri::command]
pub async fn select_files(
    filters: Option<Vec<DialogFilter>>,
) -> Result<Option<Vec<String>>, String> {
    let filters = filters.unwrap_or_default();
    let result = tokio::task::spawn_blocking(move || {
        let mut dialog = rfd::FileDialog::new();
        for f in &filters {
            let exts: Vec<&str> = f.extensions.iter().map(|s| s.as_str()).collect();
            dialog = dialog.add_filter(&f.name, &exts);
        }
        dialog.pick_files()
    })
    .await
    .map_err(|e| e.to_string())?;

    Ok(result.map(|paths| {
        paths.iter().map(|p| p.to_string_lossy().to_string()).collect()
    }))
}
