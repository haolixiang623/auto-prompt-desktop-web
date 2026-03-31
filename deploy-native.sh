#!/bin/bash
# 直接在服务器部署 - 不使用 Docker
set -e

cd /opt/auto-prompt

echo "=== 安装 Python 环境 ==="
apt-get update
apt-get install -y python3 python3-pip python3-venv nginx

echo "=== 安装依赖 ==="
pip3 install fastapi uvicorn python-multipart pydantic argon2-cffi httpx openai openpyxl pymupdf -i https://pypi.tuna.tsinghua.edu.cn/simple

echo "=== 构建前端 ==="
cd /opt/auto-prompt
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt-get install -y nodejs
cd src && npm ci && npm run build && cd ..

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
cd /opt/auto-prompt && nohup python3 -m uvicorn pyserver.app.main:app --host 0.0.0.0 --port 3000 > /var/log/auto-prompt.log 2>&1 &

echo ""
echo "=== 部署完成 ==="
echo "访问: http://180.76.244.18:8089"
