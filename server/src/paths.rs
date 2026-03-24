use std::path::PathBuf;

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AppPaths {
    pub data_dir: PathBuf,
    pub workspace_root: PathBuf,
    pub upload_root: PathBuf,
    pub task_root: PathBuf,
    pub auth_db_path: PathBuf,
    pub settings_path: PathBuf,
    pub case_library_path: PathBuf,
    pub review_rule_library_path: PathBuf,
}

impl AppPaths {
    pub fn new(data_dir: PathBuf) -> Self {
        Self {
            workspace_root: data_dir.join("workspaces"),
            upload_root: data_dir.join("uploads"),
            task_root: data_dir.join("tasks"),
            auth_db_path: data_dir.join("auth.db"),
            settings_path: data_dir.join("settings.json"),
            case_library_path: data_dir.join("case_library.json"),
            review_rule_library_path: data_dir.join("review_rule_library.json"),
            data_dir,
        }
    }

    pub fn from_env() -> Self {
        let base = std::env::var("AUTO_PROMPT_DATA_DIR")
            .map(PathBuf::from)
            .unwrap_or_else(|_| default_data_dir());
        Self::new(base)
    }

    pub fn user_workspace_root(&self, user_id: &str) -> PathBuf {
        self.workspace_root.join(user_id)
    }

    pub fn user_upload_root(&self, user_id: &str) -> PathBuf {
        self.upload_root.join(user_id)
    }

    pub fn user_task_root(&self, user_id: &str) -> PathBuf {
        self.task_root.join(user_id)
    }
}

fn default_data_dir() -> PathBuf {
    dirs::data_local_dir()
        .or_else(dirs::data_dir)
        .unwrap_or_else(std::env::temp_dir)
        .join("auto-prompt-web")
}

#[cfg(test)]
mod tests {
    use std::path::PathBuf;

    use super::AppPaths;

    #[test]
    fn creates_named_subdirectories_under_data_root() {
        let base = PathBuf::from("/tmp/auto-prompt-web-tests");
        let paths = AppPaths::new(base.clone());

        assert_eq!(paths.data_dir, base);
        assert_eq!(paths.workspace_root, base.join("workspaces"));
        assert_eq!(paths.upload_root, base.join("uploads"));
        assert_eq!(paths.task_root, base.join("tasks"));
        assert_eq!(paths.auth_db_path, base.join("auth.db"));
        assert_eq!(paths.settings_path, base.join("settings.json"));
        assert_eq!(paths.case_library_path, base.join("case_library.json"));
    }
}
