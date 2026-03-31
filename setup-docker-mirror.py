#!/usr/bin/env python3
"""配置 Docker 镜像源并预拉取镜像"""
import paramiko
import time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('180.76.244.18', username='root', password='Lxhao1230.0', timeout=30)

print('配置国内 Docker 镜像源...')
daemon_json = '''{
  "registry-mirrors": [
    "https://docker.mirrors.ustc.edu.cn",
    "https://hub-mirror.c.163.com",
    "https://mirror.baidubce.com"
  ]
}'''

stdin, stdout, stderr = ssh.exec_command(f'mkdir -p /etc/docker && cat > /etc/docker/daemon.json << \'EOF\'\n{daemon_json}\nEOF')
print(stdout.read().decode())

stdin, stdout, stderr = ssh.exec_command('systemctl restart docker && sleep 3 && docker info | grep -A 5 "Registry Mirrors"')
print('Docker 镜像源配置:')
print(stdout.read().decode())

print('预拉取基础镜像...')
images = [
    ('node:20-bookworm-slim', 'docker.mirrors.ustc.edu.cn/library/node:20-bookworm-slim'),
    ('python:3.11-slim-bookworm', 'docker.mirrors.ustc.edu.cn/library/python:3.11-slim-bookworm'),
    ('nginx:alpine', 'docker.mirrors.ustc.edu.cn/library/nginx:alpine')
]

for official, mirror in images:
    print(f'拉取 {official}...')
    # 先尝试拉取官方镜像（配置了mirror后会自动走mirror）
    stdin, stdout, stderr = ssh.exec_command(f'docker pull {official} 2>&1', timeout=300)
    output = stdout.read().decode()
    error = stderr.read().decode()
    if 'Error' in output or 'Error' in error:
        print(f'  官方源失败，尝试镜像: {mirror}')
        stdin, stdout, stderr = ssh.exec_command(f'docker pull {mirror} && docker tag {mirror} {official} 2>&1', timeout=300)
        print(stdout.read().decode()[-300:])
    else:
        print(f'  ✓ {official} 拉取成功')

print('\n基础镜像准备完成！')
ssh.close()
