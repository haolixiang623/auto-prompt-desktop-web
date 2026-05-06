import { deleteWorkbookRow, insertWorkbookRow } from './factorsWorkbookRowOperations.js'

function normalizeRowValues(values, size) {
  const normalized = Array.isArray(values) ? [...values] : []
  while (normalized.length < size) {
    normalized.push('')
  }
  return normalized.slice(0, size)
}

function cloneRows(rows, width) {
  return (Array.isArray(rows) ? rows : []).map((row) => ({
    ...row,
    values: normalizeRowValues(row?.values || [], width),
  }))
}

function workbookWidth(headers, rows, patches) {
  return Math.max(
    Array.isArray(headers) ? headers.length : 0,
    ...(Array.isArray(rows) ? rows.map((row) => Array.isArray(row?.values) ? row.values.length : 0) : [0]),
    ...(Array.isArray(patches) ? patches.map((patch) => Array.isArray(patch?.rowValues) ? patch.rowValues.length : 0) : [0]),
    1,
  )
}

function cellTargetId(rowNumber, columnIndex) {
  return rowNumber ? `cell-${rowNumber}-${columnIndex}` : `draft-cell-${columnIndex}`
}

export function applyRepairSuggestionPatches({
  headers = [],
  rows = [],
  mergedRanges = [],
  suggestion = {},
  createRow = (row) => row,
} = {}) {
  const patches = Array.isArray(suggestion?.patches) ? suggestion.patches : []
  const width = workbookWidth(headers, rows, patches)

  let nextRows = cloneRows(rows, width)
  let nextMergedRanges = Array.isArray(mergedRanges) ? [...mergedRanges] : []
  let focusTargetId = 'toolbar-anchor'
  let hasStructuralChanges = false

  for (const patch of patches) {
    if (patch?.type === 'cell_update') {
      const rowNumber = Number(patch.rowNumber)
      const columnIndex = Number(patch.columnIndex)
      nextRows = nextRows.map((row) => {
        if (Number(row?.rowNumber) !== rowNumber) {
          return row
        }
        const values = normalizeRowValues(row?.values || [], width)
        values[columnIndex] = patch.after ?? ''
        return {
          ...row,
          values,
        }
      })
      focusTargetId = cellTargetId(rowNumber, columnIndex)
      continue
    }

    if (patch?.type === 'row_insert') {
      const result = insertWorkbookRow({
        rows: nextRows,
        headers,
        mergedRanges: nextMergedRanges,
        sourceRowNumber: patch.afterRowNumber,
        mode: 'blank',
        createRow,
      })
      nextRows = cloneRows(result?.rows || [], width).map((row) => (
        Number(row?.rowNumber) === Number(result?.insertedRowNumber)
          ? {
              ...row,
              values: normalizeRowValues(patch.rowValues || [], width),
            }
          : row
      ))
      nextMergedRanges = Array.isArray(result?.mergedRanges) ? result.mergedRanges : []
      focusTargetId = cellTargetId(
        Number(result?.insertedRowNumber) || null,
        Number(patch.focusColumnIndex ?? 0),
      )
      hasStructuralChanges = true
      continue
    }

    if (patch?.type === 'row_delete') {
      const result = deleteWorkbookRow({
        rows: nextRows,
        mergedRanges: nextMergedRanges,
        rowNumber: patch.rowNumber,
      })
      nextRows = cloneRows(result?.rows || [], width)
      nextMergedRanges = Array.isArray(result?.mergedRanges) ? result.mergedRanges : []
      focusTargetId = result?.focusRowNumber
        ? cellTargetId(result.focusRowNumber, Number(patch.focusColumnIndex ?? 0))
        : 'toolbar-anchor'
      hasStructuralChanges = true
    }
  }

  return {
    rows: nextRows,
    mergedRanges: nextMergedRanges,
    focusTargetId,
    hasStructuralChanges,
  }
}
