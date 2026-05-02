<template>
  <!-- 左右双栏，左侧固定 Step 导航，右侧滚动内容 -->
  <div class="flex h-full min-h-0">

    <!-- ═══ 左侧固定 Step 导航 ═══ -->
    <div class="w-56 flex-shrink-0 bg-white border-r flex flex-col">
      <!-- 标题 -->
      <div class="px-5 pt-6 pb-4 border-b">
        <h1 class="text-base font-bold text-gray-900 leading-tight">材料分类提示词</h1>
        <p class="text-xs text-gray-400 mt-1 leading-relaxed">基于材料样本生成可下载的分类提示词 JSON</p>
      </div>

      <!-- Step 列表 -->
      <nav class="flex-1 py-4 px-3 space-y-1">
        <button v-for="(s, i) in steps" :key="i"
          @click="handleStepNav(i + 1)"
          :disabled="i + 1 > maxReachableStep"
          class="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left transition-all"
          :class="[
            currentStep === i + 1
              ? 'bg-blue-50 text-blue-700'
              : currentStep > i + 1
                ? 'text-green-700 hover:bg-green-50 cursor-pointer'
                : i + 1 <= maxReachableStep
                  ? 'text-gray-500 hover:bg-gray-50 cursor-pointer'
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

      <!-- 底部状态 + 操作 -->
      <div class="px-3 pb-4 pt-2 border-t space-y-2">
        <div v-if="isRunning" class="flex items-center gap-2 px-3 py-2 bg-blue-50 rounded-lg">
          <svg class="animate-spin w-3.5 h-3.5 text-blue-500 flex-shrink-0" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
          </svg>
          <span class="text-xs text-blue-600">分类中...</span>
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

    <!-- ═══ 右侧滚动内容区 ═══ -->
    <div class="flex-1 overflow-y-auto bg-gray-50">
      <div class="p-6 max-w-3xl">

        <!-- ── STEP 1：上传工作区与配置 ── -->
        <div v-if="currentStep === 1" class="space-y-4">
          <div>
            <span class="text-lg font-bold text-gray-900">上传工作区与配置参数</span>
            <p class="text-sm text-gray-500 mt-1">上传统一结构工作区，自动扫描一级材料目录下的全部样本附件并生成分类提示词</p>
          </div>

          <!-- 工作区选择 -->
          <div class="bg-white rounded-xl border p-4">
            <label class="block text-xs font-semibold text-gray-600 mb-2 uppercase tracking-wide">工作区</label>
            <div class="flex gap-2">
              <input v-model="workDir" type="text" placeholder="上传后会显示服务端工作区路径"
                class="flex-1 px-3 py-2 border rounded-lg text-sm bg-gray-50 text-gray-700" readonly />
              <button @click="selectWorkDir"
                class="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition flex-shrink-0">
                上传文件夹...
              </button>
            </div>
            <p class="text-xs text-gray-400 mt-2">工作区需包含：factors.xlsx，以及按材料名称建立的一级子目录；每个子目录下放样本图片或 PDF</p>
          </div>

          <div class="rounded-xl border border-blue-200 bg-blue-50 p-4">
            <p class="text-sm font-semibold text-blue-700 mb-1">统一工作区结构提醒</p>
            <ul class="text-xs text-blue-700 list-disc pl-4 space-y-1">
              <li>根目录必须包含：`factors.xlsx`。</li>
              <li>根目录下每种材料使用一个同名子目录，例如 `营业证照/`、`法人身份证明/`。</li>
              <li>每个材料目录下至少放 1 个样本图片或 PDF，系统会自动扫描全部附件生成分类提示词。</li>
            </ul>
          </div>
          <WorkspaceValidationStatusBar
            v-if="workDir"
            :status="classifyValidationStatus"
            :issue-count="classifyValidationErrors.length"
            :checking="classifyValidationChecking"
            :checked-at="classifyValidationCheckedAt"
            @validate="runClassifyWorkspaceValidation"
            @open-repair="openFactorsWorkbookRepairDesk"
            @download-workbook="downloadFactorsWorkbook"
          />

          <!-- 材料名称 + 样本附件 双列预览 -->
          <div v-if="workDir" class="grid grid-cols-2 gap-4">
            <div class="bg-white rounded-xl border overflow-hidden">
              <div class="flex items-center justify-between px-4 py-3 bg-blue-50 border-b">
                <span class="text-sm font-semibold text-blue-800">材料名称</span>
                <span class="px-2 py-0.5 bg-blue-600 text-white rounded-full text-xs font-medium">{{ categories.length }} 类</span>
              </div>
              <div class="divide-y max-h-52 overflow-y-auto">
                <div v-for="(cat, idx) in categories" :key="cat" class="flex items-center gap-2.5 px-4 py-2">
                  <span class="w-5 h-5 bg-blue-100 text-blue-700 rounded-full text-xs flex items-center justify-center font-medium flex-shrink-0">{{ idx+1 }}</span>
                  <span class="text-sm text-gray-700 truncate">{{ cat }}</span>
                </div>
                <div v-if="categories.length === 0" class="px-4 py-4 text-sm text-gray-400 text-center">未找到材料名称</div>
              </div>
            </div>
            <div class="bg-white rounded-xl border overflow-hidden">
              <div class="flex items-center justify-between px-4 py-3 bg-yellow-50 border-b">
                <span class="text-sm font-semibold text-yellow-800">样本附件</span>
                <span class="px-2 py-0.5 bg-yellow-500 text-white rounded-full text-xs font-medium">{{ pendingFiles.length }} 个</span>
              </div>
              <div class="divide-y max-h-52 overflow-y-auto">
                <div v-for="f in pendingFiles" :key="f.name" class="flex items-center gap-2 px-4 py-2">
                  <svg class="w-3.5 h-3.5 text-yellow-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"/>
                  </svg>
                  <span class="text-sm text-gray-700 truncate flex-1">{{ f.name }}</span>
                  <span class="text-xs text-gray-400 flex-shrink-0">{{ formatSize(f.size) }}</span>
                </div>
                <div v-if="pendingFiles.length === 0" class="px-4 py-4 text-sm text-gray-400 text-center">暂无样本附件</div>
              </div>
            </div>
          </div>

          <!-- 迭代轮次配置 -->
          <div v-if="workDir" class="bg-white rounded-xl border p-4 flex items-center gap-6">
            <div class="flex-1">
              <div class="text-sm font-semibold text-gray-700">最大迭代轮次</div>
              <div class="text-xs text-gray-400 mt-0.5">每轮自动优化分类提示词，直到结果稳定</div>
            </div>
            <div class="flex items-center gap-3">
              <button @click="maxRounds = Math.max(1, maxRounds - 1)"
                class="w-8 h-8 bg-gray-100 border rounded-lg hover:bg-gray-200 font-bold text-gray-600 transition">-</button>
              <span class="w-10 text-center font-bold text-xl text-gray-800">{{ maxRounds }}</span>
              <button @click="maxRounds = Math.min(10, maxRounds + 1)"
                class="w-8 h-8 bg-gray-100 border rounded-lg hover:bg-gray-200 font-bold text-gray-600 transition">+</button>
            </div>
          </div>

          <!-- 模型选择 -->
          <div v-if="workDir && availableModels.length > 0" class="bg-white rounded-xl border p-4">
            <label class="block text-xs font-semibold text-gray-600 mb-2 uppercase tracking-wide">分类使用模型</label>
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
              <span v-if="!workDir">请先选择工作目录</span>
              <span v-else-if="!canClassify">目录数据未就绪（需要材料目录和样本附件）</span>
              <span v-else class="text-green-600 flex items-center gap-1">
                <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/></svg>
                {{ pendingFiles.length }} 个样本 · {{ categories.length }} 个材料目录 · 最多 {{ maxRounds }} 轮
              </span>
            </div>
            <button @click="goStep2" :disabled="!canClassify || isRunning"
              class="flex items-center gap-2 px-6 py-2.5 rounded-lg text-sm font-semibold transition-all"
              :class="canClassify && !isRunning ? 'bg-blue-600 text-white hover:bg-blue-700 shadow-sm' : 'bg-gray-100 text-gray-400 cursor-not-allowed'">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 10h16M4 14h16M4 18h16"/>
              </svg>
              开始生成
            </button>
          </div>
        </div>

        <!-- ── STEP 2：执行分类 ── -->
        <div v-if="currentStep === 2" class="space-y-4">
          <div>
            <span class="text-lg font-bold text-gray-900">执行分类</span>
            <p class="text-sm text-gray-500 mt-1">自动对 {{ pendingFiles.length }} 个样本附件执行最多 {{ maxRounds }} 轮迭代，生成材料分类提示词</p>
          </div>

          <!-- 运行中 -->
          <div v-if="isRunning" class="bg-white rounded-xl border p-12 text-center">
            <div class="w-16 h-16 rounded-full bg-blue-50 flex items-center justify-center mx-auto mb-4">
              <svg class="animate-spin w-8 h-8 text-blue-500" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
              </svg>
            </div>
            <p class="text-base font-semibold text-gray-700">正在生成分类提示词，请稍候...</p>
            <p class="text-sm text-gray-400 mt-1">最多 {{ maxRounds }} 轮迭代优化</p>
          </div>

          <!-- 统计结果 -->
          <template v-if="result && !isRunning">
            <div class="grid grid-cols-3 gap-4">
              <div class="bg-white rounded-xl border p-5 text-center">
                <div class="text-3xl font-bold text-green-600">{{ result.total_files || result.image_count || 0 }}</div>
                <div class="text-xs text-gray-500 mt-1">处理文件数</div>
              </div>
              <div class="bg-white rounded-xl border p-5 text-center">
                <div class="text-3xl font-bold text-blue-600">{{ result.categories?.length || result.material_names?.length || 0 }}</div>
                <div class="text-xs text-gray-500 mt-1">材料数</div>
              </div>
              <div class="bg-white rounded-xl border p-5 text-center">
                <div class="text-3xl font-bold text-purple-600">{{ result.step2_summary?.classified_count || 0 }}</div>
                <div class="text-xs text-gray-500 mt-1">生成方案数</div>
              </div>
            </div>
            <div class="flex items-center justify-between pt-2">
              <span class="text-sm text-gray-500">生成完成，请进入下一步审核结果</span>
              <button @click="currentStep = 3"
                class="flex items-center gap-2 px-6 py-2.5 bg-blue-600 text-white rounded-lg text-sm font-semibold hover:bg-blue-700 transition shadow-sm">
                下一步：审核结果
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/>
                </svg>
              </button>
            </div>
          </template>
        </div>

        <!-- ── STEP 3：人工审核 ── -->
        <div v-if="currentStep === 3" class="space-y-4">
          <!-- 标题栏 -->
          <div class="flex items-center justify-between">
            <div>
              <span class="text-lg font-bold text-gray-900">人工审核分类结果</span>
              <p class="text-sm text-gray-500 mt-1">检查分类明细和提示词，确认无误后完成</p>
            </div>
            <button @click="openResult"
              class="flex items-center gap-1.5 px-3 py-2 border rounded-lg text-sm text-gray-600 hover:bg-gray-50 transition">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 19a2 2 0 01-2-2V7a2 2 0 012-2h4l2 2h4a2 2 0 012 2v1M5 19h14a2 2 0 002-2v-5a2 2 0 00-2-2H9a2 2 0 00-2 2v5a2 2 0 01-2 2z"/>
              </svg>
              查看结果目录
            </button>
          </div>

          <!-- Tab 切换 -->
          <div class="flex gap-1 bg-gray-100 p-1 rounded-xl">
            <button v-for="tab in reviewTabs" :key="tab.id" @click="activeReviewTab = tab.id"
              class="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium transition"
              :class="activeReviewTab === tab.id ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'">
              {{ tab.label }}
              <span v-if="tab.badge" class="px-1.5 py-0.5 rounded-full text-xs font-semibold"
                :class="activeReviewTab === tab.id ? 'bg-blue-100 text-blue-700' : 'bg-gray-200 text-gray-600'">
                {{ tab.badge }}
              </span>
            </button>
          </div>

          <!-- ── TAB: 分类明细 ── -->
          <div v-if="activeReviewTab === 'detail'" class="space-y-3">
            <!-- 统计卡片 -->
            <div class="grid grid-cols-3 gap-3">
              <div class="bg-white rounded-xl border p-4 text-center">
                <div class="text-2xl font-bold text-blue-600">{{ result?.image_count || 0 }}</div>
                <div class="text-xs text-gray-500 mt-1">处理文件数</div>
              </div>
              <div class="bg-white rounded-xl border p-4 text-center">
                <div class="text-2xl font-bold text-green-600">{{ result?.step2_summary?.classified_count || 0 }}</div>
                <div class="text-xs text-gray-500 mt-1">生成方案数</div>
              </div>
              <div class="bg-white rounded-xl border p-4 text-center">
                <div class="text-2xl font-bold text-purple-600">{{ result?.material_names?.length || result?.categories?.length || 0 }}</div>
                <div class="text-xs text-gray-500 mt-1">材料数</div>
              </div>
            </div>

            <!-- 分类明细列表 -->
            <div class="bg-white rounded-xl border overflow-hidden">
              <div class="flex items-center justify-between px-4 py-3 bg-gray-50 border-b">
              <span class="text-sm font-semibold text-gray-700">样本分类明细</span>
                <span class="text-xs text-gray-400">共 {{ result?.step1_result?.length || 0 }} 条记录</span>
              </div>
              <div v-if="result?.step1_result?.length" class="divide-y max-h-96 overflow-y-auto">
                <div v-for="(item, i) in result.step1_result" :key="i"
                  class="px-4 py-3 hover:bg-gray-50 transition">
                  <div class="flex items-start justify-between gap-3">
                    <div class="flex-1 min-w-0">
                      <div class="flex items-center gap-2 mb-1">
                        <span class="text-xs font-mono text-gray-500 truncate">{{ item.file_name }}</span>
                        <span class="flex-shrink-0 px-2 py-0.5 rounded-full text-xs font-medium"
                          :class="item.material_type === '其他' ? 'bg-gray-100 text-gray-600' : 'bg-blue-100 text-blue-700'">
                          {{ item.material_type }}
                        </span>
                      </div>
                      <div v-if="item.key_info" class="text-xs text-gray-600 mt-0.5">
                        <span class="text-gray-400">关键信息：</span>{{ item.key_info }}
                      </div>
                      <div v-if="item.reason" class="text-xs text-gray-400 mt-0.5">
                        <span>依据：</span>{{ item.reason }}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
              <div v-else class="px-4 py-6 text-center text-sm text-gray-400">
                暂无分类明细数据
              </div>
            </div>

            <!-- 分类结果分布 -->
            <div v-if="result?.step2_summary?.folder_distribution" class="bg-white rounded-xl border overflow-hidden">
              <div class="px-4 py-3 bg-gray-50 border-b">
                <span class="text-sm font-semibold text-gray-700">分类结果分布</span>
              </div>
              <div class="p-4 grid grid-cols-2 gap-2">
                <div v-for="(count, folder) in result.step2_summary.folder_distribution" :key="folder"
                  class="flex items-center justify-between px-3 py-2 bg-gray-50 rounded-lg border">
                  <span class="text-sm text-gray-700 truncate mr-2">{{ folder }}</span>
                  <span class="px-2 py-0.5 bg-blue-100 text-blue-700 rounded-full text-xs font-medium flex-shrink-0">{{ count }} 个</span>
                </div>
              </div>
            </div>
          </div>

          <!-- ── TAB: 提示词 ── -->
          <div v-if="activeReviewTab === 'prompt'" class="space-y-5">
            <!-- 分类信息提取 -->
            <div class="space-y-2">
              <div class="flex items-center gap-2 px-1">
                <div class="w-1 h-4 bg-blue-500 rounded-full"></div>
                <span class="text-sm font-bold text-gray-800">分类信息提取提示词</span>
                <span class="px-2 py-0.5 rounded-full text-xs font-medium"
                  :class="result?.extract_prompt_source === '原始模板' ? 'bg-gray-100 text-gray-600' : 'bg-amber-100 text-amber-700'">
                  当前: {{ result?.extract_prompt_source || '原始模板' }}
                </span>
              </div>

              <!-- 原始模板（只读） -->
              <div class="bg-white rounded-xl border border-dashed border-gray-300 overflow-hidden">
                <div class="flex items-center justify-between px-4 py-2.5 bg-gray-50 border-b border-dashed border-gray-300">
                  <div class="flex items-center gap-2 min-w-0">
                    <span class="flex-shrink-0 px-2 py-0.5 bg-gray-200 text-gray-600 rounded text-xs font-medium">模板 · 只读</span>
                    <span class="text-xs text-gray-400 font-mono truncate">{{ result?.extract_template_path || '~/.claude/skills/material-classifier/默认分类信息提取模板.txt' }}</span>
                  </div>
                  <button @click="copyText(result?.extract_template_content || '', 'extract-tmpl')"
                    class="flex-shrink-0 flex items-center gap-1 px-2.5 py-1 text-xs rounded-lg border transition ml-2"
                    :class="copied === 'extract-tmpl' ? 'text-green-600 border-green-300 bg-green-50' : 'text-gray-500 hover:bg-gray-100'">
                    {{ copied === 'extract-tmpl' ? '✓ 已复制' : '复制' }}
                  </button>
                </div>
                <pre class="w-full p-4 text-xs text-gray-500 max-h-40 overflow-y-auto font-mono leading-relaxed whitespace-pre-wrap select-none">{{ result?.extract_template_content || '（模板文件未找到）' }}</pre>
              </div>

              <!-- 生成的提示词（可编辑） -->
              <div class="bg-white rounded-xl border overflow-hidden">
                <div class="flex items-center justify-between px-4 py-2.5 bg-blue-50 border-b">
                  <div class="flex items-center gap-2">
                    <span class="flex-shrink-0 px-2 py-0.5 bg-blue-100 text-blue-700 rounded text-xs font-medium">当前使用 · 可编辑</span>
                    <span class="text-xs text-blue-500">修改后点击「保存」可更新到工作目录</span>
                  </div>
                  <div class="flex items-center gap-2">
                    <button @click="runTestPrompt('extract')" :disabled="isTesting"
                      class="flex items-center gap-1 px-2.5 py-1 text-xs rounded-lg border transition"
                      :class="isTesting && testingType === 'extract' ? 'text-blue-600 border-blue-300 bg-blue-50' : 'text-gray-600 hover:bg-gray-100 disabled:opacity-40'">
                      <svg class="w-3 h-3" :class="isTesting && testingType === 'extract' ? 'animate-spin' : ''" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"/>
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
                      </svg>
                      {{ isTesting && testingType === 'extract' ? '测试中...' : '测试' }}
                    </button>
                    <button @click="copyText(editExtractPrompt, 'extract')"
                      class="flex items-center gap-1 px-2.5 py-1 text-xs rounded-lg border transition"
                      :class="copied === 'extract' ? 'text-green-600 border-green-300 bg-green-50' : 'text-gray-600 hover:bg-gray-100'">
                      {{ copied === 'extract' ? '✓ 已复制' : '复制' }}
                    </button>
                  </div>
                </div>
                <textarea v-model="editExtractPrompt" @input="promptSaved = false"
                  class="w-full p-4 text-xs text-gray-700 h-44 resize-y font-mono leading-relaxed border-0 outline-none focus:ring-2 focus:ring-blue-200 focus:ring-inset"
                  placeholder="分类信息提取提示词..."></textarea>
              </div>
            </div>

            <!-- 分类附件归集 -->
            <div class="space-y-2">
              <div class="flex items-center gap-2 px-1">
                <div class="w-1 h-4 bg-purple-500 rounded-full"></div>
                <span class="text-sm font-bold text-gray-800">分类附件归集提示词</span>
                <span class="px-2 py-0.5 rounded-full text-xs font-medium"
                  :class="result?.aggregate_prompt_source === '原始模板' ? 'bg-gray-100 text-gray-600' : 'bg-amber-100 text-amber-700'">
                  当前: {{ result?.aggregate_prompt_source || '原始模板' }}
                </span>
              </div>

              <!-- 原始模板（只读） -->
              <div class="bg-white rounded-xl border border-dashed border-gray-300 overflow-hidden">
                <div class="flex items-center justify-between px-4 py-2.5 bg-gray-50 border-b border-dashed border-gray-300">
                  <div class="flex items-center gap-2 min-w-0">
                    <span class="flex-shrink-0 px-2 py-0.5 bg-gray-200 text-gray-600 rounded text-xs font-medium">模板 · 只读</span>
                    <span class="text-xs text-gray-400 font-mono truncate">{{ result?.aggregate_template_path || '~/.claude/skills/material-classifier/默认分类附件归集模板.txt' }}</span>
                  </div>
                  <button @click="copyText(result?.aggregate_template_content || '', 'aggregate-tmpl')"
                    class="flex-shrink-0 flex items-center gap-1 px-2.5 py-1 text-xs rounded-lg border transition ml-2"
                    :class="copied === 'aggregate-tmpl' ? 'text-green-600 border-green-300 bg-green-50' : 'text-gray-500 hover:bg-gray-100'">
                    {{ copied === 'aggregate-tmpl' ? '✓ 已复制' : '复制' }}
                  </button>
                </div>
                <pre class="w-full p-4 text-xs text-gray-500 max-h-40 overflow-y-auto font-mono leading-relaxed whitespace-pre-wrap select-none">{{ result?.aggregate_template_content || '（模板文件未找到）' }}</pre>
              </div>

              <!-- 生成的提示词（可编辑） -->
              <div class="bg-white rounded-xl border overflow-hidden">
                <div class="flex items-center justify-between px-4 py-2.5 bg-purple-50 border-b">
                  <div class="flex items-center gap-2">
                    <span class="flex-shrink-0 px-2 py-0.5 bg-purple-100 text-purple-700 rounded text-xs font-medium">当前使用 · 可编辑</span>
                    <span class="text-xs text-purple-500">修改后点击「保存」可更新到工作目录</span>
                  </div>
                  <div class="flex items-center gap-2">
                    <button @click="runTestPrompt('aggregate')" :disabled="isTesting"
                      class="flex items-center gap-1 px-2.5 py-1 text-xs rounded-lg border transition"
                      :class="isTesting && testingType === 'aggregate' ? 'text-purple-600 border-purple-300 bg-purple-50' : 'text-gray-600 hover:bg-gray-100 disabled:opacity-40'">
                      <svg class="w-3 h-3" :class="isTesting && testingType === 'aggregate' ? 'animate-spin' : ''" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"/>
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
                      </svg>
                      {{ isTesting && testingType === 'aggregate' ? '测试中...' : '测试' }}
                    </button>
                    <button @click="copyText(editAggregatePrompt, 'aggregate')"
                      class="flex items-center gap-1 px-2.5 py-1 text-xs rounded-lg border transition"
                      :class="copied === 'aggregate' ? 'text-green-600 border-green-300 bg-green-50' : 'text-gray-600 hover:bg-gray-100'">
                      {{ copied === 'aggregate' ? '✓ 已复制' : '复制' }}
                    </button>
                  </div>
                </div>
                <textarea v-model="editAggregatePrompt" @input="promptSaved = false"
                  class="w-full p-4 text-xs text-gray-700 h-44 resize-y font-mono leading-relaxed border-0 outline-none focus:ring-2 focus:ring-purple-200 focus:ring-inset"
                  placeholder="分类附件归集提示词..."></textarea>
              </div>
            </div>

            <!-- 保存条 -->
            <div class="flex items-center justify-between px-4 py-3 bg-blue-50 border border-blue-200 rounded-xl">
              <span class="text-sm text-blue-700">修改提示词后保存，可用新提示词重新分类</span>
              <button @click="savePrompts"
                class="flex items-center gap-1.5 px-4 py-2 text-sm font-medium rounded-lg transition"
                :class="promptSaved ? 'bg-green-100 text-green-700 border border-green-300' : 'bg-blue-600 text-white hover:bg-blue-700'">
                <svg v-if="!promptSaved" class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3m-1 4l-3 3m0 0l-3-3m3 3V4"/>
                </svg>
                <svg v-else class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
                </svg>
                {{ promptSaved ? '已保存' : '保存提示词' }}
              </button>
            </div>
          </div>

          <!-- ── TAB: 测试结果 ── -->
          <div v-if="activeReviewTab === 'test'" class="space-y-3">
            <div v-if="!testResult" class="bg-white rounded-xl border p-8 text-center">
              <div class="w-12 h-12 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-3">
                <svg class="w-6 h-6 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"/>
                </svg>
              </div>
              <p class="text-sm text-gray-500">在「提示词」标签页点击「测试」按钮，<br>可对单个提示词进行调优测试</p>
            </div>
            <template v-else>
              <!-- 测试结论 -->
              <div class="flex items-center gap-3 px-4 py-3 rounded-xl border"
                :class="testResult.pass ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'">
                <svg class="w-5 h-5 flex-shrink-0" :class="testResult.pass ? 'text-green-600' : 'text-red-500'" fill="currentColor" viewBox="0 0 20 20">
                  <path v-if="testResult.pass" fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/>
                  <path v-else fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/>
                </svg>
                <div>
                  <div class="text-sm font-semibold" :class="testResult.pass ? 'text-green-800' : 'text-red-800'">
                    {{ testResult.type === 'extract' ? '分类信息提取' : '附件归集' }}测试{{ testResult.pass ? '通过' : '未通过' }}
                  </div>
                  <div v-if="testResult.issues?.length" class="text-xs mt-1 space-y-0.5" :class="testResult.pass ? 'text-green-700' : 'text-red-700'">
                    <div v-for="issue in testResult.issues" :key="issue">• {{ issue }}</div>
                  </div>
                </div>
              </div>

              <!-- 测试分类明细（extract 类型） -->
              <div v-if="testResult.attachments?.length" class="bg-white rounded-xl border overflow-hidden">
                <div class="px-4 py-3 bg-gray-50 border-b flex items-center justify-between">
                  <span class="text-sm font-semibold text-gray-700">测试分类明细</span>
                  <span class="text-xs text-gray-400">{{ testResult.attachments.length }} 条</span>
                </div>
                <div class="divide-y max-h-72 overflow-y-auto">
                  <div v-for="(item, i) in testResult.attachments" :key="i" class="px-4 py-3 hover:bg-gray-50">
                    <div class="flex items-start gap-2">
                      <div class="flex-1 min-w-0">
                        <div class="flex items-center gap-2 mb-0.5">
                          <span class="text-xs font-mono text-gray-500 truncate">{{ item.file_name }}</span>
                          <span class="flex-shrink-0 px-2 py-0.5 rounded-full text-xs font-medium"
                            :class="item.material_type === '其他' ? 'bg-gray-100 text-gray-600' : 'bg-blue-100 text-blue-700'">
                            {{ item.material_type }}
                          </span>
                        </div>
                        <div v-if="item.reason" class="text-xs text-gray-400">{{ item.reason }}</div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <!-- 归集方案（aggregate 类型） -->
              <div v-if="testResult.plan?.length" class="bg-white rounded-xl border overflow-hidden">
                <div class="px-4 py-3 bg-gray-50 border-b flex items-center justify-between">
                  <span class="text-sm font-semibold text-gray-700">测试归集方案</span>
                  <span class="text-xs text-gray-400">{{ testResult.plan.length }} 条</span>
                </div>
                <div class="divide-y max-h-72 overflow-y-auto">
                  <div v-for="(item, i) in testResult.plan" :key="i" class="px-4 py-3 hover:bg-gray-50">
                    <div class="flex items-center justify-between">
                      <span class="text-xs font-mono text-gray-600 truncate">{{ item.file_name }}</span>
                      <span class="ml-2 flex-shrink-0 px-2 py-0.5 bg-purple-100 text-purple-700 rounded-full text-xs">{{ item.target_folder }}</span>
                    </div>
                  </div>
                </div>
              </div>

              <button @click="testResult = null" class="w-full py-2 text-xs text-gray-400 hover:text-gray-600 transition">清空测试结果</button>
            </template>
          </div>

          <!-- 底部操作栏 -->
          <div class="flex items-center justify-between pt-2 border-t">
            <button @click="goStep2Again" :disabled="isRunning || isTesting"
              class="flex items-center gap-1.5 px-4 py-2 border border-gray-300 text-gray-600 rounded-lg text-sm hover:bg-gray-50 disabled:opacity-40 transition">
              <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
              </svg>
              结果不对，重新分类
            </button>
            <button @click="downloadResultZip" :disabled="!workDir"
              class="flex items-center gap-1.5 px-4 py-2 border border-blue-300 text-blue-600 rounded-lg text-sm hover:bg-blue-50 disabled:opacity-40 transition">
              <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 3v12m0 0l4-4m-4 4l-4-4m-5 8h18"/>
              </svg>
              下载分类结果
            </button>
            <button @click="confirmAndGoStep4" :disabled="isTesting"
              class="flex items-center gap-2 px-6 py-2.5 bg-green-600 text-white rounded-lg text-sm font-semibold hover:bg-green-700 disabled:opacity-40 transition shadow-sm">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
              </svg>
              分类正确，确认完成
            </button>
          </div>
        </div>

        <!-- ── STEP 4：确认完成 ── -->
        <div v-if="currentStep === 4" class="space-y-4">
          <div class="bg-white rounded-2xl border-2 border-green-200 p-8 text-center">
            <div class="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-5">
              <svg class="w-10 h-10 text-green-500" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/>
              </svg>
            </div>
            <h2 class="text-xl font-bold text-gray-900 mb-2">分类提示词已确认完成！</h2>
            <p class="text-sm text-gray-500 mb-1">分类提示词结果经人工审核确认，可随时下载 JSON 产物</p>
            <p class="text-xs text-gray-400">处理 {{ result?.total_files || result?.image_count || 0 }} 个样本 · 材料 {{ result?.material_names?.length || result?.categories?.length || 0 }} 个</p>
          </div>

          <div class="grid grid-cols-2 gap-4">
            <button @click="openResult"
              class="bg-white rounded-xl border p-5 text-left hover:border-blue-300 hover:bg-blue-50 transition group">
              <div class="w-9 h-9 bg-gray-100 rounded-lg flex items-center justify-center mb-3 group-hover:bg-blue-100 transition">
                <svg class="w-5 h-5 text-gray-500 group-hover:text-blue-600 transition" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 19a2 2 0 01-2-2V7a2 2 0 012-2h4l2 2h4a2 2 0 012 2v1M5 19h14a2 2 0 002-2v-5a2 2 0 00-2-2H9a2 2 0 00-2 2v5a2 2 0 01-2 2z"/>
                </svg>
              </div>
              <div class="text-sm font-semibold text-gray-800 mb-1">查看结果目录</div>
              <div class="text-xs text-gray-400">在工作区中查看生成的 JSON 和提示词文件</div>
            </button>
            <button @click="downloadResultZip"
              class="bg-white rounded-xl border p-5 text-left hover:border-green-300 hover:bg-green-50 transition group">
              <div class="w-9 h-9 bg-gray-100 rounded-lg flex items-center justify-center mb-3 group-hover:bg-green-100 transition">
                <svg class="w-5 h-5 text-gray-500 group-hover:text-green-600 transition" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 3v12m0 0l4-4m-4 4l-4-4m-5 8h18"/>
                </svg>
              </div>
              <div class="text-sm font-semibold text-gray-800 mb-1">下载分类结果 ZIP</div>
              <div class="text-xs text-gray-400">打包分类提示词 JSON、提示词文本和报告并下载</div>
            </button>
            <button @click="clear"
              class="bg-white rounded-xl border p-5 text-left hover:border-gray-300 hover:bg-gray-50 transition group">
              <div class="w-9 h-9 bg-gray-100 rounded-lg flex items-center justify-center mb-3 group-hover:bg-gray-200 transition">
                <svg class="w-5 h-5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
                </svg>
              </div>
              <div class="text-sm font-semibold text-gray-800 mb-1">重新开始</div>
              <div class="text-xs text-gray-400">对新的一批文件执行分类</div>
            </button>
          </div>
        </div>

        <!-- ── 日志面板 ── -->
        <div v-if="logs.length > 0" class="mt-6 bg-gray-900 rounded-xl overflow-hidden">
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
          :errors="classifyValidationErrors"
          :diagnostics="classifyValidationDiagnostics"
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
import { apiClient } from '../services/apiClient.js'
import { listen } from '../tauri/event.js'
import { invoke } from '../tauri/tauri.js'
import { getScopedStorageItem, removeScopedStorageItem, setScopedStorageItem } from '../services/authState.js'
import FactorsWorkbookRepairPanel from '../components/FactorsWorkbookRepairPanel.vue'
import WorkspaceValidationStatusBar from '../components/WorkspaceValidationStatusBar.vue'

