#!/usr/bin/env python3
"""检查服务器是否还有 invoke 引用"""
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('180.76.244.18', username='root', password='Lxhao1230.0', timeout=30)

print('检查服务器上的 invoke 引用...')
stdin, stdout, stderr = ssh.exec_command('''
cd /opt/auto-prompt

echo "1. 检查是否有 invoke 引用..."
grep -r "invoke(" src/ 2>/dev/null || echo "没有找到 invoke 调用"

echo ""
echo "2. 检查上传服务文件..."
grep -n "invoke" src/services/uploadService.js 2>/dev/null || echo "uploadService.js 中没有 invoke"

echo ""
echo "3. 检查 skills store..."
grep -n "invoke" src/stores/skills.js 2>/dev/null || echo "skills.js 中没有 invoke"

echo ""
echo "4. 检查构建后的文件..."
grep -r "invoke" dist/ 2>/dev/null || echo "dist 目录中没有 invoke"
''', timeout=60)

output = stdout.read().decode()
print(output)

print('\n检查前端文件内容...')
stdin, stdout, stderr = ssh.exec_command('''
cd /opt/auto-prompt

echo "检查 uploadService.js 内容:"
cat src/services/uploadService.js | head -20

echo ""
echo "检查 skills.js 内容:"
cat src/stores/skills.js | head -20
''', timeout=60)

output = stdout.read().decode()
print(output)

ssh.close()
