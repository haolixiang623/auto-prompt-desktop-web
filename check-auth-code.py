#!/usr/bin/env python3
"""检查并修复认证逻辑"""
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('180.76.244.18', username='root', password='Lxhao1230.0', timeout=30)

print('检查认证服务代码...')
stdin, stdout, stderr = ssh.exec_command('''
# 查看认证服务
cat /opt/auto-prompt/src/services/authService.js
echo ""
echo "=== 检查API客户端 ==="
cat /opt/auto-prompt/src/services/apiClient.js
echo ""
echo "=== 检查认证状态管理 ==="
cat /opt/auto-prompt/src/services/authState.js
''', timeout=60)

output = stdout.read().decode()
print(output)

print('\n检查App.vue的路由逻辑...')
stdin, stdout, stderr = ssh.exec_command('''
cat /opt/auto-prompt/src/App.vue
''', timeout=60)

output = stdout.read().decode()
print(output)

ssh.close()
