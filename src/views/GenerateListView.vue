<template>
  <WorkspaceListView
    title="要素提示词"
    subtitle="历史工作区列表，点击打开或新增生成提示词"
    createRoute="/generate/new"
    createLabel="新增提示词生成"
    iconBgClass="bg-amber-100"
    iconClass="text-amber-600"
    iconPath="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
    module="generate"
    @open="handleOpen"
  />
</template>

<script setup>
import { useRouter } from 'vue-router'
import WorkspaceListView from './WorkspaceListView.vue'

const router = useRouter()

function handleOpen(ws) {
  router.push({ path: '/generate/new', query: { workDir: ws.rootPath } })
}
</script>