const steps = [
  { title: '上传工作区与配置', active: '配置中', done: '已选工作区', pending: '待配置' },
  { title: '执行分类',       active: '分类中', done: '已分类',   pending: '待执行' },
  { title: '人工审核',       active: '审核中', done: '已审核',   pending: '待审核' },
  { title: '确认完成',       active: '已完成', done: '✓ 完成',   pending: '待确认' },
]
const WORKDIR_STORAGE_KEY = 'auto-prompt.classify.workdir'
const currentStep = ref(1)
const maxReachableStep = computed(() => {
  if (currentStep.value === 4) return 4
  if (currentStep.value === 3) return 3
  if (result.value) return 3
  if (currentStep.value === 2) return 2
  return 1
})

const workDir = ref('')
const categories = ref([])
const pendingFiles = ref([])
const maxRounds = ref(3)
const availableModels = ref([])
const selectedModelId = ref('')
const isRunning = ref(false)
const logs = ref([])
const result = ref(null)
const logContainer = ref(null)
const copied = ref(null)
const editExtractPrompt = ref('')
const editAggregatePrompt = ref('')
const promptSaved = ref(false)
const activeReviewTab = ref('detail')
const testResult = ref(null)
const isTesting = ref(false)
const testingType = ref('')
const classifyValidationErrors = ref([])
const classifyValidationDiagnostics = ref([])
const classifyValidationStatus = ref('idle')
const classifyValidationCheckedAt = ref('')
const classifyValidationChecking = ref(false)
const showFactorsWorkbookRepair = ref(false)

