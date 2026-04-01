<template>
  <!-- 整体：左右双栏，左侧固定 sidebar，右侧滚动内容 -->
  <div class="flex h-full min-h-0">

    <!-- ═══ 左侧固定 Step 导航 ═══ -->
    <div class="w-56 flex-shrink-0 bg-white border-r flex flex-col">
      <!-- 标题 -->
      <div class="px-5 pt-6 pb-4 border-b">
        <h1 class="text-base font-bold text-gray-900 leading-tight">生成提取提示词</h1>
        <p class="text-xs text-gray-400 mt-1 leading-relaxed">智能生成文档要素提取提示词</p>
      </div>

      <!-- Step 列表 -->
      <nav class="flex-1 py-4 px-3 space-y-1">
        <button v-for="(s, i) in steps" :key="i"
          @click="handleStepNav(i + 1)"
          :disabled="i + 1 > maxReachableStep"
          class="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left transition-all group"
          :class="[
            currentStep === i + 1
              ? 'bg-blue-50 text-blue-700'
              : currentStep > i + 1
                ? 'text-green-700 hover:bg-green-50 cursor-pointer'
                : i + 1 <= maxReachableStep
                  ? 'text-gray-500 hover:bg-gray-50 cursor-pointer'
                  : 'text-gray-300 cursor-not-allowed'
          ]">
          <!-- 步骤圆圈 -->
          <div class="w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 text-xs font-bold transition-all"
            :class="[
              currentStep > i + 1
                ? 'bg-green-500 text-white'
                : currentStep === i + 1
                  ? 'bg-blue-600 text-white ring-4 ring-blue-100'
                  : i + 1 <= maxReachableStep
                    ? 'bg-gray-200 text-gray-500'
                    : 'bg-gray-100 text-gray-300'
            ]">
            <svg v-if="currentStep > i + 1" class="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/>
            </svg>
            <span v-else>{{ i + 1 }}</span>
          </div>
          <!-- 步骤文字 -->
          <div class="flex-1 min-w-0">
            <div class="text-xs font-semibold truncate">{{ s.title }}</div>
            <div class="text-xs truncate mt-0.5"
              :class="currentStep === i + 1 ? 'text-blue-500' : currentStep > i + 1 ? 'text-green-500' : 'text-gray-400'">
              {{ currentStep > i + 1 ? s.done : currentStep === i + 1 ? s.active : s.pending }}
            </div>
          </div>
          <!-- 当前步骤指示线 -->
          <div v-if="currentStep === i + 1" class="w-1 h-5 rounded-full bg-blue-500 flex-shrink-0"></div>
        </button>
      </nav>

      <!-- 底部操作 -->
      <div class="px-3 pb-4 pt-2 border-t space-y-2">
        <!-- 运行状态 -->
        <div v-if="isRunning || isVerifying" class="flex items-center gap-2 px-3 py-2 bg-blue-50 rounded-lg">
          <svg class="animate-spin w-3.5 h-3.5 text-blue-500 flex-shrink-0" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
          </svg>
          <span class="text-xs text-blue-600">{{ isRunning ? `生成中... ${batchElapsed}s` : `验证中... ${verifyElapsed}s` }}</span>
        </div>
        <button @click="clear" :disabled="isRunning || isVerifying"
          class="w-full flex items-center justify-center gap-1.5 px-3 py-2 text-xs text-gray-500 border border-gray-200 rounded-lg hover:bg-gray-50 hover:text-gray-700 disabled:opacity-40 transition">
          <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
          </svg>
          重新开始
        </button>
      </div>
    </div>

    <!-- ═══ 右侧滚动内容区 ═══ -->
    <div class="flex-1 overflow-y-auto bg-gray-50">
      <div class="p-6 max-w-3xl">

        <!-- ── STEP 1 内容：上传工作区与材料 ── -->
        <div v-if="currentStep === 1" class="space-y-4">
          <div class="flex items-center gap-2 mb-1">
            <span class="text-lg font-bold text-gray-900">上传工作区与材料类型</span>
          </div>
          <p class="text-sm text-gray-500">上传包含 factors.xlsx 的工作区，然后勾选要生成提示词的材料类型（支持多选）</p>

          <!-- 工作区选择 -->
          <div class="bg-white rounded-xl border p-4">
            <label class="block text-xs font-semibold text-gray-600 mb-2 uppercase tracking-wide">工作区</label>
            <div class="flex gap-2 items-start">
              <input type="text" v-model="workDir" placeholder="上传后会显示服务端工作区路径，或直接粘贴已有路径"
                class="flex-1 px-3 py-2 border rounded-lg text-sm bg-gray-50 text-gray-700"
                @change="onWorkDirInput" />
              <button @click="selectWorkDirFromService" :disabled="isRunning"
                class="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition flex-shrink-0">
                上传文件夹...
              </button>
              <div
                class="relative flex-shrink-0"
                @mouseenter="showStructureGuide = true"
                @mouseleave="showStructureGuide = false"
              >
                <button
                  type="button"
                  class="w-10 h-10 rounded-lg border border-blue-200 bg-blue-50 text-blue-600 flex items-center justify-center hover:bg-blue-100 transition"
                  aria-label="查看工作区结构要求"
                  @click="showStructureGuide = !showStructureGuide"
                >
                  <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M12 22C6.477 22 2 17.523 2 12S6.477 2 12 2s10 4.477 10 10-4.477 10-10 10z" />
                  </svg>
                </button>

                <Transition name="structure-guide">
                  <div
                    v-if="showStructureGuide"
                    class="absolute right-0 top-12 z-30 w-80 rounded-2xl border border-slate-200 bg-white p-4 shadow-2xl"
                  >
                    <div class="flex items-start justify-between gap-3">
                      <div>
                        <p class="text-sm font-semibold text-slate-800">工作区结构示意</p>
                        <p class="text-xs text-slate-500 mt-1">上传前先确认目录长这样</p>
                      </div>
                      <span class="px-2 py-1 rounded-full bg-blue-50 text-blue-600 text-[11px] font-medium">必看</span>
                    </div>

                    <div class="mt-3 rounded-xl border border-slate-200 bg-slate-50 p-3">
                      <div class="text-[11px] text-slate-400 mb-2">示意结构</div>
                      <div class="space-y-1.5 font-mono text-xs text-slate-700 leading-5">
                        <div class="font-semibold text-slate-800">工作区/</div>
                        <div class="pl-3">├─ <span class="font-semibold text-emerald-700">factors.xlsx</span></div>
                        <div class="pl-3">├─ 材料A/</div>
                        <div class="pl-8 text-slate-500">├─ sample-1.png</div>
                        <div class="pl-8 text-slate-500">└─ sample-2.pdf</div>
                        <div class="pl-3">└─ 材料B/</div>
                        <div class="pl-8 text-slate-500">└─ sample-1.jpg</div>
                      </div>
                    </div>

                    <div class="mt-3 space-y-2 text-xs text-slate-600 leading-5">
                      <p>1. 根目录必须包含 <span class="font-semibold text-slate-800">factors.xlsx</span></p>
                      <p>2. 每种材料放在自己的子文件夹里，文件夹名建议和材料名一致</p>
                      <p>3. 子文件夹里放样本图片或 PDF，至少 1 份即可开始生成</p>
                    </div>
                  </div>
                </Transition>
              </div>
            </div>
            <p class="text-xs text-gray-400 mt-2">
              浏览器会把所选文件夹上传到服务端工作区，后续生成、验证和下载都基于这个工作区执行
            </p>
            <div class="mt-2 inline-flex items-center gap-1.5 rounded-lg bg-blue-50 px-2.5 py-1 text-xs text-blue-600">
              <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M12 22C6.477 22 2 17.523 2 12S6.477 2 12 2s10 4.477 10 10-4.477 10-10 10z" />
              </svg>
              鼠标移到右侧图标可查看结构示意，点击也能展开
            </div>
          </div>

          <!-- 要素 + 材料 双列 -->
          <div v-if="factors.length > 0 || materials.length > 0" class="grid grid-cols-2 gap-4">
            <!-- 要素字段 -->
            <div class="bg-white rounded-xl border overflow-hidden">
              <div class="flex items-center justify-between px-4 py-3 border-b bg-gray-50">
                <span class="text-sm font-semibold text-gray-700">所有要素字段</span>
                <span class="px-2 py-0.5 bg-blue-100 text-blue-700 rounded-full text-xs font-medium">{{ factors.length }} 个</span>
              </div>
              <div class="divide-y max-h-52 overflow-y-auto">
                <div v-for="(f, i) in factors.slice(0, 10)" :key="i" class="flex items-center gap-2.5 px-4 py-2">
                  <span class="w-5 h-5 rounded-full bg-blue-50 text-blue-600 text-xs flex items-center justify-center font-medium flex-shrink-0">{{ i+1 }}</span>
                  <span class="text-sm text-gray-700 truncate">{{ f.field_name }}</span>
                </div>
                <div v-if="factors.length > 10" class="px-4 py-2 text-xs text-gray-400 text-center">还有 {{ factors.length - 10 }} 个字段...</div>
              </div>
            </div>
            <!-- 材料类型多选 -->
            <div class="bg-white rounded-xl border overflow-hidden">
              <div class="flex items-center justify-between px-4 py-3 border-b bg-gray-50">
                <span class="text-sm font-semibold text-gray-700">材料类型（多选）</span>
                <div class="flex items-center gap-2">
                  <span class="px-2 py-0.5 bg-purple-100 text-purple-700 rounded-full text-xs font-medium">已选 {{ selectedMaterials.length }}/{{ materials.length }}</span>
                  <button @click="toggleAllMaterials"
                    class="text-xs text-blue-600 hover:text-blue-800 font-medium">
                    {{ selectedMaterials.length === materials.length ? '取消全选' : '全选' }}
                  </button>
                </div>
              </div>
              <div class="divide-y max-h-52 overflow-y-auto">
                <div v-for="m in materials" :key="m.name"
                  @click="toggleMaterial(m)"
                  class="flex items-center gap-3 px-4 py-3 cursor-pointer transition select-none"
                  :class="isMaterialSelected(m) ? 'bg-blue-50' : 'hover:bg-gray-50'">
                  <div class="w-4 h-4 rounded border-2 flex items-center justify-center flex-shrink-0 transition"
                    :class="isMaterialSelected(m) ? 'border-blue-500 bg-blue-500' : 'border-gray-300'">
                    <svg v-if="isMaterialSelected(m)" class="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
                      <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/>
                    </svg>
                  </div>
                  <div class="flex-1 min-w-0">
                    <div class="text-sm truncate" :class="isMaterialSelected(m) ? 'font-semibold text-blue-800' : 'text-gray-700'">{{ m.name }}</div>
                    <div class="text-xs text-gray-400">{{ m.image_count }} 个样本文件</div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- 模型选择 -->
          <div v-if="availableModels.length > 0" class="bg-white rounded-xl border p-4">
            <label class="block text-xs font-semibold text-gray-600 mb-2 uppercase tracking-wide">验证提取模型</label>
            <div class="flex flex-wrap gap-2">
              <button v-for="m in availableModels" :key="m.id"
                @click="selectedModelId = m.id"
                class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs border transition"
                :class="selectedModelId === m.id
                  ? 'bg-blue-600 text-white border-blue-600'
                  : 'bg-white text-gray-600 border-gray-300 hover:border-blue-400'">
                <span class="px-1.5 py-0.5 rounded text-xs font-medium"
                  :class="m.type === 'vl' ? 'bg-purple-200 text-purple-800' : 'bg-green-200 text-green-800'">
                  {{ m.type === 'vl' ? 'VL' : '文本' }}
                </span>
                {{ m.name }}
              </button>
            </div>
            <p class="text-xs text-gray-400 mt-2">在设置中可添加/修改模型列表</p>
          </div>

          <!-- 操作按钮 -->
          <div class="flex items-center justify-between pt-2">
            <div class="text-sm text-gray-500">
              <span v-if="!workDir">请先上传工作区</span>
              <span v-else-if="selectedMaterials.length === 0">请勾选至少一种材料类型</span>
              <span v-else class="text-green-600 flex items-center gap-1">
                <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/></svg>
                已选 {{ selectedMaterials.length }} 种材料，共 {{ factors.length }} 个要素字段
              </span>
            </div>
            <button @click="goStep2" :disabled="!canGenerate || isRunning"
              class="flex items-center gap-2 px-6 py-2.5 rounded-lg text-sm font-semibold transition-all"
              :class="canGenerate && !isRunning ? 'bg-blue-600 text-white hover:bg-blue-700 shadow-sm' : 'bg-gray-100 text-gray-400 cursor-not-allowed'">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>
              </svg>
              开始生成提示词
            </button>
          </div>
        </div>

        <!-- ── STEP 2 内容：生成提示词 ── -->
        <div v-if="currentStep === 2" class="space-y-4">
          <div class="flex items-center justify-between mb-1">
            <span class="text-lg font-bold text-gray-900">生成提示词</span>
            <span class="text-sm text-gray-500">{{ batchDoneCount }}/{{ selectedMaterials.length }} 已完成</span>
          </div>

          <!-- 批量进度 -->
          <div v-if="selectedMaterials.length > 1" class="bg-white rounded-xl border overflow-hidden">
            <div class="flex items-center justify-between px-4 py-2.5 bg-gray-50 border-b">
              <span class="text-xs font-semibold text-gray-600">批量生成进度</span>
              <span class="text-xs text-gray-400">{{ batchDoneCount }}/{{ selectedMaterials.length }}</span>
            </div>
            <div class="divide-y max-h-40 overflow-y-auto">
              <div v-for="m in selectedMaterials" :key="m.name" class="flex items-center gap-3 px-4 py-2">
                <div class="w-4 h-4 flex-shrink-0">
                  <svg v-if="batchResults[m.name]?.success" class="w-4 h-4 text-green-500" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/>
                  </svg>
                  <svg v-else-if="batchResults[m.name]?.error" class="w-4 h-4 text-red-400" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"/>
                  </svg>
                  <svg v-else-if="batchCurrentMaterial === m.name" class="animate-spin w-4 h-4 text-blue-500" fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
                  </svg>
                  <div v-else class="w-4 h-4 rounded-full border-2 border-gray-200"></div>
                </div>
                <span class="text-sm flex-1 truncate" :class="batchCurrentMaterial === m.name ? 'text-blue-700 font-medium' : batchResults[m.name] ? 'text-gray-700' : 'text-gray-400'">{{ m.name }}</span>
                <span v-if="batchResults[m.name]?.error" class="text-xs text-red-400 truncate max-w-32">失败</span>
              </div>
            </div>
          </div>

          <!-- 生成中 loading（单材料或批量时显示当前材料） -->
          <div v-if="isRunning" class="bg-white rounded-xl border p-12 text-center">
            <div class="w-16 h-16 rounded-full bg-blue-50 flex items-center justify-center mx-auto mb-4">
              <svg class="animate-spin w-8 h-8 text-blue-500" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
              </svg>
            </div>
            <p class="text-base font-semibold text-gray-700">正在生成「{{ batchCurrentMaterial }}」提示词...</p>
            <p class="text-sm text-gray-400 mt-1">调用 Qwen VL 分析图片要素，请稍候</p>
            <p class="text-lg font-mono font-bold text-blue-500 mt-3">{{ batchElapsed }}s</p>
          </div>

          <!-- 批量完成后的材料选项卡 -->
          <div v-if="!isRunning && batchDoneCount > 0" class="space-y-3">
            <!-- 材料 tab 切换 -->
            <div v-if="selectedMaterials.length > 1" class="flex flex-wrap gap-2">
              <button v-for="m in selectedMaterials" :key="m.name"
                @click="switchBatchMaterial(m.name)"
                class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs border transition"
                :class="activeBatchMaterial === m.name
                  ? 'bg-blue-600 text-white border-blue-600'
                  : batchResults[m.name]?.error ? 'bg-red-50 text-red-600 border-red-200'
                  : batchResults[m.name]?.success ? 'bg-green-50 text-green-700 border-green-200'
                  : 'bg-white text-gray-400 border-gray-200'">
                <svg v-if="batchResults[m.name]?.success" class="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                  <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/>
                </svg>
                {{ m.name }}
                <span v-if="batchResults[m.name]?.elapsed" class="opacity-70">{{ batchResults[m.name].elapsed }}s</span>
              </button>
            </div>
          </div>

          <!-- 提示词编辑区 -->
          <template v-if="activeResult && !isRunning">
            <!-- 文件信息条 -->
            <div v-if="activeResult.output_file" class="flex items-center gap-2 px-4 py-2.5 bg-green-50 border border-green-200 rounded-lg">
              <svg class="w-4 h-4 text-green-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
              </svg>
              <span class="text-xs text-green-700 flex-1 truncate">已保存至：{{ activeResult.output_file }}</span>
            </div>

            <!-- 编辑器 -->
            <div class="bg-white rounded-xl border overflow-hidden">
              <div class="flex items-center justify-between px-4 py-3 border-b bg-gray-50">
                <div class="flex items-center gap-2">
                  <span class="text-sm font-semibold text-gray-700">提示词内容</span>
                  <span class="text-xs text-gray-400 bg-gray-100 px-2 py-0.5 rounded">可直接编辑修改</span>
                  <span class="text-xs text-gray-400">{{ editablePrompt.length }} 字符 · {{ editablePrompt.split('\n').length }} 行</span>
                </div>
                <div class="flex items-center gap-2">
                  <button @click="copyPrompt"
                    class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition"
                    :class="copied ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'">
                    <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"/>
                    </svg>
                    {{ copied ? '已复制' : '复制' }}
                  </button>
                  <button v-if="promptModified" @click="savePrompt" :disabled="isSaving"
                    class="flex items-center gap-1.5 px-3 py-1.5 bg-amber-500 text-white rounded-lg text-xs font-medium hover:bg-amber-600 transition">
                    <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3m-1 4l-3 3m0 0l-3-3m3 3V4"/>
                    </svg>
                    {{ isSaving ? '保存中...' : '保存修改' }}
                  </button>
                  <span v-else class="text-xs text-gray-300">已保存</span>
                </div>
              </div>
              <textarea ref="promptTextarea" v-model="editablePrompt"
                class="w-full text-xs text-gray-700 leading-relaxed bg-white p-4 outline-none resize-none font-mono border-0"
                style="min-height: 320px;"
                placeholder="提示词内容..."/>
            </div>

            <!-- 底部操作 -->
            <div class="flex items-center justify-between">
              <button @click="currentStep = 1"
                class="flex items-center gap-1.5 px-4 py-2 text-sm text-gray-500 hover:text-gray-700 transition">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/>
                </svg>
                返回重新选择
              </button>
              <button @click="goToStep3" :disabled="batchDoneCount === 0"
                class="flex items-center gap-2 px-6 py-2.5 bg-blue-600 text-white rounded-lg text-sm font-semibold hover:bg-blue-700 transition shadow-sm disabled:opacity-50">
                下一步：验证提取
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/>
                </svg>
              </button>
            </div>
          </template>
        </div>

        <!-- ── STEP 3 内容：验证提取 ── -->
        <div v-if="currentStep === 3" class="space-y-4">
          <div class="flex items-center justify-between mb-1">
            <span class="text-lg font-bold text-gray-900">验证提取结果</span>
            <span class="text-sm text-gray-500">{{ verifyDoneCount }}/{{ selectedMaterials.length }} 已验证</span>
          </div>
          <p class="text-sm text-gray-500">用当前提示词对样本执行真实提取，确认结果正确后完成</p>

          <!-- 验证材料上传区 -->
          <div class="bg-white rounded-xl border p-4 space-y-3">
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2">
                <span class="text-sm font-semibold text-gray-700">验证材料</span>
                <span v-if="verifyWorkDir" class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs bg-green-50 text-green-700 border border-green-200">
                  <svg class="w-3 h-3" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/></svg>
                  已上传验证材料
                </span>
                <span v-else class="text-xs text-gray-400">默认使用原始工作区材料</span>
              </div>
              <div class="flex items-center gap-2">
                <div class="relative"
                  @mouseenter="showVerifyGuide = true"
                  @mouseleave="showVerifyGuide = false">
                  <button type="button"
                    class="w-8 h-8 rounded-lg border border-amber-200 bg-amber-50 text-amber-600 flex items-center justify-center hover:bg-amber-100 transition"
                    aria-label="查看验证材料格式要求"
                    @click="showVerifyGuide = !showVerifyGuide">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M12 22C6.477 22 2 17.523 2 12S6.477 2 12 2s10 4.477 10 10-4.477 10-10 10z" />
                    </svg>
                  </button>
                  <Transition name="fade">
                    <div v-if="showVerifyGuide"
                      class="absolute right-0 top-10 z-30 w-72 rounded-xl border border-amber-200 bg-white p-4 shadow-2xl text-left">
                      <p class="text-xs font-bold text-amber-700 mb-2">验证材料目录格式要求</p>
                      <div class="text-xs text-gray-600 space-y-1 font-mono bg-gray-50 rounded-lg p-3 border">
                        <p>验证材料文件夹/</p>
                        <p class="pl-3">├── 材料名A/</p>
                        <p class="pl-6">├── sample1.jpg</p>
                        <p class="pl-6">└── sample2.png</p>
                        <p class="pl-3">├── 材料名B/</p>
                        <p class="pl-6">└── sample.pdf</p>
                        <p class="pl-3">└── ...</p>
                      </div>
                      <ul class="mt-2 text-xs text-gray-500 space-y-1 list-disc pl-3.5">
                        <li><b>子文件夹名</b>必须与选中材料名一致</li>
                        <li>每个子文件夹放入待验证的<b>图片或PDF</b></li>
                        <li>不需要 factors.xlsx 等配置文件</li>
                        <li>验证时取子文件夹中<b>第一张图片</b>进行提取</li>
                      </ul>
                    </div>
                  </Transition>
                </div>
                <button @click="selectVerifyWorkDir"
                  class="px-3 py-1.5 text-xs font-medium rounded-lg transition"
                  :class="verifyWorkDir
                    ? 'bg-gray-100 text-gray-600 hover:bg-gray-200 border border-gray-200'
                    : 'bg-blue-600 text-white hover:bg-blue-700'">
                  {{ verifyWorkDir ? '重新上传' : '上传验证材料...' }}
                </button>
                <button v-if="verifyWorkDir" @click="verifyWorkDir = ''; verifyResults = Object.create(null)"
                  class="px-2 py-1.5 text-xs text-gray-400 hover:text-red-500 transition" title="清除验证材料，恢复使用原始工作区">
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                  </svg>
                </button>
              </div>
            </div>
            <div v-if="verifyWorkDir" class="flex items-center gap-2 px-3 py-2 bg-green-50 border border-green-100 rounded-lg">
              <svg class="w-4 h-4 text-green-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"/>
              </svg>
              <span class="text-xs text-green-700 truncate flex-1">{{ verifyWorkDir }}</span>
            </div>
          </div>

          <!-- 材料 tab 切换（多选时） -->
          <div v-if="selectedMaterials.length > 1" class="flex flex-wrap gap-2">
            <button v-for="m in selectedMaterials" :key="m.name"
              @click="switchVerifyMaterial(m.name)"
              class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs border transition"
              :class="activeVerifyMaterial === m.name
                ? 'bg-blue-600 text-white border-blue-600'
                : verifyResults[m.name]?.success ? 'bg-green-50 text-green-700 border-green-200'
                : verifyResults[m.name] ? 'bg-red-50 text-red-600 border-red-200'
                : 'bg-white text-gray-500 border-gray-200 hover:border-blue-300'">
              <svg v-if="verifyResults[m.name]?.success" class="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/>
              </svg>
              {{ m.name }}
            </button>
          </div>

          <!-- 当前验证材料的提示词和验证区 -->
          <div class="bg-white rounded-xl border p-3">
            <div class="flex items-center justify-between mb-2">
              <span class="text-xs font-semibold text-gray-600">当前材料：{{ activeVerifyMaterial }}</span>
              <button @click="currentStep = 2" class="text-xs text-blue-600 hover:text-blue-800">← 返回修改提示词</button>
            </div>
          </div>

          <!-- 验证按钮区 -->
          <div class="flex items-center gap-3">
            <button @click="runVerify" :disabled="isVerifying || !activeVerifyPrompt"
              class="flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-semibold transition"
              :class="isVerifying ? 'bg-blue-100 text-blue-400 cursor-not-allowed' : 'bg-blue-600 text-white hover:bg-blue-700 shadow-sm'">
              <svg v-if="isVerifying" class="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
              </svg>
              <svg v-else class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"/>
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
              </svg>
              {{ isVerifying ? `验证中... ${verifyElapsed}s` : verifyResults[activeVerifyMaterial] ? '重新验证' : '执行验证提取' }}
            </button>
            <span class="text-xs text-gray-400">调用 Qwen VL 对「{{ activeVerifyMaterial }}」样本执行提取{{ verifyWorkDir ? '（验证材料）' : '' }}</span>
          </div>

          <!-- 验证中 loading -->
          <div v-if="isVerifying" class="bg-white rounded-xl border p-10 text-center">
            <svg class="animate-spin w-10 h-10 text-blue-400 mx-auto mb-4" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
            </svg>
            <p class="text-sm text-gray-500 font-medium">正在调用模型执行提取...</p>
            <p class="text-xl font-mono font-bold text-blue-500 mt-3">{{ verifyElapsed }}s</p>
          </div>

          <!-- 未验证提示 -->
          <div v-if="!verifyResults[activeVerifyMaterial] && !isVerifying" class="bg-white rounded-xl border p-10 text-center">
            <div class="w-14 h-14 bg-blue-50 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg class="w-7 h-7 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/>
              </svg>
            </div>
            <p class="text-sm font-medium text-gray-600 mb-1">点击上方按钮验证「{{ activeVerifyMaterial }}」</p>
            <p class="text-xs text-gray-400">如结果不符，可返回 Step 2 修改该材料提示词后重新验证</p>
          </div>

          <!-- 验证结果 -->
          <div v-if="verifyResults[activeVerifyMaterial] && !isVerifying">
            <div v-if="verifyResults[activeVerifyMaterial].success" class="space-y-3">
              <div class="flex items-center gap-2 px-4 py-2.5 bg-green-50 border border-green-200 rounded-lg">
                <div class="w-2 h-2 rounded-full bg-green-500"></div>
                <span class="text-sm text-green-700 font-medium">「{{ verifyResults[activeVerifyMaterial].image_file }}」提取完成</span>
                <span v-if="verifyResults[activeVerifyMaterial].elapsed" class="ml-auto text-xs text-green-600 font-mono">{{ verifyResults[activeVerifyMaterial].elapsed }}s</span>
              </div>
              <div class="px-4 py-2.5 bg-blue-50 border border-blue-100 rounded-lg text-xs text-blue-700">
                <span class="font-semibold">说明：</span>请核对提取结果是否与原始文件内容一致。
              </div>
              <div class="bg-white rounded-xl border overflow-hidden">
                <div class="px-4 py-2.5 bg-gray-50 border-b text-xs font-semibold text-gray-600 uppercase tracking-wide">提取结果</div>
                <pre class="text-sm text-gray-800 leading-relaxed whitespace-pre-wrap p-4 max-h-72 overflow-y-auto font-mono">{{ verifyResults[activeVerifyMaterial].extraction_output }}</pre>
              </div>
            </div>
            <div v-else class="bg-red-50 border border-red-200 rounded-xl p-4 flex items-start gap-3">
              <svg class="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
              </svg>
              <div>
                <p class="text-sm font-semibold text-red-700 mb-1">提取失败</p>
                <p class="text-xs text-red-500">{{ verifyResults[activeVerifyMaterial].error }}</p>
              </div>
            </div>
          </div>

          <!-- 底部操作 -->
          <div class="flex items-center justify-between pt-2">
            <button @click="currentStep = 2"
              class="flex items-center gap-1.5 px-4 py-2 text-sm text-gray-500 border border-gray-200 rounded-lg hover:bg-gray-50 transition">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/>
              </svg>
              修改提示词
            </button>
            <button @click="confirmAndGoStep4"
              class="flex items-center gap-2 px-6 py-2.5 bg-green-600 text-white rounded-lg text-sm font-semibold hover:bg-green-700 transition shadow-sm">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
              </svg>
              {{ verifyDoneCount > 0 ? `已验证 ${verifyDoneCount} 种，确认完成` : '跳过验证，确认完成' }}
            </button>
          </div>
        </div>

        <!-- ── STEP 4 内容：确认完成 ── -->
        <div v-if="currentStep === 4" class="space-y-4">
          <!-- 成功大卡片 -->
          <div class="bg-white rounded-2xl border-2 border-green-200 p-8 text-center">
            <div class="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-5">
              <svg class="w-10 h-10 text-green-500" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/>
              </svg>
            </div>
            <h2 class="text-xl font-bold text-gray-900 mb-2">提示词已确认完成！</h2>
            <p class="text-sm text-gray-500 mb-1">提取结果经人工验证正确，提示词可正式使用</p>
            <p class="text-xs text-gray-400">共 {{ selectedMaterials.length }} 种材料 · 验证 {{ verifyDoneCount }} 种</p>
          </div>

          <!-- 下一步操作卡片 -->
          <div class="grid grid-cols-2 gap-4">
            <button @click="goNextMaterial"
              class="bg-white rounded-xl border p-5 text-left hover:border-blue-300 hover:bg-blue-50 transition group">
              <div class="w-9 h-9 bg-gray-100 rounded-lg flex items-center justify-center mb-3 group-hover:bg-blue-100 transition">
                <svg class="w-5 h-5 text-gray-500 group-hover:text-blue-600 transition" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
                </svg>
              </div>
              <div class="text-sm font-semibold text-gray-800 mb-1">生成下一个材料</div>
              <div class="text-xs text-gray-400">返回 Step1 重新选择材料类型</div>
            </button>
            <button @click="goToStep5"
              class="bg-blue-600 rounded-xl p-5 text-left hover:bg-blue-700 transition group">
              <div class="w-9 h-9 bg-blue-500 rounded-lg flex items-center justify-center mb-3">
                <svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7l5 5m0 0l-5 5m5-5H6"/>
                </svg>
              </div>
              <div class="text-sm font-semibold text-white mb-1">执行要素JSON生成</div>
              <div class="text-xs text-blue-200">使用生成好的提示词提取所有文档要素</div>
            </button>
          </div>
        </div>

        <!-- ── STEP 5 内容：要素JSON生成 ── -->
        <div v-if="currentStep === 5" class="space-y-4">
          <div class="flex items-center gap-2 mb-1">
            <span class="text-lg font-bold text-gray-900">要素JSON生成</span>
          </div>
          <p class="text-sm text-gray-500">根据 factors.xlsx 和提示词文件，为所有材料类型生成符合导入规范的 JSON（含 carriername、factors、promptGroups）</p>

          <!-- 说明 -->
          <div class="bg-blue-50 border border-blue-200 rounded-xl p-4 text-sm text-blue-800">
            <div class="font-medium mb-2">分组策略</div>
            <div class="space-y-1 text-xs">
              <div class="flex items-start gap-2"><span class="font-mono bg-blue-100 px-1 rounded flex-shrink-0">多 TXT</span><span>材料目录中有多个提示词文件 → 每个文件对应一个 promptGroup，组内要素取该文件中出现的要素</span></div>
              <div class="flex items-start gap-2"><span class="font-mono bg-blue-100 px-1 rounded flex-shrink-0">单 TXT</span><span>只有一个提示词文件 → 按每组 <strong>{{ fjGroupSize }}</strong> 个要素自动平分为多组</span></div>
              <div class="flex items-start gap-2"><span class="font-mono bg-blue-100 px-1 rounded flex-shrink-0">无 TXT</span><span>仅生成 factors，不生成 promptGroups（系统自动归入默认组合）</span></div>
            </div>
          </div>

          <!-- 配置行 -->
          <div class="flex flex-wrap items-center gap-4 bg-white border rounded-xl px-4 py-3">
            <div class="flex items-center gap-2">
              <label class="text-xs font-semibold text-gray-600 whitespace-nowrap">默认每组要素数</label>
              <div class="flex items-center border rounded-lg overflow-hidden">
                <button @click="fjGroupSize = Math.max(1, fjGroupSize - 1)"
                  class="px-2.5 py-1 text-gray-500 hover:bg-gray-100 text-sm font-bold">−</button>
                <span class="px-3 py-1 text-sm font-semibold text-blue-700 min-w-[2rem] text-center">{{ fjGroupSize }}</span>
                <button @click="fjGroupSize = Math.min(20, fjGroupSize + 1)"
                  class="px-2.5 py-1 text-gray-500 hover:bg-gray-100 text-sm font-bold">+</button>
              </div>
              <span class="text-xs text-gray-400">（仅单TXT文件时生效）</span>
            </div>
            <div class="ml-auto text-xs text-gray-400 truncate max-w-xs">{{ workDir }}</div>
          </div>

          <!-- 操作按钮 -->
          <div class="flex items-center gap-3">
            <button @click="generateFactorJson" :disabled="fjIsRunning || !workDir"
              class="flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-semibold transition"
              :class="!fjIsRunning && workDir ? 'bg-blue-600 text-white hover:bg-blue-700 shadow-sm' : 'bg-gray-100 text-gray-400 cursor-not-allowed'">
              <svg v-if="fjIsRunning" class="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
              </svg>
              {{ fjIsRunning ? '生成中...' : fjResults.length > 0 ? '重新生成' : '开始生成' }}
            </button>
          </div>

          <!-- 结果列表 -->
          <div v-if="fjResults.length > 0" class="bg-white rounded-xl border overflow-hidden">
            <div class="flex items-center justify-between px-4 py-3 border-b bg-gray-50">
              <span class="text-sm font-semibold text-gray-700">生成结果</span>
              <div class="flex items-center gap-3 text-xs">
                <span class="text-green-600 font-medium">✓ {{ fjResults.filter(r => r.success).length }} 成功</span>
                <span v-if="fjResults.filter(r => !r.success).length > 0" class="text-red-500">✗ {{ fjResults.filter(r => !r.success).length }} 失败</span>
                <span class="text-gray-400">共 {{ fjResults.length }} 个材料</span>
                <button @click="fjDownloadAll"
                  :disabled="fjDownloadingAll || fjResults.filter(r => r.success).length === 0"
                  class="px-3 py-1 rounded text-xs transition"
                  :class="fjResults.filter(r => r.success).length > 0 && !fjDownloadingAll ? 'bg-blue-600 text-white hover:bg-blue-700' : 'bg-gray-200 text-gray-400 cursor-not-allowed'">
                  {{ fjDownloadingAll ? '下载中...' : '全部下载JSON' }}
                </button>
              </div>
            </div>
            <div class="divide-y">
              <div v-for="r in fjResults" :key="r.material">
                <div class="flex items-center gap-3 px-4 py-3"
                  :class="fjPreviewItem === r ? 'bg-blue-50' : 'hover:bg-gray-50'">
                  <div class="flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center"
                    :class="r.success ? 'bg-green-100' : 'bg-red-100'">
                    <svg v-if="r.success" class="w-3.5 h-3.5 text-green-600" fill="currentColor" viewBox="0 0 20 20">
                      <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/>
                    </svg>
                    <svg v-else class="w-3.5 h-3.5 text-red-500" fill="currentColor" viewBox="0 0 20 20">
                      <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"/>
                    </svg>
                  </div>
                  <div class="flex-1 min-w-0">
                    <div class="text-sm font-medium text-gray-800">{{ r.material }}</div>
                    <div class="flex items-center gap-2 mt-0.5">
                      <template v-if="r.success">
                        <span class="text-xs text-blue-600 bg-blue-50 px-1.5 py-0.5 rounded">{{ r.factor_count }} 个要素</span>
                        <span class="text-xs text-purple-600 bg-purple-50 px-1.5 py-0.5 rounded">{{ r.group_count }} 个分组</span>
                      </template>
                      <span v-else class="text-xs text-red-400">{{ r.error }}</span>
                    </div>
                  </div>
                  <div v-if="r.success" class="flex items-center gap-1.5 flex-shrink-0">
                    <button @click="fjTogglePreview(r)"
                      class="flex items-center gap-1 px-2 py-1 rounded text-xs transition"
                      :class="fjPreviewItem === r ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'">
                      {{ fjPreviewItem === r ? '收起' : '预览' }}
                    </button>
                    <button @click="fjDownloadJson(r)"
                      class="flex items-center gap-1 px-2 py-1 bg-blue-100 text-blue-700 rounded text-xs hover:bg-blue-200">
                      下载JSON
                    </button>
                    <button @click="fjCopyJson(r)"
                      class="flex items-center gap-1 px-2 py-1 rounded text-xs transition"
                      :class="fjCopiedItem === r.material ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'">
                      {{ fjCopiedItem === r.material ? '已复制' : '复制' }}
                    </button>
                  </div>
                </div>
                <!-- JSON预览展开 -->
                <div v-if="fjPreviewItem === r" class="px-4 pb-4 bg-blue-50 border-t border-blue-100">
                  <div v-if="r.loadingPreview" class="py-4 text-center text-sm text-gray-400">加载中...</div>
                  <pre v-else-if="r.previewContent" class="text-xs text-gray-700 bg-white rounded-lg p-4 max-h-72 overflow-y-auto border border-blue-100 leading-relaxed mt-3">{{ r.previewContent }}</pre>
                  <div v-else class="py-4 text-sm text-red-400">{{ r.previewError || '无法加载预览' }}</div>
                </div>
              </div>
            </div>
          </div>

          <!-- 底部操作 -->
          <div class="flex items-center justify-between pt-2">
            <button @click="currentStep = 4"
              class="flex items-center gap-1.5 px-4 py-2 text-sm text-gray-500 border border-gray-200 rounded-lg hover:bg-gray-50 transition">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/>
              </svg>
              返回
            </button>
            <button @click="clear"
              class="flex items-center gap-2 px-5 py-2.5 bg-gray-700 text-white rounded-lg text-sm font-semibold hover:bg-gray-800 transition">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
              </svg>
              为下一个事项重新开始
            </button>
          </div>
        </div>

        <!-- ── 日志面板（始终在内容区底部） ── -->
        <div v-if="logs.length > 0" class="mt-6 bg-gray-900 rounded-xl overflow-hidden">
          <div class="flex items-center justify-between px-4 py-2.5 border-b border-gray-800">
            <div class="flex items-center gap-2">
              <span v-if="isRunning || isVerifying" class="flex items-center gap-1.5">
                <span class="w-2 h-2 rounded-full bg-green-400 animate-pulse"></span>
                <span class="text-xs text-green-400">运行中</span>
              </span>
              <span v-else class="text-xs text-gray-500">执行日志</span>
              <span class="text-xs text-gray-600">{{ logs.length }} 条</span>
            </div>
            <button @click="logs = []" class="text-xs text-gray-600 hover:text-gray-400">清空</button>
          </div>
          <div ref="logContainer" class="p-3 space-y-0.5 max-h-40 overflow-y-auto">
            <div v-for="(log, i) in logs" :key="i" class="flex gap-2 text-xs font-mono leading-5">
              <span class="text-gray-600 flex-shrink-0 tabular-nums">{{ log.time }}</span>
              <span :class="getLogClass(log.type)" class="break-all">{{ log.message }}</span>
            </div>
          </div>
        </div>

      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, onActivated, nextTick } from 'vue'
