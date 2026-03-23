<template>
  <div class="flex h-full min-h-0">

    <!-- ═══ 左侧 Step 导航 ═══ -->
    <div class="w-56 flex-shrink-0 bg-white border-r flex flex-col">
      <div class="px-5 pt-6 pb-4 border-b">
        <h1 class="text-base font-bold text-gray-900 leading-tight">审查规则生成</h1>
        <p class="text-xs text-gray-400 mt-1 leading-relaxed">从 factors.xlsx 生成审查规则 JSON</p>
      </div>

      <nav class="flex-1 py-4 px-3 space-y-1">
        <button v-for="(s, i) in steps" :key="i"
          @click="goStepNav(i + 1)"
          :disabled="i + 1 > maxReachableStep"
          class="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left transition-all"
          :class="[
            currentStep === i + 1 ? 'bg-blue-50 text-blue-700'
            : currentStep > i + 1 ? 'text-green-700 hover:bg-green-50 cursor-pointer'
            : i + 1 <= maxReachableStep ? 'text-gray-500 hover:bg-gray-50 cursor-pointer'
            : 'text-gray-300 cursor-not-allowed'
          ]">
          <div class="w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 text-xs font-bold transition-all"
            :class="[
              currentStep > i + 1 ? 'bg-green-500 text-white'
              : currentStep === i + 1 ? 'bg-blue-600 text-white ring-4 ring-blue-100'
              : i + 1 <= maxReachableStep ? 'bg-gray-200 text-gray-500'
              : 'bg-gray-100 text-gray-300'
            ]">
            <svg v-if="currentStep > i + 1" class="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/>
            </svg>
            <span v-else>{{ i + 1 }}</span>
          </div>
          <div class="flex-1 min-w-0">
            <div class="text-xs font-semibold truncate">{{ s.title }}</div>
            <div class="text-xs truncate mt-0.5"
              :class="currentStep === i + 1 ? 'text-blue-500' : currentStep > i + 1 ? 'text-green-500' : 'text-gray-400'">
              {{ currentStep > i + 1 ? s.done : currentStep === i + 1 ? s.active : s.pending }}
            </div>
          </div>
          <div v-if="currentStep === i + 1" class="w-1 h-5 rounded-full bg-blue-500 flex-shrink-0"></div>
        </button>
      </nav>

      <div class="px-3 pb-4 pt-2 border-t space-y-2">
        <div v-if="isRunning" class="flex items-center gap-2 px-3 py-2 bg-blue-50 rounded-lg">
          <svg class="animate-spin w-3.5 h-3.5 text-blue-500 flex-shrink-0" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
          </svg>
          <span class="text-xs text-blue-600">生成中...</span>
        </div>
        <button @click="clear" :disabled="isRunning"
          class="w-full flex items-center justify-center gap-1.5 px-3 py-2 text-xs text-gray-500 border border-gray-200 rounded-lg hover:bg-gray-50 hover:text-gray-700 disabled:opacity-40 transition">
          <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
          </svg>
          重新开始
        </button>
      </div>
    </div>

    <!-- ═══ 右侧内容区 ═══ -->
    <div class="flex-1 overflow-y-auto bg-gray-50">
      <div class="p-6 max-w-3xl">

        <!-- ── STEP 1：配置与生成 ── -->
        <div v-if="currentStep === 1" class="space-y-4">
          <div>
            <span class="text-lg font-bold text-gray-900">配置生成参数</span>
            <p class="text-sm text-gray-500 mt-1">上传材料工作区与推理模型，自动分析审查要点规则并生成 JSON</p>
          </div>

          <!-- 工作区选择 -->
          <div class="bg-white rounded-xl border p-5 space-y-3">
            <div class="text-sm font-semibold text-gray-700">材料工作区</div>
            <div class="flex gap-2">
              <input v-model="workDir" type="text" placeholder="上传后会显示服务端工作区路径"
                class="flex-1 px-3 py-2 border rounded-lg text-sm bg-gray-50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-300" readonly />
              <button @click="selectWorkDir"
                class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm transition font-medium">
                上传文件夹...
              </button>
            </div>
            <p class="text-xs text-gray-400">
              审查要点规则说明列用 <code class="bg-gray-100 px-1 rounded">#材料名称-字段名称#</code> 引用要素；空审查要点名称行自动跳过
            </p>
          </div>

          <!-- 推理模型配置 -->
          <div class="bg-white rounded-xl border p-5 space-y-3">
            <div class="flex items-center justify-between">
              <div>
                <div class="text-sm font-semibold text-gray-700">LLM 推理模型</div>
                <div class="text-xs text-gray-400 mt-0.5">由大模型分析规则类型，比关键词匹配更准确</div>
              </div>
              <label class="relative inline-flex items-center cursor-pointer">
                <input type="checkbox" v-model="useLlm" class="sr-only peer" />
                <div class="w-10 h-6 bg-gray-200 peer-focus:outline-none rounded-full peer
                  peer-checked:after:translate-x-4 after:content-[''] after:absolute after:top-0.5 after:left-0.5
                  after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
              </label>
            </div>

            <div v-if="useLlm">
              <!-- 模型选择 -->
              <div class="space-y-2">
                <label class="block text-xs font-medium text-gray-500">选择模型（来自设置）</label>
                <div v-if="availableModels.length === 0" class="text-xs text-amber-600 bg-amber-50 px-3 py-2 rounded-lg">
                  未找到可用模型，请先在「设置」中配置模型列表
                </div>
                <div v-else class="grid grid-cols-2 gap-2">
                  <button v-for="m in availableModels" :key="m.id"
                    @click="selectedModelId = m.id"
                    class="flex items-center gap-2 px-3 py-2 rounded-lg border text-xs text-left transition"
                    :class="selectedModelId === m.id
                      ? 'border-blue-500 bg-blue-50 text-blue-700'
                      : 'border-gray-200 bg-white text-gray-600 hover:border-gray-300'">
                    <div class="w-5 h-5 rounded-full flex items-center justify-center flex-shrink-0"
                      :class="selectedModelId === m.id ? 'bg-blue-500' : 'bg-gray-200'">
                      <svg v-if="selectedModelId === m.id" class="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
                        <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/>
                      </svg>
                    </div>
                    <div class="min-w-0">
                      <div class="font-medium truncate">{{ m.name }}</div>
                      <div class="text-gray-400 truncate">{{ m.model_id }}</div>
                    </div>
                  </button>
                </div>
              </div>
            </div>

            <div v-else class="text-xs text-gray-400 bg-gray-50 px-3 py-2 rounded-lg">
              关闭时使用本地关键词规则推断（速度快，无需API调用）
            </div>
          </div>

          <!-- 推断逻辑说明 -->
          <div class="bg-amber-50 border border-amber-200 rounded-xl p-4">
            <div class="text-xs font-semibold text-amber-800 mb-2">规则类型自动推断逻辑</div>
            <div class="grid grid-cols-3 gap-2 text-xs">
              <div class="bg-white rounded-lg p-3 border border-amber-100">
                <div class="font-semibold text-blue-600 mb-1">规则对比 (2)</div>
                <div class="text-gray-500">含 <code class="bg-gray-100 px-0.5 rounded">#材料-字段#</code> + 比较词（一致/等于/包含等）</div>
              </div>
              <div class="bg-white rounded-lg p-3 border border-amber-100">
                <div class="font-semibold text-purple-600 mb-1">大模型 (1)</div>
                <div class="text-gray-500">无明确要素引用，或描述模糊</div>
              </div>
              <div class="bg-white rounded-lg p-3 border border-amber-100">
                <div class="font-semibold text-orange-600 mb-1">Groovy脚本 (3)</div>
                <div class="text-gray-500">复杂算法（计算/天数/正则等）</div>
              </div>
            </div>
          </div>

          <!-- 操作按钮 -->
          <div class="flex gap-3">
            <button @click="generate" :disabled="!workDir || isRunning"
              class="flex items-center gap-2 px-6 py-2.5 rounded-lg text-sm font-medium transition"
              :class="workDir && !isRunning ? 'bg-blue-600 text-white hover:bg-blue-700' : 'bg-gray-200 text-gray-400 cursor-not-allowed'">
              <svg v-if="isRunning" class="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
              </svg>
              <svg v-else class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>
              </svg>
              {{ isRunning ? '生成中...' : '开始生成' }}
            </button>
          </div>

          <!-- 执行日志 -->
          <div v-if="logs.length > 0" class="bg-gray-900 rounded-xl overflow-hidden">
            <div class="flex items-center justify-between px-4 py-2.5 border-b border-gray-800">
              <div class="flex items-center gap-2">
                <span v-if="isRunning" class="flex items-center gap-1.5">
                  <span class="w-2 h-2 rounded-full bg-green-400 animate-pulse"></span>
                  <span class="text-xs text-green-400">运行中</span>
                </span>
                <span v-else class="text-xs text-gray-500">执行日志</span>
                <span class="text-xs text-gray-600">{{ logs.length }} 条</span>
              </div>
              <button @click="logs = []" class="text-xs text-gray-600 hover:text-gray-400">清空</button>
            </div>
            <div ref="logContainer" class="p-3 space-y-0.5 max-h-48 overflow-y-auto">
              <div v-for="(log, i) in logs" :key="i" class="flex gap-2 text-xs font-mono leading-5">
                <span class="text-gray-600 flex-shrink-0 tabular-nums">{{ log.time }}</span>
                <span :class="getLogClass(log.type)" class="break-all">{{ log.message }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- ── STEP 2：审查要点审核与校验方式修改 ── -->
        <div v-if="currentStep === 2" class="space-y-4">
          <div class="flex items-center justify-between">
            <div>
              <span class="text-lg font-bold text-gray-900">审查要点审核</span>
              <p class="text-sm text-gray-500 mt-1">
                共生成 <span class="font-medium text-gray-700">{{ results.filter(r => r.success).length }}</span> 个材料 ·
                <span class="font-medium text-gray-700">{{ totalKeypointCount }}</span> 个审查要点
              </p>
            </div>
            <!-- 规则类型统计 -->
            <div class="flex items-center gap-2 text-xs">
              <span class="px-2 py-1 bg-blue-100 text-blue-700 rounded-full font-medium">规则对比 ×{{ ruleTypeCounts[2] || 0 }}</span>
              <span class="px-2 py-1 bg-purple-100 text-purple-700 rounded-full font-medium">大模型 ×{{ ruleTypeCounts[1] || 0 }}</span>
              <span class="px-2 py-1 bg-orange-100 text-orange-700 rounded-full font-medium">Groovy ×{{ ruleTypeCounts[3] || 0 }}</span>
            </div>
          </div>

          <!-- 失败项提示 -->
          <div v-if="results.some(r => !r.success)" class="bg-red-50 border border-red-200 rounded-xl p-3">
            <div class="text-xs font-medium text-red-700 mb-1">以下材料生成失败：</div>
            <div v-for="r in results.filter(r => !r.success)" :key="r.material" class="text-xs text-red-600">
              {{ r.material }}：{{ r.error }}
            </div>
          </div>

          <!-- 材料列表 Accordion -->
          <div v-for="r in results.filter(r => r.success)" :key="r.material"
            class="bg-white rounded-xl border overflow-hidden">

            <!-- 材料标题栏 -->
            <div class="flex items-center gap-3 px-4 py-3 cursor-pointer hover:bg-gray-50 transition"
              @click="toggleMaterial(r.material)">
              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2">
                  <span class="text-sm font-semibold text-gray-800">{{ r.material }}</span>
                  <span class="text-xs text-gray-400">{{ r.keypoint_count }} 个要点</span>
                  <!-- 校验方式分布 -->
                  <div class="flex gap-1 ml-1">
                    <span v-if="getMaterialRuleCounts(r.material)[2]" class="px-1.5 py-0.5 bg-blue-100 text-blue-600 rounded text-xs">规则对比×{{ getMaterialRuleCounts(r.material)[2] }}</span>
                    <span v-if="getMaterialRuleCounts(r.material)[1]" class="px-1.5 py-0.5 bg-purple-100 text-purple-600 rounded text-xs">大模型×{{ getMaterialRuleCounts(r.material)[1] }}</span>
                    <span v-if="getMaterialRuleCounts(r.material)[3]" class="px-1.5 py-0.5 bg-orange-100 text-orange-600 rounded text-xs">Groovy×{{ getMaterialRuleCounts(r.material)[3] }}</span>
                  </div>
                </div>
                <div class="text-xs text-gray-400 truncate mt-0.5">{{ r.output }}</div>
              </div>
              <div class="flex items-center gap-2 flex-shrink-0">
                <!-- 修改标记 -->
                <span v-if="hasPendingChanges(r.material)" class="text-xs text-amber-600 bg-amber-50 px-2 py-0.5 rounded-full border border-amber-200">有改动</span>
                <!-- 保存按钮 -->
                <button v-if="hasPendingChanges(r.material)"
                  @click.stop="saveChanges(r)"
                  :disabled="isSaving === r.material"
                  class="flex items-center gap-1 px-2.5 py-1 bg-green-600 text-white rounded-lg text-xs hover:bg-green-700 transition">
                  <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3m-1 4l-3 3m0 0l-3-3m3 3V4"/>
                  </svg>
                  {{ isSaving === r.material ? '保存中...' : '保存' }}
                </button>
                <button @click.stop="openInFinder(r.output)"
                  class="flex items-center gap-1 px-2.5 py-1 bg-gray-100 text-gray-600 rounded-lg text-xs hover:bg-gray-200 transition">
                  <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"/>
                  </svg>
                  打开位置
                </button>
                <button @click.stop="copyMaterialJson(r)"
                  class="flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs transition"
                  :class="copiedItem === r.material ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'">
                  {{ copiedItem === r.material ? '已复制' : '复制JSON' }}
                </button>
                <svg class="w-4 h-4 text-gray-400 transition-transform"
                  :class="expandedMaterials.includes(r.material) ? 'rotate-180' : ''"
                  fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
                </svg>
              </div>
            </div>

            <!-- 要点列表展开 -->
            <div v-if="expandedMaterials.includes(r.material)" class="border-t divide-y">
              <div v-if="!keypointData[r.material]" class="py-6 text-center text-sm text-gray-400">
                加载中...
              </div>
              <div v-else-if="keypointData[r.material].length === 0" class="py-4 text-center text-sm text-gray-400">
                无审查要点
              </div>
              <div v-else v-for="(kp, idx) in keypointData[r.material]" :key="idx"
                class="px-4 py-3 hover:bg-gray-50 transition">
                <div class="flex items-start gap-3">
                  <!-- 序号 -->
                  <div class="w-6 h-6 rounded-full bg-gray-100 flex items-center justify-center text-xs text-gray-500 flex-shrink-0 mt-0.5">
                    {{ idx + 1 }}
                  </div>
                  <!-- 要点信息 -->
                  <div class="flex-1 min-w-0">
                    <div class="flex items-center gap-2 flex-wrap mb-1">
                      <span class="text-sm font-medium text-gray-800">{{ kp.kpname }}</span>
                      <!-- 当前规则类型标签 -->
                      <span class="px-2 py-0.5 rounded-full text-xs font-medium"
                        :class="getRuleTypeClass(kp.review_rule)">
                        {{ getRuleTypeLabel(kp.review_rule) }}
                      </span>
                    </div>
                    <div v-if="kp.review_rule_text" class="text-xs text-gray-400 mb-2 truncate">
                      {{ kp.review_rule_text }}
                    </div>
                    <div v-if="kp.content && kp.review_rule === '1'" class="text-xs text-gray-500 bg-gray-50 px-2 py-1 rounded mb-2 line-clamp-2">
                      {{ kp.content }}
                    </div>
                  </div>
                  <!-- 校验方式切换 -->
                  <div class="flex-shrink-0 flex items-center gap-2">
                    <span class="text-xs text-gray-400">校验:</span>
                    <button v-for="opt in ruleOptions" :key="opt.value"
                      @click="changeRuleType(r.material, idx, opt.value)"
                      class="px-2 py-1 rounded text-xs font-medium transition border"
                      :class="kp.review_rule === opt.value
                        ? opt.activeClass
                        : 'border-gray-200 text-gray-400 hover:border-gray-300 hover:text-gray-600'">
                      {{ opt.label }}
                    </button>
                    <!-- 重新生成按钮 -->
                    <button @click="regenerateKeypoint(r.material, idx)"
                      :disabled="regeneratingKp === `${r.material}-${idx}`"
                      class="p-1 text-gray-400 hover:text-blue-600 transition"
                      title="重新生成此要点">
                      <svg v-if="regeneratingKp === `${r.material}-${idx}`" class="w-4 h-4 animate-spin text-blue-500">
                        <circle class="opacity-25" cx="8" cy="8" r="6" stroke="currentColor" stroke-width="2" fill="none"/>
                        <path class="opacity-75" fill="currentColor" d="M14 8a6 6 0 01-6 6H4V8h6z"/>
                      </svg>
                      <svg v-else class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
                      </svg>
                    </button>
                  </div>
                </div>
              </div>
            </div>

          </div>

          <!-- 底部操作区 -->
          <div class="flex items-center justify-between pt-4 border-t border-gray-200">
            <button @click="goStepNav(1)"
              class="flex items-center gap-1.5 px-4 py-2 text-sm text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50 transition">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/>
              </svg>
              返回上一步
            </button>
            <div class="flex items-center gap-3">
              <!-- 保存所有改动 -->
              <button v-if="hasAnyPendingChanges"
                @click="saveAllChanges"
                :disabled="isSaving === 'all'"
                class="flex items-center gap-1.5 px-4 py-2 text-sm bg-green-600 text-white rounded-lg hover:bg-green-700 transition disabled:opacity-50">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3m-1 4l-3 3m0 0l-3-3m3 3V4"/>
                </svg>
                {{ isSaving === 'all' ? '保存中...' : '保存所有改动' }}
              </button>
              <button @click="completeReview"
                class="flex items-center gap-1.5 px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
                </svg>
                完成审核
              </button>
            </div>
          </div>

          <!-- 底部提示 -->
          <div class="text-xs text-gray-400 text-center py-2">
            修改校验方式后点击「保存所有改动」，将更新写入到对应的 JSON 文件
          </div>
        </div>

      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, onActivated, nextTick } from 'vue'
