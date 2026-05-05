import test from 'node:test'
import assert from 'node:assert/strict'

import {
  buildSearchTerms,
  issueMatchesWorkbookSearch,
  resolveWorkbookSearchMatchTarget,
  rowMatchesWorkbookSearch,
} from '../src/components/factorsWorkbookSearch.js'

test('row search matches material name even when factor and rule description do not contain the keyword', () => {
  const searchTerms = buildSearchTerms('机动车登记证')

  assert.equal(
    rowMatchesWorkbookSearch({
      searchTerms,
      materialName: '机动车登记证书(产权证)',
      factorName: '所有人',
      ruleDescription: '',
    }),
    true,
  )
})

test('issue search matches the related row material name so problem navigation stays discoverable', () => {
  const searchTerms = buildSearchTerms('机动车登记证')

  assert.equal(
    issueMatchesWorkbookSearch({
      searchTerms,
      materialName: '机动车登记证书(产权证)',
      factorName: '燃油类型',
      ruleDescription: '需与#机动车登记证书（产权证）-燃料种类#一致',
      message: '规则说明缺失',
    }),
    true,
  )
})

test('search result target prefers material cell when the keyword only matches material name', () => {
  const searchTerms = buildSearchTerms('机动车登记证')

  assert.equal(
    resolveWorkbookSearchMatchTarget({
      searchTerms,
      materialName: '机动车登记证书(产权证)',
      factorName: '所有人',
      ruleDescription: '',
    }),
    'material',
  )
})

test('search result target still prefers factor or rule when those fields are the actual hit', () => {
  const searchTerms = buildSearchTerms('燃油类型')
  assert.equal(
    resolveWorkbookSearchMatchTarget({
      searchTerms,
      materialName: '机动车登记证书(产权证)',
      factorName: '燃油类型',
      ruleDescription: '需与#机动车登记证书（产权证）-燃料种类#一致',
    }),
    'factor',
  )

  const ruleSearchTerms = buildSearchTerms('燃料种类')
  assert.equal(
    resolveWorkbookSearchMatchTarget({
      searchTerms: ruleSearchTerms,
      materialName: '机动车登记证书(产权证)',
      factorName: '燃油类型',
      ruleDescription: '需与#机动车登记证书（产权证）-燃料种类#一致',
    }),
    'rule',
  )
})
