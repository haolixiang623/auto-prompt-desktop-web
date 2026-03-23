import { invoke } from '@tauri-apps/api/tauri'

export function useFileSystem() {
  async function readDirectory(path) {
    return await invoke('read_directory', { path })
  }

  async function readFile(path) {
    return await invoke('read_file', { path })
  }

  async function writeFile(path, content) {
    return await invoke('write_file', { path, content })
  }

  async function selectDirectory() {
    return await invoke('select_directory')
  }

  async function selectFile(filters) {
    return await invoke('select_file', { filters: filters || null })
  }

  return {
    readDirectory,
    readFile,
    writeFile,
    selectDirectory,
    selectFile
  }
}
