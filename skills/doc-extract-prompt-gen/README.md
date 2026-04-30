# 文档要素提取提示词生成器 Skill

## 快速开始

### 1. 安装依赖
## 核心特性

- ✅ AI 智能分析图片内容
- ✅ 正式提示词库优先精确命中
- ✅ 自动生成精准提取规则
- ✅ 统一脚本，无需复制

## 快速开始

### 模式一：单材料模式

1. 准备工作目录（最简模式）：
   - `factors.csv` 或 `factors.xlsx`（要素名称、提取说明、规则说明）
   - 至少一张文档图片
   - `template.txt`（可选，不提供则使用默认模板）

2. 运行脚本（无需复制到工作目录）：
   ```bash
   export DASHSCOPE_API_KEY='your-key'
   python3 ~/.windsurf/skills/doc-extract-prompt-gen/generate_prompt.py /path/to/工作目录
   ```

**文件格式支持**：
- ✅ CSV 格式：`factors.csv`
- ✅ Excel 格式：`factors.xlsx` 或 `factors.xls`（推荐，更易编辑）
- 优先级：Excel (.xlsx) > Excel (.xls) > CSV (.csv)

**最简工作目录**：只需 2 个文件即可开始！
```
工作目录/
├── factors.xlsx    # 或 factors.csv
└── 文档图片.jpg
```

### 模式二：多材料批量模式（新增）

1. 准备父目录结构：
   ```
   材料集/
   ├── factors.xlsx             # 统一的要素定义（包含材料名称列）
   ├── 公司登记备案申请书/
   │   └── *.jpg
   └── 营业证照/
       └── *.jpg
   ```

2. 要素文件格式（增加材料名称列）：
   
   支持 CSV 或 Excel 格式，推荐使用 Excel 格式（更易编辑）
   
   | 材料名称 | 要素名称 | 要素提取说明 | 提取规则说明 |
   |---------|---------|------------|------------|
   | 营业证照 | 统一社会信用代码 | 企业的唯一识别码 | 18位字母数字组合 |
   | 营业证照 | 企业名称 | 公司的完整法定名称 | 包含公司类型后缀 |

3. 批量处理所有材料：
   ```bash
   export DASHSCOPE_API_KEY='your-key'
   python3 ~/.windsurf/skills/doc-extract-prompt-gen/batch_generate.py /path/to/材料集
   ```

4. 或单独处理某个材料：
   ```bash
   python3 ~/.windsurf/skills/doc-extract-prompt-gen/generate_prompt.py /path/to/材料集/营业证照 营业证照
   ```

## 输出
- 生成的提示词保存为：`<当前目录名>.txt`
- 如果有图片，会自动调用 Qwen 模型验证并打印结果

详细文档请查看 `skill.md`
