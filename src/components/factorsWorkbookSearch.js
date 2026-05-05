export function normalizeSearchText(value) {
  return String(value ?? '').trim().toLowerCase()
}

export function buildSearchTerms(keyword) {
  return normalizeSearchText(keyword).split(/\s+/).filter(Boolean)
}

export function countMatchedSearchTerms(value, searchTerms) {
  const normalized = normalizeSearchText(value)
  if (!normalized || !Array.isArray(searchTerms) || searchTerms.length === 0) return 0
  return searchTerms.filter((term) => normalized.includes(term)).length
}

export function matchesSearchTerms(parts, searchTerms) {
  if (!Array.isArray(searchTerms) || searchTerms.length === 0) return true
  const haystack = (Array.isArray(parts) ? parts : [parts])
    .map((item) => normalizeSearchText(item))
    .filter(Boolean)
    .join(' ')
  return searchTerms.every((term) => haystack.includes(term))
}

export function rowMatchesWorkbookSearch({ searchTerms, materialName = '', factorName = '', ruleDescription = '' } = {}) {
  return matchesSearchTerms([materialName, factorName, ruleDescription], searchTerms)
}

export function issueMatchesWorkbookSearch({
  searchTerms,
  materialName = '',
  factorName = '',
  ruleDescription = '',
  message = '',
} = {}) {
  return matchesSearchTerms([materialName, factorName, ruleDescription, message], searchTerms)
}

export function resolveWorkbookSearchMatchTarget({
  searchTerms,
  materialName = '',
  factorName = '',
  ruleDescription = '',
} = {}) {
  const materialMatchCount = countMatchedSearchTerms(materialName, searchTerms)
  const factorMatchCount = countMatchedSearchTerms(factorName, searchTerms)
  const ruleDescriptionMatchCount = countMatchedSearchTerms(ruleDescription, searchTerms)

  if (factorMatchCount >= materialMatchCount && factorMatchCount >= ruleDescriptionMatchCount && factorMatchCount > 0) {
    return 'factor'
  }
  if (ruleDescriptionMatchCount >= materialMatchCount && ruleDescriptionMatchCount > 0) {
    return 'rule'
  }
  if (materialMatchCount > 0) {
    return 'material'
  }
  return 'factor'
}
