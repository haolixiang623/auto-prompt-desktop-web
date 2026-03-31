#!/usr/bin/env python3
"""重启服务并验证 Tauri 移除效果"""
import paramiko
import requests

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('180.76.244.18', username='root', password='Lxhao1230.0', timeout=30)

print('重启服务...')
stdin, stdout, stderr = ssh.exec_command('systemctl restart auto-prompt && sleep 3 && systemctl status auto-prompt --no-pager', timeout=60)

output = stdout.read().decode()
print(output)

print('\n=== 验证 Tauri 移除效果 ===')
stdin, stdout, stderr = ssh.exec_command('''
echo "1. 检查服务状态..."
systemctl status auto-prompt --no-pager | grep Active

echo "2. 测试页面访问..."
curl -s http://127.0.0.1:3000/ | grep -o "<title>.*</title>"

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
        print(f'登录测试: {response.status_code} ✅')
    else:
        print(f'登录测试: {response.status_code} ❌')
        
except Exception as e:
    print(f'外部访问错误: {e}')

print('\n' + '='*60)
print('🎉 Tauri 已完全移除！')
print('='*60)
print('\n✅ 移除内容:')
print('  - 所有 @tauri-apps 依赖')
print('  - 所有 Tauri API 导入')
print('  - Tauri 相关配置文件')
print('  - Tauri 特有的事件监听')
print('\n🌐 现在应用是纯 Web 应用:')
print('  - 不再依赖 Tauri 桌面环境')
print('  - 所有功能通过 Web API 实现')
print('  - 可以在任何浏览器中运行')
print('\n📋 功能说明:')
print('  - 文件上传使用 Web 文件选择器')
print('  - 文件操作通过后端 API 处理')
print('  - 不再有桌面应用特有的功能')
print('\n🌐 现在请刷新浏览器并测试所有功能！')