const reviewTabs = computed(() => [
  { id: 'detail', label: '分类明细', badge: result.value?.step1_result?.length || null },
  { id: 'prompt', label: '提示词', badge: null },
  { id: 'test', label: '测试结果', badge: testResult.value ? '1' : null },
])

const route = useRoute()

let unlistenLog = null

async function loadModels() {
  try {
    const settings = await invoke('load_settings')
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
  } catch (e) { console.error(e) }
}

onActivated(async () => {
  await loadModels()
  const queryWorkDir = route.query.workDir
  if (queryWorkDir && queryWorkDir !== workDir.value) {
    workDir.value = queryWorkDir
    persistWorkDir()
    tagWorkspaceModule()
    addLog(`已打开工作区: ${queryWorkDir}`, 'info')
    await loadDirInfo()
  } else if (!queryWorkDir && !isRunning.value && workDir.value) {
    clear()
  }
})

onMounted(async () => {
  await loadModels()

  unlistenLog = await listen('skill-log', (event) => {
    const line = event.payload
    const type = line.includes('[错误]') ? 'error'
      : line.includes('✓') || line.includes('[完成]') ? 'success'
      : line.includes('[警告]') ? 'warning'
      : 'info'
    addLog(line, type)
    nextTick(() => { if (logContainer.value) logContainer.value.scrollTop = logContainer.value.scrollHeight })
  })

  const queryWorkDir = route.query.workDir
  if (queryWorkDir) {
    workDir.value = queryWorkDir
    persistWorkDir()
    tagWorkspaceModule()
    addLog(`已打开工作区: ${queryWorkDir}`, 'info')
    await loadDirInfo()
  } else if (!workDir.value && typeof window !== 'undefined') {
    const storedWorkDir = getScopedStorageItem(WORKDIR_STORAGE_KEY)
    if (storedWorkDir) {
      workDir.value = storedWorkDir
      tagWorkspaceModule()
      addLog(`已恢复上次工作区: ${storedWorkDir}`, 'info')
      await loadDirInfo()
    }
  }
})

