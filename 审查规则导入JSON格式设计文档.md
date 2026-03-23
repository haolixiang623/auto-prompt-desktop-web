# 审查规则导入JSON格式设计文档

## 文档信息

| 项目 | 内容 |
|------|------|
| 文档版本 | V1.0 |
| 创建日期 | 2026-03-02 |
| 功能模块 | 审查模块 - 审查规则导入 |
| 相关表 | ai_keypoint, ai_rule |

---

## 一、功能概述

支持通过JSON文件批量导入审查要点及其审查规则到指定材料下。导入内容包括：

1. **审查要点信息**：要点名称、审查内容（LLM提示词）、通过/不通过原因模板等
2. **审查规则信息**：审查模式（LLM/规则对比/Groovy脚本）、多条件配置、前置规则等

> **数据关系**：一条审查要点（`ai_keypoint`）对应一条审查规则（`ai_rule`），两者共享同一主键（`rowguid` = `kpguid`）。

---

## 二、JSON结构总览

```json
{
  "materialname": "目标材料名称",
  "keypoints": [ ... ]
}
```

---

## 三、顶层字段说明

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `materialname` | string | 是 | - | 目标材料名称，审查要点将导入到该材料下。后端根据材料名称 + taskid 查询 `ai_task_material` 获取 `materialid` 等关联信息 |
| `keypoints` | array | 是 | - | 审查要点列表，至少包含1个要点对象 |

---

## 四、keypoints 审查要点字段说明

`keypoints` 数组中每个对象同时对应 `ai_keypoint` 表和 `ai_rule` 表各一条记录。

### 4.1 审查要点字段（→ ai_keypoint）

| 字段 | 类型 | 必填 | 默认值 | 对应数据库字段 | 说明 |
|------|------|------|--------|---------------|------|
| `kpname` | string | **是** | - | `ai_keypoint.kpname` | 审查要点名称。同一材料下建议唯一，导入时做唯一性校验 |
| `content` | string | 否 | `""` | `ai_keypoint.content` | 审查内容。当 `review_rule="1"`（LLM模式）时为大模型提示词；其他模式下为审查说明文本 |
| `nopassreason` | string | 否 | `""` | `ai_keypoint.nopassreason` | 审核不通过原因（兜底）。当 `review_rule="2"` 时，不通过原因主要由 `review_conditions` 中各组的 `groupFailReason` 提供，此字段作为兜底。支持 `$载体:要素$` 占位符格式 |
| `passreason` | string | 否 | `""` | `ai_keypoint.passreason` | 审核通过原因模板。支持 `$载体:要素$` 占位符格式 |
| `pointtype` | string | 否 | `""` | `ai_keypoint.pointtype` | 要点类型。`1`=实质审查，`2`=形式审查 |
| `tagname` | string | 否 | `""` | `ai_keypoint.tagname` | 标签名称（粗颗粒度分组名称） |
| `groupname` | string | 否 | `""` | `ai_keypoint.groupname` | 分组名称 |
| `remark` | string | 否 | `""` | `ai_keypoint.remark` | 填报说明 |
| `ordernum` | int | 否 | 按数组顺序自动递增 | `ai_keypoint.ordernum` | 排序号 |
| `is_enable` | int | 否 | `1` | `ai_keypoint.is_enable` | 是否启用。`0`=禁用，`1`=启用 |
| `exclude_situations` | string | 否 | `""` | `ai_keypoint.exclude_situations` | 排除情形表达式。当用户选择的情形满足此表达式时，该审查要点不生效 |
| `review_rule_text` | string | 否 | `""` | `ai_keypoint.review_rule_text` | 审查规则文本描述（人可读的规则说明） |

### 4.2 审查规则字段（→ ai_rule）

| 字段 | 类型 | 必填 | 默认值 | 对应数据库字段 | 说明 |
|------|------|------|--------|---------------|------|
| `review_rule` | string | **是** | - | `ai_rule.review_rule` | 审查模式。`1`=大模型(LLM)，`2`=规则对比（多条件），`3`=Groovy脚本 |
| `review_conditions` | object | 条件必填 | `null` | `ai_rule.review_conditions` | 多条件配置JSON。当 `review_rule="2"` 时**必填**，格式见第五节 |
| `review_rule_js` | string | 条件必填 | `""` | `ai_rule.review_rule_js` | Groovy脚本内容。当 `review_rule="3"` 时**必填** |
| `is_point` | string | 否 | `"0"` | `ai_rule.is_point` | 是否重点审查（重点复核）。`0`=否，`1`=是 |
| `is_contrast` | string | 否 | `"0"` | `ai_rule.is_contrast` | 是否对比。`0`=否，`1`=是 |
| `failedtemplate` | string | 否 | `""` | `ai_rule.failedtemplate` | 审核不通过意见模板 |
| `successtemplate` | string | 否 | `""` | `ai_rule.successtemplate` | 审核通过意见模板 |
| `pre_rule_enabled` | int | 否 | `0` | `ai_rule.pre_rule_enabled` | 是否启用前置规则。`0`=禁用，`1`=启用 |
| `pre_conditions` | object | 否 | `null` | `ai_rule.pre_conditions` | 前置规则条件配置JSON。当 `pre_rule_enabled=1` 时填写，格式与 `review_conditions` 相同 |

### 4.3 后端自动填充字段（无需导入）

以下字段由后端根据上下文自动生成，JSON中**无需**也**不应**包含：

