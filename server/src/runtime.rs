use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;

#[derive(Debug, Clone)]
pub struct RuntimeContext {
    pub repo_root: PathBuf,
    pub skills_root: PathBuf,
    pub frontend_dist_dir: PathBuf,
}

impl RuntimeContext {
    pub fn discover() -> Self {
        let repo_root = std::env::var("AUTO_PROMPT_REPO_ROOT")
            .map(PathBuf::from)
            .unwrap_or_else(|_| PathBuf::from(env!("CARGO_MANIFEST_DIR")).join(".."));

        let skills_root = std::env::var("AUTO_PROMPT_SKILLS_DIR")
            .map(PathBuf::from)
            .unwrap_or_else(|_| repo_root.join("skills"));

        let frontend_dist_dir = std::env::var("AUTO_PROMPT_WEB_DIST")
            .map(PathBuf::from)
            .unwrap_or_else(|_| repo_root.join("dist"));

        Self {
            repo_root,
            skills_root,
            frontend_dist_dir,
        }
    }

    pub fn resolve_skill_path(&self, relative_path: &str) -> Result<PathBuf, String> {
        let path = self.skills_root.join(relative_path);
        if path.exists() {
            Ok(path)
        } else {
            Err(format!("Skill file not found: {relative_path}"))
        }
    }

    pub fn python_command(&self) -> String {
        if let Ok(explicit) = std::env::var("AUTOPROMPT_PYTHON") {
            if !explicit.trim().is_empty() && command_works(Path::new(&explicit)) {
                return explicit;
            }
        }

        for candidate in bundled_python_candidates(&self.repo_root) {
            if command_works(&candidate) {
                return candidate.to_string_lossy().to_string();
            }
        }

        let commands = if cfg!(target_os = "windows") {
            vec!["python", "python3", "py"]
        } else {
            vec!["python3", "python"]
        };

        for command in commands {
            if Command::new(command)
                .arg("--version")
                .output()
                .map(|output| output.status.success())
                .unwrap_or(false)
            {
                return command.to_string();
            }
        }

        "python3".to_string()
    }

    pub fn python_process(&self) -> Command {
        let mut command = Command::new(self.python_command());
        configure_python_stdio(&mut command);
        command
    }
}

fn bundled_python_candidates(repo_root: &Path) -> Vec<PathBuf> {
    let mut candidates = Vec::new();

    let runtime_root = std::env::var("AUTO_PROMPT_PYTHON_RUNTIME")
        .map(PathBuf::from)
        .unwrap_or_else(|_| repo_root.join("src-tauri").join("resources").join("python-runtime"));

    if runtime_root.exists() {
        if cfg!(target_os = "windows") {
            candidates.push(runtime_root.join("python.exe"));
            candidates.push(runtime_root.join("Scripts").join("python.exe"));
        } else {
            candidates.push(runtime_root.join("bin").join("python3"));
            candidates.push(runtime_root.join("bin").join("python"));
        }
    }

    candidates
}

fn command_works(path: &Path) -> bool {
    if !path.exists() && path.components().count() > 1 {
        return false;
    }

    Command::new(path)
        .arg("--version")
        .output()
        .map(|output| output.status.success())
        .unwrap_or(false)
}

fn configure_python_stdio(command: &mut Command) {
    command
        .env("PYTHONIOENCODING", "utf-8")
        .env("PYTHONUTF8", "1");
}

pub fn ensure_parent_dir(path: &Path) -> Result<(), String> {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent).map_err(|error| error.to_string())?;
    }
    Ok(())
}
