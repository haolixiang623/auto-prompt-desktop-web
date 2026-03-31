# 云服务器部署指南

## 服务器信息
- **IP**: 180.76.244.18
- **端口**: 8089
- **部署方式**: Docker + Nginx 反向代理

## 部署步骤

### 1. 连接服务器

```bash
ssh root@180.76.244.18
# 密码: Lxhao1230.0
```

### 2. 安装 Docker（如未安装）

```bash
# 安装 Docker
curl -fsSL https://get.docker.com | sh

# 安装 Docker Compose
apt-get update
apt-get install -y docker-compose-plugin

# 启动 Docker
systemctl start docker
systemctl enable docker
```

### 3. 上传项目文件

在本地执行：
```bash
# 使用 scp 上传项目文件
scp -r pyserver/ root@180.76.244.18:/opt/auto-prompt/
scp Dockerfile.python root@180.76.244.18:/opt/auto-prompt/
scp docker-compose.prod.yml root@180.76.244.18:/opt/auto-prompt/
scp nginx.conf root@180.76.244.18:/opt/auto-prompt/
scp deploy-cloud.sh root@180.76.244.18:/opt/auto-prompt/

# 上传 skills 目录
scp -r skills/ root@180.76.244.18:/opt/auto-prompt/
```

或在服务器上克隆项目：
```bash
cd /opt
git clone <你的仓库地址> auto-prompt
cd auto-prompt
```

### 4. 执行部署

在服务器上执行：
```bash
cd /opt/auto-prompt

# 给脚本执行权限
chmod +x deploy-cloud.sh

# 执行部署
./deploy-cloud.sh
```

### 5. 验证部署

```bash
# 检查容器状态
docker ps

# 查看日志
docker-compose -f docker-compose.prod.yml logs -f
```

## 访问地址

- **应用**: http://180.76.244.18:8089
- **API 文档**: http://180.76.244.18:8089/docs
- **健康检查**: http://180.76.244.18:8089/api/health

## 默认账户

- **用户名**: `admin`
- **密码**: `admin123`

**⚠️ 请及时修改默认密码！**

## 管理命令

```bash
cd /opt/auto-prompt

# 查看日志
docker-compose -f docker-compose.prod.yml logs -f

# 停止服务
docker-compose -f docker-compose.prod.yml down

# 重启服务
docker-compose -f docker-compose.prod.yml restart

# 更新部署（重新构建）
docker-compose -f docker-compose.prod.yml up -d --build

# 查看服务状态
docker-compose -f docker-compose.prod.yml ps

# 进入容器调试
docker exec -it auto-prompt-py bash
```

## 防火墙设置

如果无法访问，请检查防火墙：

```bash
# 查看防火墙状态
ufw status

# 允许 8089 端口
ufw allow 8089/tcp

# 或者如果是阿里云/腾讯云，需要在安全组中开放 8089 端口
```

## 数据备份

数据存储在 Docker volume `app-data` 中，建议定期备份：

```bash
# 备份数据
docker run --rm -v auto-prompt_app-data:/data -v /backup:/backup alpine tar czf /backup/data-backup-$(date +%Y%m%d).tar.gz -C /data .

# 恢复数据
docker run --rm -v auto-prompt_app-data:/data -v /backup:/backup alpine sh -c "cd /data && tar xzf /backup/data-backup-YYYYMMDD.tar.gz"
```

## 故障排查

### 1. 服务无法启动
```bash
# 查看详细日志
docker-compose -f docker-compose.prod.yml logs app

# 检查端口占用
netstat -tlnp | grep 8089
```

### 2. Nginx 502 错误
```bash
# 检查后端服务是否正常
docker-compose -f docker-compose.prod.yml ps

# 检查 Nginx 配置
nginx -t
```

### 3. 内存不足
```bash
# 查看内存使用
free -h

# 清理无用镜像
docker system prune -a
```
