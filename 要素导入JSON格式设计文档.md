# 要素导入JSON格式设计文档

## 文档信息

| 项目 | 内容 |
|------|------|
| 文档版本 | V1.0 |
| 创建日期 | 2026-02-28 |
| 功能模块 | 识别模块 - 要素导入 |
| 相关表 | ai_factor, ai_prompt_group, ai_prompt_group_factor |

---

## 一、功能概述

支持通过JSON文件批量导入要素及其提示词分组信息到指定载体下。导入内容包括：

1. **要素信息**：要素名称、类型、识别提示词等配置
2. **分组信息**：提示词组合配置及组合内要素关联关系

---

## 二、JSON结构总览

```json
{
  "carriername": "目标载体名称",
  "factors": [ ... ],
  "promptGroups": [ ... ]
}
```

---

## 三、顶层字段说明

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `carriername` | string | 是 | - | 目标载体名称，要素将导入到该载体下。后端根据载体名称 + taskid 查询 ai_carrier 获取 carrierguid 等关联信息 |
| `factors` | array | 是 | - | 要素列表，至少包含1个要素对象 |
| `promptGroups` | array | 否 | [] | 提示词组合列表。不传时所有要素自动归入载体的默认组合 |

---

## 四、factors 要素字段说明

`factors` 数组中每个对象对应 `ai_factor` 表的一条记录。

| 字段 | 类型 | 必填 | 默认值 | 对应数据库字段 | 说明 |
|------|------|------|--------|---------------|------|
| `factorname` | string | **是** | - | `ai_factor.factorname` | 要素名称。同一载体下必须唯一，导入时会做唯一性校验 |
| `factortype` | string | 否 | `"1"` | `ai_factor.factortype` | 要素类型。`1`=文本，`2`=图片 |
| `factor_prompt` | string | 否 | `""` | `ai_factor.factor_prompt` | 要素识别提示词。描述如何识别该要素的那句话，例如"请识别证件中的姓名（中文全名）" |
| `fieldname` | string | 否 | `""` | `ai_factor.fieldname` | JSON字段名。仅当载体类型为JSON（objecttype=1）时使用，用于从JSON载体中提取对应字段值 |
| `ordernum` | int | 否 | 按数组顺序自动递增 | `ai_factor.ordernum` | 排序号。控制要素在载体下的展示顺序 |
| `remark` | string | 否 | `""` | `ai_factor.remark` | 备注说明。对该要素的补充描述 |
| `is_usermsg` | string | 否 | `"0"` | `ai_factor.is_usermsg` | 是否要素应用。`0`=否，`1`=是。启用后该要素值将应用到业务字段 |
| `usermsg_type` | string | 否 | `""` | `ai_factor.usermsg_type` | 要素应用名称。当 `is_usermsg="1"` 时必填，同一事项下必须唯一 |
| `isrecollect` | string | 否 | `"0"` | `ai_factor.isrecollect` | 是否二次识别。`0`=否，`1`=是。启用后该要素支持重新识别 |
| `factoruse` | string | 否 | `""` | `ai_factor.factoruse` | 要素用途。对要素使用场景的描述 |
| `factor_trans` | string | 否 | `""` | `ai_factor.factor_trans` | 转换类型。用于指定要素值的转换规则 |

### 后端自动填充字段（无需导入）

以下字段由后端根据上下文自动生成，JSON中**无需**也**不应**包含：

| 字段 | 来源 | 说明 |
|------|------|------|
| `rowguid` | 系统生成UUID | 要素主键 |
| `taskid` | 通过 carriername 查询 ai_carrier 获取 | 事项标识 |
| `carrierguid` | 通过 carriername 查询 ai_carrier 获取 | 所属载体标识 |
| `carriername` | 取自顶层 carriername | 载体名称（冗余字段） |
| `collectguid` | 固定值 `"bigmode"` | 采集方式，大模型识别 |
| `identifytype` | 根据 factor_prompt 是否为空自动判断 | `"1"`=通用识别（factor_prompt为空），`"2"`=独立识别（factor_prompt不为空） |
| `operatedate` | 当前时间 | 操作时间 |
| `operateusername` | 当前登录用户 | 操作人 |
| `operateuserguid` | 当前登录用户GUID | 操作人标识 |

---

## 五、promptGroups 提示词组合字段说明

`promptGroups` 数组中每个对象对应 `ai_prompt_group` 表的一条记录，以及 `ai_prompt_group_factor` 表的关联记录。

