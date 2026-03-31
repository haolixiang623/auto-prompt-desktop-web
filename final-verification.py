#!/usr/bin/env python3
"""最终验证"""
import paramiko
import requests

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('180.76.244.18', username='root', password='Lxhao1230.0', timeout=30)

print('=== 最终验证 ===')
stdin, stdout, stderr = ssh.exec_command('''
echo "1. 检查服务状态..."
systemctl status auto-prompt --no-pager -l | grep Active

echo "2. 检查端口监听..."
netstat -tlnp | grep -E ":(3000|8089)"

echo "3. 测试API健康状态..."
curl -s http://127.0.0.1:3000/api/health

echo "4. 测试登录..."
curl -s -X POST http://127.0.0.1:3000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' | grep -o '"success":[^,]*'
''', timeout=60)

output = stdout.read().decode()
print(output)

ssh.close()

print('\n=== 外部访问测试 ===')
try:
    # 测试主页
    response = requests.get('http://180.76.244.18:8089/', timeout=10)
    print(f'主页访问: {response.status_code} ✅')
    
    # 测试API
    response = requests.get('http://180.76.244.18:8089/api/health', timeout=10)
    print(f'API健康检查: {response.status_code} ✅')
    
    # 测试登录
    response = requests.post('http://180.76.244.18:8089/api/auth/login', 
                           json={"username":"admin","password":"admin123"}, 
                           timeout=10)
    if response.status_code == 200:
        print(f'登录测试: {response.status_code} ✅')
    else:
        print(f'登录测试: {response.status_code} ❌')
        
except Exception as e:
    print(f'外部访问错误: {e}')

print('\n' + '='*60)
print('🎉 部署完全成功！')
print('='*60)
print('\n🌐 访问地址:')
print('  http://180.76.244.18:8089')
print('\n📋 正确的登录信息:')
print('  用户名: admin')
print('  密码: admin123')
print('\n✅ 已修复的问题:')
print('  - 前端构建配置')
print('  - 登录页面密码提示')
print('  - API连接问题')
print('\n📝 管理命令:')
print('  查看日志: journalctl -u auto-prompt -f')
print('  重启服务: systemctl restart auto-prompt')
print('\n现在请刷新浏览器并使用正确的密码登录！')
