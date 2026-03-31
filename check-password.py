#!/usr/bin/env python3
"""检查路由配置和修复密码"""
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('180.76.244.18', username='root', password='Lxhao1230.0', timeout=30)

print('检查路由配置...')
stdin, stdout, stderr = ssh.exec_command('''
cat /opt/auto-prompt/src/router/index.js
''', timeout=60)

output = stdout.read().decode()
print(output)

print('\n检查用户初始化脚本...')
stdin, stdout, stderr = ssh.exec_command('''
# 查找用户初始化相关代码
grep -r "admin123" /opt/auto-prompt/pyserver/ 2>/dev/null || echo "未找到admin123"
grep -r "admin123456" /opt/auto-prompt/pyserver/ 2>/dev/null || echo "未找到admin123456"
echo ""
# 查看用户数据初始化
find /opt/auto-prompt/pyserver -name "*.py" -exec grep -l "admin\|user" {} \; | head -3
''', timeout=60)

output = stdout.read().decode()
print(output)

print('\n测试两种密码...')
stdin, stdout, stderr = ssh.exec_command('''
# 测试admin123
echo "测试admin123:"
curl -s -X POST http://127.0.0.1:3000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' | grep -o '"success":[^,]*'

# 测试admin123456  
echo "测试admin123456:"
curl -s -X POST http://127.0.0.1:3000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123456"}' | grep -o '"success":[^,]*'
''', timeout=60)

output = stdout.read().decode()
print(output)

ssh.close()