import { getScopedStorageItem, removeScopedStorageItem, setScopedStorageItem } from '../services/authState.js'
import { apiClient } from '../services/apiClient.js'
import { invoke } from '../tauri/tauri.js'

const steps = [
  { title: '上传工作区与材料', active: '配置中',  done: '已选择材料', pending: '待配置' },
  { title: '生成提示词',   active: '生成中',  done: '已生成',    pending: '待生成' },
  { title: '验证提取结果', active: '验证中',  done: '已验证',    pending: '待验证' },
  { title: '确认完成',     active: '已完成',  done: '✓ 完成',    pending: '待确认' },
  { title: '要素JSON生成', active: 'JSON生成中', done: '✓ 已生成', pending: '待生成' },
]
const WORKDIR_STORAGE_KEY = 'auto-prompt.generate.workdir'
const currentStep = ref(1)
const maxReachableStep = computed(() => {
  if (currentStep.value === 5) return 5
  if (currentStep.value === 4) return 5
  if (currentStep.value === 3) return 4
  if (batchDoneCount.value > 0) return 4
  if (currentStep.value === 2) return 2
  return 1
})

const workDir = ref('')
const showStructureGuide = ref(false)
const factors = ref([])
const materials = ref([])
const selectedMaterials = ref([])  // 多选材料列表
const availableModels = ref([])
const selectedModelId = ref('')
const isRunning = ref(false)
const logs = ref([])
const logContainer = ref(null)
const promptTextarea = ref(null)
const copied = ref(false)