import { invoke } from '@tauri-apps/api/tauri'
import { listen } from '@tauri-apps/api/event'

// ─── Step 配置 ───────────────────────────────────
const steps = [
  { title: '配置与生成',   active: '配置中', done: '已生成',   pending: '待配置' },
  { title: '审核校验方式', active: '审核中', done: '✓ 完成',   pending: '待审核' },
]
const WORKDIR_STORAGE_KEY = 'auto-prompt.review-rule.workdir'
const currentStep = ref(1)
const maxReachableStep = computed(() => results.value.some(r => r.success) ? 2 : 1)

function goStepNav(n) {
  if (n > maxReachableStep.value) return
  currentStep.value = n
}

// ─── 状态 ─────────────────────────────────────────
const workDir     = ref('')
const isRunning   = ref(false)
const useLlm      = ref(true)        // 默认开启LLM
const availableModels = ref([])
const selectedModelId = ref('')
const logs        = ref([])
const results     = ref([])
const logContainer = ref(null)

// Step2 状态
const expandedMaterials = ref([])    // 展开的材料名
const keypointData   = ref({})       // { 材料名: [keypoint,...] }
const originalData   = ref({})       // 原始数据用于对比
const isSaving       = ref(null)
const copiedItem     = ref(null)
const regeneratingKp = ref(null)     // 正在重新生成的要点标识 "material-idx"