**ai_keypoint 自动填充：**

| 字段 | 来源 | 说明 |
|------|------|------|
| `rowguid` | 系统生成UUID | 审查要点主键，同时作为 ai_rule 的 kpguid |
| `taskid` | 通过 materialname 查询 ai_task_material 获取 | 事项标识 |
| `materialid` | 通过 materialname 查询 ai_task_material 获取 | 所属材料标识 |
| `materialname` | 取自顶层 materialname | 材料名称（冗余字段） |
| `fileguid` | 查询该材料下最新的 ai_keypoint_file 记录 | 关联附件标识 |
| `tagno` | 自动递增（当前材料下最大值 + 1） | 标签号 |
| `fromtype` | 固定值 `"apply_material"` | 来源类型（申请材料） |
| `aitype` | 固定值 `"2"` | 审查类别（审批要点） |
| `operatedate` | 当前时间 | 操作时间 |
| `operateusername` | 当前登录用户 | 操作人 |
| `operateuserguid` | 当前登录用户GUID | 操作人标识 |

**ai_rule 自动填充：**

| 字段 | 来源 | 说明 |
|------|------|------|
| `rowguid` | 与 ai_keypoint.rowguid 相同 | 规则主键（= kpguid） |
| `kpguid` | 与 ai_keypoint.rowguid 相同 | 关联审查要点标识 |
| `taskid` | 同 ai_keypoint.taskid | 事项标识 |
| `rulename` | 取自 kpname | 规则名称 |
| `algorithmguid` | 固定值 `"LLM"` | 运算规则标识 |
| `aitype` | 固定值 `"2"` | 审查类别 |
| `is_manual` | 固定值 `0` | 非人工规则 |
| `is_enable` | 固定值 `1` | 默认启用 |
| `test_status` | 固定值 `0` | 初始未检测 |
| `ordernum` | 固定值 `0` | 排序号 |
| `connect_ai_factor` | 根据 review_conditions / content / review_rule_js 自动提取 | 关联要素GUID列表（逗号分隔） |
| `operatedate` | 当前时间 | 操作时间 |
| `operateusername` | 当前登录用户 | 操作人 |

---

## 五、review_conditions 多条件配置格式

当 `review_rule="2"`（规则对比模式）时，需要提供 `review_conditions` 字段。格式如下：

### 5.1 结构

```json
{
  "groups": [
    {
      "logicToNext": "AND",
      "groupFailReason": "自定义不通过原因",
      "conditions": [
        {
          "elementA": "$载体名称:要素名称$",
          "elementAType": "factor",
          "elementADisplay": "$载体名称:要素名称$",
          "operator": "eq",
          "dataType": "string",
          "elementB": "固定值或$载体:要素$",
          "elementBType": "value",
          "elementBDisplay": "固定值或$载体:要素$",
          "logicToNext": "AND",
          "stringReplacements": null,
          "delimiter": null,
          "arrayKeys": null
        }
      ]
    }
  ]
}
```

### 5.2 条件字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `elementA` | string | 是 | 要素A。`elementAType=factor` 时使用 `$载体:要素$` 格式（后端自动解析为GUID）；`elementAType=value` 时为固定值 |
| `elementAType` | string | 是 | 要素A类型。`factor`=要素引用，`value`=固定值，`variable`=系统变量 |
| `elementADisplay` | string | 否 | 要素A显示名称，导入时可与 `elementA` 相同 |
| `operator` | string | 是 | 运算符。支持 `eq`/`nq`/`gt`/`lt`/`ge`/`le`/`contains`/`notblank`/`blank`/`len_gt`/`len_lt`/`len_eq`/`regex` |
| `dataType` | string | 是 | 数据类型。`string`/`int`/`float`/`date`/`array` |
| `elementB` | string | 条件 | 要素B。`notblank`/`blank` 运算符时可为空 |
| `elementBType` | string | 条件 | 要素B类型。同 `elementAType` |
| `elementBDisplay` | string | 否 | 要素B显示名称 |
| `logicToNext` | string | 否 | 与下一条件的逻辑关系。`AND`/`OR`/`null`（最后一条为null） |
| `stringReplacements` | array | 否 | 字符串替换规则。`[{"old_value":"万元","new_value":""}]` |
| `delimiter` | string | 否 | 分隔符。配置后值按此字符拆分为数组比较 |
| `arrayKeys` | array | 否 | 对象数组Key过滤。`["name","code"]`，仅取指定字段比较 |

### 5.3 组字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `logicToNext` | string | 否 | 与下一组的逻辑关系。`AND`/`OR`/`null`（最后一组为null） |
| `groupFailReason` | string | **是** | 该组不通过时的原因描述，**必填**。支持 `$载体:要素$` 占位符，运行时替换为实际值。格式详见下方说明 |
| `conditions` | array | 是 | 条件列表，至少包含1个条件对象 |

#### groupFailReason 占位符格式

| 场景 | 格式 | 示例 |
|------|------|------|
| 要素 vs 固定值 | `载体:要素【$载体:要素$】应xxx固定值` | `营业执照:注册资本【$营业执照:注册资本$】应大于500万` |
| 要素 vs 要素 | `要素A【&$载体A:要素A$@】应xxx【&$载体B:要素B$@】` | `注册资本【&$营业执照:注册资本$@】应大于【&$申请表:最低注册资本$@】` |

