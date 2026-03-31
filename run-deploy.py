#!/usr/bin/env python3
"""上传并执行部署脚本"""
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('180.76.244.18', username='root', password='Lxhao1230.0', timeout=30)

# 上传部署脚本
print('上传部署脚本...')
sftp = ssh.open_sftp()
sftp.put('deploy-baidu.sh', '/opt/auto-prompt/deploy-baidu.sh')
sftp.close()

# 执行部署
print('执行部署脚本...')
stdin, stdout, stderr = ssh.exec_command('chmod +x /opt/auto-prompt/deploy-baidu.sh && bash /opt/auto-prompt/deploy-baidu.sh 2>&1', timeout=600)

# 获取完整输出
output = stdout.read().decode('utf-8', errors='ignore')
error = stderr.read().decode('utf-8', errors='ignore')

print(output)
if error:
    print(f"\n错误输出: {error}")

ssh.close()