let unlistenLog = null

// ─── 模型选项 ────────────────────────────────────
const ruleOptions = [
  { value: '2', label: '规则对比', activeClass: 'border-blue-400 bg-blue-50 text-blue-700' },
  { value: '1', label: '大模型',   activeClass: 'border-purple-400 bg-purple-50 text-purple-700' },
  { value: '3', label: 'Groovy',   activeClass: 'border-orange-400 bg-orange-50 text-orange-700' },
]

function getRuleTypeLabel(v) {
  return { '1': '大模型', '2': '规则对比', '3': 'Groovy脚本' }[v] || v
}
function getRuleTypeClass(v) {
  return {
    '1': 'bg-purple-100 text-purple-700',
    '2': 'bg-blue-100 text-blue-700',
    '3': 'bg-orange-100 text-orange-700',
  }[v] || 'bg-gray-100 text-gray-600'
}

// ─── 统计 ─────────────────────────────────────────
const totalKeypointCount = computed(() =>
  Object.values(keypointData.value).reduce((sum, kps) => sum + kps.length, 0)
)

const ruleTypeCounts = computed(() => {
  const counts = { 1: 0, 2: 0, 3: 0 }
  for (const kps of Object.values(keypointData.value)) {
    for (const kp of kps) {
      const k = Number(kp.review_rule)
      if (counts[k] !== undefined) counts[k]++
    }
  }
  return counts
})

