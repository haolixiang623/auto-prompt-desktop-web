use serde::{Deserialize, Serialize};
use std::sync::Mutex;
use once_cell::sync::Lazy;

const MAX_LOG_ENTRIES: usize = 2000;

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct LlmLogEntry {
    pub id: u64,
    pub time: String,
    pub model: String,
    pub scene: String,           // 场景：generate / verify / classify
    pub prompt_summary: String,  // 提示词摘要（前2000字）
    pub response_summary: String,// 响应摘要（前2000字）
    pub elapsed_s: Option<f64>,
    pub success: bool,
    pub error: Option<String>,
}

static LOG_STORE: Lazy<Mutex<Vec<LlmLogEntry>>> = Lazy::new(|| Mutex::new(Vec::new()));
static LOG_ID_COUNTER: Lazy<Mutex<u64>> = Lazy::new(|| Mutex::new(0));

pub fn append_log(entry: LlmLogEntry) {
    let mut store = LOG_STORE.lock().unwrap();
    let cur_len = store.len();
    if cur_len >= MAX_LOG_ENTRIES {
        store.drain(0..cur_len - MAX_LOG_ENTRIES + 1);
    }
    store.push(entry);
}

pub fn next_id() -> u64 {
    let mut counter = LOG_ID_COUNTER.lock().unwrap();
    *counter += 1;
    *counter
}

#[derive(Debug, Serialize, Deserialize)]
pub struct LlmLogPage {
    pub total: usize,
    pub page: usize,
    pub page_size: usize,
    pub entries: Vec<LlmLogEntry>,
}

#[tauri::command]
pub fn get_llm_logs(page: Option<usize>, page_size: Option<usize>) -> LlmLogPage {
    let store = LOG_STORE.lock().unwrap();
    let total = store.len();
    let page = page.unwrap_or(1).max(1);
    let page_size = page_size.unwrap_or(20).clamp(1, 100);
    let start = ((page - 1) * page_size).min(total);
    let end = (start + page_size).min(total);
    // Return newest first
    let all_rev: Vec<LlmLogEntry> = store.iter().cloned().rev().collect();
    drop(store);
    let entries = all_rev[start..end].to_vec();
    LlmLogPage { total, page, page_size, entries }
}

#[tauri::command]
pub fn clear_llm_logs() {
    let mut store = LOG_STORE.lock().unwrap();
    store.clear();
}