// Step2: 批量生成状态
const batchResults = ref({})        // { materialName: { success, prompt_template, output_file, error, elapsed } }
const batchCurrentMaterial = ref('') // 当前正在生成的材料名
const activeBatchMaterial = ref('')  // 当前展示编辑的材料名
const editablePrompt = ref('')
const promptModified = ref(false)
const isSaving = ref(false)
const batchStartTime = ref(0)       // 批量生成开始时间
const batchElapsed = ref(0)         // 批量总耗时(秒)
const currentElapsed = ref(0)       // 当前材料耗时(秒)
let elapsedTimer = null

// Step3: 逐材料验证状态
const isVerifying = ref(false)
const verifyResults = ref({})       // { materialName: VerifyResult }
const activeVerifyMaterial = ref('')
const verifyElapsed = ref(0)
let verifyTimer = null
const verifyWorkDir = ref('')       // 验证用的另一套材料工作区（为空时使用原始 workDir）
const showVerifyGuide = ref(false)

// Step5: 要素JSON生成
const fjIsRunning = ref(false)
const fjResults = ref([])
const fjPreviewItem = ref(null)
const fjCopiedItem = ref(null)
const fjDownloadingAll = ref(false)
const fjGroupSize = ref(4)

// 计算属性
const canGenerate = computed(() => Boolean(
  workDir.value &&
  selectedMaterials.value.length > 0 &&
  factors.value.length > 0
))
const batchDoneCount = computed(() => Object.keys(batchResults.value).length)
const verifyDoneCount = computed(() => Object.values(verifyResults.value).filter(v => v?.success).length)
const activeResult = computed(() => batchResults.value[activeBatchMaterial.value] || null)
const activeVerifyPrompt = computed(() => {
  const r = batchResults.value[activeVerifyMaterial.value]
  return r?.prompt_template || ''
})

