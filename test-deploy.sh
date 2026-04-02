#!/bin/bash
# 部署前测试脚本
# 使用方法: ./test-deploy.sh

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}==========================================${NC}"
echo -e "${GREEN}  部署前测试${NC}"
echo -e "${GREEN}==========================================${NC}"
echo ""

# 检查必要文件
echo -e "${YELLOW}[1/4] 检查必要文件...${NC}"

required_files=(
    "Dockerfile"
    "docker-compose.prod.yml"
    "nginx.conf"
    "package.json"
    "src/main.js"
    "pyserver/app/main.py"
    "pyserver/requirements.txt"
)

for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        echo -e "${GREEN}✓ $file${NC}"
    else
        echo -e "${RED}✗ $file (缺失)${NC}"
        exit 1
    fi
done

# 检查 Docker 配置
echo -e "${YELLOW}[2/4] 检查 Docker 配置...${NC}"

if command -v docker &> /dev/null; then
    echo -e "${GREEN}✓ Docker 已安装${NC}"
else
    echo -e "${RED}✗ Docker 未安装${NC}"
    exit 1
fi

if command -v docker-compose &> /dev/null; then
    echo -e "${GREEN}✓ Docker Compose 已安装${NC}"
else
    echo -e "${RED}✗ Docker Compose 未安装${NC}"
    exit 1
fi

# 检查端口配置
echo -e "${YELLOW}[3/4] 检查端口配置...${NC}"

if grep -q "8089:80" docker-compose.prod.yml; then
    echo -e "${GREEN}✓ 端口 8089 配置正确${NC}"
else
    echo -e "${RED}✗ 端口配置错误${NC}"
    exit 1
fi

if grep -q "192.168.204.126" nginx.conf; then
    echo -e "${GREEN}✓ 服务器 IP 配置正确${NC}"
else
    echo -e "${RED}✗ 服务器 IP 配置错误${NC}"
    exit 1
fi

# 测试本地构建
echo -e "${YELLOW}[4/4] 测试本地构建...${NC}"

echo "开始构建测试..."
if docker-compose -f docker-compose.prod.yml build --no-cache; then
    echo -e "${GREEN}✓ 构建测试成功${NC}"
    
    # 清理测试镜像
    docker-compose -f docker-compose.prod.yml down
    docker system prune -f
else
    echo -e "${RED}✗ 构建测试失败${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}==========================================${NC}"
echo -e "${GREEN}  所有测试通过！可以开始部署${NC}"
echo -e "${GREEN}==========================================${NC}"
echo ""
echo -e "${YELLOW}下一步:${NC}"
echo "1. 确保可以 SSH 连接到 192.168.204.126"
echo "2. 运行部署脚本: ./deploy-production.sh"
echo ""
echo -e "${BLUE}部署完成后访问地址:${NC}"
echo "  http://192.168.204.126:8089"
