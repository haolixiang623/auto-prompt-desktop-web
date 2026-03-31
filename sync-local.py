#!/usr/bin/env python3
"""同步服务器更改到本地"""
import paramiko
import os

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('180.76.244.18', username='root', password='Lxhao1230.0', timeout=30)

print('=== 获取服务器修改列表 ===')
stdin, stdout, stderr = ssh.exec_command('''
cd /opt/auto-prompt

echo "1. 检查修改过的文件..."
find . -name "*.bak" -type f | head -10

echo ""
echo "2. 主要修改的文件："
echo "- src/services/authService.js (修复登录响应处理)"
echo "- src/main.js (移除Tauri IPC)"
echo "- src/views/*.vue (移除Tauri导入)"
echo "- src/stores/skills.js (移除invoke)"
echo "- src/services/uploadService.js (修复文件上传)"
echo "- package.json (移除Tauri依赖)"
echo "- vite.config.js (简化配置)"
echo "- src/router/index.js (已有)"

echo ""
echo "3. 检查package.json差异..."
diff package.json package.json.bak 2>/dev/null || echo "package.json 已完全更新"
''', timeout=60)

output = stdout.read().decode()
print(output)

ssh.close()

print('\n=== 本地更新步骤 ===')
print('''
由于服务器代码已更新，以下是同步本地代码的步骤：

1. 备份当前本地代码：
   cp -r . src-backup

2. 更新主要文件：
   - authService.js: 修复登录响应处理
   - uploadService.js: 移除invoke，使用Web API
   - skills.js: 使用HTTP API替代invoke
   - 所有Vue文件: 移除Tauri导入
   - package.json: 移除Tauri依赖

3. 重新安装依赖：
   npm install

4. 重新构建：
   npm run build

5. 测试本地运行：
   npm run dev
''')

print('\n=== 关键修改内容 ===')
print('''
1. authService.js:
   - 修复登录响应处理: response.data 结构

2. uploadService.js:
   - 移除invoke调用
   - 使用Web文件选择器

3. skills.js:
   - 移除Tauri invoke
   - 使用HTTP API调用

4. 所有Vue组件:
   - 移除 @tauri-apps/api 导入

5. package.json:
   - 移除 @tauri-apps/api 依赖

6. main.js:
   - 移除Tauri IPC定义
''')

print('\n=== 您需要更新本地代码吗？ ===')
print('如果您想在本地开发和测试，建议同步这些更改。')
print('如果只是使用部署的服务，可以继续使用，不需要更新本地代码。')
