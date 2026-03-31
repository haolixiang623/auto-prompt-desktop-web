#!/usr/bin/env python3
"""调试登录后跳转问题"""
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('180.76.244.18', username='root', password='Lxhao1230.0', timeout=30)

print('检查认证状态管理...')
stdin, stdout, stderr = ssh.exec_command('''
# 检查认证服务代码
cat /opt/auto-prompt/src/services/authService.js
echo ""
echo "=== 检查认证状态管理 ==="
cat /opt/auto-prompt/src/services/authState.js
''', timeout=60)

output = stdout.read().decode()
print(output)

print('\n检查浏览器控制台错误...')
stdin, stdout, stderr = ssh.exec_command('''
# 查看最新的服务日志，特别关注认证相关
journalctl -u auto-prompt --no-pager -n 30 | grep -E "(login|auth|error|401|403)"
''', timeout=60)

output = stdout.read().decode()
print(output)

ssh.close()
