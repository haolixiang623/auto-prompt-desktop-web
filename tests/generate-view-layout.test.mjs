import fs from 'node:fs'
import path from 'node:path'
import test from 'node:test'
import assert from 'node:assert/strict'

const generateViewPath = path.resolve('src/views/GenerateView.vue')

test('GenerateView shows the full factor list instead of slicing to ten items', () => {
  const source = fs.readFileSync(generateViewPath, 'utf8')

  assert.equal(
    source.includes('factors.slice(0, 10)'),
    false,
    'factor list should not be capped at ten rows',
  )
  assert.equal(
    source.includes('factors.length > 10'),
    false,
    'factor list should not render a hidden-count placeholder',
  )
})

test('GenerateView allows long factor names to wrap', () => {
  const source = fs.readFileSync(generateViewPath, 'utf8')

  assert.match(
    source,
    /whitespace-normal|break-words/,
    'factor names should wrap instead of truncating',
  )
})

test('GenerateView allows long material names to wrap', () => {
  const source = fs.readFileSync(generateViewPath, 'utf8')

  assert.equal(
    source.includes("class=\"text-sm truncate\" :class=\"isMaterialSelected(m) ? 'font-semibold text-blue-800' : 'text-gray-700'\""),
    false,
    'material names should not be hard-truncated to a single line',
  )
  assert.match(
    source,
    /whitespace-normal.*break-words|break-words.*whitespace-normal/s,
    'material names should wrap across multiple lines when needed',
  )
})

test('GenerateView uses responsive layout classes for narrower windows', () => {
  const source = fs.readFileSync(generateViewPath, 'utf8')

  assert.match(
    source,
    /class="flex h-full min-h-0 flex-col xl:flex-row"/,
    'root layout should stack before switching to side-by-side at larger widths',
  )
  assert.match(
    source,
    /class="w-full flex-shrink-0 bg-white border-b flex flex-col xl:w-56 xl:border-b-0 xl:border-r"/,
    'step sidebar should become full-width on narrow windows',
  )
  assert.match(
    source,
    /class="flex flex-col gap-2 sm:flex-row sm:items-start"/,
    'workspace picker controls should stack on narrow windows',
  )
  assert.match(
    source,
    /flex flex-col gap-3 pt-2 sm:flex-row sm:items-center sm:justify-between/,
    'primary action row should stack on narrow windows',
  )
})

test('GenerateView keeps the step navigator compact on narrow windows', () => {
  const source = fs.readFileSync(generateViewPath, 'utf8')

  assert.match(
    source,
    /flex gap-2 overflow-x-auto/,
    'step navigator should scroll horizontally instead of consuming extra height',
  )
  assert.match(
    source,
    /min-w-\[150px\]|min-w-\[160px\]|min-w-\[170px\]/,
    'step items should use compact fixed-width cards on narrow windows',
  )
  assert.match(
    source,
    /hidden.*xl:block/s,
    'secondary step copy should stay hidden on narrow windows to keep the bar compact',
  )
})
