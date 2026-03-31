#!/usr/bin/env python3
"""检查路由配置"""
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('180.76.244.18', username='root', password='Lxhao1230.0', timeout=30)

print('检查路由配置...')
stdin, stdout, stderr = ssh.exec_command('''
# 查找路由配置文件
find /opt/auto-prompt/src -name "*router*" -o -name "*route*" | head -10
echo ""
# 查看main.js或main.ts
cat /opt/auto-prompt/src/main.js 2>/dev/null || cat /opt/auto-prompt/src/main.ts 2>/dev/null
echo ""
# 查看是否有路由目录
ls -la /opt/auto-prompt/src/router/ 2>/dev/null || echo "没有router目录"
''', timeout=60)

output = stdout.read().decode()
print(output)

print('\n检查登录页面...')
stdin, stdout, stderr = ssh.exec_command('''
cat /opt/auto-prompt/src/views/LoginView.vue
''', timeout=60)

output = stdout.read().decode()
print(output)

ssh.close()
