#!/usr/bin/env python3
"""检查并修复前后端连接问题"""
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('180.76.244.18', username='root', password='Lxhao1230.0', timeout=30)

print('检查后端API状态...')
stdin, stdout, stderr = ssh.exec_command('''
# 测试后端API
curl -s http://127.0.0.1:3000/api/health
echo ""
# 检查服务状态
systemctl status auto-prompt --no-pager -l
echo ""
# 查看服务日志
journalctl -u auto-prompt --no-pager -n 20
''', timeout=60)

output = stdout.read().decode()
error = stderr.read().decode()
print(output)
if error:
    print(f'错误: {error}')

print('\n检查前端配置...')
stdin, stdout, stderr = ssh.exec_command('''
# 检查前端是否配置了正确的API地址
grep -r "localhost\|127.0.0.1" /opt/auto-prompt/src/ 2>/dev/null || echo "未找到localhost配置"
echo ""
# 检查vite配置
cat /opt/auto-prompt/vite.config.js
''', timeout=60)

output = stdout.read().decode()
print(output)

print('\n修复前端配置...')
# 需要修改前端配置，使用相对路径而不是localhost
stdin, stdout, stderr = ssh.exec_command('''
# 备份原配置
cp /opt/auto-prompt/vite.config.js /opt/auto-prompt/vite.config.js.bak

# 更新配置文件
cat > /opt/auto-prompt/vite.config.js << 'EOF'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:3000',
        changeOrigin: true,
        secure: false,
      },
    },
  },
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
    rollupOptions: {
      output: {
        manualChunks: undefined,
      },
    },
  },
  base: './',
})
EOF

echo "配置已更新"
''', timeout=60)

output = stdout.read().decode()
print(output)

print('\n重新构建前端...')
stdin, stdout, stderr = ssh.exec_command('''
cd /opt/auto-prompt
npm run build
''', timeout=120)

output = stdout.read().decode()
error = stderr.read().decode()
print(output)
if error:
    print(f'错误: {error}')

print('\n重启服务...')
stdin, stdout, stderr = ssh.exec_command('systemctl restart auto-prompt && sleep 3 && systemctl status auto-prompt --no-pager', timeout=60)

output = stdout.read().decode()
print(output)

ssh.close()
