#!/usr/bin/env python3
"""检查当前错误状态并修复"""
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('180.76.244.18', username='root', password='Lxhao1230.0', timeout=30)

print('=== 检查当前服务器状态 ===')
stdin, stdout, stderr = ssh.exec_command('''
cd /opt/auto-prompt

echo "1. 检查构建是否成功..."
if [ -d "dist" ]; then
  echo "dist 目录存在，检查文件..."
  ls -la dist/assets/ | head -5
else
  echo "dist 目录不存在，需要重新构建"
fi

echo ""
echo "2. 检查服务状态..."
systemctl status auto-prompt --no-pager | grep -E "Active|Main PID"

echo ""
echo "3. 查看最新日志..."
journalctl -u auto-prompt --no-pager -n 5

echo ""
echo "4. 检查是否还有 invoke..."
grep -r "invoke(" src/views/*.vue 2>/dev/null | head -3 || echo "Vue 文件中没有 invoke"
''', timeout=60)

output = stdout.read().decode()
print(output)

ssh.close()

print('\n' + '='*60)
print('请告诉我具体的错误信息')
print('='*60)
print('\n1. 打开浏览器开发者工具 (F12)')
print('2. 查看 Console 标签页')
print('3. 告诉我红色错误信息是什么')
print('\n或者尝试刷新页面 (Ctrl+F5) 看看是否还有错误')
