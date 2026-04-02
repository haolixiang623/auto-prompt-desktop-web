---
name: factor-json-generator
description: 自动为每个材料目录生成符合导入规范的要素JSON文件（含 carriername、factors、promptGroups）。
---

# 要素信息录入JSON生成器 v2

## 核心功能

1. **读取要素定义**：从 `factors.xlsx` 读取材料名称、要素名称、要素用途、要素类型
2. **提取识别规则**：从材料目录下的提示词TXT文件中提取各要素的识别提示词
3. **生成导入JSON**：为每个材料生成包含 `carriername`、`factors`、`promptGroups` 的完整导入结构
4. **智能分组**：根据TXT文件数量自动选择分组策略

## 输出格式（符合导入规范）

```json
{
  "carriername": "营业执照",
  "factors": [
    {
      "factorname": "企业名称",
      "factortype": "1",
      "factor_prompt": "请识别营业执照中的企业名称（全称）",
      "factoruse": "公司的完整法定名称",
      "ordernum": 1,
      "remark": "",
      "is_usermsg": "0",
      "isrecollect": "0",
      "factor_trans": ""
    }
  ],
  "promptGroups": [
    {
      "groupname": "分组1",
      "grouptype": "2",
      "ordernum": 1,
      "prompt_template": "...",
      "modelguid": "",
      "factors": ["企业名称", "统一社会信用代码", "法定代表人", "注册资本"]
    },
    {
      "groupname": "分组2",
      "grouptype": "2",
      "ordernum": 2,
      "prompt_template": "...",
      "modelguid": "",
      "factors": ["营业期限", "经营范围"]
    }
  ]
}
```

## 分组策略

| 场景 | 策略 |
|------|------|
| 材料目录有**多个**提示词TXT | 每个TXT对应一个 promptGroup，组内要素 = 该TXT中出现的要素 |
| 材料目录只有**一个**提示词TXT | 按 `--group-size N`（默认4）将所有要素平分为多组 |
| 材料目录**无**提示词TXT | 仅生成 factors，不生成 promptGroups（系统自动归入默认组合） |

## 目录结构要求

```
材料集/
├── factors.xlsx                     # 要素定义文件（必需）
├── 营业证照/
│   ├── 营业证照--要素提取完整提示词.txt   # 单TXT → 按group-size分组
│   └── 营业证照--要素信息录入.json        # 输出
├── 公司登记备案申请书/
│   ├── 公司登记备案申请书--基本信息提示词.txt   # 多TXT → 每文件一组
│   ├── 公司登记备案申请书--变更信息提示词.txt
│   └── 公司登记备案申请书--要素信息录入.json
└── ...
```

## factors.xlsx 格式

| 材料名称（A列） | 要素名称（B列） | 要素用途（C列） | 要素类型（D列，可选） |
|---------|---------|---------|---------|
| 营业证照 | 统一社会信用代码 | 企业的唯一识别码 | 1 |
| 营业证照 | 企业名称 | 公司的完整法定名称 | 1 |

> D列要素类型：`1`=文本（默认），`2`=图片

## 提示词TXT格式要求

```
（主提示词内容，会被提取为 prompt_template）

# 识别要素列表及规则
## 1.统一社会信用代码
在文档中查找由18位字母和数字组成的字符串...

## 2.企业名称
提取包含完整法定名称的文本...
```

> 支持 `## 1.要素名称` 和 `## 1、要素名称` 两种编号格式

## 使用方法

```bash
# 基础用法（默认每组4个要素）
python3 generate_factor_json.py 材料集/

# 指定每组要素数
python3 generate_factor_json.py 材料集/ --group-size 6
```

## 核心特性

- ✅ 输出符合标准导入规范（carriername + factors + promptGroups）
- ✅ 多TXT文件 → 每文件对应一个 promptGroup
- ✅ 单TXT文件 → 按 group-size 自动平分分组
- ✅ 自动提取 prompt_template（主提示词内容）
- ✅ 支持 Excel D列指定要素类型
- ✅ 输出结构化 RESULTS_JSON 供程序解析

## 注意事项

- 要素名称必须在 Excel 和 TXT 中完全一致（含全角/半角符号）
- 生成的JSON文件会覆盖同名文件
- `promptGroups[].factors` 中的名称需在 `factors` 数组中存在（系统校验）
