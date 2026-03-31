#!/usr/bin/env python3
"""修复 Tauri IPC 错误"""
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('180.76.244.18', username='root', password='Lxhao1230.0', timeout=30)

print('检查 Tauri 相关代码...')
stdin, stdout, stderr = ssh.exec_command('''
# 查找使用 Tauri IPC 的代码
grep -r "__TAURI_IPC__" /opt/auto-prompt/src/ 2>/dev/null
echo ""
# 查找 Tauri 相关的模拟文件
ls -la /opt/auto-prompt/src/tauri/
''', timeout=60)

output = stdout.read().decode()
print(output)

print('\n修复 Tauri IPC 模拟...')
stdin, stdout, stderr = ssh.exec_command('''
# 检查现有的 Tauri 模拟文件
cat /opt/auto-prompt/src/tauri/tauri.js
''', timeout=60)

output = stdout.read().decode()
print(output)

ssh.close()
