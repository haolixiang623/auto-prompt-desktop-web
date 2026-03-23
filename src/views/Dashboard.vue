<template>
  <div
    ref="containerRef"
    class="relative w-full h-full overflow-hidden bg-gray-950 select-none"
    @mousemove="onMouseMove"
    @mouseleave="onMouseLeave"
  >
    <!-- 鼠标跟随光晕 -->
    <div
      class="pointer-events-none fixed z-0 rounded-full transition-opacity duration-300"
      :style="spotlightStyle"
    ></div>

    <!-- 背景网格 -->
    <div class="absolute inset-0 z-0 opacity-10"
      style="background-image: linear-gradient(rgba(255,255,255,.05) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,.05) 1px, transparent 1px); background-size: 40px 40px;">
    </div>

    <!-- 主内容 -->
    <div class="relative z-10 flex flex-col h-full px-10 py-8">

      <!-- 顶部标题 -->
      <div class="mb-10">
        <div class="flex items-center gap-3 mb-2">
          <div class="w-2 h-2 rounded-full bg-blue-400 animate-pulse"></div>
          <span class="text-xs font-mono text-blue-400 tracking-widest uppercase">Auto-Prompt Desktop</span>
        </div>
        <h1 class="text-4xl font-bold text-white leading-tight">智能提示词<br>
          <span class="bg-gradient-to-r from-blue-400 via-violet-400 to-purple-400 bg-clip-text text-transparent">工具集</span>
        </h1>
        <p class="text-gray-400 mt-3 text-sm max-w-sm">基于 Qwen VL 大模型，自动生成文档要素提取提示词，提升数据录入效率</p>
      </div>

      <!-- 功能卡片组 -->
      <div class="flex gap-4 flex-1 min-h-0 items-start">
        <div
          v-for="(card, i) in cards"
          :key="card.id"
          class="relative rounded-2xl overflow-hidden cursor-pointer transition-all duration-500 ease-[cubic-bezier(0.34,1.56,0.64,1)] flex-shrink-0"
          :style="cardStyle(i)"
          @mouseenter="expandCard(i)"
          @mouseleave="collapseCard"
          @click="card.route && $router.push(card.route)"
        >
          <!-- 卡片背景渐变 -->
          <div class="absolute inset-0" :style="{ background: card.bg }"></div>

          <!-- 卡片背景装饰圆 -->
          <div class="absolute -right-8 -top-8 w-40 h-40 rounded-full opacity-20"
            :style="{ background: card.accent }"></div>
          <div class="absolute -left-4 -bottom-8 w-32 h-32 rounded-full opacity-10"
            :style="{ background: card.accent }"></div>

          <!-- 卡片内容 -->
          <div class="relative z-10 p-6 h-full flex flex-col justify-between" style="min-height: 260px;">
            <!-- 图标 -->
            <div class="w-12 h-12 rounded-xl flex items-center justify-center mb-4 flex-shrink-0"
              :style="{ background: card.iconBg }">
              <svg class="w-6 h-6" :style="{ color: card.iconColor }" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" :d="card.icon"/>
              </svg>
            </div>

            <!-- 标签 -->
            <div class="text-xs font-mono tracking-widest uppercase mb-2 flex-shrink-0"
              :style="{ color: card.labelColor }">{{ card.label }}</div>

            <!-- 标题 -->
            <h3 class="text-xl font-bold text-white mb-2 flex-shrink-0">{{ card.title }}</h3>

            <!-- 描述（展开时显示） -->
            <p class="text-sm leading-relaxed flex-1 transition-all duration-500 overflow-hidden"
              :style="{ color: card.descColor, maxHeight: expandedIdx === i ? '120px' : '0px', opacity: expandedIdx === i ? 1 : 0 }">
              {{ card.desc }}
            </p>

            <!-- 步骤标签（展开时显示） -->
            <div class="flex flex-wrap gap-1.5 mt-3 transition-all duration-500"
              :style="{ opacity: expandedIdx === i ? 1 : 0, transform: expandedIdx === i ? 'translateY(0)' : 'translateY(8px)' }">
              <span v-for="step in card.steps" :key="step"
                class="text-xs px-2 py-0.5 rounded-full font-medium"
                :style="{ background: card.stepBg, color: card.stepColor }">
                {{ step }}
              </span>
            </div>

            <!-- 箭头 -->
            <div class="flex items-center justify-between mt-4 flex-shrink-0">
              <span class="text-xs" :style="{ color: card.labelColor }">{{ card.meta }}</span>
              <div class="w-8 h-8 rounded-full flex items-center justify-center transition-all duration-300"
                :style="{ background: expandedIdx === i ? card.accent : 'rgba(255,255,255,0.1)' }">
                <svg class="w-4 h-4 text-white transition-transform duration-300"
                  :style="{ transform: expandedIdx === i ? 'translateX(2px)' : 'none' }"
                  fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/>
                </svg>
              </div>
            </div>
          </div>

          <!-- 卡片悬浮光效 -->
          <div class="absolute inset-0 opacity-0 transition-opacity duration-300 pointer-events-none"
            :style="{ opacity: expandedIdx === i ? 0.08 : 0, background: `radial-gradient(ellipse at 50% 0%, white, transparent 70%)` }">
          </div>
        </div>
      </div>

      <!-- 底部快速统计 -->
      <div class="mt-6 grid grid-cols-4 gap-3">
        <div v-for="stat in stats" :key="stat.label"
          class="rounded-xl px-4 py-3 flex items-center gap-3 border border-white/5"
          style="background: rgba(255,255,255,0.04);">
          <div class="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
            :style="{ background: stat.iconBg }">
            <svg class="w-4 h-4" :style="{ color: stat.color }" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" :d="stat.icon"/>
            </svg>
          </div>
          <div>
            <div class="text-xs text-gray-500">{{ stat.label }}</div>
            <div class="text-base font-bold" :style="{ color: stat.color }">{{ stat.value }}</div>
          </div>
        </div>
      </div>

    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const containerRef = ref(null)
