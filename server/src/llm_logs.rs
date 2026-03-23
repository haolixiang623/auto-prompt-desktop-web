use std::sync::{Arc, Mutex};

use chrono::Local;
use serde::{Deserialize, Serialize};

const MAX_LOG_ENTRIES: usize = 2_000;

#[derive(Debug, Serialize, Deserialize, Clone, PartialEq)]
#[serde(rename_all = "camelCase")]
pub struct LlmLogEntry {
    pub id: u64,
    pub time: String,
    pub model: String,
    pub scene: String,
    pub prompt_summary: String,
    pub response_summary: String,
    pub elapsed_s: Option<f64>,
    pub success: bool,
    pub error: Option<String>,
}

#[derive(Debug, Serialize, Deserialize, Clone, PartialEq)]
#[serde(rename_all = "camelCase")]
pub struct LlmLogPage {
    pub total: usize,
    pub page: usize,
    pub page_size: usize,
    pub entries: Vec<LlmLogEntry>,
}

#[derive(Debug, Clone, Default)]
pub struct LlmLogStore {
    entries: Arc<Mutex<Vec<LlmLogEntry>>>,
    next_id: Arc<Mutex<u64>>,
}

impl LlmLogStore {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn append(&self, mut entry: LlmLogEntry) {
        let mut id_guard = self.next_id.lock().expect("llm log id poisoned");
        *id_guard += 1;
        entry.id = *id_guard;
        drop(id_guard);

        let mut guard = self.entries.lock().expect("llm log store poisoned");
        if guard.len() >= MAX_LOG_ENTRIES {
            let drain_count = guard.len() - MAX_LOG_ENTRIES + 1;
            guard.drain(0..drain_count);
        }
        guard.push(entry);
    }

    pub fn page(&self, page: usize, page_size: usize) -> LlmLogPage {
        let guard = self.entries.lock().expect("llm log store poisoned");
        let total = guard.len();
        let page = page.max(1);
        let page_size = page_size.clamp(1, 100);
        let start = ((page - 1) * page_size).min(total);
        let end = (start + page_size).min(total);

        let reversed: Vec<LlmLogEntry> = guard.iter().cloned().rev().collect();
        LlmLogPage {
            total,
            page,
            page_size,
            entries: reversed[start..end].to_vec(),
        }
    }

    pub fn clear(&self) {
        let mut guard = self.entries.lock().expect("llm log store poisoned");
        guard.clear();
    }
}

impl LlmLogEntry {
    pub fn now(
        model: String,
        scene: String,
        prompt_summary: String,
        response_summary: String,
        elapsed_s: Option<f64>,
        success: bool,
        error: Option<String>,
    ) -> Self {
        Self {
            id: 0,
            time: Local::now().format("%Y-%m-%d %H:%M:%S").to_string(),
            model,
            scene,
            prompt_summary,
            response_summary,
            elapsed_s,
            success,
            error,
        }
    }
}
