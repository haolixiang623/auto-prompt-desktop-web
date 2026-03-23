use std::collections::HashSet;
use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;

fn project_root_from_manifest() -> Option<PathBuf> {
    std::env::var("CARGO_MANIFEST_DIR")
        .ok()
        .and_then(|m| PathBuf::from(m).parent().map(|p| p.to_path_buf()))
}

fn dedupe_paths(paths: Vec<PathBuf>) -> Vec<PathBuf> {
    let mut seen = HashSet::new();
    let mut out = Vec::new();
    for p in paths {
        let k = p.to_string_lossy().to_lowercase();
        if seen.insert(k) {
            out.push(p);
        }
    }
    out
}

fn candidate_roots() -> Vec<PathBuf> {
    let mut roots = Vec::new();

    if let Some(project_root) = project_root_from_manifest() {
        roots.push(project_root.clone());
        roots.push(project_root.join("src-tauri").join("resources"));
    }

    if let Ok(exe_path) = std::env::current_exe() {
        if let Some(exe_dir) = exe_path.parent() {
            roots.push(exe_dir.to_path_buf());
            roots.push(exe_dir.join("resources"));

            #[cfg(target_os = "macos")]
            {
                if let Some(contents) = exe_dir.parent().and_then(|p| p.parent()) {
                    roots.push(contents.join("Resources"));
                }
            }
        }
    }

    if let Ok(cwd) = std::env::current_dir() {
        roots.push(cwd.clone());
        roots.push(cwd.join("resources"));
        if let Some(parent) = cwd.parent() {
            roots.push(parent.to_path_buf());
            roots.push(parent.join("resources"));
        }
    }

    dedupe_paths(roots)
}

fn bundled_skills_root() -> Option<PathBuf> {
    for root in candidate_roots() {
        let p = root.join("skills");
        if p.exists() {
            return Some(p);
        }
    }
    None
}

fn copy_dir_all(src: &Path, dst: &Path) -> std::io::Result<()> {
    if !dst.exists() {
        fs::create_dir_all(dst)?;
    }
    for entry in fs::read_dir(src)? {
        let entry = entry?;
        let ty = entry.file_type()?;
        let from = entry.path();
        let to = dst.join(entry.file_name());
        if ty.is_dir() {
            copy_dir_all(&from, &to)?;
        } else {
            if let Some(parent) = to.parent() {
                fs::create_dir_all(parent)?;
            }
            fs::copy(from, to)?;
        }
    }
    Ok(())
}

fn app_data_root() -> PathBuf {
    let base = dirs::data_local_dir()
        .or_else(dirs::data_dir)
        .or_else(|| std::env::current_dir().ok())
        .unwrap_or_else(|| PathBuf::from("."));
    base.join("auto-prompt-app")
}

pub fn ensure_user_skills_root() -> Result<PathBuf, String> {
    let user_skills = app_data_root().join("skills");
    if user_skills.exists() {
        return Ok(user_skills);
    }

    if let Some(src) = bundled_skills_root() {
        copy_dir_all(&src, &user_skills)
            .map_err(|e| format!("Failed to copy bundled skills to user directory: {}", e))?;
        return Ok(user_skills);
    }

    fs::create_dir_all(&user_skills)
        .map_err(|e| format!("Failed to create user skills directory: {}", e))?;
    Ok(user_skills)
}

pub fn resolve_skill_path(skill_relative_path: &str) -> Result<PathBuf, String> {
    let user_root = ensure_user_skills_root()?;
    let user_path = user_root.join(skill_relative_path);
    if user_path.exists() {
        return Ok(user_path);
    }

    if let Some(src_root) = bundled_skills_root() {
        let src_path = src_root.join(skill_relative_path);
        if src_path.exists() {
            if let Some(parent) = user_path.parent() {
                fs::create_dir_all(parent)
                    .map_err(|e| format!("Failed to create skill directory: {}", e))?;
            }
            fs::copy(&src_path, &user_path)
                .map_err(|e| format!("Failed to copy skill file: {}", e))?;
            return Ok(user_path);
        }
    }

    Err(format!("Skill file not found: {}", skill_relative_path))
}