> **说明**：
> - 运行时使用 `replaceByregex()` 方法替换 `$载体:要素$` 占位符为实际值
> - 双要素对比时，`&` 和 `@` 用于标记占位符边界，后端当普通字符保留，由第三方自行处理
> - 多组不通过时，返回所有不通过组的 `groupFailReason`，用换行符 `\n` 拼接

### 5.4 要素引用解析规则

`elementA` / `elementB` 中使用 `$载体名称:要素名称$` 格式引用要素时，后端按以下规则解析：

| 步骤 | 操作 | 说明 |
|------|------|------|
| 1 | 提取载体名称和要素名称 | 从 `$载体:要素$` 中解析出 `载体名称` 和 `要素名称` |
| 2 | 查询载体 | 在当前事项的 `ai_carrier` 表中按 `carriername` 查找载体，获取 `carrierguid` |
| 3 | 查询要素 | 在该载体下的 `ai_factor` 表中按 `factorname` 查找要素，获取 `rowguid`（即 factorguid） |
| 4 | 替换为GUID | 将 `elementA`/`elementB` 的值替换为要素的 `rowguid` |

> **注意**：`elementADisplay` / `elementBDisplay` 保持原始的 `$载体:要素$` 格式不变，用于前端展示。

#### 特殊载体说明

以下载体为系统内置，不需要在 `ai_carrier` 表中存在，导入时无需校验载体是否存在：

| 载体名称 | 说明 | 示例 |
|----------|------|------|
| 常规信息 | 系统变量（当前日期、当前时间等） | `$常规信息:当前日期$` |
| 法人信息 | 法人相关要素 | `$法人信息:企业名称$` |
| 自然人信息 | 自然人相关要素 | `$自然人信息:姓名$` |

> 当 `elementAType` 或 `elementBType` 为 `variable` 时，载体名称通常为上述特殊载体。

### 5.5 运算符-数据类型兼容矩阵

导入时需校验运算符与数据类型的兼容性：

| 运算符 | string | int | float | date | array |
|--------|:------:|:---:|:-----:|:----:|:-----:|
| eq | ✓ | ✓ | ✓ | ✓ | ✓(数组相等) |
| nq | ✓ | ✓ | ✓ | ✓ | ✗ |
| gt | ✓ | ✓ | ✓ | ✓ | ✗ |
| lt | ✓ | ✓ | ✓ | ✓ | ✗ |
| ge | ✓ | ✓ | ✓ | ✓ | ✗ |
| le | ✓ | ✓ | ✓ | ✓ | ✗ |
| contains | ✓ | ✗ | ✗ | ✗ | ✓(数组包含) |
| notblank | ✓ | ✓ | ✓ | ✓ | ✓ |
| blank | ✓ | ✓ | ✓ | ✓ | ✓ |
| len_gt | ✓ | ✗ | ✗ | ✗ | ✓ |
| len_lt | ✓ | ✗ | ✗ | ✗ | ✓ |
| len_eq | ✓ | ✗ | ✗ | ✗ | ✓ |
| regex | ✓ | ✗ | ✗ | ✗ | ✗ |

> **长度含义**：
> - `dataType=string`（未配置分隔符）：字符串字符长度
> - `dataType=string`（已配置分隔符）：拆分后数组元素个数
> - `dataType=array`：数组元素个数

### 5.6 分隔符约束规则

当条件配置了分隔符（`delimiter` 非空）时，拆分后值变为数组，**只允许**以下运算符：

```
eq / contains / len_gt / len_lt / len_eq / notblank / blank
```

导入时校验：若配置了 `delimiter` 且 `operator` 不在以上列表中，报错。

### 5.7 arrayKeys 适用条件

`arrayKeys` 仅在以下条件同时满足时有效：

```
dataType = "array"  且  operator = "eq" 或 "contains"
```

其他情况下即使配置了 `arrayKeys` 也会被忽略。

---

## 六、完整示例

### 6.1 规则对比模式（review_rule="2"）

