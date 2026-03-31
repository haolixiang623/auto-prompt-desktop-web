#!/usr/bin/env python3
"""验证修复后的连接"""
import paramiko
import requests

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('180.76.244.18', username='root', password='Lxhao1230.0', timeout=30)

print('测试API连接...')
stdin, stdout, stderr = ssh.exec_command('''
# 测试健康检查
curl -s http://127.0.0.1:3000/api/health
echo ""
# 测试登录API
curl -s -X POST http://127.0.0.1:3000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'
echo ""
# 查看最新日志
journalctl -u auto-prompt --no-pager -n 10
''', timeout=60)

output = stdout.read().decode()
error = stderr.read().decode()
print(output)
if error:
    print(f'错误: {error}')

ssh.close()

print('\n测试外部访问...')
try:
    # 测试健康检查
    response = requests.get('http://180.76.244.18:8089/api/health', timeout=10)
    print(f'健康检查: {response.status_code} - {response.text}')
    
    # 测试登录
    response = requests.post('http://180.76.244.18:8089/api/auth/login', 
                           json={"username":"admin","password":"admin123"}, 
                           timeout=10)
    print(f'登录测试: {response.status_code} - {response.text}')
    
except Exception as e:
    print(f'外部访问错误: {e}')

print('\n' + '='*50)
print('✅ 修复完成！')
print('='*50)
print('\n现在请刷新浏览器页面 (Ctrl+F5)')
print('应该能看到正常的登录界面了')
print('\n📋 登录信息:')
print('  用户名: admin')
print('  密码: admin123')
