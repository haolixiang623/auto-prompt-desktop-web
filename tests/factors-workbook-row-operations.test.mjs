import test from 'node:test'
import assert from 'node:assert/strict'

import {
  deleteWorkbookRow,
  insertWorkbookRow,
} from '../src/components/factorsWorkbookRowOperations.js'

function createRow(rowNumber, values, extra = {}) {
  return {
    clientId: `row-${rowNumber ?? 'new'}`,
    rowNumber,
    values,
    ...extra,
  }
}

test('insertWorkbookRow adds a blank row that keeps group columns and extends merged ranges', () => {
  const result = insertWorkbookRow({
    headers: ['事项名称', '材料名称', '要素字段名称', '审查要点规则说明'],
    rows: [
      createRow(2, ['道路运输证申领', '道路运输证申领登记表', '业户名称', '规则A']),
      createRow(3, ['道路运输证申领', '道路运输证申领登记表', '车辆号牌', '规则B']),
    ],
    mergedRanges: [
      { startRow: 2, endRow: 3, startColumn: 1, endColumn: 1 },
      { startRow: 2, endRow: 3, startColumn: 2, endColumn: 2 },
    ],
    sourceRowNumber: 3,
    mode: 'blank',
    createRow: (row) => createRow(null, row.values, { clientId: 'row-new' }),
  })

  assert.deepEqual(
    result.rows.map((row) => ({ rowNumber: row.rowNumber, values: row.values })),
    [
      { rowNumber: 2, values: ['道路运输证申领', '道路运输证申领登记表', '业户名称', '规则A'] },
      { rowNumber: 3, values: ['道路运输证申领', '道路运输证申领登记表', '车辆号牌', '规则B'] },
      { rowNumber: 4, values: ['道路运输证申领', '道路运输证申领登记表', '', ''] },
    ],
  )
  assert.deepEqual(result.mergedRanges, [
    { startRow: 2, endRow: 4, startColumn: 1, endColumn: 1 },
    { startRow: 2, endRow: 4, startColumn: 2, endColumn: 2 },
  ])
  assert.equal(result.insertedRowNumber, 4)
})

test('insertWorkbookRow copies the full source row and shifts later rows down', () => {
  const result = insertWorkbookRow({
    headers: ['材料名称', '要素字段名称', '审查要点规则说明'],
    rows: [
      createRow(2, ['营业证照', '统一社会信用代码', '规则A']),
      createRow(3, ['营业证照', '法定代表人', '规则B']),
      createRow(4, ['营业证照', '成立日期', '规则C']),
    ],
    mergedRanges: [],
    sourceRowNumber: 3,
    mode: 'copy',
    createRow: (row) => createRow(null, row.values, { clientId: 'row-copy' }),
  })

  assert.deepEqual(
    result.rows.map((row) => ({ rowNumber: row.rowNumber, values: row.values })),
    [
      { rowNumber: 2, values: ['营业证照', '统一社会信用代码', '规则A'] },
      { rowNumber: 3, values: ['营业证照', '法定代表人', '规则B'] },
      { rowNumber: 4, values: ['营业证照', '法定代表人', '规则B'] },
      { rowNumber: 5, values: ['营业证照', '成立日期', '规则C'] },
    ],
  )
  assert.equal(result.insertedRowNumber, 4)
})

test('deleteWorkbookRow removes the row, reindexes remaining rows, and shrinks merged ranges', () => {
  const result = deleteWorkbookRow({
    rows: [
      createRow(2, ['道路运输证申领', '道路运输证申领登记表', '业户名称']),
      createRow(3, ['道路运输证申领', '道路运输证申领登记表', '车辆号牌']),
      createRow(4, ['道路运输证申领', '道路运输证申领登记表', '经营许可证号']),
    ],
    mergedRanges: [
      { startRow: 2, endRow: 4, startColumn: 1, endColumn: 1 },
      { startRow: 2, endRow: 4, startColumn: 2, endColumn: 2 },
    ],
    rowNumber: 3,
  })

  assert.equal(result.deleted, true)
  assert.deepEqual(
    result.rows.map((row) => ({ rowNumber: row.rowNumber, values: row.values })),
    [
      { rowNumber: 2, values: ['道路运输证申领', '道路运输证申领登记表', '业户名称'] },
      { rowNumber: 3, values: ['道路运输证申领', '道路运输证申领登记表', '经营许可证号'] },
    ],
  )
  assert.deepEqual(result.mergedRanges, [
    { startRow: 2, endRow: 3, startColumn: 1, endColumn: 1 },
    { startRow: 2, endRow: 3, startColumn: 2, endColumn: 2 },
  ])
  assert.equal(result.focusRowNumber, 3)
})