function getMaterialRuleCounts(material) {
  const kps = keypointData.value[material] || []
  const counts = {}
  for (const kp of kps) {
    const k = Number(kp.review_rule)
    counts[k] = (counts[k] || 0) + 1
  }
  return counts
}

function hasPendingChanges(material) {
  const orig = originalData.value[material]
  const curr = keypointData.value[material]
  if (!orig || !curr) return false
  return JSON.stringify(orig.map(k => k.review_rule)) !== JSON.stringify(curr.map(k => k.review_rule))
}

// 检查是否有任何待保存的改动
const hasAnyPendingChanges = computed(() => {
  return results.value
    .filter(r => r.success)
    .some(r => hasPendingChanges(r.material))
})

// 保存所有改动
async function saveAllChanges() {
  const successResults = results.value.filter(r => r.success && hasPendingChanges(r.material))
  if (successResults.length === 0) return

  isSaving.value = 'all'
  try {
    for (const r of successResults) {
      await saveChanges(r)
    }
    addLog(`已保存所有 ${successResults.length} 个材料的改动`, 'success')
  } catch (e) {
    addLog(`保存失败: ${e}`, 'error')
  } finally {
    isSaving.value = null
  }
}

// 完成审核
function completeReview() {
  addLog('审查规则审核完成', 'success')
  clear()
}

