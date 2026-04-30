import { apiClient } from '../services/apiClient.js'
import { runTask } from '../services/taskService.js'
import { resolveWorkspaceId, selectUploadedFiles, selectWorkspace } from '../services/uploadService.js'

const TASK_COMMANDS = {
  generate_prompt: { kind: 'generate', eventName: 'skill-log' },
  verify_extraction: { kind: 'verify-extraction', eventName: 'skill-log' },
  classify_materials: { kind: 'classify', eventName: 'skill-log' },
  test_classify_prompt: { kind: 'test-classify-prompt', eventName: 'skill-log' },
  generate_factor_json: { kind: 'factor-json', eventName: 'skill-log' },
  generate_review_rule: { kind: 'review-rule', eventName: 'review-rule-log' },
  regenerate_keypoint: { kind: 'regenerate-keypoint', eventName: 'review-rule-log' }
}

function withWorkspaceId(args = {}) {
  if (args.workspaceId) return args
  if (args.workDir) {
    const workspaceId = resolveWorkspaceId(args.workDir)
    if (workspaceId) {
      return { ...args, workspaceId }
    }
  }
  return args
}

export async function invoke(command, args = {}) {
  if (command === 'select_directory') {
    const workspace = await selectWorkspace()
    return workspace?.rootPath || null
  }

  if (command === 'select_file') {
    return selectUploadedFiles(args.filters || [], false)
  }

  if (command === 'select_files') {
    return selectUploadedFiles(args.filters || [], true)
  }

  if (command in TASK_COMMANDS) {
    const task = TASK_COMMANDS[command]
    return runTask(task.kind, withWorkspaceId(args), task.eventName)
  }

  if (command === 'load_settings') {
    return apiClient.get('/api/settings')
  }

  if (command === 'save_settings') {
    return apiClient.put('/api/settings', args.settings)
  }

  if (command === 'get_default_god_prompts') {
    return apiClient.get('/api/settings/default-prompts')
  }

  if (command === 'get_god_prompts') {
    return apiClient.get('/api/god-prompts')
  }

  if (command === 'save_god_prompts') {
    return apiClient.put('/api/god-prompts', { prompts: args.prompts || {} })
  }

  if (command === 'test_api_key') {
    return apiClient.post('/api/settings/test-key', { apiKey: args.apiKey })
  }

  if (command === 'test_model_config') {
    return apiClient.post('/api/settings/test-model', {
      model: args.model,
      fallbackApiKey: args.fallbackApiKey,
      timeout: args.timeout
    })
  }

  if (command === 'get_llm_logs') {
    return apiClient.get('/api/logs', { page: args.page, pageSize: args.pageSize })
  }

  if (command === 'clear_llm_logs') {
    return apiClient.delete('/api/logs')
  }

  if (command === 'check_environment') {
    return apiClient.get('/api/health')
  }

  if (command === 'install_packages') {
    return apiClient.post('/api/health/install-packages', { packages: args.packages })
  }

  if (command === 'install_python') {
    return apiClient.post('/api/health/install-python', {})
  }

  if (command === 'load_case_library') {
    return apiClient.get('/api/cases')
  }

  if (command === 'import_case_library_json') {
    return apiClient.post('/api/cases/import-json', {
      sourcePath: args.sourcePath,
      overwrite: args.overwrite
    })
  }

  if (command === 'import_cases_from_txt') {
    return apiClient.post('/api/cases/import-txt', { filePaths: args.filePaths })
  }

  if (command === 'import_cases_excel') {
    return apiClient.post('/api/cases/import-excel', {
      filePath: args.filePath,
      overwrite: args.overwrite
    })
  }

  if (command === 'import_review_rules_excel') {
    return apiClient.post('/api/review-rules/import-excel', {
      filePath: args.filePath,
      overwrite: args.overwrite
    })
  }

  if (command === 'delete_case') {
    return apiClient.delete(`/api/cases/${encodeURIComponent(args.caseId)}`)
  }

  if (command === 'load_review_rule_library') {
    return apiClient.get('/api/review-rules')
  }

  if (command === 'save_review_rule_library') {
    return apiClient.put('/api/review-rules', args.rules || [])
  }

  if (command === 'clear_review_rule_library') {
    return apiClient.delete('/api/review-rules')
  }

  if (command === 'open_in_finder') {
    apiClient.open('/api/files/download', { path: args.path })
    return null
  }

  if (command === 'open_classified_dir') {
    apiClient.open('/api/browse', { path: `${args.workDir}/已分类材料` })
    return null
  }

  return apiClient.post(`/api/invoke/${command}`, args)
}
