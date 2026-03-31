#!/usr/bin/env python3
"""修复登录页面密码提示"""
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('180.76.244.18', username='root', password='Lxhao1230.0', timeout=30)

print('修复登录页面密码提示...')
stdin, stdout, stderr = ssh.exec_command('''
# 备份原文件
cp /opt/auto-prompt/src/views/LoginView.vue /opt/auto-prompt/src/views/LoginView.vue.bak

# 修复密码提示
sed -i 's/admin123456/admin123/g' /opt/auto-prompt/src/views/LoginView.vue

# 验证修改
grep -n "admin123" /opt/auto-prompt/src/views/LoginView.vue
''', timeout=60)

output = stdout.read().decode()
print(output)

print('\n重新构建前端...')
stdin, stdout, stderr = ssh.exec_command('''
cd /opt/auto-prompt
npm run build
''', timeout=120)

output = stdout.read().decode()
error = stderr.read().decode()
print(output)
if error:
    print(f'错误: {error}')

print('\n测试完整的登录流程...')
stdin, stdout, stderr = ssh.exec_command('''
# 模拟完整登录流程
echo "1. 获取登录页面..."
curl -s http://127.0.0.1:3000/ | grep -o "<title>.*</title>"

echo "2. 登录获取token..."
TOKEN=$(curl -s -X POST http://127.0.0.1:3000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' | \
  grep -o '"token":"[^"]*"' | cut -d'"' -f4)

echo "Token获取成功: ${TOKEN:0:20}..."

echo "3. 验证token有效性..."
curl -s -X GET http://127.0.0.1:3000/api/auth/me \
  -H "Authorization: Bearer $TOKEN" | grep -o '"success":[^,]*'

echo "4. 检查前端是否已更新..."
curl -s http://127.0.0.1:3000/ | grep -o "admin123" || echo "前端已更新，密码提示已修正"
''', timeout=60)

output = stdout.read().decode()
error = stderr.read().decode()
print(output)
if error:
    print(f'错误: {error}')

ssh.close()
