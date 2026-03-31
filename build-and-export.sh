#!/bin/bash
# 本地构建并导出镜像，然后上传到服务器部署

set -e

echo "=== 本地构建镜像 ==="

# 构建前端
echo "[1/3] 构建前端..."
npm ci
npm run build

# 构建 Docker 镜像
echo "[2/3] 构建 Docker 镜像..."
docker build -f Dockerfile.python -t auto-prompt-app:latest .

# 导出镜像
echo "[3/3] 导出镜像..."
docker save auto-prompt-app:latest > auto-prompt-app.tar
docker save nginx:alpine > nginx-alpine.tar 2>/dev/null || echo "nginx:alpine 将在服务器上拉取"

echo ""
echo "=== 镜像导出完成 ==="
echo "文件大小:"
ls -lh *.tar
echo ""
echo "=== 上传到服务器 ==="
echo "执行以下命令上传:"
echo "  scp auto-prompt-app.tar root@180.76.244.18:/opt/auto-prompt/"
echo ""
echo "然后在服务器上执行:"
echo "  docker load < /opt/auto-prompt/auto-prompt-app.tar"
echo "  cd /opt/auto-prompt && docker-compose -f docker-compose.prod.yml up -d"
