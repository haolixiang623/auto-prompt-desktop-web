# Auto Prompt 生产环境部署指南

本仓库只保留一条受支持的部署路径：

- `Dockerfile`
- `docker-compose.prod.yml`
- `nginx.conf`
- `deploy-production.sh`

## 服务器信息
- **IP地址**: 192.168.204.126
- **用户名**: root
- **密码**: Zwfw1b@2022
- **端口**: 8089

## 部署前准备

### 1. SSH 连接配置

#### 方法一：使用密码认证（临时）
```bash
# 安装 sshpass
brew install hudochenkov/sshpass/sshpass  # macOS
# 或
sudo apt-get install sshpass  # Ubuntu

# 测试连接
sshpass -p 'Zwfw1b@2022' ssh -o StrictHostKeyChecking=no root@192.168.204.126 'echo SSH连接成功'
```

#### 方法二：配置SSH密钥（推荐）
```bash
# 生成SSH密钥（如果还没有）
ssh-keygen -t rsa -b 4096 -C "deployment"

# 复制公钥到服务器
ssh-copy-id -i ~/.ssh/id_rsa.pub root@192.168.204.126

# 测试连接
ssh root@192.168.204.126 'echo SSH连接成功'
```

### 2. 本地环境检查
```bash
# 运行测试脚本
./test-deploy.sh
```

## 部署步骤

### 1. 自动部署
```bash
# 使用SSH密钥认证
./deploy-production.sh

# 或使用密码认证
sshpass -p 'Zwfw1b@2022' ./deploy-production.sh
```

### 2. 手动部署（可选）
如果自动部署失败，可以按以下步骤手动部署同一套生产 Docker 方案：

#### 步骤1：准备服务器环境
```bash
ssh root@192.168.204.126

# 在服务器上执行
# 安装Docker
curl -fsSL https://get.docker.com | sh
systemctl enable docker
systemctl start docker

# 安装Docker Compose
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# 创建部署目录
mkdir -p /opt/auto-prompt
mkdir -p /opt/auto-prompt/logs/nginx
mkdir -p /opt/auto-prompt/data

# 配置防火墙
firewall-cmd --permanent --add-port=8089/tcp
firewall-cmd --reload
```

#### 步骤2：上传代码
```bash
# 在本地执行
rsync -avz --exclude='.git' --exclude='node_modules' \
  src/ pyserver/ skills/ package*.json index.html vite.config.js \
  Dockerfile docker-compose.prod.yml nginx.conf \
  root@192.168.204.126:/opt/auto-prompt/
```

#### 步骤3：启动服务
```bash
ssh root@192.168.204.126

# 在服务器上执行
cd /opt/auto-prompt
docker-compose -f docker-compose.prod.yml up -d --build
```

## 验证部署

### 1. 检查服务状态
```bash
ssh root@192.168.204.126

# 在服务器上执行
cd /opt/auto-prompt
docker-compose -f docker-compose.prod.yml ps
```

### 2. 查看日志
```bash
ssh root@192.168.204.126

# 在服务器上执行
cd /opt/auto-prompt
docker-compose -f docker-compose.prod.yml logs -f
```

### 3. 健康检查
```bash
# 在本地执行
curl http://192.168.204.126:8089/api/health
```

### 4. 访问应用
- **应用地址**: http://192.168.204.126:8089
- **API文档**: http://192.168.204.126:8089/docs

## 默认账户
- **用户名**: admin
- **密码**: admin123
- **重要**: 首次登录后请立即修改默认密码！

## 常用管理命令

在服务器上执行以下命令：

```bash
cd /opt/auto-prompt

# 查看服务状态
docker-compose -f docker-compose.prod.yml ps

# 查看日志
docker-compose -f docker-compose.prod.yml logs -f

# 重启服务
docker-compose -f docker-compose.prod.yml restart

# 停止服务
docker-compose -f docker-compose.prod.yml down

# 更新代码后重新部署
docker-compose -f docker-compose.prod.yml up -d --build
```

## 故障排查

### 1. 服务无法启动
```bash
# 查看详细日志
docker-compose -f docker-compose.prod.yml logs

# 检查端口占用
netstat -tlnp | grep 8089

# 检查Docker状态
systemctl status docker
```

### 2. 无法访问应用
```bash
# 检查防火墙
firewall-cmd --list-ports

# 检查nginx配置
docker exec auto-prompt-nginx nginx -t

# 重新加载nginx
docker exec auto-prompt-nginx nginx -s reload
```

### 3. 数据持久化问题
```bash
# 检查数据卷
docker volume ls

# 备份数据
docker run --rm -v app-data:/data -v $(pwd):/backup alpine tar czf /backup/data-backup.tar.gz -C /data .
```

## 安全建议

1. **修改默认密码**: 首次登录后立即修改admin账户密码
2. **配置HTTPS**: 生产环境建议配置SSL证书
3. **限制访问**: 配置防火墙规则，只允许必要的IP访问
4. **定期备份**: 设置定期数据备份计划
5. **监控日志**: 定期检查应用和系统日志

## 更新部署

当需要更新应用时：

```bash
# 方法1：使用部署脚本
./deploy-production.sh

# 方法2：手动更新
ssh root@192.168.204.126
cd /opt/auto-prompt
docker-compose -f docker-compose.prod.yml up -d --build
```

## 回滚操作

如果新版本有问题，可以回滚到之前版本：

```bash
ssh root@192.168.204.126
cd /opt/auto-prompt

# 查看之前的镜像版本
docker images | grep auto-prompt

# 使用之前的镜像启动
docker-compose -f docker-compose.prod.yml down
# 编辑docker-compose.prod.yml，指定特定镜像版本
docker-compose -f docker-compose.prod.yml up -d
```
