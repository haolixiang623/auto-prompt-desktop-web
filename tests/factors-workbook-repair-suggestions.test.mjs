import test from 'node:test'
import assert from 'node:assert/strict'

import { applyRepairSuggestionPatches } from '../src/components/factorsWorkbookRepairSuggestions.js'

function createRow(row) {
  return {
    clientId: row.clientId || `row-${row.rowNumber ?? 'draft'}`,
    rowNumber: row.rowNumber ?? null,
    values: [...(row.values || [])],
  }
}

test('applyRepairSuggestionPatches updates workbook cells in the current draft only', () => {
  const result = applyRepairSuggestionPatches({
    headers: ['材料名称', '要素字段名称', '审查要点规则说明'],
    rows: [
      createRow({ rowNumber: 2, values: ['营业证照', '统一社会信用代码', '#营业证照-统一社会信用代吗#不能为空'] }),
    ],
    mergedRanges: [],
    suggestion: {
      patches: [
        {
          type: 'cell_update',
          rowNumber: 2,
          columnIndex: 2,
          after: '#营业证照-统一社会信用代码#不能为空',
        },
      ],
    },
    createRow,
  })

  assert.equal(result.rows[0].values[2], '#营业证照-统一社会信用代码#不能为空')
  assert.equal(result.focusTargetId, 'cell-2-2')
  assert.equal(result.hasStructuralChanges, false)
})

test('applyRepairSuggestionPatches can insert a suggested factor row', () => {
  const result = applyRepairSuggestionPatches({
    headers: ['事项名称', '材料名称', '要素字段名称', '审查要点名称', '审查要点规则说明'],
    rows: [
      createRow({ rowNumber: 2, values: ['道路运输证申领', '营业证照', '统一社会信用代码', '', ''] }),
      createRow({ rowNumber: 3, values: ['道路运输证申领', '营业证照', '', '统一社会信用代码校验', '#营业证照-注册资本#不能为空'] }),
    ],
    mergedRanges: [],
    suggestion: {
      patches: [
        {
          type: 'row_insert',
          afterRowNumber: 3,
          rowValues: ['道路运输证申领', '营业证照', '注册资本', '', ''],
          focusColumnIndex: 2,
        },
      ],
    },
    createRow,
  })

  assert.deepEqual(
    result.rows.map((row) => row.values),
    [
      ['道路运输证申领', '营业证照', '统一社会信用代码', '', ''],
      ['道路运输证申领', '营业证照', '', '统一社会信用代码校验', '#营业证照-注册资本#不能为空'],
      ['道路运输证申领', '营业证照', '注册资本', '', ''],
    ],
  )
  assert.equal(result.focusTargetId, 'cell-4-2')
  assert.equal(result.hasStructuralChanges, true)
})

test('applyRepairSuggestionPatches can delete duplicate rows from the draft', () => {
  const result = applyRepairSuggestionPatches({
    headers: ['材料名称', '要素字段名称'],
    rows: [
      createRow({ rowNumber: 2, values: ['营业证照', '统一社会信用代码'] }),
      createRow({ rowNumber: 3, values: ['营业证照', '统一社会信用代码'] }),
    ],
    mergedRanges: [],
    suggestion: {
      patches: [
        {
          type: 'row_delete',
          rowNumber: 3,
        },
      ],
    },
    createRow,
  })

  assert.deepEqual(
    result.rows.map((row) => ({ rowNumber: row.rowNumber, values: row.values })),
    [
      { rowNumber: 2, values: ['营业证照', '统一社会信用代码'] },
    ],
  )
  assert.equal(result.hasStructuralChanges, true)
})
