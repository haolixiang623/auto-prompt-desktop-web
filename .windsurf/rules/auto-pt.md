---
trigger: manual
---
仅针对桌面端进行功能修改优化，浏览器端暂不考虑

## 文件/目录选择器实现规范

**禁止使用前端对话框 API**：
- 禁止使用 `@tauri-apps/api/dialog` 的 `open()` 方法（会导致 macOS UI 卡死）
- 所有文件/目录选择功能必须通过 Rust 后端命令实现

**Rust 后端实现**（`src-tauri/src/commands/fs.rs`）：
- **使用 `rfd` crate + `tokio::task::spawn_blocking`**，在独立阻塞线程中调用 `rfd::FileDialog`
- **禁止使用** `tauri::api::dialog::FileDialogBuilder` + `app.run_on_main_thread()`：该方案在 macOS 上不稳定，`run_on_main_thread` 回调可能永远不执行导致 `rx.await` 永久挂起
- **禁止使用** `app: tauri::AppHandle` 参数（rfd 方案不需要）
- 提供三个命令（无需 AppHandle 参数）：
  - `select_directory()` - 目录选择器
  - `select_file(filters: Option<Vec<DialogFilter>>)` - 单文件选择器
  - `select_files(filters: Option<Vec<DialogFilter>>)` - 多文件选择器
- 所有命令必须注册到 `src-tauri/src/main.rs` 的 `invoke_handler`
- `Cargo.toml` 需添加依赖：`rfd = "0.14"`

**正确实现示例**：
```rust
#[tauri::command]
pub async fn select_directory() -> Result<Option<String>, String> {
    let result = tokio::task::spawn_blocking(|| {
        rfd::FileDialog::new().pick_folder()
    })
    .await
    .map_err(|e| e.to_string())?;
    Ok(result.map(|p| p.to_string_lossy().to_string()))
}
```

**前端调用方式**：
```javascript
// 目录选择
const dir = await invoke('select_directory')

// 单文件选择（带过滤器）
const file = await invoke('select_file', {
  filters: [{ name: 'JSON', extensions: ['json'] }]
})

// 多文件选择（带过滤器）
const files = await invoke('select_files', {
  filters: [{ name: '文本文件', extensions: ['txt'] }]
})
```

**注意事项**：
- 移除所有 `import { open } from '@tauri-apps/api/dialog'` 导入
- `composables/useFileSystem.js` 和 `composables/useSkills.js` 中的选择器函数也必须调用 Rust 命令
- 所有返回值为 `Option<String>` 或 `Option<Vec<String>>`，需判空处理

