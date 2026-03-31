#!/usr/bin/env python3
"""查找并移除所有 Tauri 引用"""
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('180.76.244.18', username='root', password='Lxhao1230.0', timeout=30)

print('查找所有 Tauri 引用...')
stdin, stdout, stderr = ssh.exec_command('''
cd /opt/auto-prompt

echo "1. 查找所有引用 @tauri-apps 的文件..."
grep -r "@tauri-apps" src/ || echo "没有找到 @tauri-apps 引用"

echo ""
echo "2. 查找所有引用 tauri 的文件..."
grep -r "tauri" src/ || echo "没有找到 tauri 引用"

echo ""
echo "3. 检查具体的引用文件..."
find src/ -name "*.vue" -exec grep -l "tauri" {} \;
find src/ -name "*.js" -exec grep -l "tauri" {} \;
''', timeout=60)

output = stdout.read().decode()
print(output)

print('\n移除 GenerateView.vue 中的 Tauri 引用...')
stdin, stdout, stderr = ssh.exec_command('''
cd /opt/auto-prompt

# 检查 GenerateView.vue 的 Tauri 引用
echo "检查 GenerateView.vue:"
grep -n "tauri" src/views/GenerateView.vue

echo ""
echo "移除 Tauri 引用..."
# 备份原文件
cp src/views/GenerateView.vue src/views/GenerateView.vue.bak

# 移除 Tauri 相关的导入和使用
sed -i '/import.*tauri/d' src/views/GenerateView.vue
sed -i '/tauri\./d' src/views/GenerateView.vue

echo "移除后的文件:"
grep -n "tauri" src/views/GenerateView.vue || echo "已移除所有 tauri 引用"
''', timeout=60)

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