function addLog(message, type = 'info') {
  logs.value.push({
    time: new Date().toLocaleTimeString(),
    message: String(message),
    type
  })
  nextTick(() => {
    if (logContainer.value) {
      logContainer.value.scrollTop = logContainer.value.scrollHeight
    }
  })
}

function getLogClass(type) {
  switch (type) {
    case 'error':
      return 'text-red-400'
    case 'success':
      return 'text-green-400'
    case 'warning':
      return 'text-yellow-400'
    default:
      return 'text-blue-300'
  }
}

function persistWorkDir() {
  if (typeof window === 'undefined') return
  if (workDir.value) {
    setScopedStorageItem(WORKDIR_STORAGE_KEY, workDir.value)
  } else {
    removeScopedStorageItem(WORKDIR_STORAGE_KEY)
  }
}

// 多选材料辅助
function isMaterialSelected(m) {
  return selectedMaterials.value.some(s => s.name === m.name)
}
function toggleMaterial(m) {
  const idx = selectedMaterials.value.findIndex(s => s.name === m.name)
  if (idx >= 0) selectedMaterials.value.splice(idx, 1)
  else selectedMaterials.value.push(m)
}
function toggleAllMaterials() {
  if (selectedMaterials.value.length === materials.value.length) {
    selectedMaterials.value = []
  } else {
    selectedMaterials.value = [...materials.value]
  }
}
function switchBatchMaterial(name) {
  activeBatchMaterial.value = name
  const r = batchResults.value[name]
  editablePrompt.value = r?.prompt_template || ''
  promptModified.value = false
}
function switchVerifyMaterial(name) {
  activeVerifyMaterial.value = name
}