```json
{
  "materialname": "营业执照",
  "keypoints": [
    {
      "kpname": "企业名称一致性检查",
      "content": "",
      "nopassreason": "",
      "passreason": "",
      "review_rule_text": "检查营业执照上的企业名称与申请表填写的企业名称是否一致",
      "review_rule": "2",
      "review_conditions": {
        "groups": [
          {
            "logicToNext": null,
            "groupFailReason": "营业执照:企业名称【&$营业执照:企业名称$@】应等于【&$申请表:企业名称$@】",
            "conditions": [
              {
                "elementA": "$营业执照:企业名称$",
                "elementAType": "factor",
                "elementADisplay": "$营业执照:企业名称$",
                "operator": "eq",
                "dataType": "string",
                "elementB": "$申请表:企业名称$",
                "elementBType": "factor",
                "elementBDisplay": "$申请表:企业名称$",
                "logicToNext": null,
                "stringReplacements": null,
                "delimiter": null,
                "arrayKeys": null
              }
            ]
          }
        ]
      },
      "is_point": "0",
      "is_contrast": "1",
      "pre_rule_enabled": 0,
      "pre_conditions": null
    },
    {
      "kpname": "注册资本数值校验",
      "content": "",
      "review_rule_text": "检查营业执照上的注册资本是否大于等于申请表中的最低注册资本要求",
      "review_rule": "2",
      "review_conditions": {
        "groups": [
          {
            "logicToNext": null,
            "groupFailReason": "营业执照:注册资本【&$营业执照:注册资本$@】应大于等于【&$申请表:最低注册资本$@】",
            "conditions": [
              {
                "elementA": "$营业执照:注册资本$",
                "elementAType": "factor",
                "elementADisplay": "$营业执照:注册资本$",
                "operator": "ge",
                "dataType": "float",
                "elementB": "$申请表:最低注册资本$",
                "elementBType": "factor",
                "elementBDisplay": "$申请表:最低注册资本$",
                "logicToNext": null,
                "stringReplacements": [
                  {"old_value": "万元", "new_value": ""},
                  {"old_value": "元", "new_value": ""}
                ],
                "delimiter": null,
                "arrayKeys": null
              }
            ]
          }
        ]
      },
      "is_point": "1"
    },
    {
      "kpname": "经营范围包含性检查",
      "content": "",
      "review_rule_text": "检查营业执照经营范围按顿号拆分后，是否包含申请表中的拟经营范围",
      "review_rule": "2",
      "review_conditions": {
        "groups": [
          {
            "logicToNext": null,
            "groupFailReason": "营业执照:经营范围应包含申请表:拟经营范围",
            "conditions": [
              {
                "elementA": "$营业执照:经营范围$",
                "elementAType": "factor",
                "elementADisplay": "$营业执照:经营范围$",
                "operator": "contains",
                "dataType": "string",
                "elementB": "$申请表:拟经营范围$",
                "elementBType": "factor",
                "elementBDisplay": "$申请表:拟经营范围$",
                "logicToNext": null,
                "stringReplacements": null,
                "delimiter": "、",
                "arrayKeys": null
              }
            ]
          }
        ]
      }
    }
  ]
}
```

### 6.2 LLM模式（review_rule="1"）

```json
{
  "materialname": "居民身份证",
  "keypoints": [
    {
      "kpname": "身份证有效期检查",
      "content": "请判断身份证的有效期是否已过期。如果已过期，请说明过期日期。当前日期为$常规信息:当前日期$，身份证有效期为$居民身份证:有效期$。",
      "nopassreason": "身份证已过期",
      "passreason": "身份证在有效期内",
      "review_rule": "1",
      "is_point": "1"
    }
  ]
}
```

### 6.3 Groovy脚本模式（review_rule="3"）

```json
{
  "materialname": "申请表",
  "keypoints": [
    {
      "kpname": "申请人年龄校验",
      "content": "",
      "review_rule": "3",
      "review_rule_js": "def idcard = input.get(\"居民身份证:身份证号\")\nif (idcard == null || idcard.length() < 18) {\n    return [pass: false, reason: \"身份证号无效\"]\n}\ndef birthYear = idcard.substring(6, 10).toInteger()\ndef age = java.time.Year.now().value - birthYear\nif (age < 18) {\n    return [pass: false, reason: \"申请人未满18周岁，当前年龄：\" + age]\n}\nreturn [pass: true, reason: \"申请人年龄符合要求\"]",
      "nopassreason": "申请人年龄不符合要求",
      "passreason": "申请人年龄符合要求"
    }
  ]
}
```

### 6.4 最简导入

```json
{
  "materialname": "营业执照",
  "keypoints": [
    {
      "kpname": "企业名称一致性",
      "review_rule": "2",
      "review_conditions": {
        "groups": [{
          "groupFailReason": "营业执照:企业名称【&$营业执照:企业名称$@】应等于【&$申请表:企业名称$@】",
          "conditions": [{
            "elementA": "$营业执照:企业名称$",
            "elementAType": "factor",
            "elementADisplay": "$营业执照:企业名称$",
            "operator": "eq",
            "dataType": "string",
            "elementB": "$申请表:企业名称$",
            "elementBType": "factor",
            "elementBDisplay": "$申请表:企业名称$"
          }]
        }]
      }
    }
  ]
}
```

### 6.5 带前置规则的导入

```json
{
  "materialname": "营业执照",
  "keypoints": [
    {
      "kpname": "注册资本校验（仅限有限责任公司）",
      "review_rule": "2",
      "pre_rule_enabled": 1,
      "pre_conditions": {
        "groups": [{
          "conditions": [{
            "elementA": "$申请表:企业类型$",
            "elementAType": "factor",
            "elementADisplay": "$申请表:企业类型$",
            "operator": "contains",
            "dataType": "string",
            "elementB": "有限责任",
            "elementBType": "value",
            "elementBDisplay": "有限责任"
          }]
        }]
      },
      "review_conditions": {
        "groups": [{
          "groupFailReason": "营业执照:注册资本【$营业执照:注册资本$】应大于等于100万",
          "conditions": [{
            "elementA": "$营业执照:注册资本$",
            "elementAType": "factor",
            "elementADisplay": "$营业执照:注册资本$",
            "operator": "ge",
            "dataType": "float",
            "elementB": "100",
            "elementBType": "value",
            "elementBDisplay": "100",
            "stringReplacements": [{"old_value": "万元", "new_value": ""}]
          }]
        }]
      },
      "nopassreason": "$营业执照:注册资本$不满足最低注册资本要求"
    }
  ]
}
```

### 6.6 空值判断（notblank / blank）

> **场景**：检查某个要素是否已填写，不需要比较值。`notblank`/`blank` 运算符时 `elementB` 为空。

