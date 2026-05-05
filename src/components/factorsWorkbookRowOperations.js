const ROW_CARRY_FORWARD_HEADER_PATTERNS = ['事项名称', '材料名称']

function normalizeText(value) {
  return String(value ?? '').trim()
}

function normalizeRowValues(values, size) {
  const normalized = Array.isArray(values) ? [...values] : []
  while (normalized.length < size) {
    normalized.push('')
  }
  return normalized.slice(0, size)
}

function normalizeMergedRanges(mergedRanges) {
  const seen = new Set()
  return (Array.isArray(mergedRanges) ? mergedRanges : [])
    .map((item) => {
      const startRow = Number(item?.startRow)
      const endRow = Number(item?.endRow)
      const startColumn = Number(item?.startColumn)
      const endColumn = Number(item?.endColumn)
      if (
        !Number.isFinite(startRow) ||
        !Number.isFinite(endRow) ||
        !Number.isFinite(startColumn) ||
        !Number.isFinite(endColumn) ||
        startRow < 1 ||
        endRow < startRow ||
        startColumn < 1 ||
        endColumn < startColumn
      ) {
        return null
      }
      return { startRow, endRow, startColumn, endColumn }
    })
    .filter(Boolean)
    .filter((item) => {
      const key = `${item.startRow}:${item.endRow}:${item.startColumn}:${item.endColumn}`
      if (seen.has(key)) {
        return false
      }
      seen.add(key)
      return true
    })
    .sort((left, right) => {
      if (left.startRow !== right.startRow) return left.startRow - right.startRow
      if (left.startColumn !== right.startColumn) return left.startColumn - right.startColumn
      if (left.endRow !== right.endRow) return left.endRow - right.endRow
      return left.endColumn - right.endColumn
    })
}

function rowWidth(rows, headers) {
  return Math.max(
    Array.isArray(headers) ? headers.length : 0,
    ...(Array.isArray(rows) ? rows.map((row) => (Array.isArray(row?.values) ? row.values.length : 0)) : [0]),
    1,
  )
}

function normalizeRows(rows, width) {
  return (Array.isArray(rows) ? rows : []).map((row) => ({
    ...row,
    values: normalizeRowValues(row?.values || [], width),
  }))
}

function resequenceRows(rows, width) {
  return normalizeRows(rows, width).map((row, index) => ({
    ...row,
    rowNumber: index + 2,
  }))
}

function buildBlankRowValues(headers, sourceValues, width) {
  const normalizedSourceValues = normalizeRowValues(sourceValues, width)
  return normalizeRowValues(headers, width).map((header, index) => (
    ROW_CARRY_FORWARD_HEADER_PATTERNS.some((pattern) => normalizeText(header).includes(pattern))
      ? normalizedSourceValues[index] || ''
      : ''
  ))
}

function shiftMergedRangesForInsert(mergedRanges, sourceRowNumber) {
  if (!Number.isFinite(sourceRowNumber) || sourceRowNumber < 1) {
    return normalizeMergedRanges(mergedRanges)
  }
  const insertedRowNumber = sourceRowNumber + 1
  return normalizeMergedRanges(mergedRanges).map((range) => {
    if (sourceRowNumber >= range.startRow && sourceRowNumber <= range.endRow) {
      return {
        ...range,
        endRow: range.endRow + 1,
      }
    }
    if (range.startRow >= insertedRowNumber) {
      return {
        ...range,
        startRow: range.startRow + 1,
        endRow: range.endRow + 1,
      }
    }
    return range
  })
}

function shiftMergedRangesForDelete(mergedRanges, deletedRowNumber) {
  if (!Number.isFinite(deletedRowNumber) || deletedRowNumber < 1) {
    return normalizeMergedRanges(mergedRanges)
  }
  return normalizeMergedRanges(mergedRanges)
    .flatMap((range) => {
      if (deletedRowNumber < range.startRow) {
        return [{
          ...range,
          startRow: range.startRow - 1,
          endRow: range.endRow - 1,
        }]
      }
      if (deletedRowNumber > range.endRow) {
        return [range]
      }

      if (range.startRow === range.endRow) {
        return []
      }

      const nextRange = {
        ...range,
        endRow: range.endRow - 1,
      }

      if (nextRange.startRow === nextRange.endRow && nextRange.startColumn === nextRange.endColumn) {
        return []
      }
      return [nextRange]
    })
}

export function insertWorkbookRow({
  rows,
  headers,
  mergedRanges,
  sourceRowNumber = null,
  mode = 'blank',
  createRow = (row) => row,
} = {}) {
  const width = rowWidth(rows, headers)
  const normalizedRows = normalizeRows(rows, width)
  const targetRowNumber = Number(sourceRowNumber)
  const sourceIndex = Number.isFinite(targetRowNumber)
    ? normalizedRows.findIndex((row) => Number(row?.rowNumber) === targetRowNumber)
    : normalizedRows.length - 1
  const safeSourceIndex = sourceIndex >= 0 ? sourceIndex : normalizedRows.length - 1
  const insertIndex = sourceIndex >= 0 ? sourceIndex + 1 : normalizedRows.length
  const sourceRow = safeSourceIndex >= 0 ? normalizedRows[safeSourceIndex] : null
  const anchorRowNumber = sourceRow ? Number(sourceRow.rowNumber) : null
  const nextValues = mode === 'copy' && sourceRow
    ? [...sourceRow.values]
    : buildBlankRowValues(headers, sourceRow?.values || [], width)

  const insertedRow = createRow({
    rowNumber: null,
    values: nextValues,
  })

  const nextRows = resequenceRows(
    [
      ...normalizedRows.slice(0, insertIndex),
      {
        ...insertedRow,
        values: normalizeRowValues(insertedRow?.values || nextValues, width),
      },
      ...normalizedRows.slice(insertIndex),
    ],
    width,
  )

  return {
    rows: nextRows,
    mergedRanges: anchorRowNumber
      ? shiftMergedRangesForInsert(mergedRanges, anchorRowNumber)
      : normalizeMergedRanges(mergedRanges),
    insertedRowNumber: insertIndex + 2,
  }
}

export function deleteWorkbookRow({ rows, mergedRanges, rowNumber } = {}) {
  const width = rowWidth(rows, [])
  const normalizedRows = normalizeRows(rows, width)
  const normalizedRowNumber = Number(rowNumber)
  const deleteIndex = normalizedRows.findIndex((row) => Number(row?.rowNumber) === normalizedRowNumber)
  if (deleteIndex < 0) {
    return {
      rows: normalizedRows,
      mergedRanges: normalizeMergedRanges(mergedRanges),
      deleted: false,
      focusRowNumber: null,
    }
  }

  const nextRows = resequenceRows(
    normalizedRows.filter((_, index) => index !== deleteIndex),
    width,
  )
  const fallbackIndex = Math.min(deleteIndex, nextRows.length - 1)

  return {
    rows: nextRows,
    mergedRanges: shiftMergedRangesForDelete(mergedRanges, normalizedRowNumber),
    deleted: true,
    focusRowNumber: fallbackIndex >= 0 ? nextRows[fallbackIndex].rowNumber : null,
  }
}
