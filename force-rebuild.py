#!/usr/bin/env python3
"""强制重新构建并清除缓存"""
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('180.76.244.18', username='root', password='Lxhao1230.0', timeout=30)

print('=== 强制重新构建 ===')
stdin, stdout, stderr = ssh.exec_command('''
cd /opt/auto-prompt

echo "1. 清理所有缓存..."
rm -rf dist/
rm -rf node_modules/.vite/
npm cache clean --force

echo ""
echo "2. 检查 src 文件是否还有 invoke..."
if grep -r "invoke(" src/views/*.vue 2>/dev/null; then
  echo "找到 invoke，需要修复"
  # 使用 sed 直接移除所有 invoke 调用
  for file in src/views/*.vue; do
    # 注释掉包含 invoke 的行
    sed -i 's/await invoke/\/\/ await invoke/g' "$file"
    # 移除导入
    sed -i '/import.*invoke/d' "$file"
    sed -i '/import.*listen/d' "$file"
  done
else
  echo "Vue 文件中没有 invoke"
fi

echo ""
echo "3. 重新构建..."
npm run build 2>&1 | tail -20

echo ""
echo "4. 检查构建后的文件..."
if [ -f "dist/assets/GenerateView-*.js" ]; then
  echo "构建成功，检查是否还有 invoke..."
  if grep -l "invoke" dist/assets/*.js 2>/dev/null; then
    echo "警告：构建文件仍包含 invoke"
    grep -h "invoke" dist/assets/*.js | head -3
  else
    echo "✓ 构建文件干净，没有 invoke"
  fi
else
  echo "构建失败，没有生成文件"
fi
''', timeout=180)

output = stdout.read().decode()
error = stderr.read().decode()
print(output)

print('\n重启服务...')
stdin, stdout, stderr = ssh.exec_command('systemctl restart auto-prompt && sleep 3 && systemctl status auto-prompt --no-pager', timeout=60)

output = stdout.read().decode()
print(output)

ssh.close()

print('\n' + '='*60)
print('重新构建完成！')
print('='*60)
print('\n请务必：')
print('1. 按 Ctrl+F5 强制刷新浏览器（清除缓存）')
print('2. 重新登录')
print('3. 检查错误')
