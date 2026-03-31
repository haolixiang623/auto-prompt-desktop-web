#!/usr/bin/env python3
"""检查前端可能的错误"""
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('180.76.244.18', username='root', password='Lxhao1230.0', timeout=30)

print('=== 检查前端配置和可能的错误 ===')
stdin, stdout, stderr = ssh.exec_command('''
# 检查前端构建是否有问题
cd /opt/auto-prompt
echo "1. 检查package.json中的依赖:"
cat package.json | grep -A 20 "dependencies"

echo ""
echo "2. 检查是否有构建警告:"
npm run build 2>&1 | grep -i warn || echo "没有构建警告"

echo ""
echo "3. 检查环境变量:"
cat .env 2>/dev/null || echo "没有.env文件"

echo ""
echo "4. 检查Vite配置中的API基础URL:"
grep -n "VITE_API_BASE_URL" vite.config.js || echo "没有设置API基础URL"
''', timeout=120)

output = stdout.read().decode()
error = stderr.read().decode()
print(output)
if error:
    print(f'错误: {error}')

print('\n=== 测试API端点 ===')
stdin, stdout, stderr = ssh.exec_command('''
# 测试各个API端点
echo "测试 /api/health:"
curl -s http://127.0.0.1:3000/api/health

echo ""
echo "测试 /api/auth/me (无token):"
curl -s http://127.0.0.1:3000/api/auth/me

echo ""
echo "测试 /api/auth/me (有token):"
TOKEN=$(curl -s -X POST http://127.0.0.1:3000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' | \
  grep -o '"token":"[^"]*"' | cut -d'"' -f4)
curl -s -X GET http://127.0.0.1:3000/api/auth/me \
  -H "Authorization: Bearer $TOKEN"
''', timeout=60)

output = stdout.read().decode()
print(output)

ssh.close()