```json
{
  "materialname": "居民身份证",
  "keypoints": [
    {
      "kpname": "身份证号码非空检查",
      "review_rule_text": "检查身份证号码是否已识别到",
      "review_rule": "2",
      "review_conditions": {
        "groups": [{
          "groupFailReason": "居民身份证:身份证号码未识别到",
          "conditions": [{
            "elementA": "$居民身份证:身份证号码$",
            "elementAType": "factor",
            "elementADisplay": "$居民身份证:身份证号码$",
            "operator": "notblank",
            "dataType": "string",
            "elementB": "",
            "elementBType": "value",
            "elementBDisplay": ""
          }]
        }]
      }
    }
  ]
}
```

### 6.7 长度比较（len_gt / len_lt / len_eq）

> **场景**：检查字符串长度或数组元素个数。`elementB` 为数字。

```json
{
  "materialname": "居民身份证",
  "keypoints": [
    {
      "kpname": "身份证号码长度校验",
      "review_rule_text": "检查身份证号码长度是否为18位",
      "review_rule": "2",
      "review_conditions": {
        "groups": [{
          "groupFailReason": "居民身份证:身份证号码【$居民身份证:身份证号码$】长度应为18位",
          "conditions": [{
            "elementA": "$居民身份证:身份证号码$",
            "elementAType": "factor",
            "elementADisplay": "$居民身份证:身份证号码$",
            "operator": "len_eq",
            "dataType": "string",
            "elementB": "18",
            "elementBType": "value",
            "elementBDisplay": "18"
          }]
        }]
      }
    }
  ]
}
```

### 6.8 正则匹配（regex）

> **场景**：用正则表达式校验格式。`elementB` 为正则表达式字符串。

```json
{
  "materialname": "居民身份证",
  "keypoints": [
    {
      "kpname": "身份证号码格式校验",
      "review_rule_text": "检查身份证号码是否符合18位格式（末位可为X）",
      "review_rule": "2",
      "review_conditions": {
        "groups": [{
          "groupFailReason": "居民身份证:身份证号码【$居民身份证:身份证号码$】格式不正确",
          "conditions": [{
            "elementA": "$居民身份证:身份证号码$",
            "elementAType": "factor",
            "elementADisplay": "$居民身份证:身份证号码$",
            "operator": "regex",
            "dataType": "string",
            "elementB": "^\\d{17}[\\dXx]$",
            "elementBType": "value",
            "elementBDisplay": "^\\d{17}[\\dXx]$"
          }]
        }]
      }
    }
  ]
}
```

### 6.9 组内多条件（AND / OR）

> **场景**：同一组内多个条件用 `logicToNext` 连接。所有条件按逻辑关系求值后，决定该组是否通过。

```json
{
  "materialname": "居民身份证",
  "keypoints": [
    {
      "kpname": "身份证完整性检查",
      "review_rule_text": "检查姓名和身份证号码都已识别到",
      "review_rule": "2",
      "review_conditions": {
        "groups": [{
          "groupFailReason": "居民身份证:姓名和身份证号码必须同时识别到",
          "conditions": [
            {
              "elementA": "$居民身份证:姓名$",
              "elementAType": "factor",
              "elementADisplay": "$居民身份证:姓名$",
              "operator": "notblank",
              "dataType": "string",
              "elementB": "",
              "elementBType": "value",
              "elementBDisplay": "",
              "logicToNext": "AND"
            },
            {
              "elementA": "$居民身份证:身份证号码$",
              "elementAType": "factor",
              "elementADisplay": "$居民身份证:身份证号码$",
              "operator": "notblank",
              "dataType": "string",
              "elementB": "",
              "elementBType": "value",
              "elementBDisplay": "",
              "logicToNext": null
            }
          ]
        }]
      }
    }
  ]
}
```

### 6.10 多组逻辑（AND / OR）

> **场景**：多个组之间用 `logicToNext` 连接。例如"企业名称一致 **且** 注册资本达标"。每组有独立的 `groupFailReason`，不通过时只返回失败组的原因。

```json
{
  "materialname": "营业执照",
  "keypoints": [
    {
      "kpname": "营业执照综合校验",
      "review_rule_text": "企业名称一致且注册资本达标且有效期在有效期内",
      "review_rule": "2",
      "review_conditions": {
        "groups": [
          {
            "logicToNext": "AND",
            "groupFailReason": "营业执照:企业名称【&$营业执照:企业名称$@】应等于【&$申请表:企业名称$@】",
            "conditions": [{
              "elementA": "$营业执照:企业名称$",
              "elementAType": "factor",
              "elementADisplay": "$营业执照:企业名称$",
              "operator": "eq",
              "dataType": "string",
              "elementB": "$申请表:企业名称$",
              "elementBType": "factor",
              "elementBDisplay": "$申请表:企业名称$"
            }]
          },
          {
            "logicToNext": "AND",
            "groupFailReason": "营业执照:注册资本【$营业执照:注册资本$】应大于等于100万",
            "conditions": [{
              "elementA": "$营业执照:注册资本$",
              "elementAType": "factor",
              "elementADisplay": "$营业执照:注册资本$",
              "operator": "ge",
              "dataType": "float",
              "elementB": "100",
              "elementBType": "value",
              "elementBDisplay": "100",
              "stringReplacements": [
                {"old_value": "万元", "new_value": ""},
                {"old_value": "万", "new_value": ""}
              ]
            }]
          },
          {
            "logicToNext": null,
            "groupFailReason": "营业执照:有效期【&$营业执照:营业期限$@】应大于等于【&$常规信息:当前日期$@】",
            "conditions": [{
              "elementA": "$营业执照:营业期限$",
              "elementAType": "factor",
              "elementADisplay": "$营业执照:营业期限$",
              "operator": "ge",
              "dataType": "date",
              "elementB": "$常规信息:当前日期$",
              "elementBType": "variable",
              "elementBDisplay": "$常规信息:当前日期$"
            }]
          }
        ]
      }
    }
  ]
}
```

