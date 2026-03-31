#!/usr/bin/env python3
"""修复登录响应数据结构问题"""
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('180.76.244.18', username='root', password='Lxhao1230.0', timeout=30)

print('修复登录服务处理响应数据结构...')
stdin, stdout, stderr = ssh.exec_command('''
# 备份原文件
cp /opt/auto-prompt/src/services/authService.js /opt/auto-prompt/src/services/authService.js.bak

# 修复登录函数以正确处理嵌套的响应数据
cat > /opt/auto-prompt/src/services/authService.js << 'EOF'
import { apiClient } from './apiClient.js'
import {
  authState,
  clearAuthState,
  getAuthToken,
  hasAuthSession,
  isAdminUser,
  setAuthSession,
  setCurrentUser
} from './authState.js'

let authLoadPromise = null

export { authState, hasAuthSession, isAdminUser }

export async function ensureAuthLoaded() {
  if (authState.ready) return authState
  if (authLoadPromise) return authLoadPromise

  const token = getAuthToken()
  if (!token) {
    authState.ready = true
    return authState
  }

  authState.loading = true
  authLoadPromise = apiClient.get('/api/auth/me')
    .then((response) => {
      // 处理嵌套的响应结构
      const user = response.data || response
      setCurrentUser(user)
      return authState
    })
    .catch(() => {
      clearAuthState()
      return authState
    })
    .finally(() => {
      authState.loading = false
      authState.ready = true
      authLoadPromise = null
    })

  return authLoadPromise
}

export async function login(username, password) {
  const response = await apiClient.post('/api/auth/login', { username, password })
  
  // 处理嵌套的响应结构
  const session = response.data || response
  
  console.log('Login response:', session)
  console.log('Token:', session.token)
  console.log('User:', session.user)
  
  setAuthSession(session)
  return session
}

export async function logout() {
  try {
    if (getAuthToken()) {
      await apiClient.post('/api/auth/logout', {})
    }
  } catch {
    // Ignore logout failures and clear client state anyway.
  }

  clearAuthState()
}
EOF

echo "authService.js 已更新"
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
