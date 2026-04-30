<template>
  <div class="h-full overflow-y-auto bg-gray-50">
    <!-- 顶部标题 -->
    <div class="bg-white border-b px-6 py-4">
      <h1 class="text-xl font-bold text-gray-900">设置</h1>
      <p class="text-sm text-gray-500 mt-0.5">配置应用参数和API密钥</p>
    </div>

    <!-- Tab 导航 -->
    <div class="bg-white border-b sticky top-0 z-10">
      <div class="flex px-6">
        <button v-for="tab in tabs" :key="tab.id"
          @click="activeTab = tab.id"
          class="px-4 py-3 text-sm font-medium border-b-2 transition-colors"
          :class="activeTab === tab.id
            ? 'border-blue-500 text-blue-600'
            : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'">
          {{ tab.name }}
        </button>
      </div>
    </div>

    <div class="p-6">
      <!-- 保存按钮 -->
      <div class="flex justify-end mb-4">
        <button
          @click="saveSettings"
          :disabled="saving"
          class="flex items-center gap-2 px-5 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 shadow-sm text-sm font-medium">
          <svg v-if="!saving" class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3m-1 4l-3 3m0 0l-3-3m3 3V4"/>
          </svg>
          <svg v-else class="w-4 h-4 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
          </svg>
          {{ saving ? '保存中...' : '保存设置' }}
        </button>
      </div>

      <!-- 状态提示 -->
      <transition name="fade">
        <div v-if="saveStatus" class="mb-4 p-3 rounded-lg text-sm"
          :class="saveStatus.type === 'success' ? 'bg-green-50 text-green-700 border border-green-200' : 'bg-red-50 text-red-700 border border-red-200'">
          {{ saveStatus.message }}
        </div>
      </transition>

      <!-- Tab 1: API 配置 -->
      <div v-show="activeTab === 'api'" class="space-y-4">
        <div class="bg-white rounded-xl shadow-sm border p-5">
          <h2 class="text-base font-semibold text-gray-800 mb-4">OpenAI 兼容 API 配置</h2>
          <div class="space-y-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-2">API Key</label>
              <div class="flex gap-2">
                <input
                  :type="showKey ? 'text' : 'password'"
                  v-model="apiKey"
                  placeholder="请输入默认 API Key（可选）"
                  autocomplete="off"
                  autocapitalize="off"
                  autocorrect="off"
                  spellcheck="false"
                  data-1p-ignore="true"
                  class="flex-1 px-4 py-2.5 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-300"
                />
                <button
                  @click="showKey = !showKey"
                  class="px-4 py-2.5 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 font-medium text-sm">
                  {{ showKey ? '隐藏' : '显示' }}
                </button>
                <button
                  @click="testApiKey"
                  :disabled="!apiKey || testing"
                  class="px-5 py-2.5 rounded-lg text-sm font-medium disabled:opacity-50 transition-colors min-w-[100px]"
                  :class="testStatus
                    ? (testStatus.type === 'success' ? 'bg-green-100 text-green-700 hover:bg-green-200' : 'bg-red-100 text-red-700 hover:bg-red-200')
                    : 'bg-gray-200 text-gray-700 hover:bg-gray-300'">
                  <span v-if="testing">测试中...</span>
                  <span v-else-if="testStatus && testStatus.type === 'success'">✓ 成功</span>
                  <span v-else-if="testStatus && testStatus.type === 'error'">✗ 失败</span>
                  <span v-else>测试连接</span>
                </button>
              </div>
              <p class="mt-2 text-sm text-gray-500">
                作为默认 API Key 使用；当模型配置中未单独填写 `api_key` 时会自动回退到这里。
              </p>
              <p
                class="mt-2 text-xs"
                :class="apiKeySaveState.tone === 'success' ? 'text-green-600' : apiKeySaveState.tone === 'warning' ? 'text-amber-600' : 'text-red-600'"
              >
                {{ apiKeySaveState.message }}
              </p>
              <p v-if="testStatus && testStatus.type === 'error'" class="mt-1 text-xs text-red-600">{{ testStatus.message }}</p>
            </div>
          </div>
        </div>
      </div>

      <!-- Tab 2: 生成配置 -->
      <div v-show="activeTab === 'generation'" class="space-y-4">
        <!-- 默认模型 -->
        <div class="bg-white rounded-xl shadow-sm border p-5">
          <h2 class="text-base font-semibold text-gray-800 mb-4">默认模型</h2>
          <div class="flex items-center gap-3 p-3 bg-amber-50 border border-amber-200 rounded-lg">
            <svg class="w-5 h-5 text-amber-500 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
              <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"/>
            </svg>
            <label class="text-sm font-medium text-amber-700 flex-shrink-0">生成默认使用</label>
            <select v-model="defaultModelId" class="flex-1 px-3 py-2 border border-amber-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-amber-300">
              <option v-for="m in models" :key="m.id" :value="m.id">{{ m.name }} ({{ m.model }})</option>
            </select>
          </div>
        </div>

        <!-- 超时设置 -->
        <div class="bg-white rounded-xl shadow-sm border p-5">
          <h2 class="text-base font-semibold text-gray-800 mb-4">超时设置</h2>
          <div class="flex items-center gap-4">
            <div class="flex items-center gap-2">
              <span class="text-sm text-gray-600">API 调用超时</span>
              <input
                v-model="llmTimeout"
                type="number"
                min="10"
                max="600"
                step="10"
                class="w-24 px-3 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-300"
              />
              <span class="text-sm text-gray-600">秒</span>
            </div>
            <span class="text-xs text-gray-400">建议值：120秒</span>
          </div>
        </div>

        <!-- 模型列表 -->
        <div class="bg-white rounded-xl shadow-sm border p-5">
          <div class="flex items-center justify-between mb-4">
            <h2 class="text-base font-semibold text-gray-800">模型列表</h2>
            <button @click="addModel"
              class="flex items-center gap-1.5 px-3 py-1.5 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
              </svg>
              添加模型
            </button>
          </div>

          <div class="space-y-2">
            <div v-for="(m, idx) in models" :key="m.id" class="rounded-lg border bg-gray-50">
              <div class="flex items-center gap-3 px-4 py-3">
                <span class="px-2 py-0.5 rounded text-xs font-medium flex-shrink-0"
                  :class="m.type === 'vl' ? 'bg-purple-100 text-purple-700' : 'bg-green-100 text-green-700'">
                  {{ m.type === 'vl' ? 'VL' : '文本' }}
                </span>
                <!-- 查看态 -->
                <div class="flex-1 min-w-0" v-if="editingIdx !== idx">
                  <div class="text-sm font-medium text-gray-800 truncate flex items-center gap-1.5">
                    {{ m.name }}
                    <span v-if="defaultModelId === m.id" class="text-xs text-amber-600 bg-amber-50 border border-amber-200 rounded px-1.5">默认</span>
                  </div>
                  <div class="text-xs text-gray-400 truncate font-mono">{{ m.model }}</div>
                  <div class="text-[11px] text-gray-400 truncate">{{ m.base_url }}</div>
                </div>
                <!-- 编辑态 -->
                <div class="flex-1 min-w-0 grid gap-2 lg:grid-cols-4" v-else>
                  <input v-model="editBuf.name" placeholder="显示名称" class="flex-1 px-2 py-1 border rounded text-sm" />
                  <input v-model="editBuf.model" placeholder="model" class="flex-1 px-2 py-1 border rounded text-sm font-mono" />
                  <input v-model="editBuf.base_url" placeholder="base_url" class="flex-1 px-2 py-1 border rounded text-sm font-mono" />
                  <input v-model="editBuf.api_key" placeholder="api_key（留空则使用默认）" class="flex-1 px-2 py-1 border rounded text-sm font-mono" />
                  <select v-model="editBuf.type" class="px-2 py-1 border rounded text-sm">
                    <option value="vl">VL</option>
                    <option value="text">文本</option>
                  </select>
                </div>
                <!-- 操作按钮 -->
                <div class="flex gap-1.5 flex-shrink-0">
                  <template v-if="editingIdx !== idx">
                    <button
                      @click="testModel(idx)"
                      :disabled="Boolean(modelTestStates[m.id]?.loading)"
                      class="px-2.5 py-1 text-xs rounded transition"
                      :class="modelTestStates[m.id]?.type === 'success'
                        ? 'bg-green-100 text-green-700 hover:bg-green-200'
                        : modelTestStates[m.id]?.type === 'error'
                          ? 'bg-red-100 text-red-700 hover:bg-red-200'
                          : 'bg-blue-100 text-blue-700 hover:bg-blue-200'">
                      {{ modelTestStates[m.id]?.loading ? '测试中...' : '测试' }}
                    </button>
                    <button @click="startEdit(idx)" class="px-2.5 py-1 text-xs bg-gray-200 text-gray-600 rounded hover:bg-gray-300">编辑</button>
                    <button v-if="deleteConfirmIdx !== idx" @click="deleteConfirmIdx = idx"
                      class="px-2.5 py-1 text-xs bg-red-100 text-red-600 rounded hover:bg-red-200">删除</button>
                    <template v-else>
                      <span class="text-xs text-red-600 font-medium">确认?</span>
                      <button @click="deleteModel(idx)" class="px-2.5 py-1 text-xs bg-red-600 text-white rounded hover:bg-red-700">是</button>
                      <button @click="deleteConfirmIdx = -1" class="px-2.5 py-1 text-xs bg-gray-200 text-gray-600 rounded hover:bg-gray-300">否</button>
                    </template>
                  </template>
                  <template v-else>
                    <button
                      @click="testModel(idx)"
                      :disabled="Boolean(modelTestStates[m.id]?.loading)"
                      class="px-2.5 py-1 text-xs rounded transition"
                      :class="modelTestStates[m.id]?.type === 'success'
                        ? 'bg-green-100 text-green-700 hover:bg-green-200'
                        : modelTestStates[m.id]?.type === 'error'
                          ? 'bg-red-100 text-red-700 hover:bg-red-200'
                          : 'bg-blue-100 text-blue-700 hover:bg-blue-200'">
                      {{ modelTestStates[m.id]?.loading ? '测试中...' : '测试' }}
                    </button>
                    <button @click="confirmEdit(idx)" class="px-2.5 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700">保存</button>
                    <button @click="cancelEdit" class="px-2.5 py-1 text-xs bg-gray-200 text-gray-600 rounded hover:bg-gray-300">取消</button>
                  </template>
                </div>
              </div>
              <div
                v-if="modelTestStates[m.id]"
                class="border-t px-4 py-2 text-xs flex items-center justify-between gap-3"
                :class="modelTestStates[m.id]?.type === 'success'
                  ? 'bg-green-50 text-green-700 border-green-100'
                  : modelTestStates[m.id]?.type === 'error'
                    ? 'bg-red-50 text-red-700 border-red-100'
                    : 'bg-blue-50 text-blue-700 border-blue-100'">
                <span class="truncate">{{ modelTestStates[m.id]?.message }}</span>
                <button @click="clearModelTestState(m.id)" class="text-gray-400 hover:text-gray-600 flex-shrink-0">清除</button>
              </div>
              <!-- 参数编辑区 -->
              <div v-if="editingIdx === idx" class="border-t px-4 py-3 bg-white rounded-b-lg">
                <div class="flex items-center justify-between mb-2">
                  <span class="text-xs font-medium text-gray-500">额外参数</span>
                  <button @click="addParam" class="text-xs text-blue-600 hover:text-blue-800 flex items-center gap-0.5">
                    <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/></svg>
                    添加
                  </button>
                </div>
                <div v-if="editBuf.params.length === 0" class="text-xs text-gray-400 py-1">
                  暂无额外参数（如需禁用 thinking 模式，添加 <code class="bg-gray-100 px-1 rounded">enable_thinking=false</code>）
                </div>
                <div v-for="(p, pi) in editBuf.params" :key="pi" class="flex items-center gap-2 mb-1.5">
                  <input v-model="p.key" placeholder="参数名" class="flex-1 px-2 py-1 border rounded text-xs font-mono" />
                  <select v-model="p.valueType" @change="onParamTypeChange(p)" class="px-2 py-1 border rounded text-xs w-20">
                    <option value="bool">布尔</option>
                    <option value="string">字符串</option>
                    <option value="number">数字</option>
                  </select>
                  <template v-if="p.valueType === 'bool'">
                    <select v-model="p.boolVal" class="px-2 py-1 border rounded text-xs w-20">
                      <option :value="true">true</option>
                      <option :value="false">false</option>
                    </select>
                  </template>
                  <template v-else>
                    <input v-model="p.strVal" :placeholder="p.valueType === 'number' ? '数值' : '字符串'" class="w-28 px-2 py-1 border rounded text-xs font-mono" />
                  </template>
                  <button @click="removeParam(pi)" class="text-red-400 hover:text-red-600 p-0.5">
                    <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
                  </button>
                </div>
              </div>
            </div>
            <div v-if="models.length === 0" class="text-sm text-gray-400 text-center py-4">暂无模型配置</div>
          </div>
        </div>
      </div>

      <!-- Tab 3: 提示词配置 -->
      <div v-show="activeTab === 'prompts'" class="space-y-4">
        <div class="bg-white rounded-xl shadow-sm border p-5">
          <div class="flex items-center justify-between mb-3">
            <div>
              <h2 class="text-base font-semibold text-gray-800">造物主提示词 · 分类优化</h2>
              <p class="text-xs text-gray-400 mt-1">用于 AI 迭代优化「材料分类」提示词</p>
            </div>
            <button @click="godPrompt = defaultGodPrompts.classify" class="text-xs text-gray-400 hover:text-blue-600 px-2 py-1">恢复默认</button>
          </div>
          <textarea v-model="godPrompt" rows="8"
            class="w-full px-3 py-2 border rounded-lg text-sm font-mono leading-relaxed resize-y focus:outline-none focus:ring-2 focus:ring-blue-300 bg-gray-50"></textarea>
        </div>

        <div class="bg-white rounded-xl shadow-sm border p-5">
          <div class="flex items-center justify-between mb-3">
            <div>
              <h2 class="text-base font-semibold text-gray-800">造物主提示词 · 要素提取</h2>
              <p class="text-xs text-gray-400 mt-1">用于「要素提示词」功能生成提取规则</p>
            </div>
            <button @click="extractGodPrompt = defaultGodPrompts.extract" class="text-xs text-gray-400 hover:text-blue-600 px-2 py-1">恢复默认</button>
          </div>
          <textarea v-model="extractGodPrompt" rows="8"
            class="w-full px-3 py-2 border rounded-lg text-sm font-mono leading-relaxed resize-y focus:outline-none focus:ring-2 focus:ring-blue-300 bg-gray-50"></textarea>
        </div>
      </div>

      <!-- Tab 4: 关于 -->
      <div v-show="activeTab === 'about'" class="space-y-4">
        <div class="bg-white rounded-xl shadow-sm border p-5">
          <h2 class="text-base font-semibold text-gray-800 mb-4">当前状态</h2>
          <div class="space-y-3 text-sm">
            <div class="flex items-center gap-3">
              <span
                class="w-2 h-2 rounded-full"
                :class="apiKeySaveState.tone === 'success' ? 'bg-green-500' : apiKeySaveState.tone === 'warning' ? 'bg-amber-500' : 'bg-red-500'"
              ></span>
              <span class="text-gray-600">API密钥:</span>
              <span :class="apiKeySaveState.tone === 'success' ? 'text-green-600' : apiKeySaveState.tone === 'warning' ? 'text-amber-600' : 'text-red-600'">
                {{ apiKeySaveState.label }}
              </span>
            </div>
            <div class="flex items-center gap-3">
              <span class="w-2 h-2 rounded-full bg-green-500"></span>
              <span class="text-gray-600">应用版本:</span>
              <span class="text-gray-800">v0.1.0</span>
            </div>
            <div class="flex items-center gap-3">
              <span class="w-2 h-2 rounded-full bg-green-500"></span>
              <span class="text-gray-600">模型数量:</span>
              <span class="text-gray-800">{{ models.length }} 个</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, onMounted, onActivated } from 'vue'