### 6.11 分隔符 + 字符串替换组合

> **场景**：先做字符串替换统一分隔符，再按分隔符拆分为数组，最后用 `contains` 判断包含关系。

```json
{
  "materialname": "营业执照",
  "keypoints": [
    {
      "kpname": "经营范围混合分隔符校验",
      "review_rule_text": "经营范围中各种分隔符统一替换为顿号后，拆分数组判断是否包含申请范围",
      "review_rule": "2",
      "review_conditions": {
        "groups": [{
          "groupFailReason": "营业执照:经营范围应包含申请表:拟经营范围",
          "conditions": [{
            "elementA": "$营业执照:经营范围$",
            "elementAType": "factor",
            "elementADisplay": "$营业执照:经营范围$",
            "operator": "contains",
            "dataType": "string",
            "elementB": "$申请表:拟经营范围$",
            "elementBType": "factor",
            "elementBDisplay": "$申请表:拟经营范围$",
            "stringReplacements": [
              {"old_value": "，", "new_value": "、"},
              {"old_value": ",", "new_value": "、"},
              {"old_value": "；", "new_value": "、"},
              {"old_value": ";", "new_value": "、"}
            ],
            "delimiter": "、"
          }]
        }]
      }
    }
  ]
}
```

### 6.12 分隔符 + 长度比较

> **场景**：用分隔符拆分后，判断数组元素个数。例如"联系电话至少填写2个"。

```json
{
  "materialname": "申请表",
  "keypoints": [
    {
      "kpname": "联系电话数量检查",
      "review_rule_text": "联系电话按顿号拆分后至少2个",
      "review_rule": "2",
      "review_conditions": {
        "groups": [{
          "groupFailReason": "申请表:联系电话至少应填写2个",
          "conditions": [{
            "elementA": "$申请表:联系电话$",
            "elementAType": "factor",
            "elementADisplay": "$申请表:联系电话$",
            "operator": "len_gt",
            "dataType": "string",
            "elementB": "1",
            "elementBType": "value",
            "elementBDisplay": "1",
            "delimiter": "、"
          }]
        }]
      }
    }
  ]
}
```

### 6.13 数组类型 + arrayKeys

> **场景**：`dataType=array` 时直接将要素值作为JSON数组比较。`arrayKeys` 用于对象数组时只保留指定Key进行比较。

```json
{
  "materialname": "申请表",
  "keypoints": [
    {
      "kpname": "股东信息一致性",
      "review_rule_text": "申请表股东列表与工商系统股东列表中姓名和证件号一致",
      "review_rule": "2",
      "review_conditions": {
        "groups": [{
          "groupFailReason": "申请表:股东列表与工商系统:股东列表不一致（仅比较姓名和证件号）",
          "conditions": [{
            "elementA": "$申请表:股东列表$",
            "elementAType": "factor",
            "elementADisplay": "$申请表:股东列表$",
            "operator": "eq",
            "dataType": "array",
            "elementB": "$法人信息:股东列表$",
            "elementBType": "variable",
            "elementBDisplay": "$法人信息:股东列表$",
            "arrayKeys": ["name", "idcard"]
          }]
        }]
      }
    }
  ]
}
```

### 6.14 系统变量引用（variable 类型）

> **场景**：使用 `elementBType=variable` 引用系统变量（常规信息、法人信息、自然人信息等内置载体）。

```json
{
  "materialname": "居民身份证",
  "keypoints": [
    {
      "kpname": "身份证姓名与申请人一致",
      "review_rule_text": "身份证上的姓名与系统中自然人姓名一致",
      "review_rule": "2",
      "review_conditions": {
        "groups": [{
          "groupFailReason": "居民身份证:姓名【&$居民身份证:姓名$@】应等于【&$自然人信息:姓名$@】",
          "conditions": [{
            "elementA": "$居民身份证:姓名$",
            "elementAType": "factor",
            "elementADisplay": "$居民身份证:姓名$",
            "operator": "eq",
            "dataType": "string",
            "elementB": "$自然人信息:姓名$",
            "elementBType": "variable",
            "elementBDisplay": "$自然人信息:姓名$"
          }]
        }]
      }
    }
  ]
}
```

### 6.15 排除情形（exclude_situations）

> **场景**：某些情形下审查要点不需要审查。`exclude_situations` 为情形表达式字符串。

```json
{
  "materialname": "营业执照",
  "keypoints": [
    {
      "kpname": "注册资本校验（排除个体工商户）",
      "review_rule_text": "当不是个体工商户时，检查注册资本是否达标",
      "exclude_situations": "个体工商户",
      "review_rule": "2",
      "review_conditions": {
        "groups": [{
          "groupFailReason": "营业执照:注册资本【$营业执照:注册资本$】应大于等于50万",
          "conditions": [{
            "elementA": "$营业执照:注册资本$",
            "elementAType": "factor",
            "elementADisplay": "$营业执照:注册资本$",
            "operator": "ge",
            "dataType": "float",
            "elementB": "50",
            "elementBType": "value",
            "elementBDisplay": "50",
            "stringReplacements": [{"old_value": "万元", "new_value": ""}]
          }]
        }]
      }
    }
  ]
}
```

