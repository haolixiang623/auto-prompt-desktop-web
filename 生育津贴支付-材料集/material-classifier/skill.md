---
name: material-classifier
description: 材料分类提示词自动生成与优化工具，将无序附件自动分类归集到对应材料目录
---

# 材料分类提示词自动优化工具

此 Skill 使用 AI（Qwen）自动完成附件分类，并持续优化分类提示词，直到分类结果达到质量标准。

## 核心流程

1. **读取材料类别**：从 `factors.csv/xlsx` 第一列读取材料名称并去重
2. **建立目录结构**：在 `已分类材料/` 下为每种材料自动创建目录
3. **两步分类**：
   - **步骤1**：使用"分类信息提取提示词"让 Qwen 识别每个附件属于哪种材料
   - **步骤2**：使用"分类附件归集提示词"生成最终归集方案
4. **质量评估**：评估两步结果是否完整准确（所有附件都有分类、材料类型有效等）
5. **AI 优化**：若评估未通过，调用 Qwen 优化对应提示词模板，直接覆盖原模板文件
6. **自动归集**：自动执行文件归集，无需人工确认

## 目录结构要求

```
分类材料集/
├── factors.csv / factors.xlsx       # 材料类别定义文件（必需）
├── 待分类材料/                      # 待分类的附件图片（必需）
│   ├── 材料1_2 公司登记(备案)申请书1.jpg
│   ├── 材料1_3 公司登记(备案)申请书2.jpg
│   └── ...
├── 已分类材料/                      # 自动创建，分类结果存放处
│   ├── 公司登记备案申请书/
│   └── 营业证照/
├── 分类信息提取提示词模板.txt        # 步骤1模板（自动优化并覆盖保存）
└── 分类附件归集提示词模板.txt        # 步骤2模板（自动优化并覆盖保存）
```

## factors 文件格式

| 材料名称 | 要素名称 | 要素提取说明 | 提取规则说明 |
|---------|---------|------------|------------|
| 公司登记备案申请书 | 企业变更的事项列表 | ... | ... |
| 营业证照 | 统一社会信用代码 | ... | ... |

**第一列**（材料名称）用于生成分类目录，去重后作为材料类别列表。

## 模板占位符说明

### 分类信息提取提示词模板
- `$(material_list)`：插入材料类别列表（`- 材料名称` 格式）

### 分类附件归集提示词模板
- `$(material_list)`：插入材料目录列表
- `$(classification_result)`：插入步骤1的分类提取结果

## 使用方法

### 1. 准备环境

```bash
pip install openai openpyxl
export DASHSCOPE_API_KEY='sk-93f0c5b35b9c4ab4a3949a4bc4de4fc2'
```

### 2. 运行脚本

```bash
# 使用默认目录（Auto-Prompt/分类材料集/）
python3 .windsurf/skills/material-classifier/classify_materials.py

# 指定工作目录
python3 .windsurf/skills/material-classifier/classify_materials.py /path/to/分类材料集

# 指定工作目录 + 最大优化轮次（默认3轮）
python3 .windsurf/skills/material-classifier/classify_materials.py /path/to/分类材料集 5
```

### 3. 查看结果

- **优化后的提示词**：直接覆盖原模板文件（`分类信息提取提示词模板.txt` 和 `分类附件归集提示词模板.txt`）
- **归集报告**：`分类材料集/classification_report.json`
- **已分类附件**：`分类材料集/已分类材料/<材料名称>/`

## 输出说明

### 步骤1输出（分类信息提取）

```json
{
  "attachments": [
    {
      "file_name": "材料1_2 公司登记(备案)申请书1.jpg",
      "material_type": "公司登记备案申请书",
      "key_info": "公司变更登记申请书，含法人签名",
      "reason": "文件标题为'公司登记(备案)申请书'，属于公司登记备案申请书类材料"
    }
  ]
}
```

### 步骤2输出（附件归集）

```json
{
  "classification_plan": [
    {
      "file_name": "材料1_2 公司登记(备案)申请书1.jpg",
      "target_folder": "公司登记备案申请书",
      "page_group": "group_1",
      "confidence": "high",
      "notes": "第1页"
    }
  ],
  "summary": {
    "total_files": 11,
    "classified_count": 11,
    "unclassified_count": 0,
    "folder_distribution": {"公司登记备案申请书": 5, "营业证照": 2}
  }
}
```