import { invoke } from '../tauri/tauri.js'
import { getApiKeySaveState } from './settingsState.js'

const OPENAI_COMPAT_BASE_URL = 'https://api.openai.com/v1'
const DASHSCOPE_COMPAT_BASE_URL = 'https://dashscope.aliyuncs.com/compatible-mode/v1'

const apiKey = ref('')
const savedApiKey = ref('')
const apiKeyConfigured = ref(false)
const modelName = ref('qwen-vl-max')
const models = ref([])
const defaultModelId = ref('')
const showKey = ref(false)
const saving = ref(false)
const testing = ref(false)
const saveStatus = ref(null)
const testStatus = ref(null)
const deleteConfirmIdx = ref(-1)

// Tab 配置
const activeTab = ref('api')
const tabs = [
  { id: 'api', name: 'API 配置' },
  { id: 'generation', name: '生成配置' },
  { id: 'prompts', name: '提示词配置' },
  { id: 'about', name: '关于' },
]

const godPrompt = ref('')
const extractGodPrompt = ref('')
const llmTimeout = ref(120)
const defaultGodPrompts = ref({ classify: '', extract: '' })
const editingIdx = ref(-1)
const editBuf = ref({ name: '', model: '', base_url: OPENAI_COMPAT_BASE_URL, api_key: '', type: 'vl', params: [] })
const modelTestStates = ref({})
const apiKeySaveState = computed(() => getApiKeySaveState({
  apiKey: apiKey.value,
  savedApiKey: savedApiKey.value,
  apiKeyConfigured: apiKeyConfigured.value
}))

