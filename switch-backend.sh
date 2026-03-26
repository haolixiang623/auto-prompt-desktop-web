#!/bin/bash
# 后端切换脚本 - 用于在 Rust 和 Python 后端之间切换

set -e

BACKEND_TYPE=${1:-"python"}  # 默认使用 Python 后端

if [ "$BACKEND_TYPE" != "rust" ] && [ "$BACKEND_TYPE" != "python" ]; then
    echo "用法: $0 [rust|python]"
    exit 1
fi

echo "=========================================="
echo "切换后端: $BACKEND_TYPE"
echo "=========================================="

# 备份数据
echo "[1/5] 备份数据..."
if [ -d "data" ]; then
    tar -czf "data-backup-$(date +%Y%m%d-%H%M%S).tar.gz" data/
fi

# 停止现有容器
echo "[2/5] 停止现有容器..."
docker-compose down 2>/dev/null || true

# 选择 Dockerfile
if [ "$BACKEND_TYPE" == "python" ]; then
    echo "[3/5] 切换到 Python 后端..."
    
    # 检查 Python 后端文件是否存在
    if [ ! -f "Dockerfile.python" ]; then
        echo "错误: Dockerfile.python 不存在"
        exit 1
    fi
    
    # 使用 Python 版本的 docker-compose
    if [ -f "docker-compose.python.yml" ]; then
        DOCKER_COMPOSE_FILE="docker-compose.python.yml"
    else
        # 创建临时 compose 文件
        cat > docker-compose.python.yml << 'EOF'
version: '3.8'
services:
  app:
    build:
      context: .
      dockerfile: Dockerfile.python
    container_name: auto-prompt-py
    ports:
      - "3000:3000"
    volumes:
      - app-data:/data
    restart: unless-stopped
volumes:
  app-data:
EOF
        DOCKER_COMPOSE_FILE="docker-compose.python.yml"
    fi
    
else
    echo "[3/5] 切换到 Rust 后端..."
    DOCKER_COMPOSE_FILE="docker-compose.yml"
fi

# 清理旧镜像
echo "[4/5] 清理旧镜像..."
docker-compose -f "$DOCKER_COMPOSE_FILE" down --rmi local 2>/dev/null || true

# 构建并启动
echo "[5/5] 构建并启动新后端..."
docker-compose -f "$DOCKER_COMPOSE_FILE" up -d --build

# 等待服务启动
sleep 3

# 检查服务状态
if docker-compose -f "$DOCKER_COMPOSE_FILE" ps | grep -q "Up"; then
    echo ""
    echo "=========================================="
    echo "✓ 后端切换成功!"
    echo "=========================================="
    echo "服务地址: http://localhost:3000"
    echo "API 文档: http://localhost:3000/docs"
    echo ""
    echo "查看日志:"
    echo "  docker-compose -f $DOCKER_COMPOSE_FILE logs -f"
    echo ""
    echo "停止服务:"
    echo "  docker-compose -f $DOCKER_COMPOSE_FILE down"
else
    echo ""
    echo "=========================================="
    echo "✗ 启动失败，查看日志:"
    echo "=========================================="
    docker-compose -f "$DOCKER_COMPOSE_FILE" logs
    exit 1
fi
