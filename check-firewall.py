#!/usr/bin/env python3
"""检查防火墙和网络配置"""
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('180.76.244.18', username='root', password='Lxhao1230.0', timeout=30)

print('=== 防火墙检查 ===')

# 检查 iptables
print('\n1. iptables 规则:')
stdin, stdout, stderr = ssh.exec_command('iptables -L -n 2>&1 | head -20')
print(stdout.read().decode())

# 检查 ufw
print('\n2. ufw 状态:')
stdin, stdout, stderr = ssh.exec_command('ufw status 2>&1')
print(stdout.read().decode())

# 检查路由
print('\n3. 路由表:')
stdin, stdout, stderr = ssh.exec_command('ip route')
print(stdout.read().decode())

# 检查网卡
print('\n4. 网卡状态:')
stdin, stdout, stderr = ssh.exec_command('ip addr show | grep -E "(inet|eth|ens)"')
print(stdout.read().decode())

# 检查是否可以访问外网 HTTP
print('\n5. HTTP 测试:')
stdin, stdout, stderr = ssh.exec_command('curl -s -o /dev/null -w "%{http_code}" http://www.baidu.com')
http_result = stdout.read().decode()
print(f'百度 HTTP: {http_result}')

# 检查 traceroute
print('\n6. 到 Docker Hub 的路由:')
stdin, stdout, stderr = ssh.exec_command('traceroute -T -n registry-1.docker.io 2>&1 | head -10 || mtr -n --report --report-cycles 3 registry-1.docker.io 2>&1 | head -20')
print(stdout.read().decode())

ssh.close()
