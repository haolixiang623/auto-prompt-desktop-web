<template>
  <!-- 整体：左右双栏，左侧固定 sidebar，右侧滚动内容 -->
  <div class="flex h-full min-h-0 flex-col xl:flex-row">

    <!-- ═══ 左侧固定 Step 导航 ═══ -->
    <div class="w-full flex-shrink-0 bg-white border-b flex flex-col xl:w-56 xl:border-b-0 xl:border-r">
      <!-- 标题 -->
      <div class="border-b px-4 pb-4 pt-5 sm:px-5 sm:pt-6">
        <h1 class="text-base font-bold text-gray-900 leading-tight">生成提取提示词</h1>
        <p class="text-xs text-gray-400 mt-1 leading-relaxed">智能生成文档要素提取提示词</p>
      </div>

      <!-- Step 列表 -->
      <nav class="flex gap-2 overflow-x-auto px-3 py-3 xl:flex-1 xl:flex-col xl:gap-1 xl:overflow-visible xl:px-3 xl:py-4">
        <button v-for="(s, i) in steps" :key="i"
          @click="handleStepNav(i + 1)"
          :disabled="i + 1 > maxReachableStep"
          class="group flex min-w-[160px] flex-shrink-0 items-center gap-2 rounded-lg px-3 py-2 text-left transition-all xl:w-full xl:min-w-0 xl:gap-3 xl:px-3 xl:py-2.5"
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
          <div class="flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full text-[11px] font-bold transition-all xl:h-7 xl:w-7 xl:text-xs"
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
          <div class="min-w-0 flex-1">
            <div class="text-xs font-semibold truncate">{{ s.title }}</div>
            <div class="mt-0.5 hidden truncate text-xs xl:block"
              :class="currentStep === i + 1 ? 'text-blue-500' : currentStep > i + 1 ? 'text-green-500' : 'text-gray-400'">
              {{ currentStep > i + 1 ? s.done : currentStep === i + 1 ? s.active : s.pending }}
            </div>
          </div>
          <!-- 当前步骤指示线 -->
          <div v-if="currentStep === i + 1" class="hidden h-5 w-1 flex-shrink-0 rounded-full bg-blue-500 xl:block"></div>
        </button>
      </nav>

      <!-- 底部操作 -->
      <div class="border-t px-3 pb-4">
        <div class="flex flex-col gap-3 pt-2 sm:flex-row sm:items-center sm:justify-between xl:flex-col xl:items-stretch xl:justify-start">
        <!-- 运行状态 -->
        <div v-if="isRunning || isVerifying" class="flex items-center gap-2 rounded-lg bg-blue-50 px-3 py-2 sm:flex-1 xl:flex-none">
          <svg class="animate-spin w-3.5 h-3.5 text-blue-500 flex-shrink-0" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
          </svg>
          <span class="text-xs text-blue-600">{{ isRunning ? `生成中... ${batchElapsed}s` : `验证中... ${verifyElapsed}s` }}</span>
        </div>
        <button v-if="isRunning" @click="cancelBatchGeneration" :disabled="stopRequested"
          class="flex w-full items-center justify-center gap-1.5 rounded-lg border border-red-200 px-3 py-2 text-xs text-red-600 transition hover:bg-red-50 disabled:opacity-50 sm:w-auto sm:min-w-36 xl:w-full">
          <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 6h12v12H6z" />
          </svg>
          {{ stopRequested ? '停止中...' : '停止生成' }}
        </button>
        <button @click="clear" :disabled="isRunning || isVerifying"
          class="flex w-full items-center justify-center gap-1.5 rounded-lg border border-gray-200 px-3 py-2 text-xs text-gray-500 transition hover:bg-gray-50 hover:text-gray-700 disabled:opacity-40 sm:w-auto sm:min-w-36 xl:w-full">
          <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
          </svg>
          重新开始
        </button>
        </div>
      </div>
    </div>

    <!-- ═══ 右侧滚动内容区 ═══ -->
    <div class="flex-1 overflow-y-auto bg-gray-50">
      <div class="w-full max-w-5xl p-4 sm:p-6">

        <!-- ── STEP 1 内容：上传工作区与材料 ── -->
        <div v-if="currentStep === 1" class="space-y-4">
          <div class="flex items-center gap-2 mb-1">
            <span class="text-lg font-bold text-gray-900">上传工作区与材料类型</span>
          </div>
          <p class="text-sm text-gray-500">上传包含 factors.xlsx 的工作区，然后勾选要生成提示词的材料类型（支持多选）</p>

          <!-- 工作区选择 -->
          <div class="bg-white rounded-xl border p-4">
            <label class="block text-xs font-semibold text-gray-600 mb-2 uppercase tracking-wide">工作区</label>
            <div class="flex flex-col gap-2 sm:flex-row sm:items-start">
              <input type="text" v-model="workDir" placeholder="上传后会显示服务端工作区路径，或直接粘贴已有路径"
                class="w-full flex-1 px-3 py-2 border rounded-lg text-sm bg-gray-50 text-gray-700"
                @change="onWorkDirInput" />
              <button @click="selectWorkDirFromService" :disabled="isRunning || isUploading"
                class="flex w-full flex-shrink-0 items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-blue-700 disabled:opacity-50 sm:w-auto">
                <svg v-if="isUploading" class="animate-spin w-4 h-4 flex-shrink-0" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
                </svg>
                {{ isUploading ? (uploadPhase === 'picking' ? '选择中...' : '上传中...') : '上传文件夹...' }}
              </button>
              <div
                class="relative flex-shrink-0 self-end sm:self-auto"
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
                      <p>4. 统一校验会同时检查要素列和审查要点列，建议 factors.xlsx 维护完整的统一工作表</p>
                    </div>
                  </div>
                </Transition>
              </div>
            </div>
            <!-- 上传进度条 -->
            <Transition name="structure-guide">
              <div v-if="isUploading && uploadPhase === 'picking'" class="mt-3 rounded-lg border border-amber-200 bg-amber-50 p-3">
                <div class="flex items-center gap-2">
                  <svg class="animate-spin w-4 h-4 text-amber-500 flex-shrink-0" fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
                  </svg>
                  <span class="text-sm font-medium text-amber-700">正在扫描文件夹，请在弹窗中选择目录...</span>
                </div>
              </div>
            </Transition>
            <Transition name="structure-guide">
              <div v-if="isUploading && uploadPhase === 'uploading'" class="mt-3 rounded-lg border border-blue-200 bg-blue-50 p-3 space-y-2">
                <div class="flex items-center justify-between">
                  <div class="flex items-center gap-2">
                    <svg class="animate-spin w-4 h-4 text-blue-500 flex-shrink-0" fill="none" viewBox="0 0 24 24">
                      <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                      <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
                    </svg>
                    <span class="text-sm font-medium text-blue-700">正在上传 {{ uploadFileCount }} 个文件...</span>
                  </div>
                  <span class="text-xs text-blue-500 tabular-nums font-medium">{{ uploadProgress }}%</span>
                </div>
                <div class="w-full bg-blue-200 rounded-full h-2 overflow-hidden">
                  <div class="bg-blue-600 h-2 rounded-full transition-all duration-300 ease-out" :style="{ width: uploadProgress + '%' }"></div>
                </div>
                <div class="flex items-center justify-between text-xs text-blue-500">
                  <span class="tabular-nums">{{ formatSize(uploadedBytes) }} / {{ formatSize(totalBytes) }}</span>
                  <span v-if="uploadSpeed" class="tabular-nums">{{ uploadSpeed }}</span>
                </div>
              </div>
            </Transition>
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

          <WorkspaceValidationStatusBar
            v-if="workDir"
            :status="factorValidationStatus"
            :issue-count="factorValidationErrors.length"
            :checking="factorValidationChecking"
            :checked-at="factorValidationCheckedAt"
            @validate="runGenerateWorkspaceValidation"
            @open-repair="openFactorsWorkbookRepairDesk"
            @download-workbook="downloadFactorsWorkbook"
          />

          <!-- 要素 + 材料 双列 -->
          <div v-if="factors.length > 0 || materials.length > 0" class="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <!-- 要素字段 -->
            <div class="bg-white rounded-xl border overflow-hidden">
              <div class="flex flex-col gap-2 px-4 py-3 border-b bg-gray-50 sm:flex-row sm:items-center sm:justify-between">
                <span class="text-sm font-semibold text-gray-700">识别要素字段</span>
                <span class="px-2 py-0.5 bg-blue-100 text-blue-700 rounded-full text-xs font-medium">{{ selectedFactors.length }} 个</span>
              </div>
              <div class="max-h-72 overflow-y-auto p-3">
                <div class="grid grid-cols-1 gap-2 xl:grid-cols-2">
                  <div
                    v-for="(f, i) in selectedFactors"
                    :key="`${f.field_name}-${i}`"
                    class="flex items-start gap-2.5 rounded-lg border border-slate-100 bg-slate-50 px-3 py-2.5"
                  >
                    <span class="mt-0.5 flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full bg-blue-50 text-xs font-medium text-blue-600">{{ i + 1 }}</span>
                    <span class="min-w-0 text-sm leading-5 text-gray-700 whitespace-normal break-words">{{ f.field_name }}</span>
                  </div>
                </div>
              </div>
            </div>
            <!-- 材料类型多选 -->
            <div class="bg-white rounded-xl border overflow-hidden">
              <div class="flex flex-col gap-2 px-4 py-3 border-b bg-gray-50 sm:flex-row sm:items-center sm:justify-between">
                <span class="text-sm font-semibold text-gray-700">材料类型（多选）</span>
                <div class="flex items-center gap-2 self-start sm:self-auto">
                  <span class="px-2 py-0.5 bg-purple-100 text-purple-700 rounded-full text-xs font-medium">已选 {{ selectedMaterials.length }}/{{ materials.length }}</span>
                  <button @click="toggleAllMaterials"
                    class="text-xs text-blue-600 hover:text-blue-800 font-medium">
                    {{ selectedMaterials.length === materials.length ? '取消全选' : '全选' }}
                  </button>
                </div>
              </div>
              <div class="divide-y max-h-72 overflow-y-auto">
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
                    <div
                      class="text-sm leading-5 whitespace-normal break-words"
                      :class="isMaterialSelected(m) ? 'font-semibold text-blue-800' : 'text-gray-700'"
                    >
                      {{ m.name }}
                    </div>
                    <div class="mt-1 text-xs text-gray-400">{{ m.image_count }} 个样本文件</div>
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

          <div class="bg-white rounded-xl border p-4 space-y-4">
            <div class="flex items-center justify-between gap-4">
              <div>
                <div class="text-sm font-semibold text-gray-700">优先使用提示词库</div>
                <div class="text-xs text-gray-400 mt-1">默认开启，命中时直接复用历史要素提示词</div>
              </div>
              <label class="inline-flex items-center cursor-pointer">
                <input v-model="useCaseLibrary" type="checkbox" class="sr-only peer">
                <div class="relative w-11 h-6 bg-gray-200 rounded-full peer peer-checked:bg-blue-600 transition-colors">
                  <div class="absolute top-0.5 left-0.5 h-5 w-5 bg-white rounded-full transition-transform peer-checked:translate-x-5"></div>
                </div>
              </label>
            </div>
            <div v-if="availableExtractProfiles.length > 0">
              <label class="block text-xs font-semibold text-gray-600 mb-2 uppercase tracking-wide">未命中规则 Profile</label>
              <select v-model="selectedRuleProfileId" class="w-full px-3 py-2 border rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-300">
                <option v-for="profile in availableExtractProfiles" :key="profile.id" :value="profile.id">
                  {{ profile.name || profile.id }}
                </option>
              </select>
            </div>
          </div>

          <!-- 操作按钮 -->
          <div class="flex flex-col gap-3 pt-2 sm:flex-row sm:items-center sm:justify-between">
            <div class="text-sm text-gray-500">
              <span v-if="!workDir">请先上传工作区</span>
              <span v-else-if="selectedMaterials.length === 0">请勾选至少一种材料类型</span>
              <span v-else class="text-green-600 flex items-center gap-1">
                <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/></svg>
                已选 {{ selectedMaterials.length }} 种材料，共 {{ selectedFactors.length }} 个要素字段
              </span>
            </div>
            <button @click="goStep2" :disabled="!canGenerate || isRunning"
              class="flex w-full items-center justify-center gap-2 rounded-lg px-6 py-2.5 text-sm font-semibold transition-all sm:w-auto"
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
            <p class="text-sm text-gray-400 mt-1">调用所选模型分析图片要素，请稍候</p>
            <p class="text-lg font-mono font-bold text-blue-500 mt-3">{{ batchElapsed }}s</p>
            <button @click="cancelBatchGeneration" :disabled="stopRequested"
              class="mt-5 inline-flex items-center gap-2 rounded-lg border border-red-200 px-4 py-2 text-sm font-medium text-red-600 transition hover:bg-red-50 disabled:opacity-50">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 6h12v12H6z" />
              </svg>
              {{ stopRequested ? '停止中...' : '停止生成' }}
            </button>
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

            <div class="bg-white rounded-xl border overflow-hidden">
              <div class="flex items-center justify-between px-4 py-3 border-b bg-gray-50">
                <div class="flex items-center gap-2">
                  <span class="text-sm font-semibold text-gray-700">要素提示词</span>
                  <span class="text-xs text-gray-400 bg-gray-100 px-2 py-0.5 rounded">{{ activeArtifactFactors.length }} 个字段</span>
                </div>
                <div class="flex items-center gap-2">
                  <button @click="copyPrompt"
                    class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition"
                    :class="copied ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'">
                    <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"/>
                    </svg>
                    {{ copied ? '已复制预览' : '复制预览' }}
                  </button>
                  <button v-if="promptModified" @click="saveArtifact" :disabled="isSaving"
                    class="flex items-center gap-1.5 px-3 py-1.5 bg-amber-500 text-white rounded-lg text-xs font-medium hover:bg-amber-600 transition">
                    <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3m-1 4l-3 3m0 0l-3-3m3 3V4"/>
                    </svg>
                    {{ isSaving ? '保存中...' : '保存修改' }}
                  </button>
                  <span v-else class="text-xs text-gray-300">已保存</span>
                </div>
              </div>
              <div class="divide-y">
                <div v-for="(factor, factorIndex) in activeArtifactFactors" :key="`${factor.factorname}-${factorIndex}`" class="p-4 space-y-2">
                  <div class="flex items-center justify-between gap-3">
                    <div>
                      <div class="text-sm font-semibold text-gray-800">{{ factor.factorname }}</div>
                      <div v-if="factor.factoruse" class="text-xs text-gray-400 mt-1">{{ factor.factoruse }}</div>
                    </div>
                    <span class="px-2 py-0.5 rounded-full text-xs font-medium"
                      :class="factor.source === 'case_library'
                        ? 'bg-green-50 text-green-700 border border-green-200'
                        : factor.source === 'ai_generated'
                          ? 'bg-blue-50 text-blue-700 border border-blue-200'
                          : 'bg-amber-50 text-amber-700 border border-amber-200'">
                      {{ sourceLabel(factor.source) }}
                    </span>
                  </div>
                  <textarea
                    :value="factor.factor_prompt"
                    @input="updateFactorPrompt(factorIndex, $event.target.value)"
                    class="w-full text-xs text-gray-700 leading-relaxed bg-white p-3 outline-none resize-y font-mono border rounded-lg"
                    rows="4"
                    placeholder="请输入该要素对应的提取提示词..."
                  />
                </div>
              </div>
            </div>

            <div class="bg-white rounded-xl border overflow-hidden">
              <div class="px-4 py-3 border-b bg-gray-50 flex items-center justify-between">
                <span class="text-sm font-semibold text-gray-700">完整提示词预览</span>
                <span class="text-xs text-gray-400">系统按模板自动拼装，仅供验证查看</span>
              </div>
              <pre class="text-xs text-gray-700 leading-relaxed whitespace-pre-wrap p-4 max-h-72 overflow-y-auto font-mono">{{ activePreviewPrompt }}</pre>
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
            <span class="text-xs text-gray-400">调用所选模型对「{{ activeVerifyMaterial }}」样本执行提取{{ verifyWorkDir ? '（验证材料）' : '' }}</span>
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
                  <div v-else class="flex items-center gap-1.5 flex-shrink-0">
                    <button @click="retrySingleMaterial(r.material)"
                      :disabled="isRunning || !!retryingMaterials[r.material]"
                      class="flex items-center gap-1 px-2 py-1 rounded text-xs transition"
                      :class="!isRunning && !retryingMaterials[r.material]
                        ? 'bg-orange-100 text-orange-700 hover:bg-orange-200'
                        : 'bg-gray-100 text-gray-400 cursor-not-allowed'">
                      <svg v-if="retryingMaterials[r.material]" class="w-3 h-3 animate-spin" fill="none" viewBox="0 0 24 24">
                        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
                      </svg>
                      {{ retryingMaterials[r.material] ? '生成中...' : '重新生成' }}
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

        <FactorsWorkbookRepairPanel
          :open="showFactorsWorkbookRepair"
          :work-dir="workDir"
          :errors="factorValidationErrors"
          :diagnostics="factorValidationDiagnostics"
          @close="showFactorsWorkbookRepair = false"
          @validation-updated="handleFactorsWorkbookValidationUpdated"
          @log="addLog"
        />

      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, onActivated, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { getScopedStorageItem, removeScopedStorageItem, setScopedStorageItem } from '../services/authState.js'
