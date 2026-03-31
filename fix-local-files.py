#!/usr/bin/env python3
"""批量修复所有本地 Tauri 引用并上传到服务器"""
import os
import re

# 所有需要修复的文件
files_to_fix = [
    'src/stores/skills.js',
    'src/views/CaseLibraryView.vue',
    'src/views/ClassifyView.vue',
    'src/views/FactorJsonView.vue',
    'src/views/ReviewRuleView.vue',
    'src/composables/useFileSystem.js',
    'src/composables/useSkills.js',
    'src/views/EnvCheckView.vue',
    'src/views/LlmLogView.vue',
    'src/views/ReviewRuleLibraryView.vue',
    'src/views/SettingsView.vue'
]

# 导入替换规则
import_replacements = {
    "import { invoke } from '@tauri-apps/api/tauri'": "import { apiClient } from '../services/apiClient.js'",
    "import { listen } from '@tauri-apps/api/event'": "// Tauri listen removed",
    "import { invoke } from '@tauri-apps/api/tauri';": "import { apiClient } from '../services/apiClient.js';",
    "import { listen } from '@tauri-apps/api/event';": "// Tauri listen removed;"
}

print('开始批量修复本地文件...')

for file_path in files_to_fix:
    full_path = os.path.join('d:\\projects\\auto-prompt-desktop-web', file_path)
    if not os.path.exists(full_path):
        print(f'跳过: {file_path} (文件不存在)')
        continue
    
    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 替换导入语句
        original_content = content
        for old_import, new_import in import_replacements.items():
            content = content.replace(old_import, new_import)
        
        # 如果内容有变化，保存
        if content != original_content:
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f'✓ 修复: {file_path}')
        else:
            print(f'- 无需修复: {file_path}')
            
    except Exception as e:
        print(f'✗ 错误 {file_path}: {e}')

print('\n所有本地文件修复完成！')
print('现在上传到服务器...')
