export function buildPreviewPrompt(templateText, factorsList) {
  const template = String(templateText || '').trim() || '$(factors)'
  const factorLines = (factorsList || []).map((factor, index) => {
    const factorName = factor.factorname || factor.name || ''
    const factorPrompt = factor.factor_prompt || ''
    return `## ${index + 1}.${factorName}\n${factorPrompt}`
  }).join('\n')
  return template.includes('$(factors)')
    ? template.replace('$(factors)', factorLines)
    : `${template}\n${factorLines}`.trim()
}

export function normalizeArtifact(artifact, materialName = '') {
  const base = artifact && typeof artifact === 'object' ? artifact : {}
  const template = base.template && typeof base.template === 'object' ? base.template : {}
  const factorsList = Array.isArray(base.factors) ? base.factors : []
  return {
    version: String(base.version || '1'),
    carriername: base.carriername || materialName || '',
    template: {
      prompt_template: template.prompt_template || '',
    },
    meta: base.meta && typeof base.meta === 'object' ? base.meta : {},
    factors: factorsList.map((factor, index) => ({
      index: Number(factor.index || index + 1),
      factorname: factor.factorname || factor.name || '',
      factortype: factor.factortype || '1',
      factoruse: factor.factoruse || '',
      factor_prompt: factor.factor_prompt || '',
      source: factor.source || 'manual_edit',
    })),
  }
}

export function applyFactorPromptEdit(result, factorIndex, nextPrompt) {
  if (!result?.artifact) return result
  const nextFactors = result.artifact.factors.map((factor, index) => (
    index === factorIndex
      ? { ...factor, factor_prompt: nextPrompt, source: 'manual_edit' }
      : factor
  ))
  const nextArtifact = {
    ...result.artifact,
    factors: nextFactors,
  }
  const nextPreviewPrompt = buildPreviewPrompt(nextArtifact.template?.prompt_template || '', nextArtifact.factors)
  return {
    ...result,
    artifact: nextArtifact,
    preview_prompt: nextPreviewPrompt,
    prompt_template: nextPreviewPrompt,
    dirty: true,
  }
}

export function sourceLabel(source) {
  if (source === 'case_library') return '提示词库'
  if (source === 'ai_generated') return 'AI生成'
  return '人工修改'
}
