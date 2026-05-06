import fs from 'node:fs'
import path from 'node:path'
import test from 'node:test'
import assert from 'node:assert/strict'

const componentPath = path.resolve('src/components/FactorsWorkbookRepairPanel.vue')
const statusBarPath = path.resolve('src/components/WorkspaceValidationStatusBar.vue')
const generateViewPath = path.resolve('src/views/GenerateView.vue')
const classifyViewPath = path.resolve('src/views/ClassifyView.vue')
const reviewRuleViewPath = path.resolve('src/views/ReviewRuleView.vue')

test('FactorsWorkbookRepairPanel becomes a full-screen repair desk instead of an inline page block', () => {
  const source = fs.readFileSync(componentPath, 'utf8')

  assert.match(source, /工作区校验与修复台/, 'repair panel should present a dedicated repair workspace title')
  assert.match(source, /fixed inset-0/, 'repair panel should render as a full-screen overlay instead of stretching the page')
  assert.match(source, /返回业务页继续/, 'repair panel should let the user leave the repair workspace and continue the original task')
  assert.match(source, /问题导航/, 'repair panel should surface a focused issue navigator')
  assert.match(source, /搜索材料名称 \/ 要素字段名称 \/ 审查要点规则说明/, 'repair panel should expose search for material names, factor names, and review rule descriptions')
  assert.match(source, /displayedRows/, 'repair panel should keep the main workbook table as a dedicated displayed row set')
  assert.match(source, /searchMatchedRows/, 'repair panel should keep search matches separate from the full workbook display order')
  assert.match(source, /rowIssueSummaryMap/, 'repair panel should calculate which rows have validation issues before sorting the main table')
  assert.match(source, /rowsWithIssuesCount/, 'repair panel should surface how many issue rows are being pushed to the front')
  assert.match(source, /visibleColumns/, 'repair panel should project a compact visible-column view instead of rendering every workbook column by default')
  assert.match(source, /visibleColumnIndices/, 'repair panel should compute visible column indices for the compact repair view')
  assert.match(source, /showAllColumns/, 'repair panel should let users temporarily expand the full column set')
  assert.match(source, /revealedColumnIndices/, 'repair panel should remember hidden columns that were auto-revealed during navigation')
  assert.match(source, /columnIndexFromTargetId/, 'repair panel should resolve a focused target back to its column index before auto-revealing hidden columns')
  assert.match(source, /revealColumn/, 'repair panel should auto-reveal a hidden column when navigation targets it')
  assert.match(source, /filteredIssueList/, 'repair panel should keep the issue navigator in sync with the active search')
  assert.match(source, /factorColumnIndex/, 'repair panel should resolve the factor field column before filtering search results')
  assert.match(source, /ruleDescriptionColumnIndex/, 'repair panel should resolve the review rule description column for search filtering')
  assert.match(source, /searchResultItems/, 'repair panel should show a dedicated search result list while searching')
  assert.match(source, /搜索结果列表会按命中字段定位：命中材料名称时跳到材料名称，命中要素字段名称时跳到要素字段，命中审查要点规则说明时跳到对应规则说明。/, 'repair panel should explain that search result clicks follow the matched field')
  assert.match(source, /默认前置 .* 行问题数据/, 'repair panel should tell the user that issue rows are prioritized in the full table')
  assert.match(source, /默认展示 .* \/ .* 列/, 'repair panel should summarize the compact default column set for the user')
  assert.match(source, /显示全部列/, 'repair panel should offer a way to expand all hidden columns')
  assert.match(source, /恢复默认列/, 'repair panel should let users collapse back to the compact default column set')
  assert.match(source, /合并单元格已按原表结构展开显示/, 'repair panel should explain that merged workbook cells are expanded for repair')
  assert.match(source, /mergedRanges/, 'repair panel should keep workbook merge metadata so merged regions can be preserved after save')
  assert.match(source, /syncMerged/, 'repair panel should sync edits inside merged workbook regions')
  assert.match(source, /expandMergedWorkbookData/, 'repair panel should expand merged workbook data locally before rendering')
  assert.match(source, /collectDisplayRowNumbers/, 'repair panel should restore row numbers covered by merged regions even when source rows are sparse')
  assert.match(source, /carryForwardDisplayColumns/, 'repair panel should carry forward visible group-column values such as 事项名称 and 材料名称')
  assert.match(source, /sticky top-0 z-10/, 'repair panel should freeze the table header while the table scrolls')
  assert.match(source, /countMatchedSearchTerms/, 'repair panel should count which search terms hit each field before choosing a jump target')
  assert.match(source, /resolveSearchResultMatchTarget/, 'repair panel should determine whether the active result matched material name, factor name, or rule description')
  assert.match(source, /matchTarget/, 'repair panel should store the chosen search-result target on each result item')
  assert.match(source, /resolveRowMaterialTargetId/, 'repair panel should compute the row-level material-name cell for search navigation')
  assert.match(source, /resolveRuleDescriptionTargetId/, 'repair panel should still support resolving review-rule-description targets')
  assert.match(source, /resolveRowRuleDescriptionTargetId/, 'repair panel should compute the row-level review-rule-description cell for search navigation')
  assert.match(source, /focusSearchResult/, 'repair panel should focus field-specific cells from the search result list')
  assert.match(source, /currentFocusLabel/, 'repair panel should describe the actual focused target instead of only echoing the previously selected issue')
  assert.match(source, /buildTargetLocationLabel/, 'repair panel should derive the visible focus summary from the focused target id')
  assert.match(
    source,
    /selectedIssueId\.value = item\.anchorIssue \? item\.anchorIssue\.id : ''/,
    'repair panel should clear stale issue selection when a search result has no anchored validation issue',
  )
  assert.equal(
    source.includes('搜索材料 / 要素 / 审查要点'),
    false,
    'repair panel should no longer search across materials and review points',
  )
  assert.equal(
    source.includes('v-else-if="visibleRows.length === 0"'),
    false,
    'repair panel should no longer replace the main table with a no-match state during search',
  )
  assert.match(source, /下载修复后的 factors\.xlsx/, 'repair panel should expose a repaired workbook download action')
  assert.match(source, /一键生成修复建议/, 'repair panel should let the user generate repair suggestions for the current diagnostics')
  assert.match(source, /人工审核通过后，系统会直接帮你修改当前修复草稿/, 'repair panel should explain that reviewed suggestions directly repair the draft')
  assert.match(source, /审核通过并修复/, 'repair panel should allow the user to approve a suggestion and immediately repair the draft')
  assert.match(source, /驳回建议/, 'repair panel should let the user reject a suggestion after review')
  assert.match(source, /待审核 .* 已修复 .* 已驳回/, 'repair panel should summarize review and repair progress instead of only showing suggestion counts')
  assert.match(source, /generateRepairSuggestions/, 'repair panel should request repair suggestions from the backend')
  assert.match(source, /\/api\/workspaces\/factors-workbook\/apply-repair-suggestion/, 'repair panel should be able to execute workspace-level repair actions after human approval')
  assert.match(source, /applySuggestion/, 'repair panel should apply accepted suggestions into the in-memory workbook draft')
  assert.match(source, /workspace_material_clone/, 'repair panel should recognize workspace material copy repairs as executable actions')
  assert.match(source, /保存并重新校验/, 'repair panel should save workbook edits and immediately re-run validation')
  assert.match(source, /新增行/, 'repair panel should allow inserting a new workbook row during repair')
  assert.match(source, /复制行/, 'repair panel should allow cloning an existing workbook row during repair')
  assert.match(source, /删除行/, 'repair panel should allow deleting an existing workbook row during repair')
  assert.match(source, /insertWorkbookRow/, 'repair panel should route row insertion and row copying through shared workbook row helpers')
  assert.match(source, /deleteWorkbookRow/, 'repair panel should route row deletion through shared workbook row helpers')
  assert.equal(source.includes('新增列'), false, 'repair panel should no longer allow adding columns during repair')
  assert.equal(source.includes('删除列'), false, 'repair panel should no longer allow deleting columns during repair')
  assert.equal(source.includes('补齐必需列'), false, 'repair panel should no longer mutate workbook structure by auto-adding required columns')
})