function normalizeModel(model) {
  const legacyStyle = Object.prototype.hasOwnProperty.call(model || {}, 'model_id') || !model?.base_url
  return {
    ...model,
    model: model?.model || model?.model_id || '',
    base_url: model?.base_url || (legacyStyle ? DASHSCOPE_COMPAT_BASE_URL : OPENAI_COMPAT_BASE_URL),
    api_key: model?.api_key || '',
    type: model?.type || 'vl',
    params: model?.params || []
  }
}

function paramToEditItem(p) {
  if (typeof p.value === 'boolean') {
    return { key: p.key, valueType: 'bool', boolVal: p.value, strVal: '' }
  } else if (typeof p.value === 'number') {
    return { key: p.key, valueType: 'number', boolVal: false, strVal: String(p.value) }
  } else {
    return { key: p.key, valueType: 'string', boolVal: false, strVal: String(p.value ?? '') }
  }
}

function editItemToParam(p) {
  let value
  if (p.valueType === 'bool') value = p.boolVal
  else if (p.valueType === 'number') value = Number(p.strVal)
  else value = p.strVal
  return { key: p.key, value }
}

function startEdit(idx) {
  editingIdx.value = idx
  deleteConfirmIdx.value = -1
  const m = models.value[idx]
  editBuf.value = {
    name: m.name,
    model: m.model,
    base_url: m.base_url || OPENAI_COMPAT_BASE_URL,
    api_key: m.api_key || '',
    type: m.type,
    params: (m.params || []).map(paramToEditItem)
  }
}
function cancelEdit() { editingIdx.value = -1 }
function confirmEdit(idx) {
  models.value[idx] = {
    ...models.value[idx],
    name: editBuf.value.name,
    model: editBuf.value.model,
    base_url: editBuf.value.base_url,
    api_key: editBuf.value.api_key,
    type: editBuf.value.type,
    params: editBuf.value.params.filter(p => p.key.trim()).map(editItemToParam)
  }
  editingIdx.value = -1
}
function addModel() {
  const newId = String(Date.now())
  models.value.unshift({ id: newId, name: '新模型', model: '', base_url: OPENAI_COMPAT_BASE_URL, api_key: '', type: 'vl', params: [] })
  startEdit(0)
}
function deleteModel(idx) {
  const m = models.value[idx]
  if (defaultModelId.value === m.id) {
    defaultModelId.value = models.value[idx === 0 ? 1 : 0]?.id ?? ''
  }
  models.value.splice(idx, 1)
  deleteConfirmIdx.value = -1
}

