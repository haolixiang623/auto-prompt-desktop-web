#!/usr/bin/env python3
"""检查并修复 invoke 函数引用"""
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('180.76.244.18', username='root', password='Lxhao1230.0', timeout=30)

print('查找所有 invoke 引用...')
stdin, stdout, stderr = ssh.exec_command('''
cd /opt/auto-prompt

echo "1. 查找所有 invoke 引用..."
grep -r "invoke(" src/ || echo "没有找到 invoke 调用"

echo ""
echo "2. 检查哪些文件还在使用 invoke..."
grep -r "invoke" src/ | grep -v "import.*invoke" | grep -v "//" || echo "没有找到 invoke 使用"
''', timeout=60)

output = stdout.read().decode()
print(output)

print('\n检查上传服务...')
stdin, stdout, stderr = ssh.exec_command('''
cd /opt/auto-prompt

echo "检查 uploadService.js..."
cat src/services/uploadService.js
''', timeout=60)

output = stdout.read().decode()
print(output)

ssh.close()
