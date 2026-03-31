#!/usr/bin/env python3
"""添加全局 mock 来兼容 Tauri 代码"""
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('180.76.244.18', username='root', password='Lxhao1230.0', timeout=30)

print('=== 恢复原始文件并添加全局 mock ===')
stdin, stdout, stderr = ssh.exec_command('''
cd /opt/auto-prompt

echo "1. 从备份恢复所有原始 Vue 文件..."
for file in src/views/*.vue.bak; do
  if [ -f "$file" ]; then
    original="${file%.bak}"
    cp "$file" "$original"
    echo "恢复: $(basename $original)"
  fi
done

echo ""
echo "2. 恢复 stores 和 composables..."
for file in src/stores/*.js.bak src/composables/*.js.bak; do
  if [ -f "$file" ]; then
    original="${file%.bak}"
    cp "$file" "$original"
    echo "恢复: $(basename $original)"
  fi
done

echo ""
echo "3. 检查 main.js 并添加全局 mock..."
cat > /tmp/mock.js << 'EOF'
// Tauri API mock for web environment
if (typeof window !== 'undefined') {
  // Mock invoke function
  window.invoke = async function(command, args) {
    console.log('Mock invoke called:', command, args);
    
    // Map common commands to HTTP API
    const apiClient = {
      get: async (path) => {
        const res = await fetch('/api' + path);
        return res.json();
      },
      post: async (path, body) => {
        const res = await fetch('/api' + path, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body)
        });
        return res.json();
      }
    };
    
    // Map commands to API endpoints
    switch(command) {
      case 'load_settings':
        return apiClient.get('/settings');
      case 'select_directory':
        throw new Error('select_directory not available in web mode');
      case 'read_factors':
        return apiClient.get('/workspaces/factors?workDir=' + encodeURIComponent(args?.workDir || ''));
      case 'get_materials':
        return apiClient.get('/workspaces/materials?workDir=' + encodeURIComponent(args?.workDir || ''));
      case 'generate_prompt':
        return apiClient.post('/generate/prompt', args);
      case 'verify_extraction':
        return apiClient.post('/generate/verify', args);
      case 'save_prompt_file':
        return apiClient.post('/generate/save', args);
      case 'generate_factor_json':
        return apiClient.post('/generate/factor-json', args);
      case 'read_json_file':
        return apiClient.get('/files/read?path=' + encodeURIComponent(args?.path || ''));
      case 'open_in_finder':
        return apiClient.post('/files/open', args);
      case 'get_llm_logs':
        return apiClient.get('/logs');
      case 'clear_llm_logs':
        return apiClient.delete('/logs');
      case 'check_environment':
        return apiClient.get('/health');
      case 'test_api_key':
        return apiClient.post('/settings/test-key', args);
      case 'save_settings':
        return apiClient.put('/settings', args?.settings);
      case 'get_default_god_prompts':
        return apiClient.get('/settings/default-prompts');
      case 'load_case_library':
        return apiClient.get('/cases');
      case 'import_case_library_json':
        return apiClient.post('/cases/import-json', args);
      case 'import_cases_from_txt':
        return apiClient.post('/cases/import-txt', args);
      case 'delete_case':
        return apiClient.delete('/cases/' + encodeURIComponent(args?.caseId || ''));
      case 'load_review_rule_library':
        return apiClient.get('/review-rules');
      case 'save_review_rule_library':
        return apiClient.put('/review-rules', args?.rules || []);
      case 'clear_review_rule_library':
        return apiClient.delete('/review-rules');
      case 'open_classified_dir':
        return apiClient.post('/browse', { path: args?.workDir + '/已分类材料' });
      default:
        console.warn('Unknown invoke command:', command);
        throw new Error('Command ' + command + ' not implemented in web mock');
    }
  };
  
  // Mock listen function
  window.listen = async function(event, callback) {
    console.log('Mock listen called:', event);
    
    if (event === 'skill-log') {
      // Set up polling for logs
      const interval = setInterval(async () => {
        try {
          const res = await fetch('/api/logs');
          const data = await res.json();
          if (data && Array.isArray(data)) {
            data.forEach(log => callback({ payload: log }));
          }
        } catch(e) {}
      }, 1000);
      
      // Return unlisten function
      return () => clearInterval(interval);
    }
    
    // Return dummy unlisten function
    return () => {};
  };
}
EOF

# 将 mock 添加到 main.js 的开头
if ! grep -q "Tauri API mock" src/main.js; then
  cat /tmp/mock.js src/main.js > /tmp/main.js
  mv /tmp/main.js src/main.js
  echo "已添加全局 mock 到 main.js"
else
  echo "main.js 已包含 mock"
fi

echo ""
echo "4. 重新构建..."
npm run build 2>&1 | tail -15
''', timeout=180)

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

print('\n' + '='*60)
print('✅ 全局 mock 方案已部署！')
print('='*60)
print('\n这种方法的优势：')
print('  - 不需要修改每个 Vue 文件')
print('  - 保持原始代码结构')
print('  - 通过全局 mock 兼容 Tauri 调用')
print('\n现在请刷新浏览器测试！')
