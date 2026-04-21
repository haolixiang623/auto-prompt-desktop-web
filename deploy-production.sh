#!/bin/bash
# 生产环境部署脚本 - Auto Prompt
# 唯一受支持的部署入口：Dockerfile + docker-compose.prod.yml
# 目标服务器: 192.168.204.126
# 使用方法: ./deploy-production.sh

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 服务器配置
PROD_SERVER="192.168.204.126"
PROD_USER="root"
PROD_PORT="22"
APP_NAME="auto-prompt"
DEPLOY_PATH="/opt/$APP_NAME"

echo -e "${GREEN}==========================================${NC}"
echo -e "${GREEN}  Auto Prompt 生产环境部署脚本${NC}"
echo -e "${GREEN}  目标服务器: $PROD_SERVER${NC}"
echo -e "${GREEN}==========================================${NC}"
echo ""

# 检查本地环境
echo -e "${YELLOW}[1/8] 检查本地环境...${NC}"

# 检查 SSH 连接
echo "检查SSH连接..."
if command -v sshpass &> /dev/null; then
    # 使用sshpass进行密码认证
    if sshpass -p 'Zwfw1b@2022' ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no $PROD_USER@$PROD_SERVER "echo 'SSH连接成功'" 2>/dev/null; then
        SSH_METHOD="sshpass"
        echo -e "${GREEN}✓ SSH密码认证连接成功${NC}"
    else
        echo -e "${RED}错误: SSH密码认证失败${NC}"
        echo "请检查服务器IP和密码是否正确"
        exit 1
    fi
else
    # 使用密钥认证
    if ssh -o ConnectTimeout=5 -o BatchMode=yes $PROD_USER@$PROD_SERVER "echo 'SSH连接成功'" 2>/dev/null; then
        SSH_METHOD="ssh"
        echo -e "${GREEN}✓ SSH密钥认证连接成功${NC}"
    else
        echo -e "${RED}错误: 无法连接到生产服务器 $PROD_SERVER${NC}"
        echo "请选择以下方式之一:"
        echo "1. 配置SSH密钥: ssh-copy-id $PROD_USER@$PROD_SERVER"
        echo "2. 安装sshpass: brew install hudochenkov/sshpass/sshpass"
        echo "3. 检查服务器IP和密码是否正确"
        exit 1
    fi
fi

# 检查本地文件
if [ ! -f "docker-compose.prod.yml" ]; then
    echo -e "${RED}错误: 找不到 docker-compose.prod.yml 文件${NC}"
    exit 1
fi

if [ ! -f "Dockerfile" ]; then
    echo -e "${RED}错误: 找不到 Dockerfile 文件${NC}"
    exit 1
fi

echo -e "${GREEN}✓ 本地环境检查通过${NC}"

# 准备生产服务器环境
echo -e "${YELLOW}[2/8] 准备生产服务器环境...${NC}"

if [ "$SSH_METHOD" = "sshpass" ]; then
    sshpass -p 'Zwfw1b@2022' ssh $PROD_USER@$PROD_SERVER << 'EOF'
set -e

# 检查 Docker 是否安装
if ! command -v docker &> /dev/null; then
    echo "安装 Docker..."
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker
    systemctl start docker
    usermod -aG docker root
fi

# 检查 Docker Compose 是否安装
if ! command -v docker-compose &> /dev/null; then
    echo "安装 Docker Compose..."
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
fi

# 创建部署目录
mkdir -p /opt/auto-prompt
mkdir -p /opt/auto-prompt/logs/nginx
mkdir -p /opt/auto-prompt/data

# 设置防火墙规则（如果需要）
if command -v firewall-cmd &> /dev/null; then
    firewall-cmd --permanent --add-port=8089/tcp
    firewall-cmd --reload
elif command -v ufw &> /dev/null; then
    ufw allow 8089/tcp
fi

echo "生产服务器环境准备完成"
EOF
else
    ssh $PROD_USER@$PROD_SERVER << 'EOF'
set -e

# 检查 Docker 是否安装
if ! command -v docker &> /dev/null; then
    echo "安装 Docker..."
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker
    systemctl start docker
    usermod -aG docker root
fi

# 检查 Docker Compose 是否安装
if ! command -v docker-compose &> /dev/null; then
    echo "安装 Docker Compose..."
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
fi

# 创建部署目录
mkdir -p /opt/auto-prompt
mkdir -p /opt/auto-prompt/logs/nginx
mkdir -p /opt/auto-prompt/data

# 设置防火墙规则（如果需要）
if command -v firewall-cmd &> /dev/null; then
    firewall-cmd --permanent --add-port=8089/tcp
    firewall-cmd --reload
elif command -v ufw &> /dev/null; then
    ufw allow 8089/tcp
fi

echo "生产服务器环境准备完成"
EOF
fi

echo -e "${GREEN}✓ 生产服务器环境准备完成${NC}"

