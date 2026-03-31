<template>
  <div class="h-full flex flex-col bg-gray-50 overflow-hidden">
    <!-- 顶栏 -->
    <div class="flex-shrink-0 bg-white border-b border-gray-200 px-6 py-4">
      <div class="flex items-center justify-between">
        <div>
          <h1 class="text-lg font-semibold text-gray-900">环境监测</h1>
          <p class="text-sm text-gray-500 mt-0.5">检测运行环境状态，确保所有依赖已正确安装</p>
        </div>
        <button
          @click="runCheck"
          :disabled="checking"
          class="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          <svg
            class="w-4 h-4"
            :class="{ 'animate-spin': checking }"
            fill="none" stroke="currentColor" viewBox="0 0 24 24"
          >
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
          </svg>
          {{ checking ? '检测中...' : '重新检测' }}
        </button>
      </div>
    </div>

    <!-- 主内容 -->
    <div class="flex-1 overflow-y-auto px-6 py-5 space-y-4">

      <!-- 初始/加载状态 -->
      <div v-if="!envStatus && !checking && !checkError" class="flex flex-col items-center justify-center py-20 text-gray-400">
        <svg class="w-16 h-16 mb-4 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
            d="M9 3H5a2 2 0 00-2 2v4m6-6h10a2 2 0 012 2v4M9 3v18m0 0h10a2 2 0 002-2V9M9 21H5a2 2 0 01-2-2V9m0 0h18"/>
        </svg>
        <p class="text-sm">点击「重新检测」开始环境检测</p>
      </div>

      <div v-if="checking" class="flex flex-col items-center justify-center py-20 text-gray-400">
        <svg class="w-10 h-10 mb-4 text-blue-400 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
            d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
        </svg>
        <p class="text-sm">正在检测环境...</p>
      </div>

      <div v-if="checkError" class="bg-red-50 border border-red-200 rounded-xl p-4 text-red-700 text-sm">
        检测失败：{{ checkError }}
      </div>

      <template v-if="envStatus && !checking">

        <!-- 整体状态横幅 -->
        <div
          class="rounded-xl p-4 flex items-center gap-4"
          :class="allGood ? 'bg-green-50 border border-green-200' : 'bg-amber-50 border border-amber-200'"
        >
          <div
            class="w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0"
            :class="allGood ? 'bg-green-100' : 'bg-amber-100'"
          >
            <svg class="w-5 h-5" :class="allGood ? 'text-green-600' : 'text-amber-600'" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path v-if="allGood" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
              <path v-else stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
            </svg>
          </div>
          <div class="flex-1">
            <div class="font-medium text-sm" :class="allGood ? 'text-green-800' : 'text-amber-800'">
              {{ allGood ? '所有依赖就绪，可以正常使用' : `存在 ${missingCount} 个未安装的依赖包` }}
            </div>
            <div class="text-xs mt-0.5" :class="allGood ? 'text-green-600' : 'text-amber-600'">
              {{ allGood ? 'Python 环境与所有依赖均已正确安装' : '请点击下方「一键安装缺失依赖」补全运行环境' }}
            </div>
          </div>
          <button
            v-if="!allGood"
            @click="console.log('Button clicked!'); installMissing()"
            :disabled="installing"
            class="flex items-center gap-1.5 px-3 py-1.5 bg-amber-600 text-white text-xs font-medium rounded-lg hover:bg-amber-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex-shrink-0"
            @mouseenter="console.log('Button mouseenter - installing:', installing, 'allGood:', allGood)"
          >
            <svg class="w-3.5 h-3.5" :class="{ 'animate-spin': installing }" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/>
            </svg>
            {{ installing ? '安装中...' : '一键安装缺失依赖' }}
          </button>
        </div>

        <!-- Python 环境 -->
        <div class="bg-white border border-gray-200 rounded-xl overflow-hidden">
          <div class="px-5 py-3.5 border-b border-gray-100 flex items-center gap-2">
            <svg class="w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4"/>
            </svg>
            <span class="text-sm font-semibold text-gray-700">Python 运行环境</span>
          </div>
          <div class="px-5 py-4 flex items-center justify-between">
            <div class="flex items-center gap-3">
              <StatusBadge :ok="envStatus.python.available" />
              <div>
                <div class="text-sm font-medium text-gray-800">
                  {{ envStatus.python.available ? envStatus.python.version : 'Python 未找到' }}
                </div>
                <div class="text-xs text-gray-500 mt-0.5">
                  {{ envStatus.python.available
                    ? `${getPythonCommandDisplay()} 可正常调用`
                    : envStatus.python.installable
                    ? getInstallMethodText()
                    : '请手动安装 Python 3.9+ 后重新检测' }}
                </div>
              </div>
            </div>
            <div class="flex items-center gap-2">
              <span
                class="text-xs px-2.5 py-1 rounded-full font-medium"
                :class="envStatus.python.available
                  ? 'bg-green-100 text-green-700'
                  : 'bg-red-100 text-red-700'"
              >
                {{ envStatus.python.available ? '正常' : '缺失' }}
              </span>
              <button
                v-if="!envStatus.python.available && envStatus.python.installable"
                @click="installPython"
                :disabled="installing"
                class="text-xs px-2.5 py-1 bg-blue-50 text-blue-600 rounded-lg hover:bg-blue-100 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium"
              >
                {{ installing ? '安装中...' : '在线安装' }}
              </button>
            </div>
          </div>
        </div>

        <!-- 依赖包 -->
        <div class="bg-white border border-gray-200 rounded-xl overflow-hidden">
          <div class="px-5 py-3.5 border-b border-gray-100 flex items-center gap-2">
            <svg class="w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4"/>
            </svg>
            <span class="text-sm font-semibold text-gray-700">Python 依赖包</span>
          </div>
          <div class="divide-y divide-gray-100">
            <div
              v-for="pkg in envStatus.packages"
              :key="pkg.name"
              class="px-5 py-4 flex items-center justify-between"
            >
              <div class="flex items-center gap-3 flex-1 min-w-0">
                <StatusBadge :ok="pkg.installed" />
                <div class="min-w-0">
                  <div class="flex items-center gap-2">
                    <span class="text-sm font-medium text-gray-800">{{ pkg.display_name }}</span>
                    <span v-if="pkg.installed" class="text-xs text-gray-400 font-mono">v{{ pkg.version }}</span>
                  </div>
                  <div class="text-xs text-gray-500 mt-0.5 truncate">{{ pkg.description }}</div>
                </div>
              </div>
              <div class="flex items-center gap-2 flex-shrink-0 ml-4">
                <span
                  class="text-xs px-2.5 py-1 rounded-full font-medium"
                  :class="pkg.installed
                    ? 'bg-green-100 text-green-700'
                    : 'bg-red-100 text-red-700'"
                >
                  {{ pkg.installed ? '已安装' : '未安装' }}
                </span>
                <button
                  v-if="!pkg.installed"
                  @click="installSingle(pkg.name)"
                  :disabled="installing"
                  class="text-xs px-2.5 py-1 bg-blue-50 text-blue-600 rounded-lg hover:bg-blue-100 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium"
                >
                  安装
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- API 配置状态 -->
        <div class="bg-white border border-gray-200 rounded-xl overflow-hidden">
          <div class="px-5 py-3.5 border-b border-gray-100 flex items-center gap-2">
            <svg class="w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z"/>
            </svg>
            <span class="text-sm font-semibold text-gray-700">API 配置</span>
          </div>
          <div class="px-5 py-4 flex items-center justify-between">
            <div class="flex items-center gap-3">
              <StatusBadge :ok="apiKeyConfigured" />
              <div>
                <div class="text-sm font-medium text-gray-800">
                  {{ apiKeyConfigured ? 'DASHSCOPE_API_KEY 已配置' : 'API Key 未配置' }}
                </div>
                <div class="text-xs text-gray-500 mt-0.5">
                  {{ apiKeyConfigured
                    ? '可正常调用 AI 模型接口'
                    : '请前往「设置」页面配置 API Key' }}
                </div>
              </div>
            </div>
            <div class="flex items-center gap-2">
              <span
                class="text-xs px-2.5 py-1 rounded-full font-medium"
                :class="apiKeyConfigured
                  ? 'bg-green-100 text-green-700'
                  : 'bg-amber-100 text-amber-700'"
              >
                {{ apiKeyConfigured ? '已配置' : '未配置' }}
              </span>
              <router-link
                v-if="!apiKeyConfigured && canManageSettings"
                to="/settings"
                class="text-xs px-2.5 py-1 bg-blue-50 text-blue-600 rounded-lg hover:bg-blue-100 transition-colors font-medium"
              >
                去设置
              </router-link>
            </div>
          </div>
        </div>

        <!-- 安装日志 -->
        <div v-if="installLog" class="bg-gray-900 rounded-xl overflow-hidden">
          <div class="px-4 py-2.5 border-b border-gray-800 flex items-center justify-between">
            <div class="flex items-center gap-2">
              <div class="w-2 h-2 rounded-full" :class="installSuccess ? 'bg-green-400' : 'bg-red-400'"></div>
              <span class="text-xs font-mono text-gray-400">安装日志</span>
            </div>
            <button @click="installLog = ''" class="text-xs text-gray-600 hover:text-gray-400">清除</button>
          </div>
          <pre class="px-4 py-3 text-xs font-mono text-gray-300 whitespace-pre-wrap max-h-48 overflow-y-auto leading-relaxed">{{ installLog }}</pre>
        </div>

      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { apiClient } from '../services/apiClient.js'