// ─── 生命周期 ─────────────────────────────────────
async function loadModels() {
  try {
    const settings = await invoke('load_settings')
    const mods = (settings.models && settings.models.length > 0) ? settings.models : [
      { id: '1', name: 'Qwen VL Max', model_id: 'qwen-vl-max', type: 'vl' },
      { id: '4', name: 'Qwen Plus (文本)', model_id: 'qwen-plus', type: 'text' },
      { id: '5', name: 'Qwen Max (文本)', model_id: 'qwen-max', type: 'text' },
    ]
    availableModels.value = mods
    const defaultId = settings.default_model_id || mods[0]?.id || ''
    if (!mods.find(m => m.id === selectedModelId.value)) {
      selectedModelId.value = defaultId
    }
  } catch (e) { console.error('加载模型列表失败', e) }
}

onActivated(() => { loadModels() })

onMounted(async () => {
  await loadModels()
  unlistenLog = await listen('review-rule-log', (event) => {
    const line = event.payload
    const type = line.includes('[错误]') ? 'error'
      : line.includes('[完成]') || line.includes('✓') ? 'success'
      : line.includes('[警告]') ? 'warning' : 'info'
    addLog(line, type)
    nextTick(() => { if (logContainer.value) logContainer.value.scrollTop = logContainer.value.scrollHeight })
  })

  if (!workDir.value && typeof window !== 'undefined') {
    const storedWorkDir = window.localStorage.getItem(WORKDIR_STORAGE_KEY)
    if (storedWorkDir) {
      workDir.value = storedWorkDir
      addLog(`已恢复上次工作区: ${storedWorkDir}`, 'info')
    }
  }
})