# 同步代码到生产服务器
echo -e "${YELLOW}[3/8] 同步代码到生产服务器...${NC}"

# 创建临时目录打包
TEMP_DIR="/tmp/auto-prompt-deploy-$(date +%s)"
mkdir -p $TEMP_DIR

# 复制必要文件
cp -r src $TEMP_DIR/
cp -r pyserver $TEMP_DIR/
cp -r skills $TEMP_DIR/
cp package.json package-lock.json $TEMP_DIR/
cp index.html vite.config.js postcss.config.js tailwind.config.js $TEMP_DIR/
cp Dockerfile docker-compose.prod.yml nginx.conf $TEMP_DIR/
cp -r 材料集 $TEMP_DIR/ 2>/dev/null || true
cp -r 分类材料集 $TEMP_DIR/ 2>/dev/null || true
cp -r 生育津贴支付-材料集 $TEMP_DIR/ 2>/dev/null || true

# 打包
cd $TEMP_DIR
tar -czf /tmp/auto-prompt-deploy.tar.gz .
cd - >/dev/null

# 传输到生产服务器
scp /tmp/auto-prompt-deploy.tar.gz $PROD_USER@$PROD_SERVER:/tmp/

# 在生产服务器解压
ssh $PROD_USER@$PROD_SERVER << EOF
cd /opt/auto-prompt
tar -xzf /tmp/auto-prompt-deploy.tar.gz -C .
rm /tmp/auto-prompt-deploy.tar.gz
chown -R root:root /opt/auto-prompt
EOF

# 清理临时文件
rm -rf $TEMP_DIR /tmp/auto-prompt-deploy.tar.gz

echo -e "${GREEN}✓ 代码同步完成${NC}"

# 停止旧服务
echo -e "${YELLOW}[4/8] 停止旧服务...${NC}"
ssh $PROD_USER@$PROD_SERVER "cd /opt/auto-prompt && docker-compose -f docker-compose.prod.yml down 2>/dev/null || true"
echo -e "${GREEN}✓ 旧服务已停止${NC}"

# 构建并启动新服务
echo -e "${YELLOW}[5/8] 构建并启动新服务...${NC}"
ssh $PROD_USER@$PROD_SERVER << EOF
cd /opt/auto-prompt
docker-compose -f docker-compose.prod.yml up -d --build
EOF

echo -e "${GREEN}✓ 服务构建完成${NC}"

# 等待服务启动
echo -e "${YELLOW}[6/8] 等待服务启动...${NC}"
sleep 15

# 检查服务状态
echo -e "${YELLOW}[7/8] 检查服务状态...${NC}"

SERVICE_STATUS=$(ssh $PROD_USER@$PROD_SERVER "cd /opt/auto-prompt && docker-compose -f docker-compose.prod.yml ps")

if echo "$SERVICE_STATUS" | grep -q "Up"; then
    echo -e "${GREEN}✓ 服务运行正常${NC}"
else
    echo -e "${RED}✗ 服务启动失败${NC}"
    echo "服务状态:"
    echo "$SERVICE_STATUS"
    echo ""
    echo "查看日志:"
    ssh $PROD_USER@$PROD_SERVER "cd /opt/auto-prompt && docker-compose -f docker-compose.prod.yml logs"
    exit 1
fi

# 健康检查
echo -e "${YELLOW}[8/8] 执行健康检查...${NC}"
if curl -f -s --max-time 10 http://$PROD_SERVER:8089/api/health >/dev/null 2>&1; then
    echo -e "${GREEN}✓ 健康检查通过${NC}"
else
    echo -e "${YELLOW}⚠ 健康检查失败，但服务可能仍在启动中${NC}"
fi

# 部署完成信息
echo ""
echo -e "${GREEN}==========================================${NC}"
echo -e "${GREEN}  部署完成！${NC}"
echo -e "${GREEN}==========================================${NC}"
echo ""
echo -e "${BLUE}访问地址:${NC}"
echo "  应用: http://$PROD_SERVER:8089"
echo "  API文档: http://$PROD_SERVER:8089/docs"
echo ""
echo -e "${BLUE}管理命令 (在生产服务器上执行):${NC}"
echo "  查看日志: cd /opt/auto-prompt && docker-compose -f docker-compose.prod.yml logs -f"
echo "  停止服务: cd /opt/auto-prompt && docker-compose -f docker-compose.prod.yml down"
echo "  重启服务: cd /opt/auto-prompt && docker-compose -f docker-compose.prod.yml restart"
echo "  查看状态: cd /opt/auto-prompt && docker-compose -f docker-compose.prod.yml ps"
echo ""
echo -e "${YELLOW}默认账户:${NC}"
echo "  用户名: admin"
echo "  密码: admin123"
echo -e "${RED}  请及时修改默认密码！${NC}"
echo ""
echo -e "${GREEN}部署成功完成！${NC}"