watch(editablePrompt, (val) => {
  // sync edits back into batchResults so they persist on tab switch
  if (activeBatchMaterial.value && batchResults.value[activeBatchMaterial.value]) {
    batchResults.value[activeBatchMaterial.value].prompt_template = val
    promptModified.value = true
  }
})

async function loadModels() {
  try {
    const settings = await apiClient.get('/api/settings')
    const mods = (settings.models && settings.models.length > 0) ? settings.models : [
      { id: '1', name: 'Qwen VL Max', model_id: 'qwen-vl-max', type: 'vl' },
      { id: '2', name: 'Qwen VL Plus', model_id: 'qwen-vl-plus', type: 'vl' },
      { id: '3', name: 'Qwen2.5 VL 72B', model_id: 'qwen2.5-vl-72b-instruct', type: 'vl' },
    ]
    availableModels.value = mods
    const defaultId = settings.default_model_id || mods[0]?.id || ''
    if (!mods.find(m => m.id === selectedModelId.value)) {
      selectedModelId.value = defaultId
    }
  } catch (e) { console.error(e) }
}

onActivated(() => { loadModels() })

onMounted(async () => {
  await loadModels()

  // 使用 HTTP API 获取日志
  const logInterval = setInterval(async () => {
    try {
      const logs = await apiClient.get('/api/logs')
      // 处理日志...
    } catch (e) {
      // 忽略错误
    }
  }, 1000)

  onUnmounted(() => clearInterval(logInterval))

  if (!workDir.value && typeof window !== 'undefined') {
    const storedWorkDir = getScopedStorageItem(WORKDIR_STORAGE_KEY)
    if (storedWorkDir) {
      workDir.value = storedWorkDir
      addLog(`已恢复上次工作区: ${storedWorkDir}`, 'info')
      await loadDirectoryData()
    }
  }
})

