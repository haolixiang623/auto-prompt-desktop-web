#!/usr/bin/env python3
"""检查应用错误日志"""
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('180.76.244.18', username='root', password='Lxhao1230.0', timeout=30)

print('=== 检查应用错误日志 ===')
stdin, stdout, stderr = ssh.exec_command('''
# 查看最新的应用日志
echo "1. 最近的服务日志:"
journalctl -u auto-prompt --no-pager -n 50

echo ""
echo "2. 查看错误相关的日志:"
journalctl -u auto-prompt --no-pager | grep -i error | tail -10

echo ""
echo "3. 查看警告相关的日志:"
journalctl -u auto-prompt --no-pager | grep -i warn | tail -10

echo ""
echo "4. 查看最近的HTTP请求日志:"
journalctl -u auto-prompt --no-pager | grep "HTTP\|GET\|POST" | tail -20
''', timeout=60)

output = stdout.read().decode()
error = stderr.read().decode()
print(output)
if error:
    print(f'错误: {error}')

print('\n=== 检查Python应用日志 ===')
stdin, stdout, stderr = ssh.exec_command('''
# 检查是否有应用日志文件
ls -la /opt/auto-prompt/logs/ 2>/dev/null || echo "没有logs目录"

# 检查数据目录
ls -la /opt/auto-prompt/data/
''', timeout=60)

output = stdout.read().decode()
print(output)

ssh.close()
