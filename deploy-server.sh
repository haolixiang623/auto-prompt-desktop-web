#!/bin/bash
# 服务器端部署脚本
set -e

cd /opt/auto-prompt

echo "=== 配置 Docker 镜像源 ==="
mkdir -p /etc/docker
cat > /etc/docker/daemon.json << 'EOF'
{
  "registry-mirrors": [
    "https://docker.mirrors.ustc.edu.cn",
    "https://hub-mirror.c.163.com",
    "https://mirror.baidubce.com"
  ]
}
EOF
systemctl restart docker
sleep 5

echo "=== 手动拉取基础镜像 ==="
docker pull docker.mirrors.ustc.edu.cn/library/node:20-bookworm-slim && docker tag docker.mirrors.ustc.edu.cn/library/node:20-bookworm-slim node:20-bookworm-slim || true
docker pull docker.mirrors.ustc.edu.cn/library/python:3.11-slim-bookworm && docker tag docker.mirrors.ustc.edu.cn/library/python:3.11-slim-bookworm python:3.11-slim-bookworm || true
docker pull docker.mirrors.ustc.edu.cn/library/nginx:alpine && docker tag docker.mirrors.ustc.edu.cn/library/nginx:alpine nginx:alpine || true

echo "=== 停止旧服务 ==="
docker-compose -f docker-compose.prod.yml down 2>/dev/null || true

echo "=== 构建并启动 ==="
export DOCKER_BUILDKIT=0
docker-compose -f docker-compose.prod.yml build --no-cache
docker-compose -f docker-compose.prod.yml up -d

echo "=== 等待启动 ==="
sleep 15

echo "=== 检查状态 ==="
docker ps

echo ""
echo "=== 部署完成 ==="
echo "访问: http://180.76.244.18:8089"