pub fn case_library_path() -> Result<PathBuf, String> {
    let root = ensure_user_skills_root()?;
    let path = root.join("doc-extract-prompt-gen").join("case_library.json");
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent)
            .map_err(|e| format!("Failed to create case library directory: {}", e))?;
    }
    Ok(path)
}

fn bundled_python_runtime_root() -> Option<PathBuf> {
    candidate_roots()
        .into_iter()
        .map(|root| root.join("python-runtime"))
        .find(|path| path.exists())
}

fn user_python_runtime_root() -> PathBuf {
    app_data_root().join("python-runtime")
}

fn runtime_manifest_path(root: &Path) -> PathBuf {
    root.join("runtime-manifest.json")
}

fn runtime_manifest_contents(root: &Path) -> Option<String> {
    fs::read_to_string(runtime_manifest_path(root)).ok()
}

fn python_executable_from_runtime_root(root: &Path) -> Option<PathBuf> {
    #[cfg(target_os = "windows")]
    {
        let candidates = vec![
            root.join("python.exe"),
            root.join("Scripts").join("python.exe"),
        ];
        return candidates.into_iter().find(|p| p.exists());
    }

    #[cfg(not(target_os = "windows"))]
    {
        let candidates = vec![
            root.join("bin").join("python3"),
            root.join("bin").join("python"),
        ];
        return candidates.into_iter().find(|p| p.exists());
    }
}

fn runtime_has_expected_layout(root: &Path) -> bool {
    if python_executable_from_runtime_root(root).is_none() {
        return false;
    }

    let pip_dir = root.join("Lib").join("site-packages").join("pip");
    let ensurepip_dir = root.join("Lib").join("ensurepip");
    pip_dir.exists() && ensurepip_dir.exists()
}

fn should_refresh_user_runtime(user_runtime: &Path, bundled_runtime: &Path) -> bool {
    if !user_runtime.exists() {
        return true;
    }

    if !runtime_has_expected_layout(user_runtime) {
        return true;
    }

    match (
        runtime_manifest_contents(user_runtime),
        runtime_manifest_contents(bundled_runtime),
    ) {
        (Some(user_manifest), Some(bundled_manifest)) => user_manifest != bundled_manifest,
        (None, Some(_)) => true,
        _ => false,
    }
}

fn replace_runtime(src: &Path, dst: &Path) -> Result<(), String> {
    if dst.exists() {
        fs::remove_dir_all(dst)
            .map_err(|e| format!("Failed to remove stale Python runtime: {}", e))?;
    }

    copy_dir_all(src, dst).map_err(|e| format!("Failed to copy bundled Python runtime: {}", e))
}

pub fn ensure_user_python_runtime() -> Result<PathBuf, String> {
    let user_runtime = user_python_runtime_root();

    if let Some(src) = bundled_python_runtime_root() {
        if should_refresh_user_runtime(&user_runtime, &src) {
            replace_runtime(&src, &user_runtime)?;
        }
        return Ok(user_runtime);
    }

    if runtime_has_expected_layout(&user_runtime) {
        return Ok(user_runtime);
    }

    Err("Bundled Python runtime not found".to_string())
}

fn python_command_works(path: &Path) -> bool {
    Command::new(path)
        .arg("--version")
        .output()
        .map(|o| o.status.success())
        .unwrap_or(false)
}

pub fn bundled_python_path() -> Option<PathBuf> {
    if let Ok(user_runtime) = ensure_user_python_runtime() {
        if let Some(path) = python_executable_from_runtime_root(&user_runtime) {
            if python_command_works(&path) {
                return Some(path);
            }
        }
    }

    if let Some(root) = bundled_python_runtime_root() {
        if let Some(path) = python_executable_from_runtime_root(&root) {
            if python_command_works(&path) {
                return Some(path);
            }
        }
    }

    None
}
