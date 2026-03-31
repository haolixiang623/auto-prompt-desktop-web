#!/usr/bin/env python3
"""验证前端访问"""
import paramiko
import requests

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('180.76.244.18', username='root', password='Lxhao1230.0', timeout=30)

print('测试本地访问...')
stdin, stdout, stderr = ssh.exec_command('''
# 测试前端页面
curl -s http://127.0.0.1:3000/ | head -20
echo ""
# 测试通过 Nginx 访问
curl -s http://127.0.0.1:8089/ | head -20
''', timeout=60)

output = stdout.read().decode()
error = stderr.read().decode()
print(output)
if error:
    print(f'错误: {error}')

ssh.close()

print('\n测试外部访问...')
try:
    response = requests.get('http://180.76.244.18:8089/', timeout=10)
    if response.status_code == 200:
        print(f'✅ 外部访问成功！状态码: {response.status_code}')
        if 'html' in response.text[:500]:
            print('✅ 返回了 HTML 页面')
    else:
        print(f'❌ 外部访问失败，状态码: {response.status_code}')
except Exception as e:
    print(f'❌ 外部访问错误: {e}')

print('\n' + '='*50)
print('🎉 部署完成！')
print('='*50)
print('\n🌐 访问地址:')
print('  应用: http://180.76.244.18:8089')
print('  API文档: http://180.76.244.18:8089/docs')
print('\n📋 默认账户:')
print('  用户名: admin')
print('  密码: admin123')
print('\n⚠️  如果仍无法访问，请检查:')
print('  1. 浏览器是否阻止了 HTTP 访问')
print('  2. 防火墙是否放行 8089 端口')
print('  3. 百度云安全组是否配置正确')