function addParam() {
  editBuf.value.params.push({ key: '', valueType: 'bool', boolVal: false, strVal: '' })
}
function removeParam(pi) {
  editBuf.value.params.splice(pi, 1)
}
function onParamTypeChange(p) {
  if (p.valueType === 'bool') p.boolVal = false
  else p.strVal = ''
}

function clearModelTestState(modelId) {
  const next = { ...modelTestStates.value }
  delete next[modelId]
  modelTestStates.value = next
}

function buildModelPayloadForTest(idx) {
  const current = models.value[idx]
  if (!current) return null
  if (editingIdx.value === idx) {
    return normalizeModel({
      ...current,
      name: editBuf.value.name,
      model: editBuf.value.model,
      base_url: editBuf.value.base_url,
      api_key: editBuf.value.api_key,
      type: editBuf.value.type,
      params: editBuf.value.params.filter(p => p.key.trim()).map(editItemToParam)
    })
  }
  return normalizeModel(current)
}

async function testModel(idx) {
  const current = models.value[idx]
  if (!current) return
  const modelId = current.id
  const payload = buildModelPayloadForTest(idx)
  modelTestStates.value = {
    ...modelTestStates.value,
    [modelId]: { loading: true, type: 'loading', message: '正在测试模型连接...' }
  }
  try {
    const result = await invoke('test_model_config', {
      model: payload,
      fallbackApiKey: apiKey.value,
      timeout: llmTimeout.value
    })
    const detail = [
      result.model ? `模型: ${result.model}` : '',
      Number.isFinite(result.elapsed_s) ? `${result.elapsed_s}s` : '',
      result.preview ? `返回: ${result.preview}` : ''
    ].filter(Boolean).join(' · ')
    modelTestStates.value = {
      ...modelTestStates.value,
      [modelId]: { loading: false, type: 'success', message: detail || '连接成功' }
    }
  } catch (error) {
    modelTestStates.value = {
      ...modelTestStates.value,
      [modelId]: { loading: false, type: 'error', message: `测试失败: ${String(error)}` }
    }
  }
}

