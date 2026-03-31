#!/usr/bin/env python3
"""验证部署成功"""
import paramiko
import requests

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('180.76.244.18', username='root', password='Lxhao1230.0', timeout=30)

print('验证服务状态...')
stdin, stdout, stderr = ssh.exec_command('''
# 检查服务状态
systemctl status auto-prompt --no-pager -l
echo ""
# 测试本地访问
curl -s http://127.0.0.1:3000/api/health || echo "Health check failed"
echo ""
# 检查端口
netstat -tlnp | grep -E ":(3000|8089)"
''', timeout=60)

output = stdout.read().decode()
error = stderr.read().decode()
print(output)
if error:
    print(f'错误: {error}')

ssh.close()

print('\n' + '='*50)
print('✅ 部署成功！')
print('='*50)
print('\n🌐 访问地址:')
print('  应用: http://180.76.244.18:8089')
print('  API文档: http://180.76.244.18:8089/docs')
print('  健康检查: http://180.76.244.18:8089/api/health')
print('\n📋 默认账户:')
print('  用户名: admin')
print('  密码: admin123')
print('\n⚙️ 管理命令:')
print('  查看日志: journalctl -u auto-prompt -f')
print('  重启服务: systemctl restart auto-prompt')
print('  停止服务: systemctl stop auto-prompt')
print('\n⚠️  请及时修改默认密码！')
