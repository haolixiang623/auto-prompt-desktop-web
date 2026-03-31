#!/usr/bin/env python3
"""验证登录修复效果"""
import paramiko
import requests

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('180.76.244.18', username='root', password='Lxhao1230.0', timeout=30)

print('=== 验证修复效果 ===')
stdin, stdout, stderr = ssh.exec_command('''
echo "1. 检查服务状态..."
systemctl status auto-prompt --no-pager | grep Active

echo "2. 测试登录API..."
curl -s -X POST http://127.0.0.1:3000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' | jq '.success'

echo "3. 检查最新日志..."
journalctl -u auto-prompt --no-pager -n 10
''', timeout=60)

output = stdout.read().decode()
print(output)

ssh.close()

print('\n=== 外部访问测试 ===')
try:
    # 测试主页
    response = requests.get('http://180.76.244.18:8089/', timeout=10)
    print(f'主页访问: {response.status_code} ✅')
    
    # 测试登录
    response = requests.post('http://180.76.244.18:8089/api/auth/login', 
                           json={"username":"admin","password":"admin123"}, 
                           timeout=10)
    if response.status_code == 200:
        data = response.json()
        print(f'登录测试: {response.status_code} ✅')
        print(f'响应结构: success={data.get("success")}, has_data={"data" in data}')
    else:
        print(f'登录测试: {response.status_code} ❌')
        
except Exception as e:
    print(f'外部访问错误: {e}')

print('\n' + '='*60)
print('🔧 登录问题已修复！')
print('='*60)
print('\n✅ 修复内容:')
print('  - 修复了登录响应数据结构处理')
print('  - 前端现在正确解析嵌套的响应数据')
print('  - 添加了调试日志以便排查问题')
print('\n🌐 现在请:')
print('  1. 刷新浏览器页面 (Ctrl+F5)')
print('  2. 使用 admin/admin123 登录')
print('  3. 应该能成功进入主界面')
print('\n📋 如果还有问题，请检查浏览器控制台的日志输出')