onUnmounted(() => { if (unlistenLog) unlistenLog() })

// ─── 工具函数 ──────────────────────────────────────
function getLogClass(type) {
  return { error: 'text-red-400', success: 'text-green-400', warning: 'text-yellow-400', info: 'text-blue-300' }[type] || 'text-gray-400'
}
function addLog(message, type = 'info') {
  logs.value.push({ time: new Date().toLocaleTimeString(), message, type })
}

function persistWorkDir() {
  if (typeof window === 'undefined') return
  if (workDir.value) {
    window.localStorage.setItem(WORKDIR_STORAGE_KEY, workDir.value)
  } else {
    window.localStorage.removeItem(WORKDIR_STORAGE_KEY)
  }
}

// ─── Step1：上传工作区 ────────────────────────────
async function selectWorkDir() {
  try {
    const selected = await invoke('select_directory')
    if (!selected) return
    workDir.value = selected
    persistWorkDir()
    addLog(`已上传工作区: ${selected}`, 'info')
  } catch (e) {
    addLog(`上传工作区失败: ${e}`, 'error')
  }
}

// ─── Step1：生成 ──────────────────────────────────
async function generate() {
  if (!workDir.value || isRunning.value) return
  isRunning.value = true
  results.value = []
  keypointData.value = {}
  originalData.value = {}
  expandedMaterials.value = []
  addLog('开始生成审查规则JSON...', 'info')
  addLog(`工作目录: ${workDir.value}`, 'info')

  // 获取选中模型的 model_id（用于 Python --model 参数）和 api_key
  let modelId = null
  let apiKey = null
  let baseUrl = null

  if (useLlm.value) {
    try {
      const settings = await invoke('load_settings')
      apiKey = settings.api_key || null
      baseUrl = 'https://dashscope.aliyuncs.com/compatible-mode/v1'
      const selModel = (settings.models || []).find(m => m.id === selectedModelId.value)
      modelId = selModel?.model_id || null
      addLog(`启用 LLM 推理，模型: ${modelId || '默认'}`, 'info')
    } catch (e) {
      addLog(`读取设置失败，将使用本地推断: ${e}`, 'warning')
    }
  }

  try {
    const res = await invoke('generate_review_rule', {
      workDir: workDir.value,
      useLlm: useLlm.value,
      apiKey: apiKey,
      baseUrl: baseUrl,
      model: modelId,
    })
    results.value = res
    const successCount = res.filter(r => r.success).length
    addLog(`生成完成！共 ${res.length} 个材料，成功 ${successCount} 个`, 'success')

    if (successCount > 0) {
      // 自动跳转 Step2 并加载要点数据
      currentStep.value = 2
      await loadAllKeypointData(res.filter(r => r.success))
    }
  } catch (e) {
    addLog(`生成失败: ${e}`, 'error')
  } finally {
    isRunning.value = false
  }
}

