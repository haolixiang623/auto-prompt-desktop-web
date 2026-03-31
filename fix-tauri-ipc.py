#!/usr/bin/env python3
"""修复 Tauri IPC 定义"""
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('180.76.244.18', username='root', password='Lxhao1230.0', timeout=30)

print('修复 Tauri IPC 全局定义...')
stdin, stdout, stderr = ssh.exec_command('''
# 在主入口文件中添加 Tauri IPC 定义
cp /opt/auto-prompt/src/main.js /opt/auto-prompt/src/main.js.bak

cat > /opt/auto-prompt/src/main.js << 'EOF'
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import './style.css'

// 为浏览器环境模拟 Tauri IPC
if (!window.__TAURI_IPC__) {
  window.__TAURI_IPC__ = async function(command, args) {
    console.log('Mock Tauri IPC call:', command, args)
    // 这里可以返回模拟数据或抛出错误
    throw new Error(`Tauri IPC command "${command}" is not available in browser environment`)
  }
}

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

echo "main.js 已更新"
''', timeout=60)

output = stdout.read().decode()
print(output)

print('\n检查是否还有其他地方使用 __TAURI_IPC__...')
stdin, stdout, stderr = ssh.exec_command('''
grep -r "__TAURI_IPC__" /opt/auto-prompt/src/ --exclude="main.js"
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