import { authState } from '../services/authState.js'

// ── 状态徽章子组件 ──────────────────────────────────────────
const StatusBadge = {
  props: { ok: Boolean },
  template: `
    <div class="w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0"
         :class="ok ? 'bg-green-100' : 'bg-red-100'">
      <svg class="w-4 h-4" :class="ok ? 'text-green-500' : 'text-red-500'"
           fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path v-if="ok" stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7"/>
        <path v-else stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M6 18L18 6M6 6l12 12"/>
      </svg>
    </div>
  `
}

// ── 状态变量 ────────────────────────────────────────────────
const checking = ref(false)
const checkError = ref('')
const envStatus = ref(null)
const installing = ref(false)
const installLog = ref('')
const installSuccess = ref(true)
const apiKeyConfigured = ref(false)
const canManageSettings = computed(() => authState.user?.role === 'admin')

// ── 计算属性 ────────────────────────────────────────────────
const allGood = computed(() => {
  if (!envStatus.value) return false
  return envStatus.value.python.available &&
    envStatus.value.packages.every(p => p.installed)
})

const missingCount = computed(() => {
  if (!envStatus.value) return 0
  return envStatus.value.packages.filter(p => !p.installed).length
})

// ── 检测环境 ────────────────────────────────────────────────
async function runCheck() {
  checking.value = true
  checkError.value = ''
  try {
    const [status, settings] = await Promise.all([
      invoke('check_environment'),
      invoke('load_settings')
    ])
    envStatus.value = status
    apiKeyConfigured.value = Boolean(settings.api_key_configured || (settings.api_key && settings.api_key.trim()))
  } catch (e) {
    checkError.value = String(e)
  } finally {
    checking.value = false
  }
}

