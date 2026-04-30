import fs from 'node:fs'
import path from 'node:path'
import test from 'node:test'
import assert from 'node:assert/strict'

const ROOT = process.cwd()

test('repository no longer ships the legacy local case library helpers', () => {
  const removedPaths = [
    'skills/doc-extract-prompt-gen/case_library.json',
    'skills/case-import',
  ]

  for (const relativePath of removedPaths) {
    assert.equal(
      fs.existsSync(path.join(ROOT, relativePath)),
      false,
      `expected legacy artifact to be removed: ${relativePath}`,
    )
  }

  const docSkillPath = path.join(ROOT, 'skills/doc-extract-prompt-gen/skill.md')
  const docSkill = fs.readFileSync(docSkillPath, 'utf8')

  assert.equal(
    docSkill.includes('case_library.json'),
    false,
    'expected active prompt generation skill docs to stop referencing the legacy local case library file',
  )
  assert.equal(
    docSkill.includes('步骤 0：案例库匹配'),
    false,
    'expected active prompt generation skill docs to stop describing the removed local case library matching step',
  )
})
