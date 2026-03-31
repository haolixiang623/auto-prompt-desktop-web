#!/usr/bin/env python3
"""从本地正确修复后的文件上传到服务器"""
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('180.76.244.18', username='root', password='Lxhao1230.0', timeout=30)

print('=== 从本地修复后的文件上传到服务器 ===')
sftp = ssh.open_sftp()

# 上传所有已修复的 Vue 文件
vue_files = [
    'src/views/GenerateView.vue',
    'src/views/ClassifyView.vue',
    'src/views/CaseLibraryView.vue',
    'src/views/ReviewRuleView.vue',
    'src/views/ReviewRuleLibraryView.vue',
    'src/views/FactorJsonView.vue',
    'src/views/EnvCheckView.vue',
    'src/views/SettingsView.vue',
    'src/views/LlmLogView.vue'
]

print('上传修复后的 Vue 文件...')
for file_path in vue_files:
    try:
        sftp.put(file_path, f'/opt/auto-prompt/{file_path}')
        print(f'✓ {file_path}')
    except Exception as e:
        print(f'✗ {file_path}: {e}')

# 上传服务文件
service_files = [
    'src/services/authService.js',
    'src/services/apiClient.js',
    'src/services/uploadService.js',
    'src/services/taskService.js',
    'src/stores/skills.js'
]

print('\n上传修复后的服务文件...')
for file_path in service_files:
    try:
        sftp.put(file_path, f'/opt/auto-prompt/{file_path}')
        print(f'✓ {file_path}')
    except Exception as e:
        print(f'✗ {file_path}: {e}')

sftp.close()

print('\n=== 在服务器上重新构建 ===')
stdin, stdout, stderr = ssh.exec_command('cd /opt/auto-prompt && npm run build 2>&1 | tail -20', timeout=120)

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
print('上传和构建完成！')
print('='*60)
