# 材料分类提示词自动优化工具 Skill

## 核心特性

- ✅ 自动读取材料类别定义
- ✅ 智能两步分类（信息提取 + 附件归集）
- ✅ AI 迭代优化提示词直至达标
- ✅ 直接覆盖原模板文件，仅保留最新版本
- ✅ 自动建立分类目录结构
- ✅ 自动执行文件归集，无需人工确认

## 快速开始

### 1. 准备目录结构

```
分类材料集/
├── factors.csv / factors.xlsx       # 材料类别定义（第一列为材料名称）
├── 待分类材料/                      # 待分类的附件图片
│   ├── 材料1_2 公司登记申请书1.jpg
│   └── ...
├── 分类信息提取提示词模板.txt        # 步骤1模板（自动优化）
└── 分类附件归集提示词模板.txt        # 步骤2模板（自动优化）
```

### 2. 运行脚本

```bash
export DASHSCOPE_API_KEY='your-api-key'

# 使用默认目录（Auto-Prompt/分类材料集/）
python3 .windsurf/skills/material-classifier/classify_materials.py

# 指定工作目录
python3 .windsurf/skills/material-classifier/classify_materials.py /path/to/分类材料集

# 指定最大优化轮次（默认3轮）
python3 .windsurf/skills/material-classifier/classify_materials.py /path/to/分类材料集 5
```

### 3. 查看结果

- **优化后的提示词**：直接覆盖原模板文件（`分类信息提取提示词模板.txt` 和 `分类附件归集提示词模板.txt`）
- **归集报告**：`分类材料集/classification_report.json`
- **已分类附件**：`分类材料集/已分类材料/<材料名称>/`

## 工作流程

1. **读取材料类别**：从 `factors.csv/xlsx` 第一列去重获取材料名称
2. **建立目录**：自动在 `已分类材料/` 下创建各材料子目录
3. **步骤1**：Qwen 分析所有附件图片，识别每张属于哪个材料类别
4. **步骤2**：根据步骤1结果生成归集方案（含置信度、页组）
5. **质量评估**：检查分类完整性和准确性
6. **AI 优化**：未通过则调用 Qwen 优化提示词并直接覆盖原模板，进入下一轮
7. **文件归集**：自动复制文件到对应目录，无需人工确认

## 模板占位符

- `$(material_list)`：材料类别列表
- `$(classification_result)`：步骤1的分类结果（仅步骤2模板）

详细文档请查看 `skill.md`