import { apiClient } from '../services/apiClient.js'
import { cancelTask, isTaskCancelledError, startTask, waitForTask } from '../services/taskService.js'
import { invoke } from '../tauri/tauri.js'
import { selectWorkspace } from '../services/uploadService.js'
import FactorsWorkbookRepairPanel from '../components/FactorsWorkbookRepairPanel.vue'
import WorkspaceValidationStatusBar from '../components/WorkspaceValidationStatusBar.vue'
import { applyFactorPromptEdit, buildPreviewPrompt, normalizeArtifact, sourceLabel } from './generateArtifactState.js'

const route = useRoute()

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
const isUploading = ref(false)
const uploadPhase = ref('')
const uploadProgress = ref(0)
const uploadFileCount = ref(0)
const uploadedBytes = ref(0)
const totalBytes = ref(0)
const uploadSpeed = ref('')
let uploadSpeedLastTime = 0
let uploadSpeedLastBytes = 0
const factors = ref([])
const materials = ref([])
const selectedMaterials = ref([])  // 多选材料列表
const availableModels = ref([])
const selectedModelId = ref('')
const availableExtractProfiles = ref([])
const selectedRuleProfileId = ref('')
const useCaseLibrary = ref(true)
const isRunning = ref(false)
const logs = ref([])
const logContainer = ref(null)
const copied = ref(false)
const factorValidationErrors = ref([])
const factorValidationDiagnostics = ref([])
const factorValidationStatus = ref('idle')
const factorValidationCheckedAt = ref('')
const factorValidationChecking = ref(false)
const showFactorsWorkbookRepair = ref(false)
const currentTaskId = ref('')
const stopRequested = ref(false)

