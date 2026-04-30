import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

function loadAddModel() {
  const source = readFileSync(new URL('../src/views/SettingsView.vue', import.meta.url), 'utf8')
  const match = source.match(/function addModel\(\)\s*\{[\s\S]*?\n\}/)

  assert.ok(match, 'Expected addModel function to exist in SettingsView.vue')

  return new Function(
    'models',
    'startEdit',
    'Date',
    'OPENAI_COMPAT_BASE_URL',
    `${match[0]}\nreturn addModel;`,
  )
}

test('addModel inserts the new model at the beginning of the list', () => {
  const models = {
    value: [
      { id: '1', name: 'Existing A', model: 'a', base_url: 'https://example-a.invalid/v1', api_key: '', type: 'vl', params: [] },
      { id: '2', name: 'Existing B', model: 'b', base_url: 'https://example-b.invalid/v1', api_key: '', type: 'text', params: [] },
    ],
  }

  let editedIndex = -1
  const addModel = loadAddModel()(models, (idx) => {
    editedIndex = idx
  }, { now: () => 123456 }, 'https://api.openai.com/v1')

  addModel()

  assert.equal(models.value[0].id, '123456')
  assert.equal(models.value[0].model, '')
  assert.equal(models.value[0].base_url, 'https://api.openai.com/v1')
  assert.equal(models.value[0].type, 'vl')
  assert.equal(editedIndex, 0)
  assert.deepEqual(
    models.value.map((model) => model.id),
    ['123456', '1', '2'],
  )
})
