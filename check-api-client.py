#!/usr/bin/env python3
"""检查API客户端和登录流程"""
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('180.76.244.18', username='root', password='Lxhao1230.0', timeout=30)

print('检查API客户端配置...')
stdin, stdout, stderr = ssh.exec_command('''
cat /opt/auto-prompt/src/services/apiClient.js
''', timeout=60)

output = stdout.read().decode()
print(output)

print('\n检查登录响应数据格式...')
stdin, stdout, stderr = ssh.exec_command('''
# 详细测试登录响应
curl -s -X POST http://127.0.0.1:3000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' | jq '.'
''', timeout=60)

output = stdout.read().decode()
print(output)

print('\n检查Dashboard组件...')
stdin, stdout, stderr = ssh.exec_command('''
cat /opt/auto-prompt/src/views/Dashboard.vue | head -50
''', timeout=60)

output = stdout.read().decode()
print(output)

ssh.close()