const mouse = ref({ x: -9999, y: -9999 })
const expandedIdx = ref(null)

function onMouseMove(e) {
  const rect = containerRef.value?.getBoundingClientRect()
  if (!rect) return
  mouse.value = { x: e.clientX, y: e.clientY }
}
function onMouseLeave() {
  mouse.value = { x: -9999, y: -9999 }
}

const spotlightStyle = computed(() => ({
  width: '600px',
  height: '600px',
  left: mouse.value.x - 300 + 'px',
  top: mouse.value.y - 300 + 'px',
  background: 'radial-gradient(circle, rgba(99,102,241,0.15) 0%, rgba(139,92,246,0.08) 40%, transparent 70%)',
  opacity: mouse.value.x < 0 ? 0 : 1,
}))

function expandCard(i) { expandedIdx.value = i }
function collapseCard() { expandedIdx.value = null }

function cardStyle(i) {
  const isExpanded = expandedIdx.value === i
  const hasExpanded = expandedIdx.value !== null
  const baseW = isExpanded ? 320 : hasExpanded ? 160 : 220
  return {
    width: baseW + 'px',
    height: isExpanded ? '380px' : '260px',
    filter: hasExpanded && !isExpanded ? 'brightness(0.7)' : 'brightness(1)',
  }
}