async function onWorkDirInput() {
  const dir = workDir.value.trim()
  workDir.value = dir
  persistWorkDir()
  if (dir) await loadDirectoryData()
}

async function selectWorkDir() {
  try {
    // 使用文件选择器
    const input = document.createElement('input')
    input.type = 'file'
    input.webkitdirectory = true
    input.onchange = async (e) => {
      const files = e.target.files
      if (files.length === 0) return
      // 上传文件到服务器
      const formData = new FormData()
      for (const file of files) {
        formData.append('files', file)
      }
      const result = await apiClient.upload('/api/workspaces/upload', formData)
      if (result.data && result.data.path) {
        workDir.value = result.data.path
        persistWorkDir()
        addLog(`已上传工作区: ${result.data.path}`, 'info')
        await loadDirectoryData()
      }
    }
    input.click()
  } catch (error) {
    addLog(`上传工作区失败: ${error}`, 'error')
  }
}

async function selectWorkDirV2() {
  try {
    const input = document.createElement('input')
    input.type = 'file'
    input.webkitdirectory = true
    input.onchange = async (e) => {
      const files = Array.from(e.target.files || [])
      if (files.length === 0) return

      const entries = files.map((file) => ({
        file,
        relativePath: file.webkitRelativePath || file.name
      }))

      const formData = new FormData()
      formData.append('name', entries[0]?.relativePath?.split('/')[0] || 'workspace')
      formData.append(
        'manifest',
        JSON.stringify(entries.map((entry) => ({ relativePath: entry.relativePath })))
      )
      entries.forEach((entry) => {
        formData.append('files', entry.file, entry.file.name)
      })

      const result = await apiClient.upload('/api/workspaces', formData)
      const nextPath = result?.rootPath || result?.data?.path || ''
      if (nextPath) {
        workDir.value = nextPath
        persistWorkDir()
        addLog(`宸蹭笂浼犲伐浣滃尯: ${nextPath}`, 'info')
        await loadDirectoryData()
      }
    }
    input.click()
  } catch (error) {
    addLog(`涓婁紶宸ヤ綔鍖哄け璐? ${error}`, 'error')
  }
}

