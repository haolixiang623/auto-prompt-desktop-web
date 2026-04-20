import fs from 'node:fs'
import path from 'node:path'
import test from 'node:test'
import assert from 'node:assert/strict'

const generateViewPath = path.resolve('src/views/GenerateView.vue')

test('GenerateView derives visible factors from selected materials', () => {
  const source = fs.readFileSync(generateViewPath, 'utf8')

  assert.match(
    source,
    /const selectedFactors = computed\(\(\) => \{/,
    'GenerateView should compute the visible factors for the current material selection',
  )
  assert.match(
    source,
    /selectedMaterialNames\.value\.has\(factor\.material\)/,
    'visible factors should be filtered by selected materials',
  )
})

test('GenerateView uses selected factor counts in Step1 summaries', () => {
  const source = fs.readFileSync(generateViewPath, 'utf8')

  assert.match(
    source,
    /\{\{\s*selectedFactors\.length\s*\}\}\s*个/,
    'Step1 factor badge should use the filtered factor count',
  )
  assert.match(
    source,
    /共\s*\{\{\s*selectedFactors\.length\s*\}\}\s*个要素字段/,
    'Step1 footer summary should use the filtered factor count',
  )
  assert.doesNotMatch(
    source,
    /共\s*\{\{\s*factors\.length\s*\}\}\s*个要素字段/,
    'Step1 footer summary should not use the full factor count anymore',
  )
})
