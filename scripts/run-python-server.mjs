import { spawn } from 'node:child_process'
import { access } from 'node:fs/promises'
import path from 'node:path'

const projectRoot = process.cwd()

const pythonCandidates = [
  { command: process.env.AUTOPROMPT_PYTHON, args: [] },
  { command: 'python', args: [] },
  { command: 'py', args: ['-3.11'] },
  { command: 'py', args: ['-3.12'] },
  { command: 'C:\\Users\\HLX\\AppData\\Local\\Programs\\Python\\Python311\\python.exe', args: [] },
  { command: 'C:\\Users\\HLX\\AppData\\Local\\Programs\\Python\\Python312\\python.exe', args: [] }
].filter((item) => item.command)

function run(command, args) {
  return new Promise((resolve) => {
    let child
    try {
      child = spawn(command, args, {
        cwd: projectRoot,
        stdio: 'pipe',
        windowsHide: true
      })
    } catch (error) {
      resolve({ ok: false, error, stdout: '', stderr: '' })
      return
    }

    let stdout = ''
    let stderr = ''

    child.stdout.on('data', (chunk) => {
      stdout += String(chunk)
    })
    child.stderr.on('data', (chunk) => {
      stderr += String(chunk)
    })

    child.on('error', (error) => {
      resolve({ ok: false, error, stdout, stderr })
    })
    child.on('close', (code) => {
      resolve({ ok: code === 0, code, stdout, stderr })
    })
  })
}

async function exists(filePath) {
  try {
    await access(filePath)
    return true
  } catch {
    return false
  }
}

async function resolvePython() {
  for (const candidate of pythonCandidates) {
    if (candidate.command.endsWith('.exe') && !(await exists(candidate.command))) {
      continue
    }
    const probe = await run(candidate.command, [...candidate.args, '--version'])
    if (probe.ok) {
      return candidate
    }
  }
  throw new Error('No usable Python interpreter found. Set AUTOPROMPT_PYTHON or install Python 3.11+.')
}

const mode = process.argv[2] === 'prod' ? 'prod' : 'dev'
const extraArgs = process.argv.slice(3)

const uvicornArgs = [
  '-m',
  'uvicorn',
  'pyserver.app.main:app',
  '--host',
  '0.0.0.0',
  '--port',
  process.env.PORT || '3000'
]

if (mode === 'dev') {
  uvicornArgs.push('--reload')
}

uvicornArgs.push(...extraArgs)

try {
  const python = await resolvePython()
  let child
  try {
    child = spawn(python.command, [...python.args, ...uvicornArgs], {
      cwd: projectRoot,
      stdio: 'inherit',
      windowsHide: false,
      env: process.env
    })
  } catch (error) {
    console.error(error instanceof Error ? error.message : String(error))
    process.exit(1)
  }

  child.on('exit', (code) => {
    process.exit(code ?? 0)
  })
  child.on('error', (error) => {
    console.error(String(error))
    process.exit(1)
  })
} catch (error) {
  console.error(error instanceof Error ? error.message : String(error))
  process.exit(1)
}