### 6.16 混合模式批量导入

> **场景**：同一材料下同时导入不同审查模式（LLM + 规则对比 + Groovy）的规则。

```json
{
  "materialname": "营业执照",
  "keypoints": [
    {
      "kpname": "企业名称一致性",
      "review_rule": "2",
      "review_conditions": {
        "groups": [{
          "groupFailReason": "营业执照:企业名称【&$营业执照:企业名称$@】应等于【&$申请表:企业名称$@】",
          "conditions": [{
            "elementA": "$营业执照:企业名称$",
            "elementAType": "factor",
            "elementADisplay": "$营业执照:企业名称$",
            "operator": "eq",
            "dataType": "string",
            "elementB": "$申请表:企业名称$",
            "elementBType": "factor",
            "elementBDisplay": "$申请表:企业名称$"
          }]
        }]
      }
    },
    {
      "kpname": "营业执照真伪鉴别",
      "review_rule": "1",
      "content": "请判断这份营业执照是否为真实有效的营业执照。观察是否有明显的PS痕迹、水印是否正常、字体是否规范。",
      "nopassreason": "营业执照疑似伪造",
      "passreason": "营业执照真实有效",
      "is_point": "1"
    },
    {
      "kpname": "统一社会信用代码校验",
      "review_rule": "3",
      "review_rule_js": "def code = input.get(\"营业执照:统一社会信用代码\")\nif (code == null || code.length() != 18) {\n    return [pass: false, reason: \"统一社会信用代码长度应为18位，当前：\" + (code == null ? \"空\" : code.length() + \"位\")]\n}\nreturn [pass: true, reason: \"统一社会信用代码格式正确\"]",
      "nopassreason": "统一社会信用代码格式不正确",
      "passreason": "统一社会信用代码格式正确"
    }
  ]
}
```

### 示例场景索引

| 示例 | 场景 | 关键特性 |
|------|------|----------|
| 6.1 | 规则对比基础 | eq + 字符串替换 + 分隔符 |
| 6.2 | LLM模式 | content提示词 + 系统变量 |
| 6.3 | Groovy脚本 | review_rule_js |
| 6.4 | 最简导入 | 仅必填字段 |
| 6.5 | 前置规则 | pre_rule_enabled + pre_conditions |
| 6.6 | 空值判断 | notblank，elementB为空 |
| 6.7 | 长度比较 | len_eq，elementB为数字 |
| 6.8 | 正则匹配 | regex，elementB为正则表达式 |
| 6.9 | 组内多条件 | 条件间 logicToNext=AND |
| 6.10 | 多组逻辑 | 组间 logicToNext=AND，variable类型 |
| 6.11 | 替换+分隔符 | stringReplacements + delimiter 组合 |
| 6.12 | 分隔符+长度 | delimiter + len_gt |
| 6.13 | 数组+arrayKeys | dataType=array + arrayKeys过滤 |
| 6.14 | 系统变量 | elementBType=variable，内置载体 |
| 6.15 | 排除情形 | exclude_situations |
| 6.16 | 混合模式 | 同一材料下LLM+规则+Groovy |

---

## 七、校验规则

### 7.1 导入前校验

| 校验项 | 规则 | 错误提示 |
|--------|------|----------|
| materialname 有效性 | 必须能在 `ai_task_material` 表中通过 taskid + materialname 唯一匹配到一条记录 | "材料不存在：xxx" |
| keypoints 非空 | keypoints 数组长度 ≥ 1 | "至少需要一个审查要点" |
| kpname 必填 | 每个要点的 kpname 不能为空 | "审查要点名称不能为空" |
| kpname 唯一（导入内） | 同一JSON内 kpname 不重复 | "导入数据中存在重复的审查要点名称：xxx" |
| kpname 唯一（数据库） | 与目标材料下已有审查要点不重名 | "审查要点名称已存在：xxx" |
| review_rule 必填 | 每个要点的 review_rule 不能为空，且值必须为 `"1"`/`"2"`/`"3"` | "审查模式不能为空" 或 "审查模式值无效：xxx" |
| review_conditions 必填 | 当 `review_rule="2"` 时，review_conditions 不能为空 | "规则对比模式下，多条件配置不能为空" |
| review_rule_js 必填 | 当 `review_rule="3"` 时，review_rule_js 不能为空 | "Groovy脚本模式下，脚本内容不能为空" |
| content 建议填写 | 当 `review_rule="1"` 时，content 为空则警告（非阻断） | "（警告）LLM模式下建议填写审查内容" |
| 要素引用有效性 | review_conditions 中 `$载体:要素$` 格式的引用必须在当前事项下存在 | "条件引用了不存在的要素：$xxx:yyy$" |
| pre_conditions 一致性 | 当 `pre_rule_enabled=1` 时，pre_conditions 不应为空 | "启用了前置规则但未配置前置条件" |
| 运算符合法性 | operator 值必须在支持的运算符列表中 | "不支持的运算符：xxx" |
| 数据类型合法性 | dataType 值必须在 `string`/`int`/`float`/`date`/`array` 中 | "不支持的数据类型：xxx" |
| groupFailReason 必填 | 当 `review_rule="2"` 时，每个组的 `groupFailReason` 不能为空 | "组N缺少审核不通过原因(groupFailReason)" |
| 运算符-数据类型兼容性 | operator 与 dataType 必须符合兼容矩阵（见第5.5节） | "运算符xxx不支持数据类型yyy" |
| 分隔符运算符约束 | 配置了 `delimiter` 时，`operator` 必须在 eq/contains/len_gt/len_lt/len_eq/notblank/blank 中 | "配置分隔符后不支持运算符：xxx" |
| elementB 联动校验 | `notblank`/`blank` 运算符时 elementB 应为空；`len_*` 运算符时 elementB 应为数字 | "空值判断运算符不需要要素B" 或 "长度比较的要素B应为数字" |

