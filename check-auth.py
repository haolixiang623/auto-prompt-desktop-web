#!/usr/bin/env python3
"""检查登录状态持久化问题"""
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('180.76.244.18', username='root', password='Lxhao1230.0', timeout=30)

print('检查登录流程...')
stdin, stdout, stderr = ssh.exec_command('''
# 测试完整的登录流程
echo "1. 测试登录..."
TOKEN=$(curl -s -X POST http://127.0.0.1:3000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' | \
  grep -o '"token":"[^"]*"' | cut -d'"' -f4)

echo "Token: $TOKEN"

echo "2. 测试使用token获取用户信息..."
curl -s -X GET http://127.0.0.1:3000/api/auth/me \
  -H "Authorization: Bearer $TOKEN"

echo ""
echo "3. 检查前端登录相关代码..."
grep -r "localStorage\|sessionStorage" /opt/auto-prompt/src/ 2>/dev/null || echo "未找到存储相关代码"
''', timeout=60)

output = stdout.read().decode()
error = stderr.read().decode()
print(output)
if error:
    print(f'错误: {error}')

print('\n检查前端认证逻辑...')
stdin, stdout, stderr = ssh.exec_command('''
# 查看登录相关的Vue组件
find /opt/auto-prompt/src -name "*.vue" -exec grep -l "login\|auth" {} \;
echo ""
# 查看API调用相关代码
find /opt/auto-prompt/src -name "*.js" -o -name "*.ts" -o -name "*.vue" | xargs grep -l "api\|fetch\|axios" 2>/dev/null | head -5
''', timeout=60)

output = stdout.read().decode()
print(output)

ssh.close()
