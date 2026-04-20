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
    `${match[0]}\nreturn addModel;`,
  )
}

test('addModel inserts the new model at the beginning of the list', () => {
  const models = {
    value: [
      { id: '1', name: 'Existing A', model_id: 'a', type: 'vl', params: [] },
      { id: '2', name: 'Existing B', model_id: 'b', type: 'text', params: [] },
    ],
  }

  let editedIndex = -1
  const addModel = loadAddModel()(models, (idx) => {
    editedIndex = idx
  }, { now: () => 123456 })

  addModel()

  assert.equal(models.value[0].id, '123456')
  assert.equal(models.value[0].model_id, '')
  assert.equal(models.value[0].type, 'vl')
  assert.equal(editedIndex, 0)
  assert.deepEqual(
    models.value.map((model) => model.id),
    ['123456', '1', '2'],
  )
})
