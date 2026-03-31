#!/usr/bin/env python3
"""测试 Docker 镜像可用性并构建"""
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('180.76.244.18', username='root', password='Lxhao1230.0', timeout=30)

# 尝试可用的镜像源
mirrors = [
    ('registry.cn-hangzhou.aliyuncs.com/library/node:20', 'node:20'),
    ('registry.cn-hangzhou.aliyuncs.com/library/node:18', 'node:18'),
    ('registry.cn-hangzhou.aliyuncs.com/library/python:3.11', 'python:3.11'),
    ('registry.cn-hangzhou.aliyuncs.com/library/nginx:alpine', 'nginx:alpine'),
]

print('测试镜像源...')
for mirror, official in mirrors:
    print(f'尝试 {mirror}...')
    stdin, stdout, stderr = ssh.exec_command(f'docker pull {mirror} 2>&1', timeout=120)
    output = stdout.read().decode()
    if 'Error' in output:
        print(f'  ✗ 失败')
    else:
        print(f'  ✓ 成功')
        # 打标签
        ssh.exec_command(f'docker tag {mirror} {official}')

print('\n检查已拉取的镜像:')
stdin, stdout, stderr = ssh.exec_command('docker images')
print(stdout.read().decode())

ssh.close()
