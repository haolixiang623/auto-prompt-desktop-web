#!/bin/bash
# 批量移除所有 Vue 文件中的 Tauri 引用
cd /opt/auto-prompt

echo "=== 批量修复所有 Vue 文件 ==="

# 移除所有 Tauri 导入
for file in src/views/*.vue; do
  echo "处理 $file..."
  sed -i '/import { invoke } from/d' "$file"
  sed -i '/import { listen } from/d' "$file"
  sed -i '/import.*@tauri-apps/d' "$file"
done

# 替换常见的 invoke 调用为注释（临时方案）
for file in src/views/*.vue; do
  # 替换简单的 invoke 调用
  sed -i 's/await invoke(/\/\/ TODO: Replace invoke call /g' "$file"
done

echo "=== 重新构建 ==="
npm run build

echo "=== 重启服务 ==="
systemctl restart auto-prompt

echo "=== 完成 ==="
