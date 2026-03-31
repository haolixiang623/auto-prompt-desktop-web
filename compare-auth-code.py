#!/usr/bin/env python3
"""对比本地和服务器登录代码"""
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('180.76.244.18', username='root', password='Lxhao1230.0', timeout=30)

print('=== 对比登录相关代码 ===')
stdin, stdout, stderr = ssh.exec_command('''
echo "【服务器 authService.js】:"
cat /opt/auto-prompt/src/services/authService.js
echo ""
echo "【服务器 LoginView.vue 关键部分】:"
grep -A 10 "async function handleLogin" /opt/auto-prompt/src/views/LoginView.vue || echo "找不到 handleLogin"
''', timeout=60)

output = stdout.read().decode()
print(output)

ssh.close()

print('\n' + '='*60)
print('【本地 authService.js】:')
with open('d:\\projects\\auto-prompt-desktop-web\\src\\services\\authService.js', 'r') as f:
    print(f.read())
