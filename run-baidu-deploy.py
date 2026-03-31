#!/usr/bin/env python3
"""使用百度云内部源部署"""
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('180.76.244.18', username='root', password='Lxhao1230.0', timeout=30)

# 上传部署脚本
sftp = ssh.open_sftp()
sftp.put('deploy-baidu-source-v2.sh', '/opt/auto-prompt/deploy-baidu-source-v2.sh')
sftp.close()

print('上传部署脚本完成，开始执行...')
stdin, stdout, stderr = ssh.exec_command('chmod +x /opt/auto-prompt/deploy-baidu-source-v2.sh && bash /opt/auto-prompt/deploy-baidu-source-v2.sh 2>&1', timeout=600)

# 实时输出
import sys
import time
while True:
    if stdout.channel.recv_exit_status() != -1:
        break
    output = stdout.read(1024).decode('utf-8', errors='ignore')
    if output:
        print(output, end='')
        sys.stdout.flush()
    time.sleep(0.1)

# 获取剩余输出
remaining = stdout.read().decode('utf-8', errors='ignore')
if remaining:
    print(remaining)

error = stderr.read().decode('utf-8', errors='ignore')
if error:
    print(f"\n错误输出: {error}")

ssh.close()
