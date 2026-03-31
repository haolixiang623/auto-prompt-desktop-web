#!/usr/bin/env python3
"""智能修复所有 Vue 文件中的 Tauri 引用"""
import paramiko
import re

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('180.76.244.18', username='root', password='Lxhao1230.0', timeout=30)

print('=== 智能修复所有 Vue 文件 ===')
stdin, stdout, stderr = ssh.exec_command('''
cd /opt/auto-prompt

echo "1. 从备份恢复原始文件..."
for file in src/views/*.vue; do
  if [ -f "${file}.bak" ]; then
    cp "${file}.bak" "$file"
    echo "恢复 $file"
  fi
done

echo ""
echo "2. 移除所有 Tauri 导入..."
for file in src/views/*.vue src/stores/*.js src/composables/*.js; do
  if [ -f "$file" ]; then
    # 移除所有 Tauri 相关导入
    sed -i '/import.*invoke.*from/d' "$file"
    sed -i '/import.*listen.*from/d' "$file"
    sed -i '/import.*@tauri-apps/d' "$file"
    sed -i '/import.*tauri/d' "$file"
    echo "清理 $file"
  fi
done

echo ""
echo "3. 将 invoke 调用替换为 apiClient.post..."
# 使用更精确的替换
for file in src/views/*.vue; do
  if [ -f "$file" ]; then
    # 替换 invoke('xxx', { ... }) 为 apiClient.post('/api/xxx', { ... })
    sed -i "s/await invoke('load_settings')/await apiClient.get('\\/api\\/settings')/g" "$file"
    sed -i "s/await invoke('select_directory')/await apiClient.post('\\/api\\/workspaces\\/select')/g" "$file"
    sed -i "s/invoke('select_directory')/apiClient.post('\\/api\\/workspaces\\/select')/g" "$file"
    sed -i "s/await invoke('read_factors'/await apiClient.get('\\/api\\/workspaces\\/factors'/g" "$file"
    sed -i "s/await invoke('get_materials'/await apiClient.get('\\/api\\/workspaces\\/materials'/g" "$file"
    sed -i "s/await invoke('generate_prompt'/await apiClient.post('\\/api\\/generate\\/prompt'/g" "$file"
    sed -i "s/await invoke('verify_extraction'/await apiClient.post('\\/api\\/generate\\/verify'/g" "$file"
    sed -i "s/await invoke('save_prompt_file'/await apiClient.post('\\/api\\/generate\\/save'/g" "$file"
    sed -i "s/await invoke('generate_factor_json'/await apiClient.post('\\/api\\/generate\\/factor-json'/g" "$file"
    sed -i "s/await invoke('read_json_file'/await apiClient.get('\\/api\\/files\\/read'/g" "$file"
    sed -i "s/await invoke('open_in_finder'/await apiClient.post('\\/api\\/files\\/open'/g" "$file"
    sed -i "s/await invoke('get_llm_logs'/await apiClient.get('\\/api\\/logs'/g" "$file"
    sed -i "s/await invoke('clear_llm_logs'/await apiClient.delete('\\/api\\/logs'/g" "$file"
    sed -i "s/await invoke('check_environment'/await apiClient.get('\\/api\\/health'/g" "$file"
    sed -i "s/await invoke('test_api_key'/await apiClient.post('\\/api\\/settings\\/test-key'/g" "$file"
    sed -i "s/await invoke('save_settings'/await apiClient.put('\\/api\\/settings'/g" "$file"
    sed -i "s/await invoke('get_default_god_prompts'/await apiClient.get('\\/api\\/settings\\/default-prompts'/g" "$file"
    sed -i "s/await invoke('load_case_library'/await apiClient.get('\\/api\\/cases'/g" "$file"
    sed -i "s/await invoke('import_case_library_json'/await apiClient.post('\\/api\\/cases\\/import-json'/g" "$file"
    sed -i "s/await invoke('import_cases_from_txt'/await apiClient.post('\\/api\\/cases\\/import-txt'/g" "$file"
    sed -i "s/await invoke('delete_case'/await apiClient.delete('\\/api\\/cases'/g" "$file"
    sed -i "s/await invoke('load_review_rule_library'/await apiClient.get('\\/api\\/review-rules'/g" "$file"
    sed -i "s/await invoke('save_review_rule_library'/await apiClient.put('\\/api\\/review-rules'/g" "$file"
    sed -i "s/await invoke('clear_review_rule_library'/await apiClient.delete('\\/api\\/review-rules'/g" "$file"
    sed -i "s/await invoke('open_classified_dir'/await apiClient.post('\\/api\\/browse'/g" "$file"
  fi
done

echo ""
echo "4. 处理 listen 调用..."
for file in src/views/*.vue; do
  if [ -f "$file" ]; then
    # 将 listen 调用替换为 setInterval 轮询
    sed -i 's/await listen(.*skill-log.*//g' "$file"
    sed -i 's/unlistenSkillLog = await listen/unlistenSkillLog = null \/\/ Removed Tauri listen/g' "$file"
  fi
done

echo ""
echo "5. 重新构建..."
cd /opt/auto-prompt
npm run build 2>&1 | tail -30
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
print('🎉 智能修复完成！')
print('='*60)