let saveStatusTimer = null
let testStatusTimer = null

const DEFAULT_MODELS = [
  { id: '1', name: 'Qwen VL Max', model: 'qwen-vl-max', base_url: DASHSCOPE_COMPAT_BASE_URL, api_key: '', type: 'vl', params: [] },
  { id: '2', name: 'Qwen VL Plus', model: 'qwen-vl-plus', base_url: DASHSCOPE_COMPAT_BASE_URL, api_key: '', type: 'vl', params: [] },
  { id: '3', name: 'Qwen2.5 VL 72B', model: 'qwen2.5-vl-72b-instruct', base_url: DASHSCOPE_COMPAT_BASE_URL, api_key: '', type: 'vl', params: [] },
  { id: '4', name: 'Qwen Plus (文本)', model: 'qwen-plus', base_url: DASHSCOPE_COMPAT_BASE_URL, api_key: '', type: 'text', params: [] },
  { id: '5', name: 'Qwen Max (文本)', model: 'qwen-max', base_url: DASHSCOPE_COMPAT_BASE_URL, api_key: '', type: 'text', params: [] },
]

async function loadSettings() {
  try {
    const settings = await invoke('load_settings')
    apiKey.value = settings.api_key || ''
    savedApiKey.value = settings.api_key || ''
    apiKeyConfigured.value = Boolean(settings.api_key_configured)
    modelName.value = settings.model_name || 'qwen-vl-max'
    models.value = (settings.models && settings.models.length > 0)
      ? settings.models.map(normalizeModel)
      : DEFAULT_MODELS
    defaultModelId.value = settings.default_model_id || (models.value[0]?.id ?? '')
    godPrompt.value = settings.god_prompt || ''
    extractGodPrompt.value = settings.extract_god_prompt || ''
    llmTimeout.value = settings.llm_timeout || 120
  } catch (error) {
    console.error('Failed to load settings:', error)
    models.value = DEFAULT_MODELS
  }

  try {
    const defaults = await invoke('get_default_god_prompts')
    defaultGodPrompts.value = defaults
    // Pre-fill if empty
    if (!godPrompt.value) godPrompt.value = defaults.classify
    if (!extractGodPrompt.value) extractGodPrompt.value = defaults.extract
  } catch (error) {
    console.error('Failed to load default god prompts:', error)
  }
}

