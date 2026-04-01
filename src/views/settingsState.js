export function getApiKeySaveState({ apiKey, savedApiKey, apiKeyConfigured }) {
  const currentValue = String(apiKey ?? '')
  const savedValue = String(savedApiKey ?? '')
  const hasUnsavedChanges = currentValue !== savedValue

  if (hasUnsavedChanges) {
    return apiKeyConfigured
      ? {
          tone: 'warning',
          label: '未保存',
          message: '当前输入与服务端已保存值不同，请点击“保存设置”后再执行生成。'
        }
      : {
          tone: 'warning',
          label: '未保存',
          message: '检测到当前输入框已有内容，但服务端尚未保存，请点击“保存设置”。'
        }
  }

  if (apiKeyConfigured) {
    return {
      tone: 'success',
      label: '已配置',
      message: '服务端已保存 API Key，可直接用于生成提示词。'
    }
  }

  return {
    tone: 'error',
    label: '未配置',
    message: '服务端当前没有保存 API Key。'
  }
}