const cards = [
  {
    id: 'generate',
    route: '/generate',
    label: '01 // EXTRACT',
    title: '要素提示词生成',
    desc: '基于 Qwen VL 视觉大模型，智能分析文档图片，自动生成高质量的要素提取提示词，支持多材料批量生成与验证。',
    meta: '5步引导流程',
    steps: ['选择材料', '批量生成', '验证提取', '要素JSON'],
    bg: 'linear-gradient(135deg, #1e1b4b 0%, #312e81 50%, #1e3a5f 100%)',
    accent: '#6366f1',
    iconBg: 'rgba(99,102,241,0.2)',
    iconColor: '#818cf8',
    labelColor: '#818cf8',
    descColor: '#a5b4fc',
    stepBg: 'rgba(99,102,241,0.2)',
    stepColor: '#a5b4fc',
    icon: 'M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z',
  },
  {
    id: 'classify',
    route: '/classify',
    label: '02 // CLASSIFY',
    title: '材料智能分类',
    desc: '上传无序的材料附件，AI自动识别并归集到对应材料目录，支持迭代优化分类提示词，人工审核确认。',
    meta: '4步引导流程',
    steps: ['上传工作区', '执行分类', '人工审核', '确认完成'],
    bg: 'linear-gradient(135deg, #064e3b 0%, #065f46 50%, #1a3a2a 100%)',
    accent: '#10b981',
    iconBg: 'rgba(16,185,129,0.2)',
    iconColor: '#34d399',
    labelColor: '#34d399',
    descColor: '#6ee7b7',
    stepBg: 'rgba(16,185,129,0.2)',
    stepColor: '#6ee7b7',
    icon: 'M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z',
  },
  {
    id: 'review-rule',
    route: '/review-rule',
    label: '03 // RULES',
    title: '审查规则生成',
    desc: '基于 factors.xlsx 的审查要点列，自动推断规则类型（规则对比/大模型/Groovy脚本），生成符合导入规范的审查规则 JSON。',
    meta: '支持LLM增强推理',
    steps: ['读取Excel', '推断规则类型', '构建条件', '导出JSON'],
    bg: 'linear-gradient(135deg, #1c1917 0%, #292524 50%, #1a1818 100%)',
    accent: '#f59e0b',
    iconBg: 'rgba(245,158,11,0.2)',
    iconColor: '#fbbf24',
    labelColor: '#fbbf24',
    descColor: '#fde68a',
    stepBg: 'rgba(245,158,11,0.15)',
    stepColor: '#fde68a',
    icon: 'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4',
  },
  {
    id: 'cases',
    route: '/cases',
    label: '04 // LIBRARY',
    title: '提示词库',
    desc: '浏览、搜索和管理历史生成的提示词案例，复用优质提示词，持续积累知识库。',
    meta: '案例检索与管理',
    steps: ['浏览案例', '搜索过滤', '复用提示词'],
    bg: 'linear-gradient(135deg, #1e1b2e 0%, #2d1b69 50%, #1a1a2e 100%)',
    accent: '#8b5cf6',
    iconBg: 'rgba(139,92,246,0.2)',
    iconColor: '#a78bfa',
    labelColor: '#a78bfa',
    descColor: '#c4b5fd',
    stepBg: 'rgba(139,92,246,0.2)',
    stepColor: '#c4b5fd',
    icon: 'M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10',
  },
  {
    id: 'rule-library',
    route: '/rule-library',
    label: '05 // RULES DB',
    title: '审查规则库',
    desc: '管理导入的审查规则 JSON，支持按材料名称/要点名称搜索，查看完整规则结构与 JSON 模板参考。',
    meta: '规则检索与管理',
    steps: ['导入JSON', '搜索查询', '模板参考'],
    bg: 'linear-gradient(135deg, #0c1a2e 0%, #0f2a4a 50%, #0a1628 100%)',
    accent: '#0ea5e9',
    iconBg: 'rgba(14,165,233,0.2)',
    iconColor: '#38bdf8',
    labelColor: '#38bdf8',
    descColor: '#7dd3fc',
    stepBg: 'rgba(14,165,233,0.15)',
    stepColor: '#7dd3fc',
    icon: 'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01',
  },
]

const stats = [
  { label: '功能模块', value: '5 个', color: '#818cf8', iconBg: 'rgba(99,102,241,0.15)', icon: 'M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z' },
  { label: '支持模型', value: 'Qwen VL', color: '#34d399', iconBg: 'rgba(16,185,129,0.15)', icon: 'M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17H3a2 2 0 01-2-2V5a2 2 0 012-2h14a2 2 0 012 2v10a2 2 0 01-2 2h-2' },
  { label: '文件格式', value: 'PDF / 图片', color: '#fbbf24', iconBg: 'rgba(245,158,11,0.15)', icon: 'M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z' },
  { label: '导出格式', value: 'JSON / TXT', color: '#a78bfa', iconBg: 'rgba(139,92,246,0.15)', icon: 'M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4' },
]
</script>