| 字段 | 类型 | 必填 | 默认值 | 对应数据库字段 | 说明 |
|------|------|------|--------|---------------|------|
| `groupname` | string | **是** | - | `ai_prompt_group.groupname` | 组合名称，例如"基本信息组"、"组合1" |
| `grouptype` | string | 否 | `"2"` | `ai_prompt_group.grouptype` | 组合类型。`1`=默认组合（系统自动创建，每个载体仅一个），`2`=自定义组合 |
| `ordernum` | int | 否 | 按数组顺序自动递增 | `ai_prompt_group.ordernum` | 排序号。越大越靠前展示 |
| `prompt_template` | string | 否 | 系统默认模板 | `ai_prompt_group.prompt_template` | 识别提示词模板。其中 `$(factors)` 为要素占位符，运行时会被替换为组合内所有要素的编码列表 |
| `modelguid` | string | 否 | `""` | `ai_prompt_group.modelguid` | 组合专用大模型GUID。为空时使用载体或系统默认模型 |
| `modelparams` | string | 否 | `""` | `ai_prompt_group.modelparams` | 模型参数JSON。用于自定义调用大模型时的参数（如temperature等） |
| `promptguid` | string | 否 | `""` | `ai_prompt_group.promptguid` | 关联提示词模板标识。从系统预设模板中选择时填写 |
| `factors` | array\<string\> | **是** | - | 写入 `ai_prompt_group_factor` | 组合包含的**要素名称列表**。每个元素为 `factors` 数组中某个要素的 `factorname`，用于建立组合与要素的关联关系 |

### 后端自动填充字段（无需导入）

| 字段 | 来源 | 说明 |
|------|------|------|
| `rowguid` | 系统生成UUID | 组合主键 |
| `carrierguid` | 通过 carriername 查询 ai_carrier 获取 | 所属载体标识 |
| `taskid` | 通过 carriername 查询 ai_carrier 获取 | 事项标识 |
| `operatedate` | 当前时间 | 操作时间 |
| `operateusername` | 当前登录用户 | 操作人 |
| `operateuserguid` | 当前登录用户GUID | 操作人标识 |

### factors → ai_prompt_group_factor 映射规则

`promptGroups[].factors` 数组中的每个要素名称会生成一条 `ai_prompt_group_factor` 记录：

| 字段 | 生成规则 | 说明 |
|------|----------|------|
| `rowguid` | 系统生成UUID | 关联记录主键 |
| `groupguid` | 当前组合的 rowguid | 所属提示词组合标识 |
| `factorguid` | 根据 factorname 匹配已导入要素的 rowguid | 关联要素标识 |
| `factor_index` | 按要素在数组中的顺序自动分配 1~N | 要素编码序号，用于提示词中的编号（如 `1.企业名称`） |

---

## 六、完整示例

### 6.1 标准导入（要素 + 分组）

```json
{
  "carriername": "营业执照",
  "factors": [
    {
      "factorname": "企业名称",
      "factortype": "1",
      "factor_prompt": "请识别营业执照中的企业名称（全称）",
      "ordernum": 1,
      "remark": "工商登记的企业全称"
    },
    {
      "factorname": "统一社会信用代码",
      "factortype": "1",
      "factor_prompt": "请识别营业执照中的统一社会信用代码（18位字母数字组合）",
      "ordernum": 2
    },
    {
      "factorname": "法定代表人",
      "factortype": "1",
      "factor_prompt": "请识别营业执照中的法定代表人姓名",
      "ordernum": 3
    },
    {
      "factorname": "注册资本",
      "factortype": "1",
      "factor_prompt": "请识别营业执照中的注册资本金额（含单位）",
      "ordernum": 4
    },
    {
      "factorname": "营业期限",
      "factortype": "1",
      "factor_prompt": "请识别营业执照中的营业期限（起止日期）",
      "ordernum": 5
    }
  ],
  "promptGroups": [
    {
      "groupname": "基本信息组",
      "grouptype": "2",
      "ordernum": 2,
      "prompt_template": "作为图片识别专家，请识别营业执照中的基本信息：\n$(factors)\n请返回JSON格式：{\"msginfo\":[{\"name\":\"序号\",\"value\":\"识别值\",\"bbox\":\"坐标\"}]}",
      "modelguid": "",
      "factors": ["企业名称", "统一社会信用代码"]
    },
    {
      "groupname": "其他信息组",
      "grouptype": "2",
      "ordernum": 1,
      "prompt_template": "作为图片识别专家，请识别营业执照中的补充信息：\n$(factors)\n请返回JSON格式：{\"msginfo\":[{\"name\":\"序号\",\"value\":\"识别值\",\"bbox\":\"坐标\"}]}",
      "modelguid": "",
      "factors": ["法定代表人", "注册资本", "营业期限"]
    }
  ]
}
```

### 6.2 最简导入（仅要素，无分组）

```json
{
  "carriername": "居民身份证",
  "factors": [
    { "factorname": "姓名", "factor_prompt": "请识别证件中的姓名（中文全名）" },
    { "factorname": "身份证号", "factor_prompt": "请识别证件中的身份证号码（18位）" },
    { "factorname": "有效期", "factor_prompt": "请识别证件的有效期限（起止日期）" }
  ]
}
```

> 不传 `promptGroups` 时，所有要素自动归入载体的默认组合。

