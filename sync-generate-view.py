#!/usr/bin/env python3
"""同步修复后的 GenerateView.vue 到服务器"""
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('180.76.244.18', username='root', password='Lxhao1230.0', timeout=30)

print('上传修复后的 GenerateView.vue...')
sftp = ssh.open_sftp()
sftp.put('src/views/GenerateView.vue', '/opt/auto-prompt/src/views/GenerateView.vue')
sftp.close()
print('✓ 上传完成')

print('\n重新构建前端...')
stdin, stdout, stderr = ssh.exec_command('cd /opt/auto-prompt && npm run build', timeout=120)

output = stdout.read().decode()
error = stderr.read().decode()
print(output)
if error:
    print(f'错误: {error}')

print('\n重启服务...')
stdin, stdout, stderr = ssh.exec_command('systemctl restart auto-prompt && sleep 3 && systemctl status auto-prompt --no-pager', timeout=60)

output = stdout.read().decode()
print(output)

ssh.close()

print('\n' + '='*60)
print('🎉 GenerateView.vue 修复完成！')
print('='*60)
print('\n✅ 修复内容:')
print('  - 移除了所有 Tauri invoke 调用')
print('  - 替换为 HTTP API 调用')
print('  - 重新构建并重启了服务')
print('\n🌐 现在请:')
print('  1. 刷新浏览器 (Ctrl+F5)')
print('  2. 重新登录测试功能')
print('  3. 检查是否还有 invoke 错误')