async function selectWorkDirFromService() {
  try {
    const selected = await invoke('select_directory')
    if (!selected) return
    workDir.value = selected
    persistWorkDir()
    addLog(`已上传工作区: ${selected}`, 'info')
    await loadDirectoryData()
  } catch (error) {
    addLog(`上传工作区失败: ${error}`, 'error')
  }
}

async function selectVerifyWorkDir() {
  try {
    const selected = await invoke('select_directory')
    if (!selected) return
    verifyWorkDir.value = selected
    verifyResults.value = {}
    addLog(`已上传验证材料工作区: ${selected}`, 'info')
    addLog('后续验证将使用新上传的材料（而非原始工作区材料）', 'info')
  } catch (error) {
    addLog(`上传验证材料失败: ${error}`, 'error')
  }
}

async function loadDirectoryData() {
  factors.value = []
  materials.value = []
  selectedMaterials.value = []
  batchResults.value = {}
  verifyResults.value = {}
  editablePrompt.value = ''
  try {
    const factorsData = await apiClient.get('/api/workspaces/factors', { workDir: workDir.value })
    factors.value = factorsData.data || []
    addLog(`读取到 ${factors.value.length} 个要素字段`, 'success')
  } catch (error) {
    addLog(`读取要素失败: ${error}`, 'error')
  }
  try {
    const materialsData = await apiClient.get('/api/workspaces/materials', { workDir: workDir.value })
    materials.value = materialsData.data || []
    addLog(`发现 ${materials.value.length} 个材料类型`, 'success')
    selectedMaterials.value = [...materials.value]
  } catch (error) {
    addLog(`扫描材料目录失败: ${error}`, 'error')
  }
}

async function goStep2() {
  if (!canGenerate.value || isRunning.value) return
  currentStep.value = 2
  isRunning.value = true
  batchResults.value = {}
  verifyResults.value = {}
  editablePrompt.value = ''
  promptModified.value = false
  batchElapsed.value = 0
  currentElapsed.value = 0
  batchStartTime.value = Date.now()

  // 启动计时器，每秒更新
  elapsedTimer = setInterval(() => {
    batchElapsed.value = Math.floor((Date.now() - batchStartTime.value) / 1000)
  }, 1000)

  addLog(`开始批量生成提示词，共 ${selectedMaterials.value.length} 种材料`, 'info')

  for (const mat of selectedMaterials.value) {
    batchCurrentMaterial.value = mat.name
    currentElapsed.value = 0
    const matStart = Date.now()
    addLog(`[${mat.name}] 开始生成...`, 'info')
    try {
      const generateResult = await apiClient.post('/api/generate/prompt', {
        workDir: workDir.value,
        materialName: mat.name,
        modelCfgId: selectedModelId.value || null
      })
      const elapsed = ((Date.now() - matStart) / 1000).toFixed(1)
      const resultData = { ...generateResult.data }
      if (!resultData.prompt_template?.trim() && resultData.output_file) {
        const fileResult = await apiClient.get('/api/files/read', { path: resultData.output_file })
        resultData.prompt_template = fileResult?.data?.content || ''
      }
      if (!resultData.prompt_template?.trim()) {
        throw new Error('提示词文件为空，未生成有效内容')
      }
      batchResults.value[mat.name] = { ...resultData, success: true, elapsed }
      addLog(`[${mat.name}] 生成成功！耗时 ${elapsed}s`, 'success')
      if (resultData.output_file) addLog(`已保存: ${resultData.output_file}`, 'success')
    } catch (error) {
      const elapsed = ((Date.now() - matStart) / 1000).toFixed(1)
      const errStr = String(error)
      const msg = errStr.includes('API Key') || errStr.includes('DASHSCOPE')
        ? '未配置API密钥，请前往【设置】页面配置 DASHSCOPE_API_KEY'
        : String(error)
      batchResults.value[mat.name] = { success: false, error: msg, prompt_template: '', output_file: '', elapsed }
      addLog(`[${mat.name}] 生成失败: ${msg}`, 'error')
    }
  }

  clearInterval(elapsedTimer)
  batchElapsed.value = Math.floor((Date.now() - batchStartTime.value) / 1000)
  batchCurrentMaterial.value = ''
  isRunning.value = false

  // 自动切换到第一个成功的材料
  const firstSuccess = selectedMaterials.value.find(m => batchResults.value[m.name]?.success)
  if (firstSuccess) {
    activeBatchMaterial.value = firstSuccess.name
    editablePrompt.value = batchResults.value[firstSuccess.name].prompt_template || ''
    promptModified.value = false
    nextTick(() => { if (promptTextarea.value) promptTextarea.value.scrollTop = 0 })
  }
  const successCount = Object.values(batchResults.value).filter(r => r.success).length
  addLog(`批量生成完成：成功 ${successCount}/${selectedMaterials.value.length}，总耗时 ${batchElapsed.value}s`, 'success')
}

