use std::collections::HashMap;
use std::fs;
use std::path::PathBuf;
use std::sync::{Arc, RwLock};

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use serde_json::Value;
use uuid::Uuid;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum TaskKind {
    Generate,
    Classify,
    ReviewRule,
    FactorJson,
    VerifyExtraction,
    TestClassifyPrompt,
    RegenerateKeypoint,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum TaskStatus {
    Pending,
    Running,
    Succeeded,
    Failed,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "camelCase")]
pub struct Task {
    pub id: String,
    pub kind: TaskKind,
    pub status: TaskStatus,
    pub progress: Option<u8>,
    pub owner_user_id: String,
    pub workspace_id: Option<String>,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
    pub result: Option<Value>,
    pub error: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct TaskRecord {
    task: Task,
    logs: Vec<String>,
}

#[derive(Debug, Clone)]
pub struct TaskStore {
    inner: Arc<RwLock<HashMap<String, TaskRecord>>>,
    task_root: PathBuf,
}

impl TaskStore {
    pub fn new(task_root: PathBuf) -> Self {
        fs::create_dir_all(&task_root).expect("failed to create task store directory");

        let mut records = HashMap::new();
        restore_records(&task_root, &mut records);

        Self {
            inner: Arc::new(RwLock::new(records)),
            task_root,
        }
    }

    pub fn create(&self, kind: TaskKind, owner_user_id: String, workspace_id: Option<String>) -> Task {
        let now = Utc::now();
        let task = Task {
            id: Uuid::new_v4().to_string(),
            kind,
            status: TaskStatus::Pending,
            progress: Some(0),
            owner_user_id,
            workspace_id,
            created_at: now,
            updated_at: now,
            result: None,
            error: None,
        };

        let record = TaskRecord {
            task: task.clone(),
            logs: Vec::new(),
        };

        let mut guard = self.inner.write().expect("task store poisoned");
        guard.insert(
            task.id.clone(),
            record.clone(),
        );
        drop(guard);
        self.persist(&record).expect("failed to persist task");

        task
    }

    pub fn get(&self, task_id: &str, owner_user_id: &str) -> Option<Task> {
        let guard = self.inner.read().ok()?;
        guard
            .get(task_id)
            .filter(|record| record.task.owner_user_id == owner_user_id)
            .map(|record| record.task.clone())
    }

    pub fn logs(&self, task_id: &str, owner_user_id: &str) -> Option<Vec<String>> {
        let guard = self.inner.read().ok()?;
        guard
            .get(task_id)
            .filter(|record| record.task.owner_user_id == owner_user_id)
            .map(|record| record.logs.clone())
    }

    pub fn mark_running(&self, task_id: &str, progress: Option<u8>) -> Result<(), String> {
        self.update(task_id, |task| {
            task.status = TaskStatus::Running;
            task.progress = progress.or(task.progress);
        })
    }

    pub fn set_progress(&self, task_id: &str, progress: u8) -> Result<(), String> {
        self.update(task_id, |task| {
            task.progress = Some(progress);
        })
    }

    pub fn append_log(&self, task_id: &str, line: String) -> Result<(), String> {
        let mut guard = self.inner.write().map_err(|_| "task store poisoned".to_string())?;
        let record = guard
            .get_mut(task_id)
            .ok_or_else(|| format!("task not found: {task_id}"))?;
        record.logs.push(line);
        record.task.updated_at = Utc::now();
        let snapshot = record.clone();
        drop(guard);
        self.persist(&snapshot)?;
        Ok(())
    }

    pub fn complete(&self, task_id: &str, result: Value) -> Result<(), String> {
        self.update(task_id, |task| {
            task.status = TaskStatus::Succeeded;
            task.progress = Some(100);
            task.result = Some(result.clone());
            task.error = None;
        })
    }

    pub fn fail(&self, task_id: &str, error: String) -> Result<(), String> {
        self.update(task_id, |task| {
            task.status = TaskStatus::Failed;
            task.error = Some(error.clone());
        })
    }

    fn update<F>(&self, task_id: &str, mut update_task: F) -> Result<(), String>
    where
        F: FnMut(&mut Task),
    {
        let mut guard = self.inner.write().map_err(|_| "task store poisoned".to_string())?;
        let record = guard
            .get_mut(task_id)
            .ok_or_else(|| format!("task not found: {task_id}"))?;
        update_task(&mut record.task);
        record.task.updated_at = Utc::now();
        let snapshot = record.clone();
        drop(guard);
        self.persist(&snapshot)?;
        Ok(())
    }