// ─── Step2：加载要点数据 ────────────────────────────
async function loadAllKeypointData(successResults) {
  for (const r of successResults) {
    await loadMaterialKeypoints(r)
  }
  // 默认展开第一个材料
  if (successResults.length > 0) {
    expandedMaterials.value = [successResults[0].material]
  }
}

async function loadMaterialKeypoints(r) {
  try {
    const raw = await invoke('read_json_file', { path: r.output })
    const data = JSON.parse(raw)
    const kps = (data.keypoints || []).map(kp => ({ ...kp }))
    keypointData.value[r.material] = kps
    // 深拷贝用于对比
    originalData.value[r.material] = kps.map(kp => ({ ...kp }))
  } catch (e) {
    console.error(`加载 ${r.material} 要点失败`, e)
    keypointData.value[r.material] = []
  }
}

function toggleMaterial(material) {
  const idx = expandedMaterials.value.indexOf(material)
  if (idx >= 0) {
    expandedMaterials.value.splice(idx, 1)
  } else {
    expandedMaterials.value.push(material)
    // 如果还没加载，触发加载
    const r = results.value.find(r => r.material === material)
    if (r && !keypointData.value[material]) {
      loadMaterialKeypoints(r)
    }
  }
}

// ─── Step2：修改校验方式 ──────────────────────────
function changeRuleType(material, idx, newRule) {
  if (!keypointData.value[material]) return
  const kp = keypointData.value[material][idx]
  if (kp.review_rule === newRule) return
  kp.review_rule = newRule
  // 切换时更新相关字段
  if (newRule === '1') {
    // 大模型：确保 content 有提示词
    if (!kp.content && kp.review_rule_text) {
      kp.content = kp.review_rule_text.replace(/#([^#-]+)-([^#]+)#/g, (_, mat, field) => `$${mat.trim()}:${field.trim()}$`)
    }
  } else if (newRule === '2') {
    kp.is_contrast = '1'
    kp.is_point = '0'
    kp.pre_rule_enabled = 0
    if (!kp.review_conditions) {
      kp.review_conditions = { groups: [] }
    }
  } else if (newRule === '3') {
    if (!kp.review_rule_js) {
      kp.review_rule_js = `// 规则: ${kp.review_rule_text || kp.kpname}\n// TODO: 实现审查逻辑\nreturn [pass: true, reason: "审查通过"]`
    }
  }
  // 触发响应式更新
  keypointData.value = { ...keypointData.value }
}

// ─── Step2：保存修改 ──────────────────────────────
async function saveChanges(r) {
  if (isSaving.value && isSaving.value !== 'all') return
  const isSingleSave = isSaving.value !== 'all'
  if (isSingleSave) {
    isSaving.value = r.material
  }
  try {
    const raw = await invoke('read_json_file', { path: r.output })
    const data = JSON.parse(raw)
    data.keypoints = keypointData.value[r.material]
    const newJson = JSON.stringify(data, null, 2)
    await invoke('write_json_file', { path: r.output, content: newJson })
    // 更新 original 以清除"有改动"标记
    originalData.value[r.material] = keypointData.value[r.material].map(kp => ({ ...kp }))
    addLog(`已保存: ${r.material}`, 'success')
  } catch (e) {
    addLog(`保存失败: ${e}`, 'error')
    throw e
  } finally {
    if (isSingleSave) {
      isSaving.value = null
    }
  }
}

async function openInFinder(path) {
  try { await invoke('open_in_finder', { path }) } catch (e) {}
}

async function copyMaterialJson(r) {
  try {
    const raw = await invoke('read_json_file', { path: r.output })
    const content = JSON.stringify(JSON.parse(raw), null, 2)
    await navigator.clipboard.writeText(content)
    copiedItem.value = r.material
    setTimeout(() => { copiedItem.value = null }, 2000)
  } catch (e) {}
}

// 重新生成单个审查要点
async function regenerateKeypoint(material, idx) {
  const kp = keypointData.value[material]?.[idx]
  if (!kp) return

  regeneratingKp.value = `${material}-${idx}`
  addLog(`重新生成要点: ${kp.kpname} (${getRuleTypeLabel(kp.review_rule)})`, 'info')

  try {
    const settings = await invoke('load_settings')
    const apiKey = settings.api_key || null
    const baseUrl = 'https://dashscope.aliyuncs.com/compatible-mode/v1'
    const selModel = (settings.models || []).find(m => m.id === selectedModelId.value)
    const modelId = selModel?.model_id || null
    const timeout = settings.llm_timeout || 120

    // 调用后端重新生成
    const result = await invoke('regenerate_keypoint', {
      kpname: kp.kpname,
      ruleDesc: kp.review_rule_text || '',
      materialName: material,
      targetRule: kp.review_rule,
      apiKey: apiKey,
      baseUrl: baseUrl,
      model: modelId,
      timeout: timeout,
    })

    // 更新要点数据
    if (result) {
      keypointData.value[material][idx] = {
        ...keypointData.value[material][idx],
        ...result,
      }
      // 触发响应式更新
      keypointData.value = { ...keypointData.value }
      addLog(`✓ 已重新生成: ${kp.kpname}`, 'success')
    }
  } catch (e) {
    addLog(`重新生成失败: ${e}`, 'error')
  } finally {
    regeneratingKp.value = null
  }
}

function clear() {
  workDir.value = ''
  persistWorkDir()
  logs.value = []
  results.value = []
  keypointData.value = {}
  originalData.value = {}
  expandedMaterials.value = []
  currentStep.value = 1
  isSaving.value = null
  copiedItem.value = null
}
</script>