onUnmounted(() => { if (unlistenLog) unlistenLog() })

const canClassify = computed(() => workDir.value && categories.value.length > 0 && pendingFiles.value.length > 0)

function getLogClass(type) {
  return { error: 'text-red-400', success: 'text-green-400', warning: 'text-yellow-400', info: 'text-blue-300' }[type] || 'text-gray-400'
}

function addLog(message, type = 'info') {
  logs.value.push({ time: new Date().toLocaleTimeString(), message, type })
  nextTick(() => { if (logContainer.value) logContainer.value.scrollTop = logContainer.value.scrollHeight })
}

function persistWorkDir() {
  if (typeof window === 'undefined') return
  if (workDir.value) {
    setScopedStorageItem(WORKDIR_STORAGE_KEY, workDir.value)
  } else {
    removeScopedStorageItem(WORKDIR_STORAGE_KEY)
  }
}

function tagWorkspaceModule() {
  if (!workDir.value) return
  const parts = workDir.value.replace(/\\/g, '/').split('/').filter(Boolean)
  const wsId = parts[parts.length - 1]
  if (wsId) {
    apiClient.put(`/api/workspaces/${encodeURIComponent(wsId)}/module`, { module: 'classify' }).catch(() => {})
  }
}

function formatSize(bytes) {
  if (bytes < 1024) return `${bytes}B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)}KB`
  return `${(bytes / 1024 / 1024).toFixed(1)}MB`
}