async function runVerify() {
  if (isVerifying.value || !activeVerifyPrompt.value) return
  const matName = activeVerifyMaterial.value
  if (!matName) return
  isVerifying.value = true
  verifyElapsed.value = 0
  const verifyStart = Date.now()
  verifyTimer = setInterval(() => {
    verifyElapsed.value = Math.floor((Date.now() - verifyStart) / 1000)
  }, 1000)
  const baseDir = verifyWorkDir.value || workDir.value
  addLog(`[验证] 开始验证「${matName}」...${verifyWorkDir.value ? '（使用验证材料）' : ''}`, 'info')
  try {
    const materialDir = `${baseDir}/${matName}`
    const promptText = activeVerifyPrompt.value
    const vr = await apiClient.post('/api/generate/verify', { materialDir, promptText, modelCfgId: selectedModelId.value || null })
    verifyResults.value = { ...verifyResults.value, [matName]: vr.data }
    if (vr.data.success) {
      addLog(`[验证] 「${matName}」提取完成，请人工检查结果`, 'success')
    } else {
      addLog(`[验证失败] 「${matName}」: ${vr.data.error}`, 'error')
    }
  } catch (e) {
    addLog(`[验证异常] ${e}`, 'error')
    verifyResults.value = { ...verifyResults.value, [matName]: { success: false, image_file: '', extraction_output: '', error: String(e) } }
  } finally {
    clearInterval(verifyTimer)
    isVerifying.value = false
  }
}

async function savePrompt() {
  const matName = activeBatchMaterial.value
  const r = batchResults.value[matName]
  if (!r?.output_file || isSaving.value) return
  isSaving.value = true
  try {
    await apiClient.post('/api/generate/save-prompt', { filePath: r.output_file, content: editablePrompt.value })
    if (batchResults.value[matName]) batchResults.value[matName].prompt_template = editablePrompt.value
    promptModified.value = false
    addLog(`「${matName}」提示词修改已保存`, 'success')
  } catch (e) {
    addLog(`保存失败: ${e}`, 'error')
  } finally {
    isSaving.value = false
  }
}

function handleStepNav(step) {
  if (step > maxReachableStep.value) return
  if (isRunning.value || isVerifying.value) return
  currentStep.value = step
}

function goToStep3() {
  // 初始化验证材料为第一个已成功生成的材料
  if (!activeVerifyMaterial.value) {
    const first = selectedMaterials.value.find(m => batchResults.value[m.name]?.success)
    activeVerifyMaterial.value = first ? first.name : (selectedMaterials.value[0]?.name || '')
  }
  currentStep.value = 3
}

function confirmAndGoStep4() {
  addLog('✓ 人工确认提取结果正确，完成！', 'success')
  currentStep.value = 4
}

async function copyPrompt() {
  const text = editablePrompt.value
  if (!text) return
  try {
    await navigator.clipboard.writeText(text)
    copied.value = true
    setTimeout(() => { copied.value = false }, 2000)
  } catch (e) {
    addLog(`复制失败: ${e}`, 'error')
  }
}

function goNextMaterial() {
  selectedMaterials.value = []
  batchResults.value = {}
  verifyResults.value = {}
  verifyWorkDir.value = ''
  editablePrompt.value = ''
  promptModified.value = false
  activeBatchMaterial.value = ''
  activeVerifyMaterial.value = ''
  fjResults.value = []
  fjPreviewItem.value = null
  fjCopiedItem.value = null
  fjDownloadingAll.value = false
  currentStep.value = 1
}

function goToStep5() {
  fjResults.value = []
  fjPreviewItem.value = null
  fjCopiedItem.value = null
  fjDownloadingAll.value = false
  currentStep.value = 5
}

async function generateFactorJson() {
  if (!workDir.value || fjIsRunning.value) return
  fjIsRunning.value = true
  fjResults.value = []
  addLog(`开始生成要素JSON（每组最多 ${fjGroupSize.value} 个要素）...`, 'info')
  try {
    const materialNames = selectedMaterials.value.map(m => m.name)
    const res = await apiClient.post('/api/generate/factor-json', { workDir: workDir.value, groupSize: fjGroupSize.value, materials: materialNames })
    fjResults.value = res.data
    const ok = res.data.filter(r => r.success).length
    addLog(`生成完成！共 ${res.data.length} 个材料，成功 ${ok} 个`, 'success')
  } catch (e) {
    addLog(`生成失败: ${e}`, 'error')
  } finally {
    fjIsRunning.value = false
  }
}

async function fjTogglePreview(r) {
  if (fjPreviewItem.value === r) { fjPreviewItem.value = null; return }
  fjPreviewItem.value = r
  if (!r.previewContent && !r.loadingPreview) {
    r.loadingPreview = true
    try {
      const result = await apiClient.get('/api/files/read', { path: r.output })
      r.previewContent = JSON.stringify(JSON.parse(result.data.content), null, 2)
    } catch (e) { r.previewError = String(e) }
    finally { r.loadingPreview = false }
  }
}

function fjDownloadJson(r) {
  try { 
    apiClient.open('/api/files/download', { path: r.output })
    const filename = r.output.split(/[/\\]/).pop()
    addLog(`开始下载: ${filename}`, 'success')
  }
  catch (e) { addLog(`下载失败: ${e}`, 'error') }
}

function fjDownloadAll() {
  const successPaths = fjResults.value.filter(r => r.success).map(r => r.output)
  if (successPaths.length === 0 || fjDownloadingAll.value) return

  fjDownloadingAll.value = true
  try {
    apiClient.open('/api/files/download-batch', { pathsJson: JSON.stringify(successPaths) })
    addLog(`开始批量下载 ${successPaths.length} 个 JSON 文件`, 'success')
  } catch (e) {
    addLog(`批量下载失败: ${e}`, 'error')
  } finally {
    fjDownloadingAll.value = false
  }
}

async function fjCopyJson(r) {
  try {
    let content = r.previewContent
    if (!content) {
      const result = await apiClient.get('/api/files/read', { path: r.output })
      content = JSON.stringify(JSON.parse(result.data.content), null, 2)
    }
    await navigator.clipboard.writeText(content)
    fjCopiedItem.value = r.material
    setTimeout(() => { fjCopiedItem.value = null }, 2000)
  } catch (e) { addLog(`复制失败: ${e}`, 'error') }
}

async function clear() {
  currentStep.value = 1
  workDir.value = ''
  showStructureGuide.value = false
  persistWorkDir()
  factors.value = []
  materials.value = []
  selectedMaterials.value = []
  batchResults.value = {}
  verifyResults.value = {}
  verifyWorkDir.value = ''
  editablePrompt.value = ''
  promptModified.value = false
  activeBatchMaterial.value = ''
  activeVerifyMaterial.value = ''
  logs.value = []
  fjResults.value = []
  fjPreviewItem.value = null
  fjCopiedItem.value = null
  fjDownloadingAll.value = false
  await loadModels()
}
</script>

<style scoped>
.structure-guide-enter-active,
.structure-guide-leave-active {
  transition: opacity 0.18s ease, transform 0.18s ease;
}

.structure-guide-enter-from,
.structure-guide-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}
</style>
