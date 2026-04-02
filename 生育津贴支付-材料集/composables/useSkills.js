import { apiClient } from '../services/apiClient.js'

export function useSkills() {
  async function selectDirectory() {
    return await invoke('select_directory')
  }

  async function selectFile(filters) {
    return await invoke('select_file', { filters: filters || null })
  }

  async function readFactors(workDir) {
    return await invoke('read_factors', { workDir })
  }

  async function getMaterials(workDir) {
    return await invoke('get_materials', { workDir })
  }

  async function getMaterialCategories(workDir) {
    return await invoke('get_material_categories', { workDir })
  }

  async function getPendingFiles(workDir) {
    return await invoke('get_pending_files', { workDir })
  }

  async function loadCaseLibrary() {
    return await invoke('load_case_library')
  }

  async function searchCases(query) {
    return await invoke('search_cases', { query })
  }

  async function deleteCase(caseId) {
    return await invoke('delete_case', { caseId })
  }

  async function openClassifiedDir(workDir) {
    return await invoke('open_classified_dir', { workDir })
  }

  return {
    selectDirectory,
    selectFile,
    readFactors,
    getMaterials,
    getMaterialCategories,
    getPendingFiles,
    loadCaseLibrary,
    searchCases,
    deleteCase,
    openClassifiedDir
  }
}