// Step2: 批量生成状态
const batchResults = ref({})        // { materialName: { success, artifact, artifact_file, preview_prompt, output_file, error, elapsed, dirty } }
const batchCurrentMaterial = ref('') // 当前正在生成的材料名
const activeBatchMaterial = ref('')  // 当前展示编辑的材料名
const promptModified = ref(false)
const isSaving = ref(false)
const batchStartTime = ref(0)       // 批量生成开始时间
const batchElapsed = ref(0)         // 批量总耗时(秒)
const currentElapsed = ref(0)       // 当前材料耗时(秒)
const retryingMaterials = ref({})   // { materialName: boolean }
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
const selectedMaterialNames = computed(() => new Set(
  selectedMaterials.value.map(material => material.name)
))
const selectedFactors = computed(() => {
  if (selectedMaterialNames.value.size === 0) {
    return []
  }
  return factors.value.filter((factor) => !factor.material || selectedMaterialNames.value.has(factor.material))
})
const canGenerate = computed(() => Boolean(
  workDir.value &&
  selectedMaterials.value.length > 0 &&
  selectedFactors.value.length > 0
))
const batchDoneCount = computed(() => Object.keys(batchResults.value).length)
const verifyDoneCount = computed(() => Object.values(verifyResults.value).filter(v => v?.success).length)
const activeResult = computed(() => batchResults.value[activeBatchMaterial.value] || null)
const activeArtifactFactors = computed(() => activeResult.value?.artifact?.factors || [])
const activePreviewPrompt = computed(() => activeResult.value?.preview_prompt || '')
const activeVerifyPrompt = computed(() => {
  const r = batchResults.value[activeVerifyMaterial.value]
  return r?.preview_prompt || r?.prompt_template || ''
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

async function cancelBatchGeneration() {
  if (!isRunning.value || stopRequested.value) return
  stopRequested.value = true
  addLog('已请求停止生成，正在结束当前材料...', 'warning')
  if (!currentTaskId.value) return
  try {
    await cancelTask(currentTaskId.value)
  } catch (error) {
    stopRequested.value = false
    addLog(`停止生成失败: ${error}`, 'error')
  }
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

async function persistGenerateWorkspaceActivity(status) {
  if (!workDir.value) return
  const payload = {
    workDir: workDir.value,
    module: 'generate',
  }
  if (status !== undefined) {
    payload.status = status
  }
  await apiClient.put('/api/workspaces/activity', payload)
}

async function tagWorkspaceModule() {
  if (!workDir.value) return
  try {
    await persistGenerateWorkspaceActivity()
  } catch (error) {
    console.warn('标记要素生成工作区失败:', error)
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
  promptModified.value = Boolean(r?.dirty)
}
function switchVerifyMaterial(name) {
  activeVerifyMaterial.value = name
}

function updateFactorPrompt(factorIndex, nextPrompt) {
  const matName = activeBatchMaterial.value
  const current = batchResults.value[matName]
  if (!matName || !current?.artifact) return
  const nextResult = applyFactorPromptEdit(current, factorIndex, nextPrompt)
  batchResults.value = {
    ...batchResults.value,
    [matName]: nextResult,
  }
  promptModified.value = true
}

async function loadModels() {
  try {
    const settings = await apiClient.get('/api/settings')
    const mods = (settings.models && settings.models.length > 0) ? settings.models : [
      { id: '1', name: 'Qwen VL Max', model: 'qwen-vl-max', type: 'vl' },
      { id: '2', name: 'Qwen VL Plus', model: 'qwen-vl-plus', type: 'vl' },
      { id: '3', name: 'Qwen2.5 VL 72B', model: 'qwen2.5-vl-72b-instruct', type: 'vl' },
    ]
    availableModels.value = mods
    const defaultId = settings.default_model_id || mods[0]?.id || ''
    if (!mods.find(m => m.id === selectedModelId.value)) {
      selectedModelId.value = defaultId
    }
    availableExtractProfiles.value = Array.isArray(settings.extract_profiles) ? settings.extract_profiles : []
    const defaultProfileId = settings.default_extract_profile_id || availableExtractProfiles.value[0]?.id || ''
    if (!availableExtractProfiles.value.find(profile => profile.id === selectedRuleProfileId.value)) {
      selectedRuleProfileId.value = defaultProfileId
    }
  } catch (e) { console.error(e) }
}

onActivated(async () => {
  loadModels()
  const queryWorkDir = route.query.workDir
  if (queryWorkDir && queryWorkDir !== workDir.value) {
    workDir.value = queryWorkDir
    persistWorkDir()
    await tagWorkspaceModule()
    addLog(`已打开工作区: ${queryWorkDir}`, 'info')
    await loadDirectoryData()
  } else if (!queryWorkDir && !isRunning.value && workDir.value) {
    // 没有传入 workDir 且当前有旧工作区 → 自动重置，开始新一轮
    await clear()
  }
})

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

  // 优先使用 URL 中的 workDir 参数（从列表页跳转）
  const queryWorkDir = route.query.workDir
  if (queryWorkDir) {
    workDir.value = queryWorkDir
    persistWorkDir()
    await tagWorkspaceModule()
    addLog(`已打开工作区: ${queryWorkDir}`, 'info')
    await loadDirectoryData()
  } else if (!workDir.value && typeof window !== 'undefined') {
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
  if (dir) { await tagWorkspaceModule(); await loadDirectoryData() }
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
        await tagWorkspaceModule()
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
        await tagWorkspaceModule()
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
  if (isUploading.value) return
  isUploading.value = true
  uploadPhase.value = ''
  uploadProgress.value = 0
  uploadFileCount.value = 0
  try {
    const result = await selectWorkspace({
      onProgress: (e) => {
        uploadProgress.value = e.percent
        uploadedBytes.value = e.loaded
        totalBytes.value = e.total
        const now = Date.now()
        if (now - uploadSpeedLastTime >= 500) {
          const dt = (now - uploadSpeedLastTime) / 1000
          const db = e.loaded - uploadSpeedLastBytes
          if (dt > 0) uploadSpeed.value = formatSize(db / dt) + '/s'
          uploadSpeedLastTime = now
          uploadSpeedLastBytes = e.loaded
        }
      },
      onPhaseChange: (phase, fileCount) => {
        uploadPhase.value = phase
        if (fileCount) uploadFileCount.value = fileCount
        if (phase === 'uploading') {
          uploadSpeedLastTime = Date.now()
          uploadSpeedLastBytes = 0
        }
      }
    })
    if (!result?.rootPath) return
    workDir.value = result.rootPath
    persistWorkDir()
    await tagWorkspaceModule()
    addLog(`已上传工作区: ${result.rootPath}`, 'info')
    await loadDirectoryData()
  } catch (error) {
    addLog(`上传工作区失败: ${error}`, 'error')
  } finally {
    isUploading.value = false
    uploadPhase.value = ''
    uploadProgress.value = 0
    uploadedBytes.value = 0
    totalBytes.value = 0
    uploadSpeed.value = ''
  }
}

function formatSize(bytes) {
  if (bytes < 1024) return bytes.toFixed(0) + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
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
  factorValidationErrors.value = []
  factorValidationDiagnostics.value = []
  factorValidationStatus.value = 'idle'
  factorValidationCheckedAt.value = ''
  factorValidationChecking.value = false
  showFactorsWorkbookRepair.value = false
  batchResults.value = {}
  retryingMaterials.value = {}
  verifyResults.value = {}
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

function applyFactorValidationResult(validation) {
  factorValidationCheckedAt.value = new Date().toISOString()
  if (validation?.ok) {
    factorValidationStatus.value = 'valid'
    factorValidationErrors.value = []
    factorValidationDiagnostics.value = []
    return true
  }
  factorValidationStatus.value = 'invalid'
  factorValidationErrors.value = Array.isArray(validation?.errors) && validation.errors.length > 0
    ? validation.errors
    : ['统一工作区校验失败，请检查 factors.xlsx 与材料目录结构。']
  factorValidationDiagnostics.value = Array.isArray(validation?.diagnostics) ? validation.diagnostics : []
  return false
}

function handleFactorsWorkbookValidationUpdated(validation) {
  if (applyFactorValidationResult(validation)) {
    addLog('修复后的 factors.xlsx 已通过统一工作区校验。', 'success')
  } else {
    addLog('factors.xlsx 已保存，但仍有校验问题待处理。', 'warning')
  }
}

function openFactorsWorkbookRepairDesk() {
  if (!workDir.value) return
  showFactorsWorkbookRepair.value = true
}

function downloadFactorsWorkbook() {
  if (!workDir.value) return
  apiClient.download('/api/files/download', { path: `${workDir.value}/factors.xlsx` })
  addLog('已开始下载 factors.xlsx', 'success')
}

async function validateFactorsForMaterials(materialNames, options = {}) {
  const { openRepairOnFail = false, silentSuccess = false } = options
  factorValidationErrors.value = []
  factorValidationDiagnostics.value = []
  factorValidationChecking.value = true
  try {
    const validationResult = await apiClient.post('/api/generate/validate-factors', {
      workDir: workDir.value,
      materials: materialNames
    })
    const validation = validationResult?.data || {}
    if (!applyFactorValidationResult(validation)) {
      if (openRepairOnFail) {
        showFactorsWorkbookRepair.value = true
      }
      addLog(openRepairOnFail ? '工作区校验失败，已打开修复台。' : '工作区校验失败，请先处理后再继续。', 'error')
      factorValidationErrors.value.forEach((msg) => addLog(`校验失败: ${msg}`, 'error'))
      return false
    }
    const warnings = Array.isArray(validation.warnings) ? validation.warnings : []
    warnings.forEach((msg) => addLog(`校验提示: ${msg}`, 'warning'))
    if (!silentSuccess) {
      addLog('工作区校验通过。', 'success')
    }
    return true
  } catch (error) {
    const errMsg = `统一工作区校验请求失败: ${error}`
    factorValidationStatus.value = 'invalid'
    factorValidationCheckedAt.value = new Date().toISOString()
    factorValidationErrors.value = [errMsg]
    factorValidationDiagnostics.value = []
    if (openRepairOnFail) {
      showFactorsWorkbookRepair.value = true
    }
    addLog(errMsg, 'error')
    return false
  } finally {
    factorValidationChecking.value = false
  }
}

async function runGenerateWorkspaceValidation() {
  const materialNames = selectedMaterials.value.length > 0
    ? selectedMaterials.value.map((item) => item.name)
    : materials.value.map((item) => item.name)
  await validateFactorsForMaterials(materialNames, { openRepairOnFail: false })
}

async function goStep2() {
  if (!canGenerate.value || isRunning.value) return
  const validationOk = await validateFactorsForMaterials(
    selectedMaterials.value.map(item => item.name),
    { openRepairOnFail: true, silentSuccess: true },
  )
  if (!validationOk) {
    return
  }

  try {
    await persistGenerateWorkspaceActivity('generating')
  } catch (error) {
    addLog(`工作区进行中状态保存失败: ${error}`, 'warning')
  }

  currentStep.value = 2
  isRunning.value = true
  stopRequested.value = false
  currentTaskId.value = ''
  batchResults.value = {}
  verifyResults.value = {}
  promptModified.value = false
  batchElapsed.value = 0
  currentElapsed.value = 0
  batchStartTime.value = Date.now()

  // 启动计时器，每秒更新
  elapsedTimer = setInterval(() => {
    batchElapsed.value = Math.floor((Date.now() - batchStartTime.value) / 1000)
  }, 1000)

  addLog(`开始批量生成提示词，共 ${selectedMaterials.value.length} 种材料`, 'info')

  let stoppedByUser = false

  try {
    for (const mat of selectedMaterials.value) {
      if (stopRequested.value) {
        stoppedByUser = true
        break
      }

      batchCurrentMaterial.value = mat.name
      currentElapsed.value = 0
      const matStart = Date.now()
      addLog(`[${mat.name}] 开始生成...`, 'info')
      try {
        const task = await startTask('generate', {
          workDir: workDir.value,
          materialName: mat.name,
          modelCfgId: selectedModelId.value || null,
          useCaseLibrary: useCaseLibrary.value,
          ruleProfileId: selectedRuleProfileId.value || null
        })
        currentTaskId.value = task.id
        if (stopRequested.value) {
          await cancelTask(task.id).catch(() => {})
        }

        const resultData = { ...(await waitForTask(task.id, null)) }
        const elapsed = ((Date.now() - matStart) / 1000).toFixed(1)
        resultData.artifact = normalizeArtifact(resultData.artifact, mat.name)
        resultData.preview_prompt = resultData.preview_prompt || buildPreviewPrompt(resultData.artifact.template?.prompt_template || '', resultData.artifact.factors || [])
        resultData.prompt_template = resultData.preview_prompt
        if (!resultData.preview_prompt?.trim()) {
          throw new Error('提示词文件为空，未生成有效内容')
        }
        batchResults.value[mat.name] = { ...resultData, success: true, elapsed, dirty: false }
        addLog(`[${mat.name}] 生成成功！耗时 ${elapsed}s`, 'success')
        if (resultData.output_file) addLog(`已保存: ${resultData.output_file}`, 'success')
      } catch (error) {
        const elapsed = ((Date.now() - matStart) / 1000).toFixed(1)
        if (isTaskCancelledError(error)) {
          stoppedByUser = true
          addLog(`[${mat.name}] 已手动停止`, 'warning')
          break
        }
        const errStr = String(error)
        const msg = errStr.includes('API Key') || errStr.includes('DASHSCOPE') || errStr.includes('OPENAI_API_KEY')
          ? '未配置可用的 API 密钥，请前往【设置】页面配置默认 API Key 或模型专属 API Key'
          : String(error)
        batchResults.value[mat.name] = { success: false, error: msg, prompt_template: '', preview_prompt: '', artifact: null, artifact_file: '', output_file: '', elapsed, dirty: false }
        addLog(`[${mat.name}] 生成失败: ${msg}`, 'error')
      } finally {
        currentTaskId.value = ''
      }
    }
  } finally {
    clearInterval(elapsedTimer)
    batchElapsed.value = Math.floor((Date.now() - batchStartTime.value) / 1000)
    batchCurrentMaterial.value = ''
    currentTaskId.value = ''
    isRunning.value = false
  }

  // 自动切换到第一个成功的材料
  const firstSuccess = selectedMaterials.value.find(m => batchResults.value[m.name]?.success)
  if (firstSuccess) {
    activeBatchMaterial.value = firstSuccess.name
    promptModified.value = false
  }
  const successCount = Object.values(batchResults.value).filter(r => r.success).length
  if (stoppedByUser || stopRequested.value) {
    addLog(`已手动停止生成，已保留 ${successCount}/${selectedMaterials.value.length} 个已完成材料`, 'warning')
  } else {
    addLog(`批量生成完成：成功 ${successCount}/${selectedMaterials.value.length}，总耗时 ${batchElapsed.value}s`, 'success')
  }

  // 标记工作区生成状态
  const finalStatus = stoppedByUser || stopRequested.value
    ? ''
    : successCount > 0
      ? 'done'
      : 'error'
  try {
    await persistGenerateWorkspaceActivity(finalStatus)
  } catch (error) {
    addLog(`工作区最终状态保存失败: ${error}`, 'warning')
  }
  stopRequested.value = false
}

async function retrySingleMaterial(materialName) {
  if (!materialName || isRunning.value || retryingMaterials.value[materialName]) return
  const validationOk = await validateFactorsForMaterials([materialName])
  if (!validationOk) {
    showFactorsWorkbookRepair.value = true
    return
  }

  retryingMaterials.value = { ...retryingMaterials.value, [materialName]: true }
  const matStart = Date.now()
  addLog(`[${materialName}] 开始单个重新生成...`, 'info')
  try {
    const generateResult = await apiClient.post('/api/generate/prompt', {
      workDir: workDir.value,
      materialName,
      modelCfgId: selectedModelId.value || null,
      useCaseLibrary: useCaseLibrary.value,
      ruleProfileId: selectedRuleProfileId.value || null
    })
    const elapsed = ((Date.now() - matStart) / 1000).toFixed(1)
    const resultData = { ...generateResult.data }
    resultData.artifact = normalizeArtifact(resultData.artifact, materialName)
    resultData.preview_prompt = resultData.preview_prompt || buildPreviewPrompt(resultData.artifact.template?.prompt_template || '', resultData.artifact.factors || [])
    resultData.prompt_template = resultData.preview_prompt
    if (!resultData.preview_prompt?.trim()) {
      throw new Error('提示词文件为空，未生成有效内容')
    }
    batchResults.value[materialName] = { ...resultData, success: true, elapsed, dirty: false }
    activeBatchMaterial.value = materialName
    promptModified.value = false
    addLog(`[${materialName}] 单个重新生成成功！耗时 ${elapsed}s`, 'success')
    if (resultData.output_file) addLog(`已保存: ${resultData.output_file}`, 'success')
  } catch (error) {
    const elapsed = ((Date.now() - matStart) / 1000).toFixed(1)
    const errStr = String(error)
    const msg = errStr.includes('API Key') || errStr.includes('DASHSCOPE') || errStr.includes('OPENAI_API_KEY')
      ? '未配置可用的 API 密钥，请前往【设置】页面配置默认 API Key 或模型专属 API Key'
      : String(error)
    batchResults.value[materialName] = { success: false, error: msg, prompt_template: '', preview_prompt: '', artifact: null, artifact_file: '', output_file: '', elapsed, dirty: false }
    addLog(`[${materialName}] 单个重新生成失败: ${msg}`, 'error')
  } finally {
    const nextState = { ...retryingMaterials.value }
    delete nextState[materialName]
    retryingMaterials.value = nextState
  }
}

async function runVerify() {
  if (isVerifying.value || !activeVerifyPrompt.value) return
  const matName = activeVerifyMaterial.value
  if (!matName) return
  if (verifyWorkDir.value) {
    try {
      const verifyMaterialsRes = await apiClient.get('/api/workspaces/materials', { workDir: verifyWorkDir.value })
      const verifyMaterials = Array.isArray(verifyMaterialsRes?.data) ? verifyMaterialsRes.data : []
      const matched = verifyMaterials.find((item) => item?.name === matName)
      if (!matched || !matched.image_count) {
        const availableNames = verifyMaterials.map((item) => item?.name).filter(Boolean)
        const hint = availableNames.length > 0
          ? `当前验证目录包含：${availableNames.join('、')}`
          : '当前验证目录下未识别到任何材料子文件夹（需包含图片或PDF）'
        addLog(`[验证前校验失败] 验证目录缺少材料「${matName}」对应子文件夹或无可用图片/PDF。${hint}`, 'error')
        verifyResults.value = {
          ...verifyResults.value,
          [matName]: {
            success: false,
            image_file: '',
            extraction_output: '',
            error: `验证目录结构不符合要求：缺少「${matName}」子文件夹，或子文件夹中没有图片/PDF。${hint}`
          }
        }
        return
      }
    } catch (e) {
      addLog(`[验证前校验异常] 无法读取验证目录材料结构: ${e}`, 'error')
      verifyResults.value = {
        ...verifyResults.value,
        [matName]: {
          success: false,
          image_file: '',
          extraction_output: '',
          error: `无法读取验证目录，请确认路径有效并可访问：${e}`
        }
      }
      return
    }
  }
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
    const currentArtifact = batchResults.value[matName]?.artifact || null
    const currentArtifactFile = batchResults.value[matName]?.artifact_file || null
    const vr = await apiClient.post('/api/generate/verify', {
      materialDir,
      artifact: currentArtifact,
      artifactFile: currentArtifactFile,
      modelCfgId: selectedModelId.value || null
    })
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

async function saveArtifact() {
  const matName = activeBatchMaterial.value
  const r = batchResults.value[matName]
  if (!r?.artifact_file || !r?.artifact || isSaving.value) return
  isSaving.value = true
  try {
    const response = await apiClient.post('/api/generate/save-artifact', {
      filePath: r.artifact_file,
      artifact: r.artifact,
      previewFilePath: r.output_file || null
    })
    const savedArtifact = normalizeArtifact(response?.data?.artifact || r.artifact, matName)
    const previewPrompt = buildPreviewPrompt(savedArtifact.template?.prompt_template || '', savedArtifact.factors || [])
    batchResults.value = {
      ...batchResults.value,
      [matName]: {
        ...r,
        artifact: savedArtifact,
        preview_prompt: previewPrompt,
        prompt_template: previewPrompt,
        dirty: false,
      },
    }
    promptModified.value = false
    addLog(`「${matName}」要素提示词修改已保存`, 'success')
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
  const text = activePreviewPrompt.value
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
  promptModified.value = false
  activeBatchMaterial.value = ''
  activeVerifyMaterial.value = ''
  currentTaskId.value = ''
  stopRequested.value = false
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
  retryingMaterials.value = {}
  verifyResults.value = {}
  verifyWorkDir.value = ''
  promptModified.value = false
  activeBatchMaterial.value = ''
  activeVerifyMaterial.value = ''
  currentTaskId.value = ''
  stopRequested.value = false
  logs.value = []
  fjResults.value = []
  fjPreviewItem.value = null
  fjCopiedItem.value = null
  fjDownloadingAll.value = false
  factorValidationErrors.value = []
  factorValidationDiagnostics.value = []
  factorValidationStatus.value = 'idle'
  factorValidationCheckedAt.value = ''
  factorValidationChecking.value = false
  showFactorsWorkbookRepair.value = false
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
