#!/usr/bin/env python3
"""检查并修复前端构建问题"""
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('180.76.244.18', username='root', password='Lxhao1230.0', timeout=30)

print('检查前端文件...')
stdin, stdout, stderr = ssh.exec_command('''
cd /opt/auto-prompt
ls -la
echo ""
# 检查是否有 dist 目录
if [ -d "dist" ]; then
  echo "dist 目录存在，内容："
  ls -la dist/
else
  echo "dist 目录不存在"
fi
echo ""
# 检查是否有 src 目录
if [ -d "src" ]; then
  echo "src 目录存在"
  ls -la src/
else
  echo "src 目录不存在，需要上传前端源码"
fi
''', timeout=60)

output = stdout.read().decode()
print(output)

print('上传前端源码...')
# 上传前端源码
sftp = ssh.open_sftp()
try:
    # 上传前端文件
    files_to_upload = [
        'index.html',
        'vite.config.js',
        'postcss.config.js',
        'tailwind.config.js',
        'package.json',
        'package-lock.json'
    ]
    
    for file in files_to_upload:
        try:
            sftp.put(file, f'/opt/auto-prompt/{file}')
            print(f'✓ {file}')
        except:
            print(f'✗ {file} not found locally')
    
    # 上传 src 目录
    import os
    if os.path.exists('src'):
        print('上传 src 目录...')
        for root, dirs, files in os.walk('src'):
            remote_root = root.replace('src', '/opt/auto-prompt/src')
            for dir in dirs:
                remote_dir = os.path.join(remote_root, dir).replace('\\', '/')
                ssh.exec_command(f'mkdir -p {remote_dir}')
            for file in files:
                local_file = os.path.join(root, file)
                remote_file = os.path.join(remote_root, file).replace('\\', '/')
                try:
                    sftp.put(local_file, remote_file)
                except:
                    pass
        print('✓ src 目录上传完成')
    
finally:
    sftp.close()

print('构建前端...')
stdin, stdout, stderr = ssh.exec_command('''
cd /opt/auto-prompt
npm config set registry https://registry.npmmirror.com
npm ci
npm run build
ls -la dist/
''', timeout=300)

output = stdout.read().decode()
error = stderr.read().decode()
print(output)
if error:
    print(f'错误: {error}')

print('重启服务...')
stdin, stdout, stderr = ssh.exec_command('systemctl restart auto-prompt && sleep 3 && systemctl status auto-prompt --no-pager', timeout=60)

output = stdout.read().decode()
print(output)

ssh.close()
