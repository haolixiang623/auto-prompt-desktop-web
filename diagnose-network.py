#!/usr/bin/env python3
"""诊断网络问题"""
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('180.76.244.18', username='root', password='Lxhao1230.0', timeout=30)

print('=== 网络诊断 ===')

# 检查 DNS
print('\n1. DNS 配置:')
stdin, stdout, stderr = ssh.exec_command('cat /etc/resolv.conf')
print(stdout.read().decode())

# 测试 DNS 解析
print('\n2. DNS 解析测试:')
stdin, stdout, stderr = ssh.exec_command('nslookup registry-1.docker.io 2>&1 || host registry-1.docker.io 2>&1 || ping -c 1 8.8.8.8')
print(stdout.read().decode())

# 检查网络连接
print('\n3. 网络连通性:')
stdin, stdout, stderr = ssh.exec_command('ping -c 2 114.114.114.114')
print(stdout.read().decode()[:500])

# 检查 Docker 配置
print('\n4. Docker 配置:')
stdin, stdout, stderr = ssh.exec_command('cat /etc/docker/daemon.json 2>/dev/null || echo "No config"')
print(stdout.read().decode())

# 修复 DNS
print('\n5. 修复 DNS...')
stdin, stdout, stderr = ssh.exec_command('''
# 备份原配置
cp /etc/resolv.conf /etc/resolv.conf.bak 2>/dev/null || true
# 使用公共 DNS
cat > /etc/resolv.conf << 'EOF'
nameserver 114.114.114.114
nameserver 8.8.8.8
nameserver 223.5.5.5
EOF
# 防止被覆盖
chattr +i /etc/resolv.conf 2>/dev/null || true
# 重启 Docker
systemctl restart docker
sleep 5
echo "DNS fixed"
''')
print(stdout.read().decode())

print('\n6. 测试 Docker 拉取:')
stdin, stdout, stderr = ssh.exec_command('docker pull hello-world 2>&1', timeout=60)
result = stdout.read().decode()
print(result[:1000])

ssh.close()
