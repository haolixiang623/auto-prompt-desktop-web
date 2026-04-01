import fs from 'node:fs'
import path from 'node:path'
import test from 'node:test'
import assert from 'node:assert/strict'

const VIEWS_DIR = path.resolve('src/views')

function getScriptSetupBlock(source) {
  const match = source.match(/<script setup>([\s\S]*?)<\/script>/)
  return match?.[1] || ''
}

function hasNamedImport(scriptSource, importName, importPath) {
  const pattern = new RegExp(
    `import\\s*\\{[^}]*\\b${importName}\\b[^}]*\\}\\s*from\\s*['"]${importPath.replace('.', '\\.')}['"]`,
  )
  return pattern.test(scriptSource)
}

test('views import tauri helpers whenever invoke/listen are used', () => {
  const missingImports = []

  for (const fileName of fs.readdirSync(VIEWS_DIR)) {
    if (!fileName.endsWith('.vue')) continue

    const filePath = path.join(VIEWS_DIR, fileName)
    const source = fs.readFileSync(filePath, 'utf8')
    const scriptSource = getScriptSetupBlock(source)

    if (!scriptSource) continue

    if (/\binvoke\s*\(/.test(scriptSource) && !hasNamedImport(scriptSource, 'invoke', '../tauri/tauri.js')) {
      missingImports.push(`${fileName}: missing invoke import`)
    }

    if (/\blisten\s*\(/.test(scriptSource) && !hasNamedImport(scriptSource, 'listen', '../tauri/event.js')) {
      missingImports.push(`${fileName}: missing listen import`)
    }
  }

  assert.deepEqual(missingImports, [])
})