### 6.3 JSON载体要素导入

```json
{
  "carriername": "申请表",
  "factors": [
    {
      "factorname": "申请人姓名",
      "factortype": "1",
      "factor_prompt": "",
      "fieldname": "applicant_name",
      "ordernum": 1,
      "remark": "电子表单中的申请人姓名字段"
    },
    {
      "factorname": "联系电话",
      "factortype": "1",
      "factor_prompt": "",
      "fieldname": "phone_number",
      "ordernum": 2
    }
  ]
}
```

> JSON载体（objecttype=1）的要素通过 `fieldname` 直接映射表单字段，无需 `factor_prompt` 和分组配置。

---

## 七、校验规则

### 7.1 导入前校验

| 校验项 | 规则 | 错误提示 |
|--------|------|----------|
| carriername 有效性 | 必须能在 ai_carrier 表中通过 taskid + carriername 唯一匹配到一条记录 | "载体不存在" |
| factors 非空 | factors 数组长度 ≥ 1 | "至少需要一个要素" |
| factorname 必填 | 每个要素的 factorname 不能为空 | "要素名称不能为空" |
| factorname 唯一（导入内） | 同一JSON内 factorname 不重复 | "导入数据中存在重复的要素名称：xxx" |
| factorname 唯一（数据库） | 与目标载体下已有要素不重名 | "要素名称已存在：xxx" |
| usermsg_type 唯一 | is_usermsg=1 时，usermsg_type 在同一事项下唯一 | "要素应用字段已存在：xxx" |
| groupname 必填 | 传了 promptGroups 时，每个组合的 groupname 不能为空 | "组合名称不能为空" |
| 组合要素引用有效 | promptGroups[].factors 中的名称必须在 factors 数组中存在 | "组合'xxx'引用了不存在的要素：yyy" |
| 要素互斥 | 一个要素最多只能出现在一个 promptGroup 中 | "要素'xxx'被分配到多个组合中" |

### 7.2 导入后处理

| 处理项 | 规则 |
|--------|------|
| 未分组要素归入默认组合 | 未出现在任何 promptGroup.factors 中的要素，自动归入载体的默认组合（grouptype=1） |
| 默认组合自动创建 | 若载体下不存在默认组合，自动创建一个 |
| factor_index 自动生成 | 按要素在组合 factors 数组中的顺序分配 1~N |
| identifytype 自动判断 | factor_prompt 为空 → identifytype="1"（通用识别），不为空 → identifytype="2"（独立识别） |
| collectguid 固定填充 | 统一设置为 `"bigmode"` |

---

## 八、数据流转图

```
导入JSON
  │
  ▼
┌──────────────────────────────────────────────────────────────────┐
│ 1. 解析JSON，校验格式和字段                                        │
│ 2. 校验 carriername 有效性，获取 carrierguid / taskid               │
│ 3. 校验 factorname 唯一性（导入内 + 数据库）                       │
│ 4. 校验 promptGroups 要素引用和互斥性                              │
└────────────────────────┬─────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────────┐
│ 5. 遍历 factors，逐条写入 ai_factor 表                             │
│    - 生成 rowguid                                                 │
│    - 填充 taskid, carrierguid, carriername, collectguid 等         │
│    - 建立 factorname → rowguid 映射（供后续分组使用）               │
└────────────────────────┬─────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────────┐
│ 6. 遍历 promptGroups，逐条写入 ai_prompt_group 表                  │
│    - 生成 rowguid（groupguid）                                     │
│    - 填充 carrierguid, taskid                                      │
│ 7. 遍历组合内 factors，逐条写入 ai_prompt_group_factor 表           │
│    - 通过 factorname 映射获取 factorguid                           │
│    - 按顺序分配 factor_index = 1, 2, 3...                         │
└────────────────────────┬─────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────────┐
│ 8. 处理未分组要素 → 归入默认组合（grouptype=1）                     │
│ 9. 返回导入结果：成功数量、失败信息                                 │
└──────────────────────────────────────────────────────────────────┘
```

---

## 九、接口建议

### 9.1 导入接口

| 项目 | 内容 |
|------|------|
| Action类 | `AiFactorImportAction` 或在现有 `BigModeFactorAddAction` 中新增方法 |
| 方法签名 | `public void importFactors(String jsonData)` |
| 请求参数 | `jsonData` - 导入JSON字符串 |
| 返回参数 | `msg` - 操作结果消息，`successCount` - 成功数量，`errors` - 错误列表 |

### 9.2 返回格式

```json
{
  "msg": "导入成功",
  "successCount": 5,
  "groupCount": 2,
  "errors": []
}
```

失败时：

```json
{
  "msg": "导入失败",
  "successCount": 0,
  "groupCount": 0,
  "errors": [
    "要素名称已存在：企业名称",
    "组合'基本信息组'引用了不存在的要素：xxx"
  ]
}
```
