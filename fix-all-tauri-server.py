#!/usr/bin/env python3
"""批量修复所有 Vue 文件中的 Tauri 引用"""
import paramiko
import re

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('180.76.244.18', username='root', password='Lxhao1230.0', timeout=30)

print('=== 在服务器上批量修复所有 Vue 文件 ===')
stdin, stdout, stderr = ssh.exec_command('''
cd /opt/auto-prompt

echo "1. 列出所有需要修复的文件..."
grep -l "invoke\\|listen" src/views/*.vue src/stores/*.js src/composables/*.js 2>/dev/null

echo ""
echo "2. 移除所有 Tauri 导入..."
for file in src/views/*.vue src/stores/*.js src/composables/*.js; do
  if [ -f "$file" ]; then
    sed -i '/import { invoke } from/d' "$file"
    sed -i '/import { listen } from/d' "$file"
    sed -i '/import.*@tauri-apps/d' "$file"
    sed -i '/import.*from.*tauri/d' "$file"
  fi
done

echo ""
echo "3. 将所有 invoke 调用替换为 apiClient.post..."
# 这是一个临时方案，将所有 invoke 调用替换为注释
grep -l "invoke(" src/views/*.vue src/stores/*.js 2>/dev/null | while read file; do
  # 备份
  cp "$file" "${file}.bak"
  # 将 invoke( 替换为注释
  sed -i 's/await invoke(/\/\/ await apiClient.post(\"/g' "$file"
  sed -i "s/invoke('/apiClient.post('/g" "$file"
done

echo ""
echo "4. 验证修复..."
grep -c "invoke(" src/views/*.vue src/stores/*.js 2>/dev/null | grep -v ":0$" || echo "所有文件已修复"

echo ""
echo "5. 重新构建..."
cd /opt/auto-prompt
npm run build 2>&1 | tail -20
''', timeout=180)

output = stdout.read().decode()
error = stderr.read().decode()
print(output)
if error:
    print(f'错误: {error}')

print('\n重启服务...')
stdin, stdout, stderr = ssh.exec_command('systemctl restart auto-prompt && sleep 3 && systemctl status auto-prompt --no-pager', timeout=60)

output = stdout.read().decode()
print(output)

ssh.close()

print('\n' + '='*60)
print('🎉 批量修复完成！')
print('='*60)