onMounted(loadSettings)
onActivated(loadSettings)

async function saveSettings() {
  saving.value = true
  clearTimeout(saveStatusTimer)
  try {
    const selectedDefaultModel = models.value.find(m => m.id === defaultModelId.value)
    await invoke('save_settings', { settings: {
      api_key: apiKey.value,
      model_name: selectedDefaultModel?.model || modelName.value,
      default_model_id: defaultModelId.value,
      models: models.value,
      god_prompt: godPrompt.value,
      extract_god_prompt: extractGodPrompt.value,
      llm_timeout: llmTimeout.value
    }})
    savedApiKey.value = apiKey.value
    apiKeyConfigured.value = Boolean(apiKey.value || models.value.some(model => model.api_key && model.api_key.trim()))
    saveStatus.value = { type: 'success', message: '✓ 已保存' }
  } catch (error) {
    saveStatus.value = { type: 'error', message: `保存失败: ${error}` }
  } finally {
    saving.value = false
    saveStatusTimer = setTimeout(() => { saveStatus.value = null }, 3000)
  }
}

async function testApiKey() {
  testing.value = true
  testStatus.value = null
  clearTimeout(testStatusTimer)
  try {
    await invoke('test_api_key', { apiKey: apiKey.value })
    testStatus.value = { type: 'success' }
  } catch (error) {
    testStatus.value = { type: 'error', message: String(error) }
  } finally {
    testing.value = false
    testStatusTimer = setTimeout(() => { testStatus.value = null }, 5000)
  }
}

</script>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.3s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