async function copyText(text, key) {
  try {
    await navigator.clipboard.writeText(text)
    copied.value = key
    setTimeout(() => { copied.value = null }, 2000)
  } catch (e) {
    addLog(`复制失败: ${e}`, 'error')
  }
}

async function selectWorkDir() {
  try {
    const selected = await invoke('select_directory')
    if (!selected) return
    workDir.value = selected
    persistWorkDir()
    tagWorkspaceModule()
    addLog(`已上传工作区: ${selected}`, 'info')
    await loadDirInfo()
  } catch (e) {
    addLog(`上传工作区失败: ${e}`, 'error')
  }
}

async function loadDirInfo() {
  classifyValidationErrors.value = []
  classifyValidationDiagnostics.value = []
  classifyValidationStatus.value = 'idle'
  classifyValidationCheckedAt.value = ''
  classifyValidationChecking.value = false
  showFactorsWorkbookRepair.value = false
  try {
    const cats = await invoke('get_material_categories', { workDir: workDir.value })
    categories.value = cats
    addLog(`发现 ${cats.length} 个材料目录`, 'success')
  } catch (e) {
    addLog(`扫描材料目录失败: ${e}`, 'error')
    categories.value = []
  }
  try {
    const files = await invoke('get_pending_files', { workDir: workDir.value })
    pendingFiles.value = files
    addLog(`样本附件: ${files.length} 个`, 'success')
  } catch (e) {
    addLog(`扫描样本附件失败: ${e}`, 'error')
    pendingFiles.value = []
  }
}

