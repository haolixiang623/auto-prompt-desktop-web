#!/usr/bin/env python3
"""修复并继续部署"""
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('180.76.244.18', username='root', password='Lxhao1230.0', timeout=30)

print('修复软件源配置...')
# 清理重复的软件源配置
stdin, stdout, stderr = ssh.exec_command('''
# 备份原配置
cp /etc/apt/sources.list /etc/apt/sources.list.bak
# 清空并重新配置
cat > /etc/apt/sources.list << 'EOF'
deb http://mirrors.baidubce.com/ubuntu/ noble main restricted universe multiverse
deb http://mirrors.baidubce.com/ubuntu/ noble-updates main restricted universe multiverse
deb http://mirrors.baidubce.com/ubuntu/ noble-backports main restricted universe multiverse
deb http://mirrors.baidubce.com/ubuntu/ noble-security main restricted universe multiverse
EOF
# 移除其他配置文件
rm -f /etc/apt/sources.list.d/ubuntu.sources
apt-get update
''', timeout=120)

print(stdout.read().decode())

print('安装 Node.js 使用阿里云源...')
stdin, stdout, stderr = ssh.exec_command('''
# 使用阿里云 Node.js 源
curl -fsSL https://mirrors.aliyun.com/nodejs/release_20.x/pool/main/n/nodejs/nodejs_20.12.2-1nodesource1_amd64.deb -o nodejs.deb || \
curl -fsSL https://registry.npmmirror.com/-/binary/node/20.12.2/node-v20.12.2-linux-x64.tar.xz -o node.tar.xz
dpkg -i nodejs.deb 2>/dev/null || (tar -xf node.tar.xz && cp -r node-v20.12.2-linux-x64/* /usr/local/)
node --version
npm --version
''', timeout=180)

output = stdout.read().decode()
error = stderr.read().decode()
print(output)
if error:
    print(f'错误: {error}')

print('继续构建前端...')
stdin, stdout, stderr = ssh.exec_command('''
cd /opt/auto-prompt/src
npm config set registry https://registry.npmmirror.com
npm ci
npm run build
cd ..
''', timeout=300)

output = stdout.read().decode()
error = stderr.read().decode()
print(output)
if error:
    print(f'错误: {error}')

print('安装 Python 依赖...')
stdin, stdout, stderr = ssh.exec_command('''
pip3 install fastapi uvicorn python-multipart pydantic argon2-cffi httpx openai openpyxl pymupdf -i https://mirrors.aliyun.com/pypi/simple/
''', timeout=180)

output = stdout.read().decode()
error = stderr.read().decode()
print(output)
if error:
    print(f'错误: {error}')

print('配置并启动服务...')
stdin, stdout, stderr = ssh.exec_command('''
# 配置 Nginx
cat > /etc/nginx/sites-available/auto-prompt << 'EOF'
server {
    listen 8089;
    server_name _;
    
    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
EOF

ln -sf /etc/nginx/sites-available/auto-prompt /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl restart nginx

# 创建启动脚本
cat > /opt/auto-prompt/start.sh << 'EOF'
#!/bin/bash
cd /opt/auto-prompt
export AUTO_PROMPT_REPO_ROOT=/opt/auto-prompt
export AUTO_PROMPT_WEB_DIST=/opt/auto-prompt/dist
export AUTO_PROMPT_DATA_DIR=/opt/auto-prompt/data
export PORT=3000
exec python3 -m uvicorn pyserver.app.main:app --host 0.0.0.0 --port 3000
EOF

chmod +x /opt/auto-prompt/start.sh

# 配置 systemd 服务
cat > /etc/systemd/system/auto-prompt.service << 'EOF'
[Unit]
Description=Auto Prompt Python Backend
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/auto-prompt
ExecStart=/opt/auto-prompt/start.sh
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable auto-prompt
systemctl start auto-prompt

echo "=== 部署完成 ==="
echo "访问: http://180.76.244.18:8089"
echo "服务状态: systemctl status auto-prompt"
''', timeout=120)

output = stdout.read().decode()
error = stderr.read().decode()
print(output)
if error:
    print(f'错误: {error}')

ssh.close()