### 7.2 导入后处理

| 处理项 | 规则 |
|--------|------|
| tagno 自动生成 | 按当前材料下已有要点的最大 tagno + 1 递增分配 |
| fileguid 自动关联 | 查询当前材料下最新的 `ai_keypoint_file` 记录获取 fileguid |
| connect_ai_factor 自动提取 | 根据审查模式自动从 content / review_conditions / review_rule_js 中提取关联要素GUID |
| 要素引用解析 | review_conditions 和 pre_conditions 中 `$载体:要素$` 格式自动解析为要素GUID |
| location 默认生成 | 自动生成默认定位信息JSON |
| nopassreason 兜底生成 | 当 `review_rule="2"` 且 `nopassreason` 为空时，将所有组的 `groupFailReason` 用换行拼接后写入 `ai_keypoint.nopassreason` 作为兜底 |

---

## 八、数据流转图

```
导入JSON
  │
  ▼
┌──────────────────────────────────────────────────────────────────┐
│ 1. 解析JSON，校验格式和字段                                        │
│ 2. 校验 materialname 有效性，获取 materialid / taskid               │
│ 3. 校验 kpname 唯一性（导入内 + 数据库）                           │
│ 4. 校验 review_rule 模式和对应的必填字段                            │
└────────────────────────┬─────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────────┐
│ 5. 解析要素引用                                                    │
│    - 提取 review_conditions / pre_conditions 中的 $载体:要素$ 引用  │
│    - 查询 ai_carrier + ai_factor 获取要素GUID                      │
│    - 校验所有引用的要素都存在                                       │
│    - 替换 elementA/elementB 为要素GUID                              │
└────────────────────────┬─────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────────┐
│ 6. 遍历 keypoints，逐条写入 ai_keypoint 表                         │
│    - 生成 rowguid（同时作为 ai_rule 的 kpguid）                     │
│    - 填充 taskid, materialid, materialname, tagno, fileguid 等     │
│    - 自动分配 tagno = 当前最大值 + 1                                │
└────────────────────────┬─────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────────┐
│ 7. 逐条写入 ai_rule 表                                             │
│    - rowguid = kpguid（与 ai_keypoint 共享主键）                    │
│    - 根据 review_rule 模式设置对应字段                              │
│    - 自动提取 connect_ai_factor（关联要素）                         │
│    - 序列化 review_conditions / pre_conditions 为JSON字符串         │
└────────────────────────┬─────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────────┐
│ 8. 返回导入结果：成功数量、失败信息                                 │
└──────────────────────────────────────────────────────────────────┘
```

---

## 九、接口建议

### 9.1 导入接口

| 项目 | 内容 |
|------|------|
| Action类 | 在现有 `MaterialAiKeypointAddNewAction` 中新增方法，或新建 `AiRuleImportAction` |
| 方法签名 | `public void importRules(String jsonData)` |
| 请求参数 | `jsonData` - 导入JSON字符串；`taskid` - 事项标识（从页面上下文传入） |
| 返回参数 | `msg` - 操作结果消息，`successCount` - 成功数量，`errors` - 错误列表 |

### 9.2 返回格式

成功时：

```json
{
  "msg": "导入成功",
  "successCount": 3,
  "errors": [],
  "warnings": []
}
```

部分成功时：

```json
{
  "msg": "部分导入成功",
  "successCount": 2,
  "errors": [
    "审查要点名称已存在：企业名称一致性检查"
  ],
  "warnings": [
    "（警告）'身份证有效期检查' LLM模式下建议填写审查内容"
  ]
}
```

失败时：

```json
{
  "msg": "导入失败",
  "successCount": 0,
  "errors": [
    "材料不存在：营业执照副本",
    "条件引用了不存在的要素：$营业执照:注册地址$"
  ],
  "warnings": []
}
```

---

## 十、与要素导入的关系

审查规则导入**依赖**要素导入的结果：

```
┌─────────────────────┐     ┌──────────────────────┐
│  1. 先导入要素       │────▶│  2. 再导入审查规则     │
│  (要素导入JSON)      │     │  (审查规则导入JSON)    │
│                     │     │                      │
│  写入 ai_factor     │     │  写入 ai_keypoint     │
│  写入 ai_prompt_*   │     │  写入 ai_rule         │
└─────────────────────┘     └──────────────────────┘
```

> **原因**：审查规则的 `review_conditions` 中通过 `$载体:要素$` 格式引用要素，如果要素不存在则无法解析为GUID。因此在导入审查规则前，需确保所引用的要素已经存在（通过要素导入或手动配置）。

