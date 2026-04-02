#!/usr/bin/env python3
"""
批量导入案例到案例库

从 case-collect 目录读取已生成的提示词文件，解析其中的要素规则，
并批量导入到 doc-extract-prompt-gen 的案例库中。
"""

import os
import re
import json
from datetime import datetime
from pathlib import Path

def get_case_library_path():
    """获取案例库文件路径"""
    # 查找 doc-extract-prompt-gen skill 目录
    home = os.path.expanduser('~')
    
    # 优先查找 .windsurf/skills 目录
    windsurf_skill = os.path.join(home, 'Desktop', 'projects', 'Auto-Prompt', '.windsurf', 'skills', 'doc-extract-prompt-gen')
    if os.path.exists(windsurf_skill):
        return os.path.join(windsurf_skill, 'case_library.json')
    
    # 备选：.claude/skills 目录
    claude_skill = os.path.join(home, '.claude', 'skills', 'doc-extract-prompt-gen')
    if os.path.exists(claude_skill):
        return os.path.join(claude_skill, 'case_library.json')
    
    raise FileNotFoundError("未找到 doc-extract-prompt-gen skill 目录")

def load_case_library():
    """加载案例库"""
    case_lib_path = get_case_library_path()
    
    if not os.path.exists(case_lib_path):
        print(f"[提示] 案例库文件不存在，将创建新文件: {case_lib_path}")
        return {"version": "1.0", "description": "文档要素提取提示词案例库 - 存储经过验证的优质提取规则模板", "cases": []}
    
    try:
        with open(case_lib_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"[错误] 案例库加载失败: {e}")
        return {"version": "1.0", "cases": []}

def save_case_library(case_lib):
    """保存案例库"""
    case_lib_path = get_case_library_path()
    
    try:
        with open(case_lib_path, 'w', encoding='utf-8') as f:
            json.dump(case_lib, f, ensure_ascii=False, indent=2)
        print(f"\n✓ 案例库已保存至: {case_lib_path}")
        return True
    except Exception as e:
        print(f"\n[错误] 案例库保存失败: {e}")
        return False

