#!/usr/bin/env python3
"""批量移除所有 Tauri 引用"""
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('180.76.244.18', username='root', password='Lxhao1230.0', timeout=30)

print('批量移除所有 Tauri 引用...')
stdin, stdout, stderr = ssh.exec_command('''
cd /opt/auto-prompt

echo "1. 移除所有 Vue 文件中的 Tauri 导入..."
for file in src/views/*.vue; do
  if grep -q "@tauri-apps" "$file"; then
    echo "处理 $file"
    cp "$file" "$file.bak"
    sed -i '/import.*@tauri-apps/d' "$file"
    sed -i '/import.*tauri/d' "$file"
  fi
done

echo ""
echo "2. 移除所有 JS 文件中的 Tauri 导入..."
for file in src/stores/*.js src/composables/*.js src/services/*.js; do
  if grep -q "@tauri-apps" "$file"; then
    echo "处理 $file"
    cp "$file" "$file.bak"
    sed -i '/import.*@tauri-apps/d' "$file"
    sed -i '/import.*tauri/d' "$file"
  fi
done

echo ""
echo "3. 检查还有哪些文件有 Tauri 引用..."
grep -r "@tauri-apps" src/ || echo "所有 @tauri-apps 引用已移除"

echo ""
echo "4. 检查还有哪些文件有 tauri 引用..."
grep -r "tauri://" src/ || echo "所有 tauri:// 引用已移除"
''', timeout=120)

output = stdout.read().decode()
print(output)

print('\n重新构建...')
stdin, stdout, stderr = ssh.exec_command('''
cd /opt/auto-prompt
npm run build
''', timeout=120)

output = stdout.read().decode()
error = stderr.read().decode()
print(output)
if error:
    print(f'错误: {error}')

ssh.close()