    fn persist(&self, record: &TaskRecord) -> Result<(), String> {
        let task_path = self.task_path(&record.task.id);
        let content = serde_json::to_vec_pretty(record).map_err(|error| error.to_string())?;
        if let Some(parent) = task_path.parent() {
            fs::create_dir_all(parent).map_err(|error| error.to_string())?;
        }
        fs::write(task_path, content).map_err(|error| error.to_string())
    }

    fn task_path(&self, task_id: &str) -> PathBuf {
        let owner_user_id = self
            .inner
            .read()
            .ok()
            .and_then(|guard| guard.get(task_id).map(|record| record.task.owner_user_id.clone()))
            .unwrap_or_else(|| "unknown".to_string());
        self.task_root.join(owner_user_id).join(format!("{task_id}.json"))
    }
}

fn restore_records(task_root: &PathBuf, records: &mut HashMap<String, TaskRecord>) {
    if let Ok(entries) = fs::read_dir(task_root) {
        for entry in entries.flatten() {
            let path = entry.path();
            if path.is_dir() {
                restore_records(&path, records);
                continue;
            }
            if path.extension().and_then(|extension| extension.to_str()) != Some("json") {
                continue;
            }

            match fs::read_to_string(&path)
                .ok()
                .and_then(|content| serde_json::from_str::<TaskRecord>(&content).ok())
            {
                Some(record) => {
                    records.insert(record.task.id.clone(), record);
                }
                None => {
                    eprintln!("failed to restore task from {}", path.display());
                }
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use std::env;
    use std::fs;
    use std::path::PathBuf;

    use uuid::Uuid;

    use super::{TaskKind, TaskStatus, TaskStore};

    fn temp_task_root(test_name: &str) -> PathBuf {
        let path = env::temp_dir().join(format!("auto-prompt-task-tests-{test_name}-{}", Uuid::new_v4()));
        fs::create_dir_all(&path).unwrap();
        path
    }

    #[test]
    fn task_store_tracks_lifecycle_and_logs() {
        let task_root = temp_task_root("lifecycle");
        let store = TaskStore::new(task_root.clone());
        let task = store.create(TaskKind::Generate, "user-1".to_string(), Some("ws-1".to_string()));

        assert_eq!(task.kind, TaskKind::Generate);
        assert_eq!(task.status, TaskStatus::Pending);
        assert_eq!(task.owner_user_id, "user-1");
        assert_eq!(task.workspace_id.as_deref(), Some("ws-1"));

        store.mark_running(&task.id, Some(10)).unwrap();
        store.append_log(&task.id, "started".to_string()).unwrap();
        store.complete(&task.id, serde_json::json!({"ok": true})).unwrap();

        let stored = store.get(&task.id, "user-1").unwrap();
        assert_eq!(stored.status, TaskStatus::Succeeded);
        assert_eq!(stored.progress, Some(100));
        assert_eq!(stored.result, Some(serde_json::json!({"ok": true})));
        assert_eq!(store.logs(&task.id, "user-1").unwrap(), vec!["started".to_string()]);

        fs::remove_dir_all(task_root).unwrap();
    }

    #[test]
    fn task_store_restores_persisted_records() {
        let task_root = temp_task_root("restore");
        let first_store = TaskStore::new(task_root.clone());
        let task = first_store.create(TaskKind::Classify, "user-2".to_string(), Some("ws-2".to_string()));
        first_store.mark_running(&task.id, Some(30)).unwrap();
        first_store.append_log(&task.id, "running".to_string()).unwrap();
        first_store.fail(&task.id, "boom".to_string()).unwrap();

        let restored_store = TaskStore::new(task_root.clone());
        let restored = restored_store.get(&task.id, "user-2").unwrap();

        assert_eq!(restored.kind, TaskKind::Classify);
        assert_eq!(restored.status, TaskStatus::Failed);
        assert_eq!(restored.owner_user_id, "user-2");
        assert_eq!(restored.workspace_id.as_deref(), Some("ws-2"));
        assert_eq!(restored_store.logs(&task.id, "user-2").unwrap(), vec!["running".to_string()]);

        fs::remove_dir_all(task_root).unwrap();
    }
}