// ── 安装指定包 ──────────────────────────────────────────────
async function installSingle(pkgName) {
  await doInstall([pkgName])
}

// ── 一键安装全部缺失 ────────────────────────────────────────
async function installMissing() {
  console.log('installMissing called')
  console.log('envStatus:', envStatus.value)
  console.log('installing:', installing.value)
  console.log('allGood:', allGood.value)
  
  if (!envStatus.value) {
    console.log('envStatus.value is null, returning')
    return
  }
  const missing = envStatus.value.packages
    .filter(p => !p.installed)
    .map(p => p.name)
  console.log('missing packages:', missing)
  await doInstall(missing)
}

async function doInstall(pkgs) {
  console.log('doInstall called with packages:', pkgs)
  installing.value = true
  installLog.value = `正在安装: ${pkgs.join(', ')}...\n`
  try {
    console.log('Calling invoke install_packages...')
    const result = await invoke('install_packages', { packages: pkgs })
    console.log('install_packages result:', result)
    installSuccess.value = result.success
    installLog.value += result.output
    if (result.success) {
      console.log('Installation successful, re-running check...')
      await runCheck()
    }
  } catch (e) {
    console.error('Installation error:', e)
    installSuccess.value = false
    installLog.value += `\n错误: ${e}`
  } finally {
    console.log('Installation finished, resetting installing flag')
    installing.value = false
  }
}

// ── 跨平台显示函数 ───────────────────────────────────────────
function getPythonCommandDisplay() {
  // 根据版本信息判断使用的命令
  const version = envStatus.value?.python?.version || ''
  if (version.includes('Python 3')) {
    return navigator.platform.includes('Win') ? 'python' : 'python3'
  }
  return 'python'
}

function getInstallMethodText() {
  if (navigator.platform.includes('Win')) {
    return '可使用 winget 在线安装 Python 3.11'
  } else if (navigator.platform.includes('Mac')) {
    return '可使用 brew 安装 Python: brew install python3'
  } else {
    return '可使用包管理器安装 Python'
  }
}

// ── 安装 Python ───────────────────────────────────────────────
async function installPython() {
  installing.value = true
  installLog.value = '正在在线安装 Python 3.11...\n'
  try {
    const result = await invoke('install_python')
    installSuccess.value = result.success
    installLog.value += result.output
    if (result.success) {
      installLog.value += '\n\n✅ Python 安装成功！请重启应用后重新检测环境。'
      if (result.requires_restart) {
        // 可以添加重启提示
      }
    }
  } catch (e) {
    installSuccess.value = false
    installLog.value += `\n错误: ${e}`
  } finally {
    installing.value = false
  }
}

// ── 页面挂载自动检测 ────────────────────────────────────────
onMounted(() => {
  runCheck()
})
</script>