test('WorkspaceValidationStatusBar exposes compact validation actions', () => {
  const source = fs.readFileSync(statusBarPath, 'utf8')

  assert.match(source, /立即校验/, 'status bar should allow running validation on demand')
  assert.match(source, /查看并修复/, 'status bar should open the dedicated repair workspace')
  assert.match(source, /下载 factors\.xlsx/, 'status bar should expose direct workbook download')
  assert.match(source, /校验通过|校验失败|未校验/, 'status bar should summarize validation state in a compact strip')
})

test('GenerateView mounts the shared validation status bar and repair desk', () => {
  const source = fs.readFileSync(generateViewPath, 'utf8')

  assert.match(source, /WorkspaceValidationStatusBar/, 'generate view should show the compact validation strip')
  assert.match(source, /FactorsWorkbookRepairPanel/, 'generate view should reuse the shared factors workbook repair panel')
  assert.equal(
    source.includes('统一工作区校验未通过'),
    false,
    'generate view should no longer inline the long validation error block inside the main page flow',
  )
})

test('ClassifyView mounts the shared validation status bar and repair desk', () => {
  const source = fs.readFileSync(classifyViewPath, 'utf8')

  assert.match(source, /WorkspaceValidationStatusBar/, 'classify view should show the compact validation strip')
  assert.match(source, /FactorsWorkbookRepairPanel/, 'classify view should reuse the shared factors workbook repair panel')
})

test('ReviewRuleView mounts the shared validation status bar and repair desk', () => {
  const source = fs.readFileSync(reviewRuleViewPath, 'utf8')

  assert.match(source, /WorkspaceValidationStatusBar/, 'review-rule view should show the compact validation strip')
  assert.match(source, /FactorsWorkbookRepairPanel/, 'review-rule view should reuse the shared factors workbook repair panel')
})
