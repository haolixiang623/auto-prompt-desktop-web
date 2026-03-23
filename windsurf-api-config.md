# Windsurf API 配置说明

## 当前配置状态
- 项目级配置文件：`.claude/settings.local.json` ✅ 已配置
- API测试：✅ 接口可用

## Windsurf 中找不到模型的可能原因

1. **配置位置错误**
   - Windsurf 可能在全局设置中配置API，而非项目级
   - 需要在 Windsurf 设置界面中手动配置

2. **设置界面配置步骤**
   - 打开 Windsurf 设置 (Cmd/Ctrl + ,)
   - 搜索 "API" 或 "OpenAI"
   - 配置以下项目：
     ```
     API Key: sk-0a66c03f4178cc59b9f9fb760bb3f5b6
     Base URL: https://api.asxs.top/v1
     Model: gpt-5.4
     ```

3. **配置文件位置**
   - 全局设置可能在：`~/Library/Application Support/Windsurf/User/settings.json`
   - 或在：`~/.windsurf/settings.json`

## 当前项目配置
```json
{
  "api": {
    "openai": {
      "apiKey": "sk-0a66c03f4178cc59b9f9fb760bb3f5b6",
      "baseURL": "https://api.asxs.top/v1",
      "model": "gpt-5.4"
    }
  }
}
```

## 建议
请在 Windsurf 设置界面中手动配置API参数，而不是依赖项目级配置文件。
