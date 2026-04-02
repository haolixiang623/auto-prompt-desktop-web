#!/bin/bash
# 简化版生产环境部署脚本
# 目标服务器: 192.168.204.126
# 使用方法: ./deploy-simple.sh

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 服务器配置
PROD_SERVER="192.168.204.126"
PROD_USER="root"
PROD_PASSWORD="Zwfw1b@2022"
APP_NAME="auto-prompt"
DEPLOY_PATH="/opt/$APP_NAME"

echo -e "${GREEN}==========================================${NC}"
echo -e "${GREEN}  Auto Prompt 生产环境部署脚本${NC}"
echo -e "${GREEN}  目标服务器: $PROD_SERVER${NC}"
echo -e "${GREEN}==========================================${NC}"
echo ""

# 检查必要工具
echo -e "${YELLOW}[1/5] 检查部署工具...${NC}"

if ! command -v sshpass &> /dev/null; then
    echo -e "${RED}错误: 需要安装 sshpass${NC}"
    echo "安装命令:"
    echo "  macOS: brew install hudochenkov/sshpass/sshpass"
    echo "  Ubuntu: sudo apt-get install sshpass"
    exit 1
fi

if ! command -v rsync &> /dev/null; then
    echo -e "${RED}错误: 需要安装 rsync${NC}"
    exit 1
fi

echo -e "${GREEN}✓ 部署工具检查通过${NC}"

# 测试SSH连接
echo -e "${YELLOW}[2/5] 测试SSH连接...${NC}"
if ! sshpass -p "$PROD_PASSWORD" ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no $PROD_USER@$PROD_SERVER "echo '连接成功'" 2>/dev/null; then
    echo -e "${RED}错误: 无法连接到生产服务器${NC}"
    echo "请检查服务器IP和密码是否正确"
    exit 1
fi
echo -e "${GREEN}✓ SSH连接成功${NC}"

# 准备服务器环境
echo -e "${YELLOW}[3/5] 准备服务器环境...${NC}"
sshpass -p "$PROD_PASSWORD" ssh -o StrictHostKeyChecking=no $PROD_USER@$PROD_SERVER << 'EOF'
set -e

# 检查并安装Docker
if ! command -v docker &> /dev/null; then
    echo "安装Docker..."
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker
    systemctl start docker
fi

# 检查并安装Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo "安装Docker Compose..."
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
fi

# 创建部署目录
mkdir -p /opt/auto-prompt
mkdir -p /opt/auto-prompt/logs/nginx
mkdir -p /opt/auto-prompt/data

# 配置防火墙
if command -v firewall-cmd &> /dev/null; then
    firewall-cmd --permanent --add-port=8089/tcp 2>/dev/null || true
    firewall-cmd --reload 2>/dev/null || true
elif command -v ufw &> /dev/null; then
    ufw allow 8089/tcp 2>/dev/null || true
fi

echo "服务器环境准备完成"
EOF
echo -e "${GREEN}✓ 服务器环境准备完成${NC}"

# 同步代码
echo -e "${YELLOW}[4/5] 同步代码到服务器...${NC}"

# 排除不需要的文件
EXCLUDE_ARGS="--exclude='.git' --exclude='node_modules' --exclude='.DS_Store' --exclude='*.log' --exclude='.pytest_cache' --exclude='.venv'"

# 使用rsync同步代码
sshpass -p "$PROD_PASSWORD" rsync -avz --delete $EXCLUDE_ARGS \
    src/ pyserver/ skills/ package*.json index.html vite.config.js postcss.config.js tailwind.config.js \
    Dockerfile docker-compose.prod.yml nginx.conf \
    材料集/ 分类材料集/ 生育津贴支付-材料集/ 2>/dev/null || true \
    $PROD_USER@$PROD_SERVER:/opt/auto-prompt/

echo -e "${GREEN}✓ 代码同步完成${NC}"

# 部署应用
echo -e "${YELLOW}[5/5] 启动应用...${NC}"
sshpass -p "$PROD_PASSWORD" ssh -o StrictHostKeyChecking=no $PROD_USER@$PROD_SERVER << 'EOF'
cd /opt/auto-prompt

# 停止旧服务
docker-compose -f docker-compose.prod.yml down 2>/dev/null || true

# 启动新服务
docker-compose -f docker-compose.prod.yml up -d --build

# 等待服务启动
echo "等待服务启动..."
sleep 15

# 检查服务状态
echo "检查服务状态..."
docker-compose -f docker-compose.prod.yml ps
EOF

echo -e "${GREEN}✓ 应用启动完成${NC}"

# 健康检查
echo -e "${YELLOW}执行健康检查...${NC}"
sleep 5

if curl -f -s --max-time 10 http://$PROD_SERVER:8089/api/health >/dev/null 2>&1; then
    echo -e "${GREEN}✓ 健康检查通过${NC}"
else
    echo -e "${YELLOW}⚠ 健康检查失败，服务可能仍在启动中${NC}"
    echo "等待30秒后再次检查..."
    sleep 30
    if curl -f -s --max-time 10 http://$PROD_SERVER:8089/api/health >/dev/null 2>&1; then
        echo -e "${GREEN}✓ 健康检查通过${NC}"
    else
        echo -e "${RED}✗ 健康检查失败${NC}"
        echo "请检查服务日志:"
        echo "sshpass -p '$PROD_PASSWORD' ssh $PROD_USER@$PROD_SERVER 'cd /opt/auto-prompt && docker-compose -f docker-compose.prod.yml logs'"
    fi
fi

# 部署完成
echo ""
echo -e "${GREEN}==========================================${NC}"
echo -e "${GREEN}  部署完成！${NC}"
echo -e "${GREEN}==========================================${NC}"
echo ""
echo -e "${BLUE}访问地址:${NC}"
echo "  应用: http://$PROD_SERVER:8089"
echo "  API文档: http://$PROD_SERVER:8089/docs"
echo ""
echo -e "${BLUE}管理命令:${NC}"
echo "  查看日志: sshpass -p '$PROD_PASSWORD' ssh $PROD_USER@$PROD_SERVER 'cd /opt/auto-prompt && docker-compose -f docker-compose.prod.yml logs -f'"
echo "  重启服务: sshpass -p '$PROD_PASSWORD' ssh $PROD_USER@$PROD_SERVER 'cd /opt/auto-prompt && docker-compose -f docker-compose.prod.yml restart'"
echo "  停止服务: sshpass -p '$PROD_PASSWORD' ssh $PROD_USER@$PROD_SERVER 'cd /opt/auto-prompt && docker-compose -f docker-compose.prod.yml down'"
echo ""
echo -e "${YELLOW}默认账户:${NC}"
echo "  用户名: admin"
echo "  密码: admin123"
echo -e "${RED}  请及时修改默认密码！${NC}"
echo ""
echo -e "${GREEN}部署成功完成！${NC}"