def parse_prompt_file(file_path):
    """解析提示词文件，提取要素规则"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 查找 "# 识别要素列表及规则" 部分
        factors_section = re.search(r'# 识别要素列表及规则\s*\n(.*?)(?=\n# |$)', content, re.DOTALL)
        if not factors_section:
            print(f"[警告] {os.path.basename(file_path)}: 未找到要素列表部分")
            return []
        
        factors_text = factors_section.group(1)
        
        # 解析每个要素
        # 格式: ## 1.要素名称\n提取规则，格式要求
        factor_pattern = r'## \d+\.([^\n]+)\n(.*?)(?=\n## |\n# |$)'
        matches = re.findall(factor_pattern, factors_text, re.DOTALL)
        
        factors = []
        for factor_name, rule_and_format in matches:
            factor_name = factor_name.strip()
            rule_and_format = rule_and_format.strip()
            
            # 分离提取规则和格式要求（通常用中文逗号或句号分隔）
            # 尝试找到最后一个逗号或句号作为分隔点
            parts = re.split(r'[，。](?=[^，。]*$)', rule_and_format, maxsplit=1)
            
            if len(parts) == 2:
                extraction_rule = parts[0].strip() + '。'
                format_requirement = parts[1].strip()
            else:
                extraction_rule = rule_and_format
                format_requirement = "保持原格式"
            
            factors.append({
                'factor_name': factor_name,
                'extraction_rule': extraction_rule,
                'format_requirement': format_requirement
            })
        
        return factors
    
    except Exception as e:
        print(f"[错误] 解析文件 {os.path.basename(file_path)} 失败: {e}")
        return []

def extract_material_name(filename):
    """从文件名提取材料名称"""
    # 移除扩展名和后缀
    name = filename.replace('--要素提取完整提示词.txt', '').replace('.txt', '')
    
    # 清理可能的路径前缀
    name = os.path.basename(name)
    
    # 材料名称标准化映射
    material_mapping = {
        '营业执照': '营业证照',
        '营业证照': '营业证照',
        '公司登记': '公司登记(备案)申请书',
        '公司登记备案申请书': '公司登记(备案)申请书',
        '公司登记(备案)申请书': '公司登记(备案)申请书',
        '股东决定': '股东决定',
        '董事决定': '董事决定',
        '章程修正案': '章程修正案',
        '市场主体住所': '市场主体住所(经营场所)使用(信息申报)承诺书',
        '承诺书': '市场主体住所(经营场所)使用(信息申报)承诺书',
    }
    
    # 尝试匹配材料名称
    for key, material_name in material_mapping.items():
        if key in name:
            return material_name
    
    # 如果没有匹配，返回原始名称
    return name if name else '通用'

def extract_tags_from_filename(filename):
    """从文件名提取标签"""
    # 移除扩展名和后缀
    name = filename.replace('--要素提取完整提示词.txt', '').replace('.txt', '')
    
    # 常见文档类型标签映射
    tag_mapping = {
        '营业执照': ['企业信息', '营业执照', '证照'],
        '营业证照': ['企业信息', '营业执照', '证照'],
        '公司登记': ['企业信息', '登记备案', '证照'],
        '身份证': ['个人信息', '身份证', '证照'],
        '合同': ['合同', '法律文件'],
        '发票': ['财务信息', '发票'],
    }
    
    for key, tags in tag_mapping.items():
        if key in name:
            return tags
    
    return ['其他']

def add_cases_to_library(case_lib, new_factors, source_file, source_type="imported"):
    """将新案例添加到案例库"""
    added_count = 0
    skipped_count = 0
    
    filename = os.path.basename(source_file)
    material_name = extract_material_name(filename)
    tags = extract_tags_from_filename(filename)
    
    for factor in new_factors:
        # 检查是否已存在相同的案例（基于材料名称+要素名称）
        exists = False
        for case in case_lib['cases']:
            if (case.get('material_name') == material_name and 
                case['factor_name'] == factor['factor_name']):
                # 如果规则相同，跳过
                if (case.get('extraction_rule') == factor['extraction_rule'] and
                    case.get('format_requirement') == factor['format_requirement']):
                    exists = True
                    skipped_count += 1
                    break
        
        if not exists:
            new_case = {
                "material_name": material_name,
                "factor_name": factor['factor_name'],
                "extract_desc": "",  # 从导入的文件无法获取，留空
                "rule_desc": "",     # 从导入的文件无法获取，留空
                "extraction_rule": factor['extraction_rule'],
                "format_requirement": factor['format_requirement'],
                "source": source_type,
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "tags": tags,
                "source_file": filename
            }
            case_lib['cases'].append(new_case)
            added_count += 1
            print(f"  ✓ 已添加: [{material_name}] {factor['factor_name']}")
    
    return added_count, skipped_count

def main():
    print("="*60)
    print("批量导入案例到案例库")
    print("="*60)
    
    # 1. 获取 case-collect 目录
    case_collect_dir = os.path.join(os.path.expanduser('~'), 'Desktop', 'projects', 'Auto-Prompt', 'case-collect')
    
    if not os.path.exists(case_collect_dir):
        print(f"\n[错误] case-collect 目录不存在: {case_collect_dir}")
        print("请创建该目录并放入要导入的提示词文件")
        return
    
    # 2. 查找所有 txt 文件
    txt_files = list(Path(case_collect_dir).glob('*.txt'))
    
    if not txt_files:
        print(f"\n[提示] case-collect 目录中没有找到 .txt 文件")
        print(f"目录: {case_collect_dir}")
        return
    
    print(f"\n✓ 发现 {len(txt_files)} 个提示词文件")
    
    # 3. 加载案例库
    case_lib = load_case_library()
    original_count = len(case_lib.get('cases', []))
    print(f"✓ 案例库已加载，当前有 {original_count} 个案例")
    
    # 4. 逐个解析并导入
    total_added = 0
    total_skipped = 0
    
    for txt_file in txt_files:
        print(f"\n[处理] {txt_file.name}")
        factors = parse_prompt_file(txt_file)
        
        if factors:
            print(f"  发现 {len(factors)} 个要素")
            added, skipped = add_cases_to_library(case_lib, factors, str(txt_file), source_type="imported")
            total_added += added
            total_skipped += skipped
        else:
            print(f"  未能解析出要素")
    
    # 5. 保存案例库
    if total_added > 0:
        if save_case_library(case_lib):
            print("\n" + "="*60)
            print(f"✓ 导入完成！")
            print(f"  新增案例: {total_added}")
            print(f"  跳过重复: {total_skipped}")
            print(f"  案例库总数: {len(case_lib['cases'])} (原 {original_count} + 新增 {total_added})")
            print("="*60)
    else:
        print("\n[提示] 没有新案例需要导入")

def import_from_files(txt_paths, merge=True):
    """从指定的 TXT 文件列表导入案例（供桌面端调用）。

    Args:
        txt_paths: list of absolute TXT file paths
        merge: True=增量合并, False=跳过重复但不覆盖

    Prints:
        RESULTS_JSON:{...}  on final line
    """
    case_lib = load_case_library()
    original_count = len(case_lib.get('cases', []))

    total_added = 0
    total_skipped = 0
    file_results = []

    for path in txt_paths:
        path = path.strip()
        if not os.path.exists(path):
            print(f"[错误] 文件不存在: {path}")
            file_results.append({"file": os.path.basename(path), "added": 0, "skipped": 0, "error": "文件不存在"})
            continue

        print(f"[处理] {os.path.basename(path)}")
        factors = parse_prompt_file(path)

        if factors:
            print(f"  发现 {len(factors)} 个要素")
            added, skipped = add_cases_to_library(case_lib, factors, path, source_type="imported")
            total_added += added
            total_skipped += skipped
            file_results.append({"file": os.path.basename(path), "added": added, "skipped": skipped})
        else:
            print(f"  未能解析出要素")
            file_results.append({"file": os.path.basename(path), "added": 0, "skipped": 0, "error": "未能解析出要素"})

    if total_added > 0:
        save_case_library(case_lib)

    result = {
        "status": "success",
        "imported": total_added,
        "skipped": total_skipped,
        "failed": sum(1 for r in file_results if r.get("error")),
        "total_cases": len(case_lib['cases']),
        "file_results": file_results,
    }
    print("RESULTS_JSON:" + json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='案例批量导入工具')
    parser.add_argument('--files', nargs='+', help='要导入的 TXT 文件路径列表')
    parser.add_argument('--merge', action='store_true', default=True, help='增量合并（默认）')
    args = parser.parse_args()

    if args.files:
        import_from_files(args.files, merge=args.merge)
    else:
        main()