function applyClassifyValidationResult(validation) {
  classifyValidationCheckedAt.value = new Date().toISOString()
  if (validation?.ok) {
    classifyValidationStatus.value = 'valid'
    classifyValidationErrors.value = []
    classifyValidationDiagnostics.value = []
    return true
  }
  classifyValidationStatus.value = 'invalid'
  classifyValidationErrors.value = Array.isArray(validation?.errors) && validation.errors.length > 0
    ? validation.errors
    : ['分类目录格式不符合要求，请检查工作区结构。']
  classifyValidationDiagnostics.value = Array.isArray(validation?.diagnostics) ? validation.diagnostics : []
  return false
}

function handleFactorsWorkbookValidationUpdated(validation) {
  if (applyClassifyValidationResult(validation)) {
    addLog('修复后的 factors.xlsx 已通过统一工作区校验。', 'success')
  } else {
    addLog('factors.xlsx 已保存，但分类前校验仍未完全通过。', 'warning')
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

async function validateClassifyWorkspace(options = {}) {
  const { openRepairOnFail = false, silentSuccess = false } = options
  classifyValidationErrors.value = []
  classifyValidationDiagnostics.value = []
  classifyValidationChecking.value = true
  try {
    const validationRes = await apiClient.post('/api/classify/validate-workdir', { workDir: workDir.value })
    const validation = validationRes?.data || {}
    if (!applyClassifyValidationResult(validation)) {
      if (openRepairOnFail) {
        showFactorsWorkbookRepair.value = true
      }
      addLog(openRepairOnFail ? '工作区校验失败，已打开修复台。' : '工作区校验失败，请先处理后再继续。', 'error')
      classifyValidationErrors.value.forEach((msg) => addLog(`校验失败: ${msg}`, 'error'))
      return false
    }
    const warnings = Array.isArray(validation.warnings) ? validation.warnings : []
    warnings.forEach((msg) => addLog(`校验提示: ${msg}`, 'warning'))
    if (!silentSuccess) {
      addLog('工作区校验通过。', 'success')
    }
    return true
  } catch (e) {
    const errMsg = `工作区校验请求失败: ${e}`
    classifyValidationStatus.value = 'invalid'
    classifyValidationCheckedAt.value = new Date().toISOString()
    classifyValidationErrors.value = [errMsg]
    classifyValidationDiagnostics.value = []
    if (openRepairOnFail) {
      showFactorsWorkbookRepair.value = true
    }
    addLog(errMsg, 'error')
    return false
  } finally {
    classifyValidationChecking.value = false
  }
}

async function runClassifyWorkspaceValidation() {
  await validateClassifyWorkspace()
}

async function goStep2() {
  if (!canClassify.value || isRunning.value) return
  const validationOk = await validateClassifyWorkspace({ openRepairOnFail: true, silentSuccess: true })
  if (!validationOk) return

  currentStep.value = 2
  isRunning.value = true
  result.value = null
  addLog(`开始生成材料分类提示词，最大 ${maxRounds.value} 轮迭代...`, 'info')
  try {
    const res = await invoke('classify_materials', {
      workDir: workDir.value,
      maxRounds: maxRounds.value,
      modelCfgId: selectedModelId.value || null
    })
    result.value = res
    editExtractPrompt.value = res.final_extract_prompt || ''
    editAggregatePrompt.value = res.final_aggregate_prompt || ''
    promptSaved.value = false
    addLog('材料分类提示词生成完成！', 'success')
    currentStep.value = 3
  } catch (e) {
    const errStr = String(e)
    if (errStr.includes('API Key') || errStr.includes('DASHSCOPE') || errStr.includes('OPENAI_API_KEY')) {
      addLog('生成失败: 未配置可用的 API 密钥，请前往【设置】页面配置默认 API Key 或模型专属 API Key', 'error')
    } else {
      addLog(`生成失败: ${e}`, 'error')
    }
    currentStep.value = 1
  } finally {
    isRunning.value = false
  }
}

async function runTestPrompt(type) {
  const content = type === 'extract' ? editExtractPrompt.value : editAggregatePrompt.value
  if (!content.trim()) {
    addLog('提示词内容为空，请先填写提示词', 'warning')
    return
  }
  isTesting.value = true
  testingType.value = type
  testResult.value = null
  addLog(`[测试] 开始测试 ${type === 'extract' ? '分类信息提取' : '附件归集'} 提示词...`, 'info')
  try {
    const res = await invoke('test_classify_prompt', {
      workDir: workDir.value,
      promptType: type,
      promptContent: content,
      modelCfgId: selectedModelId.value || null
    })
    testResult.value = res
    activeReviewTab.value = 'test'
    addLog(`[测试] 测试完成，结果: ${res.pass ? '✓ 通过' : '✗ 未通过'}`, res.pass ? 'success' : 'warning')
  } catch (e) {
    addLog(`[测试] 测试失败: ${e}`, 'error')
  } finally {
    isTesting.value = false
    testingType.value = ''
  }
}

async function savePrompts() {
  try {
    if (editExtractPrompt.value) {
      const path = workDir.value + '/最新分类信息提取提示词.txt'
      await invoke('write_file', { path, content: editExtractPrompt.value })
    }
    if (editAggregatePrompt.value) {
      const path = workDir.value + '/最新分类附件归集提示词.txt'
      await invoke('write_file', { path, content: editAggregatePrompt.value })
    }
    promptSaved.value = true
    addLog('✓ 提示词已保存，可使用新提示词重新分类', 'success')
  } catch (e) {
    addLog(`保存提示词失败: ${e}`, 'error')
  }
}

function handleStepNav(step) {
  if (step > maxReachableStep.value) return
  if (isRunning.value) return
  currentStep.value = step
}

async function goStep2Again() {
  result.value = null
  editExtractPrompt.value = ''
  editAggregatePrompt.value = ''
  promptSaved.value = false
  testResult.value = null
  activeReviewTab.value = 'detail'
  currentStep.value = 2
  await goStep2()
}

function confirmAndGoStep4() {
  addLog('✓ 人工审核通过，分类提示词结果已确认完成！', 'success')
  currentStep.value = 4
}

async function openResult() {
  try {
    await invoke('open_classified_dir', { workDir: workDir.value })
  } catch (e) {
    addLog(`打开目录失败: ${e}`, 'error')
  }
}

async function downloadResultZip() {
  if (!workDir.value) return
  try {
    apiClient.open('/api/classify/download-result', { workDir: workDir.value })
    addLog('开始下载分类提示词结果 ZIP。', 'success')
  } catch (e) {
    addLog(`下载分类结果失败: ${e}`, 'error')
  }
}

function clear() {
  currentStep.value = 1
  workDir.value = ''
  persistWorkDir()
  categories.value = []
  pendingFiles.value = []
  logs.value = []
  result.value = null
  editExtractPrompt.value = ''
  editAggregatePrompt.value = ''
  promptSaved.value = false
  testResult.value = null
  activeReviewTab.value = 'detail'
  classifyValidationErrors.value = []
  classifyValidationDiagnostics.value = []
  classifyValidationStatus.value = 'idle'
  classifyValidationCheckedAt.value = ''
  classifyValidationChecking.value = false
  showFactorsWorkbookRepair.value = false
  if (availableModels.value.length > 0) selectedModelId.value = availableModels.value[0].id
}
</script>
