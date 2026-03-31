#!/usr/bin/env python3
"""
云服务器部署脚本 - 通过 SSH 连接并部署
"""
import paramiko
import time
import sys

# 服务器配置
HOST = '180.76.244.18'
USERNAME = 'root'
PASSWORD = 'Lxhao1230.0'

def run_command(ssh, command, description=""):
    """执行命令并输出结果"""
    if description:
        print(f"\n>>> {description}")
    
    stdin, stdout, stderr = ssh.exec_command(command)
    
    # 读取输出
    output = stdout.read().decode('utf-8', errors='ignore')
    error = stderr.read().decode('utf-8', errors='ignore')
    
    exit_code = stdout.channel.recv_exit_status()
    
    if output.strip():
        print(output)
    if error.strip():
        print(f"[错误输出] {error}")
    
    return exit_code, output, error

def main():
    print("=" * 50)
    print("Auto Prompt 云服务器部署工具")
    print("=" * 50)
    
    # 连接服务器
    print(f"\n正在连接服务器 {HOST}...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        ssh.connect(HOST, username=USERNAME, password=PASSWORD, timeout=30)
        print("✓ 连接成功")
    except Exception as e:
        print(f"✗ 连接失败: {e}")
        return 1
    
    # 检查 Docker
    exit_code, output, _ = run_command(ssh, "which docker", "检查 Docker 安装")
    
    if exit_code != 0:
        print("\nDocker 未安装，正在安装...")
        run_command(ssh, "curl -fsSL https://get.docker.com | sh", "安装 Docker")
        run_command(ssh, "systemctl start docker && systemctl enable docker", "启动 Docker")
    else:
        print("✓ Docker 已安装")
    
    # 检查 Docker Compose
    exit_code, _, _ = run_command(ssh, "which docker-compose", "检查 Docker Compose")
    if exit_code != 0:
        run_command(ssh, "apt-get update && apt-get install -y docker-compose-plugin", "安装 Docker Compose")
    
    # 创建部署目录
    run_command(ssh, "mkdir -p /opt/auto-prompt && cd /opt/auto-prompt && pwd", "创建部署目录")
    
    # 检查本地文件
    print("\n>>> 检查部署文件...")
    sftp = ssh.open_sftp()
    
    # 检查是否已有代码
    try:
        sftp.stat('/opt/auto-prompt/docker-compose.prod.yml')
        print("✓ 部署文件已存在")
    except:
        print("✗ 部署文件不存在，请先上传项目文件")
        print("\n请执行以下命令上传文件：")
        print(f"  scp -r pyserver/ Dockerfile.python docker-compose.prod.yml nginx.conf deploy-cloud.sh {USERNAME}@{HOST}:/opt/auto-prompt/")
        sftp.close()
        ssh.close()
        return 1
    
    sftp.close()
    
    # 执行部署
    print("\n>>> 开始部署...")
    run_command(ssh, "cd /opt/auto-prompt && docker-compose -f docker-compose.prod.yml down 2>/dev/null || true", "停止旧服务")
    run_command(ssh, "cd /opt/auto-prompt && docker-compose -f docker-compose.prod.yml up -d --build", "构建并启动服务")
    
    # 等待服务启动
    print("\n>>> 等待服务启动...")
    time.sleep(10)
    
    # 检查服务状态
    print("\n>>> 检查服务状态...")
    exit_code, output, _ = run_command(ssh, "docker ps --format 'table {{.Names}}\\t{{.Status}}\\t{{.Ports}}'")
    
    if 'auto-prompt' in output and 'Up' in output:
        print("\n" + "=" * 50)
        print("✓ 部署成功!")
        print("=" * 50)
        print(f"\n访问地址: http://{HOST}:8089")
        print(f"API 文档: http://{HOST}:8089/docs")
        print("\n默认账户:")
        print("  用户名: admin")
        print("  密码: admin123")
        print("\n管理命令:")
        print("  查看日志: docker-compose -f /opt/auto-prompt/docker-compose.prod.yml logs -f")
        print("  停止服务: docker-compose -f /opt/auto-prompt/docker-compose.prod.yml down")
    else:
        print("\n" + "=" * 50)
        print("✗ 服务可能未正常启动")
        print("=" * 50)
        print("\n查看错误日志:")
        run_command(ssh, "cd /opt/auto-prompt && docker-compose -f docker-compose.prod.yml logs")
    
    ssh.close()
    return 0

if __name__ == '__main__':
    sys.exit(main())
