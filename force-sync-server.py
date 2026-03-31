#!/usr/bin/env python3
"""彻底检查并修复服务器 invoke 问题"""
import paramiko
import os

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('180.76.244.18', username='root', password='Lxhao1230.0', timeout=30)

print('=== 彻底检查服务器代码 ===')
stdin, stdout, stderr = ssh.exec_command('''
cd /opt/auto-prompt

echo "1. 检查源码中的 invoke..."
grep -r "invoke(" src/ 2>/dev/null | grep -v "//" | grep -v "console.log" || echo "源码中没有 invoke 调用"

echo ""
echo "2. 检查构建文件中的 invoke..."
grep -r "invoke" dist/ 2>/dev/null | head -5 || echo "构建文件中没有 invoke"

echo ""
echo "3. 检查是否有缓存文件..."
ls -la dist/ | head -10

echo ""
echo "4. 检查服务状态..."
systemctl status auto-prompt --no-pager | grep Active
''', timeout=60)

output = stdout.read().decode()
print(output)

print('\n=== 强制重新同步所有前端文件 ===')
# 重新上传所有前端文件
sftp = ssh.open_sftp()

# 上传配置文件
files_to_upload = [
    'package.json',
    'vite.config.js',
    'src/main.js',
    'src/services/authService.js',
    'src/services/apiClient.js',
    'src/services/uploadService.js',
    'src/services/taskService.js',
    'src/stores/skills.js',
    'src/router/index.js'
]

for file_path in files_to_upload:
    try:
        sftp.put(file_path, f'/opt/auto-prompt/{file_path}')
        print(f'✓ {file_path}')
    except Exception as e:
        print(f'✗ {file_path}: {e}')

# 上传 Vue 文件
vue_files = [
    'src/App.vue',
    'src/views/Dashboard.vue',
    'src/views/LoginView.vue',
    'src/views/GenerateView.vue',
    'src/views/ClassifyView.vue',
    'src/views/CaseLibraryView.vue',
    'src/views/ReviewRuleView.vue',
    'src/views/ReviewRuleLibraryView.vue',
    'src/views/FactorJsonView.vue',
    'src/views/EnvCheckView.vue',
    'src/views/SettingsView.vue',
    'src/views/UsersView.vue',
    'src/views/LlmLogView.vue'
]

for file_path in vue_files:
    try:
        sftp.put(file_path, f'/opt/auto-prompt/{file_path}')
        print(f'✓ {file_path}')
    except Exception as e:
        print(f'✗ {file_path}: {e}')

sftp.close()

print('\n重新构建前端...')
stdin, stdout, stderr = ssh.exec_command('''
cd /opt/auto-prompt
rm -rf dist/
npm run build
''', timeout=120)

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
