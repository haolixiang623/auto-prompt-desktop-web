import fs from 'node:fs'
import path from 'node:path'
import test from 'node:test'
import assert from 'node:assert/strict'

const ROOT = process.cwd()

const requiredFiles = [
  'Dockerfile',
  'docker-compose.prod.yml',
  'nginx.conf',
  'deploy-production.sh',
  'DEPLOYMENT-GUIDE.md',
  'test-deploy.sh',
]

const deprecatedFiles = [
  'deploy-simple.sh',
  'deploy-cloud.sh',
  'deploy-server.sh',
  'deploy-native.sh',
  'deploy-baidu.sh',
  'deploy-baidu-source.sh',
  'switch-backend.sh',
  'docker-compose.simple.yml',
  'docker-compose.python.yml',
  'Dockerfile.baidubce',
  'DEPLOY-CLOUD.md',
]

test('repository exposes only the supported production deployment path', () => {
  for (const file of requiredFiles) {
    assert.equal(
      fs.existsSync(path.join(ROOT, file)),
      true,
      `expected required deployment file to exist: ${file}`,
    )
  }

  for (const file of deprecatedFiles) {
    assert.equal(
      fs.existsSync(path.join(ROOT, file)),
      false,
      `expected deprecated deployment file to be removed: ${file}`,
    )
  }

  const packageJson = JSON.parse(fs.readFileSync(path.join(ROOT, 'package.json'), 'utf8'))

  assert.equal(
    packageJson.scripts['docker:up'],
    'docker compose -f docker-compose.prod.yml up -d --build',
  )
  assert.equal(
    packageJson.scripts['docker:down'],
    'docker compose -f docker-compose.prod.yml down',
  )
})
