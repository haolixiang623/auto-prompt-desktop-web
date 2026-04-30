import fs from 'node:fs'
import path from 'node:path'
import test from 'node:test'
import assert from 'node:assert/strict'

const ROOT = process.cwd()
const filePath = path.join(ROOT, 'src', 'views', 'GenerateView.vue')
const content = fs.readFileSync(filePath, 'utf8')

test('GenerateView exposes single-material retry action for failed rows', () => {
  assert.match(content, /retrySingleMaterial\(r\.material\)/)
  assert.match(content, /重新生成/)
  assert.match(content, /const retryingMaterials = ref\(\{\}\)/)
  assert.match(content, /validateFactorsForMaterials\(\[materialName\]\)/)
})
