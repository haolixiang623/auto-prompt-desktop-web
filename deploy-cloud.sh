#!/bin/bash
# 云服务器部署脚本 - Auto Prompt Python 后端
# 使用方法: ./deploy-cloud.sh

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}==========================================${NC}"
echo -e "${GREEN}  Auto Prompt 云服务器部署脚本${NC}"
echo -e "${GREEN}==========================================${NC}"
echo ""

# 检查 Docker 是否安装
if ! command -v docker &> /dev/null; then
    echo -e "${RED}错误: Docker 未安装${NC}"
    echo "请先安装 Docker:"
    echo "  curl -fsSL https://get.docker.com | sh"
    exit 1
fi

# 检查 Docker Compose 是否安装
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}错误: Docker Compose 未安装${NC}"
    echo "请先安装 Docker Compose"
    exit 1
fi

echo -e "${YELLOW}[1/6] 检查环境...${NC}"
docker --version
docker-compose --version

echo -e "${YELLOW}[2/6] 创建必要的目录...${NC}"
mkdir -p logs/nginx
mkdir -p data

echo -e "${YELLOW}[3/6] 停止旧服务...${NC}"
docker-compose -f docker-compose.prod.yml down 2>/dev/null || true

echo -e "${YELLOW}[4/6] 拉取最新代码（可选）...${NC}"
# git pull origin main 2>/dev/null || echo "跳过 git pull"

echo -e "${YELLOW}[5/6] 构建并启动服务...${NC}"
docker-compose -f docker-compose.prod.yml up -d --build

echo -e "${YELLOW}[6/6] 等待服务启动...${NC}"
sleep 10

# 检查服务状态
echo ""
echo -e "${GREEN}==========================================${NC}"
echo -e "${GREEN}  部署状态检查${NC}"
echo -e "${GREEN}==========================================${NC}"

if docker-compose -f docker-compose.prod.yml ps | grep -q "Up"; then
    echo -e "${GREEN}✓ 服务运行正常${NC}"
    echo ""
    echo "访问地址:"
    echo "  应用: http://180.76.244.18:8089"
    echo "  API文档: http://180.76.244.18:8089/docs"
    echo ""
    echo "管理命令:"
    echo "  查看日志: docker-compose -f docker-compose.prod.yml logs -f"
    echo "  停止服务: docker-compose -f docker-compose.prod.yml down"
    echo "  重启服务: docker-compose -f docker-compose.prod.yml restart"
    echo ""
    echo -e "${YELLOW}默认账户:${NC}"
    echo "  用户名: admin"
    echo "  密码: admin123"
    echo -e "${RED}  请及时修改默认密码！${NC}"
else
    echo -e "${RED}✗ 服务启动失败${NC}"
    echo "查看日志:"
    docker-compose -f docker-compose.prod.yml logs
    exit 1
fi
