#!/usr/bin/env python3
"""彻底移除 Tauri 相关代码"""
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('180.76.244.18', username='root', password='Lxhao1230.0', timeout=30)

print('移除 Tauri 相关依赖和配置...')
stdin, stdout, stderr = ssh.exec_command('''
cd /opt/auto-prompt

# 1. 移除 Tauri 依赖
echo "移除 package.json 中的 Tauri 依赖..."
cp package.json package.json.bak
cat package.json | jq 'del(.dependencies["@tauri-apps/api"]) | del(.devDependencies["@tauri-apps/cli"])' > package.json.tmp
mv package.json.tmp package.json

# 2. 移除 Tauri 配置
echo "移除 vite.config.js 中的 Tauri 配置..."
cp vite.config.js vite.config.js.bak
cat > vite.config.js << 'EOF'
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

# 3. 清理 main.js，移除 Tauri IPC
echo "清理 main.js..."
cat > src/main.js << 'EOF'
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import './style.css'

console.log('Main.js loading...')

const app = createApp(App)

app.use(createPinia())
app.use(router)

app.config.errorHandler = (err, instance, info) => {
  console.error('Vue error:', err, info)
}

console.log('Mounting app...')
app.mount('#app')
console.log('App mounted!')
EOF

# 4. 移除 Tauri 相关目录
echo "移除 Tauri 相关文件..."
rm -rf src/tauri
rm -f src-tauri 2>/dev/null

echo "Tauri 相关代码已移除"
''', timeout=120)

output = stdout.read().decode()
print(output)

print('\n重新安装依赖并构建...')
stdin, stdout, stderr = ssh.exec_command('''
cd /opt/auto-prompt

# 重新安装依赖（不包含 Tauri）
npm ci

# 重新构建
npm run build
''', timeout=300)

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
