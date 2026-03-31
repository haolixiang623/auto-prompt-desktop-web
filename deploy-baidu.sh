#!/bin/bash
# 使用百度云内部源部署
set -e

cd /opt/auto-prompt

echo "=== 修复 DNS 和软件源 ==="
# 使用百度云内部 DNS
cat > /etc/resolv.conf << 'EOF'
nameserver 180.76.76.76
nameserver 180.76.76.75
nameserver 114.114.114.114
EOF

# 使用百度云内部软件源
cat > /etc/apt/sources.list << 'EOF'
deb http://mirrors.baidubce.com/ubuntu/ noble main restricted universe multiverse
deb http://mirrors.baidubce.com/ubuntu/ noble-updates main restricted universe multiverse
deb http://mirrors.baidubce.com/ubuntu/ noble-backports main restricted universe multiverse
deb http://mirrors.baidubce.com/ubuntu/ noble-security main restricted universe multiverse
EOF

apt-get update

echo "=== 安装必要软件 ==="
apt-get install -y nginx python3 python3-pip curl wget

echo "=== 安装 Node.js (使用百度云镜像) ==="
curl -fsSL https://mirrors.baidubce.com/nodejs/node_20.x/pool/main/n/nodejs/nodejs_20.12.2-1nodesource1_amd64.deb -o nodejs.deb
dpkg -i nodejs.deb || apt-get install -f -y

echo "=== 构建前端 ==="
cd src
npm config set registry https://registry.npmmirror.com
npm ci
npm run build
cd ..

echo "=== 安装 Python 依赖 ==="
pip3 install fastapi uvicorn python-multipart pydantic argon2-cffi httpx openai openpyxl pymupdf -i https://mirrors.aliyun.com/pypi/simple/

echo "=== 配置 Nginx ==="
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

echo "=== 启动服务 ==="
export AUTO_PROMPT_REPO_ROOT=/opt/auto-prompt
export AUTO_PROMPT_WEB_DIST=/opt/auto-prompt/dist
export AUTO_PROMPT_DATA_DIR=/opt/auto-prompt/data
export PORT=3000

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

# 使用 systemd 管理服务
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

echo ""
echo "=== 部署完成 ==="
echo "访问: http://180.76.244.18:8089"
echo "查看日志: journalctl -u auto-prompt -f"
echo "管理服务: systemctl status auto-prompt"
