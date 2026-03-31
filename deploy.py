#!/usr/bin/env python3
"""直接通过 SSH 命令执行部署"""
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('180.76.244.18', username='root', password='Lxhao1230.0', timeout=30)

print('正在通过 SSH 直接执行部署命令...')
stdin, stdout, stderr = ssh.exec_command('cd /opt/auto-prompt && bash deploy-baidu-source-v2.sh 2>&1', timeout=600)

# 获取完整输出
output = stdout.read().decode('utf-8', errors='ignore')
error = stderr.read().decode('utf-8', errors='ignore')

print(output)
if error:
    print(f"\n错误输出: {error}")

ssh.close()
