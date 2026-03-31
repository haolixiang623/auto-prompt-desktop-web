#!/usr/bin/env python3
"""最终修复部署"""
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('180.76.244.18', username='root', password='Lxhao1230.0', timeout=30)

print('修复前端构建问题...')
# 检查并构建前端
stdin, stdout, stderr = ssh.exec_command('''
cd /opt/auto-prompt
ls -la
# 如果没有 src 目录，从项目根目录复制
if [ ! -d "src" ]; then
  echo "前端源码缺失，需要上传"
fi
''', timeout=60)

output = stdout.read().decode()
print(output)

print('安装 Python 依赖到虚拟环境...')
stdin, stdout, stderr = ssh.exec_command('''
cd /opt/auto-prompt
python3 -m venv venv
source venv/bin/activate
pip install fastapi uvicorn python-multipart pydantic argon2-cffi httpx openai openpyxl pymupdf -i https://mirrors.aliyun.com/pypi/simple/
''', timeout=180)

output = stdout.read().decode()
error = stderr.read().decode()
print(output)
if error:
    print(f'错误: {error}')

print('更新启动脚本使用虚拟环境...')
stdin, stdout, stderr = ssh.exec_command('''
cat > /opt/auto-prompt/start.sh << 'EOF'
#!/bin/bash
cd /opt/auto-prompt
export AUTO_PROMPT_REPO_ROOT=/opt/auto-prompt
export AUTO_PROMPT_WEB_DIST=/opt/auto-prompt/dist
export AUTO_PROMPT_DATA_DIR=/opt/auto-prompt/data
export PORT=3000
source venv/bin/activate
exec python -m uvicorn pyserver.app.main:app --host 0.0.0.0 --port 3000
EOF

chmod +x /opt/auto-prompt/start.sh
systemctl restart auto-prompt
sleep 5
systemctl status auto-prompt
''', timeout=120)

output = stdout.read().decode()
error = stderr.read().decode()
print(output)
if error:
    print(f'错误: {error}')

print('检查服务状态...')
stdin, stdout, stderr = ssh.exec_command('''
systemctl status auto-prompt --no-pager
netstat -tlnp | grep 3000
netstat -tlnp | grep 8089
''', timeout=60)

output = stdout.read().decode()
error = stderr.read().decode()
print(output)
if error:
    print(f'错误: {error}')

ssh.close()
